"""The MTDI engine: sources in, one MTDI packet out.

    line or values ─▶ protocol ─▶ channel mapping (keys, scale, offset, transform)
                   ─▶ 00 Validation Chamber   (presence, freshness, timing, range)
                   ─▶ 01 Environmental Intel. (baseline, deviation, SNR, transients)
                   ─▶ core fusion             (8 weighted factors per channel)
                   ─▶ 02 NVTRA                (interpretation, warnings)
                   ─▶ packet                  (what 03 I³ draws; 04 Aether rides along)

Thread safe: adapters call ingest_* from their own threads, the interface calls
snapshot() from the web server. Everything is pure Python, so the engine runs on
a single-board computer, a laptop or a server alike.
"""
from collections import deque
import math
import pathlib
import threading
import time

from . import core
from .fusion import Calibration, drift_summary, fuse
from .pillars import aether, nvtra
from .pillars.environment import ChannelEnvironment, EnvironmentLibrary
from .pillars.validation import ChannelEvidence, clipped as is_clipped
from .project import offset_of, scale_of
from .protocol import ProtocolError, parse_line

SPARK_POINTS = 120


class _Channel:
    def __init__(self, spec, window):
        self.spec = spec
        self.env = ChannelEnvironment(spec, window)
        self.evidence = ChannelEvidence(spec)
        self.rms = [deque(maxlen=int(spec["window"])) for _ in spec["keys"]]
        cal = spec.get("calibration")
        self.cal = None
        if cal:
            self.cal = Calibration(**{k: cal[k] for k in ("gain", "offset", "temp_coeff", "temp_ref",
                                                          "residual_sd", "method", "n") if k in cal})
            self.cal_temp_key = cal.get("temperature_key")
            self.cal_checks = deque(maxlen=20)   # reference - calibrated value, newest last
        self.history = deque(maxlen=600)      # (t, deviation) for correlation and sparklines
        self.value = None                     # latest physical value (scalar or vector)
        self.raw = None


class Engine:
    def __init__(self, project, clock=time.monotonic):
        self.project = project
        self.clock = clock
        self.lock = threading.RLock()
        self.weights = core.weights_for(project)
        window = project["environment"]["window"]
        self.channels = {c["id"]: _Channel(c, window) for c in project["channels"]}
        self.by_source = {}
        for c in project["channels"]:
            for sid in c["sources"]:
                self.by_source.setdefault(sid, []).append(c["id"])
        self.sources = {s["id"]: {"id": s["id"], "adapter": s["adapter"], "state": "idle", "message": "",
                                  "lines": 0, "rejected": 0, "last_error": None}
                        for s in project["sources"]}
        self.environments = EnvironmentLibrary(pathlib.Path(project.get("_dir", ".")) / "environments")
        self.events = deque(maxlen=50)
        self.recorders = []
        self.sequence = 0
        self._corr_cache = (None, [])

    # ── input ────────────────────────────────────────────────────────────────
    def ingest_line(self, source_id, line, data_source="HARDWARE"):
        """Parse one protocol line from a source. Malformed lines are counted and dropped."""
        try:
            values = parse_line(line)
        except ProtocolError as error:
            with self.lock:
                src = self.sources[source_id]
                src["rejected"] += 1
                src["last_error"] = str(error)
            return 0
        return self.ingest_values(source_id, values, data_source)

    def ingest_values(self, source_id, values, data_source="HARDWARE"):
        """Feed {KEY: number} from a source. Returns how many channels it updated."""
        if source_id not in self.sources:
            raise KeyError(f"unknown source {source_id}")
        t, wall = self.clock(), time.time()
        updated = 0
        with self.lock:
            src = self.sources[source_id]
            src["lines"] += 1
            src["last_rx"] = t
            if src["state"] in ("idle", "waiting"):
                src["state"] = "receiving"
            for rec in self.recorders:
                rec(wall, source_id, values, data_source)
            for cid in self.by_source.get(source_id, ()):
                ch = self.channels[cid]
                spec = ch.spec
                if not all(k in values for k in spec["keys"]):
                    continue
                raw = [values[k] for k in spec["keys"]]
                clip = is_clipped(spec, raw)
                phys = [r * scale_of(spec, i) + offset_of(spec, i) for i, r in enumerate(raw)]
                if spec["transform"] == "ac_rms":
                    for buf, v in zip(ch.rms, phys):
                        buf.append(v)
                    if len(ch.rms[0]) < max(4, ch.rms[0].maxlen // 2):
                        ch.evidence.record(t, wall, clip, data_source, values.get("_SEQ"))
                        continue
                    phys = [_ac_rms(buf) for buf in ch.rms]
                if ch.cal is not None:
                    temperature = values.get(ch.cal_temp_key) if ch.cal_temp_key else None
                    phys = [ch.cal.apply(phys[0], temperature)]
                state = ch.env.update(phys, t, valid=not clip)
                ch.evidence.record(t, wall, clip, data_source, values.get("_SEQ"))
                ch.value = phys if len(phys) > 1 else phys[0]
                ch.raw = raw
                if not ch.history or t - ch.history[-1][0] >= 0.09:
                    ch.history.append((t, state["deviation"]))
                updated += 1
            self.sequence += 1
        return updated

    def set_source_state(self, source_id, state, message=""):
        with self.lock:
            self.sources[source_id].update(state=state, message=message)

    # ── environmental intelligence actions ──────────────────────────────────
    def _targets(self, channel):
        if channel in (None, "", "all"):
            return list(self.channels.values())
        if channel not in self.channels:
            raise KeyError(f"unknown channel {channel}")
        return [self.channels[channel]]

    def learn(self, channel=None):
        with self.lock:
            for ch in self._targets(channel):
                ch.env.learn()
            self._event("environment", f"Re-learning baseline: {channel or 'all channels'}")

    def check_calibration(self, channel, reference):
        """Record one spot check of a calibrated channel against a reference instrument."""
        if isinstance(reference, bool):   # JSON true/false would otherwise become 1.0/0.0
            raise ValueError("reference must be a number")
        try:
            reference = float(reference)
        except (TypeError, ValueError):
            raise ValueError("reference must be a number") from None
        if not math.isfinite(reference) or abs(reference) > 1e12:
            raise ValueError("reference must be a finite number within ±1e12")
        with self.lock:
            if channel not in self.channels:
                raise KeyError(f"unknown channel {channel}")
            ch = self.channels[channel]
            if ch.cal is None:
                raise ValueError(f"{channel} has no calibration to check")
            if ch.value is None:
                raise ValueError(f"{channel} has no reading yet")
            # A reference taken now must meet a reading taken now, from real hardware.
            evidence = ch.evidence.snapshot(self.clock())
            if evidence["state"] != "connected":
                raise ValueError(f"{channel} is {evidence['state']}; check it while it is live")
            if evidence["clipped"]:
                raise ValueError(f"{channel} is clipping; its value is only a bound, so it cannot be checked")
            if ch.evidence.data_source == "SIMULATED":
                raise ValueError(f"{channel} is showing SIMULATED data; a calibration check needs real readings")
            ch.cal_checks.append(reference - ch.value)
            summary = drift_summary(ch.cal_checks, ch.cal.residual_sd)
            self._event("validation", f"{ch.spec['label']}: calibration check {reference - ch.value:+.3g} "
                                      f"{ch.spec['unit']}" + (" · DRIFT" if summary["drift"] else ""))
            return summary

    def lock_baseline(self, channel=None, frozen=True):
        with self.lock:
            for ch in self._targets(channel):
                ch.env.lock(frozen)
            self._event("environment", f"Baseline {'locked' if frozen else 'unlocked'}: {channel or 'all channels'}")

    def save_environment(self, name):
        with self.lock:
            # An optional channel that has never reported (a sensor this machine does not have)
            # is left out of the environment instead of blocking it; it is named in the record.
            absent = [cid for cid, ch in self.channels.items() if ch.spec["optional"] and ch.evidence.count == 0]
            present = {cid: ch for cid, ch in self.channels.items() if cid not in absent}
            if not present:
                raise ValueError("refused: no channel has reported yet")
            sources = {cid: ch.evidence.data_source or "—" for cid, ch in present.items()}
            record = self.environments.save(name, {cid: ch.env for cid, ch in present.items()}, sources,
                                            absent=absent)
            self._event("environment", f"Saved environment '{name}'" + (f" (without {', '.join(absent)})" if absent else ""))
            return record

    def load_environment(self, name):
        with self.lock:
            record = self.environments.load(name)
            missing = [cid for cid in self.channels if cid not in record["channels"]]
            for cid, ref in record["channels"].items():
                if cid in self.channels and len(ref["baseline"]) == len(self.channels[cid].env.axes):
                    self.channels[cid].env.pin(ref)
            self._event("environment", f"Comparing against saved environment '{name}'"
                        + (f" (not in it: {', '.join(missing)})" if missing else ""))
            return record

    def _fused(self, channels):
        """Inverse-variance estimate from the inputs that are connected right now.

        Each input's standard deviation, in order of trust: the manifest's fused[].sd, the
        calibration's residual, the live noise the environment measured, the noise floor."""
        out = {}
        for f in self.project.get("fused") or []:
            readings, used = [], []
            for cid in f["inputs"]:
                ch, spec = channels[cid], self.channels[cid].spec
                if ch["evidence"]["state"] != "connected" or ch["value"] is None \
                        or not math.isfinite(float(ch["value"])):
                    continue
                noise = ch["environment"].get("noise")
                noise = noise[0] if isinstance(noise, list) else noise
                sd, basis = f["sd"].get(cid), "manifest"
                if not sd:
                    sd, basis = (ch.get("calibration") or {}).get("residual_sd"), "calibration"
                if not sd:
                    sd, basis = noise, "measured noise"
                # Measured noise or a calibration residual can be 0, tiny or huge; squaring must stay a
                # usable variance or fuse() would raise and take the whole snapshot down with it.
                if not sd or not math.isfinite(sd) or not 1e-150 < float(sd) < 1e150:
                    sd, basis = spec["noise_floor"], "noise floor"
                readings.append((float(ch["value"]), float(sd) ** 2))
                used.append({"id": cid, "value": ch["value"], "sd": sd, "basis": basis})
            entry = {"id": f["id"], "label": f["label"], "unit": f["unit"], "method": f["method"],
                     "inputs": used, "of": len(f["inputs"]), "value": None, "sd": None}
            if readings:
                value, variance = fuse(readings)
                entry.update(value=value, sd=math.sqrt(variance))
            out[f["id"]] = entry
        return out

    def _event(self, kind, message):
        self.events.append({"t": time.time(), "kind": kind, "message": message})

    # ── output ───────────────────────────────────────────────────────────────
    def snapshot(self):
        now = self.clock()
        relock = self.project["environment"].get("auto_relock_after")
        with self.lock:
            # Histories only change on ingest, which bumps the sequence: a UI polling faster than
            # data arrives gets the same correlation without recomputing every pair.
            if self._corr_cache[0] != self.sequence:
                histories = {cid: list(ch.history) for cid, ch in self.channels.items()}
                self._corr_cache = (self.sequence, core.correlation(histories))
            corr = [dict(m, channels=list(m["channels"])) for m in self._corr_cache[1]]  # callers may mutate their copy
            positive = max([max(0.0, m["coefficient"]) for m in corr] or [0.0])
            channels = {}
            for cid, ch in self.channels.items():
                spec = ch.spec
                env = ch.env.snapshot(now)
                if relock and env["stale"] and env["stale_for"] >= relock and not env["frozen"]:
                    ch.env.learn()
                    self._event("environment", f"{spec['label']}: quiet level moved, baseline re-learned")
                    env = ch.env.snapshot(now)
                evidence = ch.evidence.snapshot(now, env.get("noise"))
                terms = core.channel_terms(spec, evidence, env, positive)
                active = evidence["state"] == "connected"
                value = ch.value
                magnitude = math.sqrt(sum(v * v for v in value)) if isinstance(value, list) else value
                channels[cid] = {
                    "id": cid, "label": spec["label"], "unit": spec["unit"], "domain": spec["domain"],
                    "kind": spec["kind"], "axes": spec["axes"], "optional": spec["optional"],
                    "value": value, "magnitude": magnitude, "raw": ch.raw,
                    "evidence": evidence, "environment": env,
                    "terms": {k: v * 100 for k, v in terms.items()},
                    "score": core.score(terms, self.weights, active),
                    "spark": [round(d, 6) for _, d in list(ch.history)[-SPARK_POINTS:]],
                }
                if ch.cal is not None:
                    channels[cid]["calibration"] = {"method": ch.cal.method, "residual_sd": ch.cal.residual_sd,
                                                    "n": ch.cal.n, "temperature_key": ch.cal_temp_key,
                                                    "checks": drift_summary(ch.cal_checks, ch.cal.residual_sd)}
            counted = [c for c in channels.values() if not (c["optional"] and c["evidence"]["state"] != "connected")]
            live = [c for c in counted if c["evidence"]["state"] == "connected"]
            fusion = nvtra.interpret(self.project, channels)
            fusion.update({
                "score": sum(c["score"] for c in counted) / len(counted) if counted else 0.0,
                "completeness": 100.0 * len(live) / len(counted) if counted else 0.0,
                "weights": self.weights, "correlation": corr, "method": core.METHOD,
            })
            return {
                "mtdi": self.project.get("mtdi", "5.0"), "sequence": self.sequence, "timestamp": time.time(),
                "project": self.project["project"], "channels": channels, "fusion": fusion,
                "fused": self._fused(channels),
                "sources": {k: dict(v, age=(now - v["last_rx"]) if v.get("last_rx") else None)
                            for k, v in self.sources.items()},
                "environments": self.environments.names(), "events": list(self.events),
                "aether": aether.record(self.project),
            }


def _ac_rms(buf):
    values = list(buf)
    mean = sum(values) / len(values)
    return math.sqrt(sum((v - mean) ** 2 for v in values) / len(values))
