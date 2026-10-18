"""The MTDI engine: sources in, one MTDI packet out.

    line or values ─▶ protocol ─▶ channel mapping (keys, scale, offset, transform)
                   ─▶ 00 Validation Chamber   (presence, freshness, timing, range)
                   ─▶ 01 Environmental Intel. (baseline, deviation, SNR, transients)
                   ─▶ core fusion             (8 weighted factors per channel)
                   ─▶ 02 NVTRA                (interpretation, warnings)
                   ─▶ packet                  (what 03 I³ draws; 04 Aether rides along)

Thread safe: adapters call ingest_* from their own threads, the interface calls
snapshot() from the web server. Everything is pure Python, so the engine runs on
a Raspberry Pi, a laptop or a server alike.
"""
from collections import deque
import math
import pathlib
import threading
import time

from . import core
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

    def _event(self, kind, message):
        self.events.append({"t": time.time(), "kind": kind, "message": message})

    # ── output ───────────────────────────────────────────────────────────────
    def snapshot(self):
        now = self.clock()
        relock = self.project["environment"].get("auto_relock_after")
        with self.lock:
            histories = {cid: list(ch.history) for cid, ch in self.channels.items()}
            corr = core.correlation(histories)
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
                "sources": {k: dict(v, age=(now - v["last_rx"]) if v.get("last_rx") else None)
                            for k, v in self.sources.items()},
                "environments": self.environments.names(), "events": list(self.events),
                "aether": aether.record(self.project),
            }


def _ac_rms(buf):
    values = list(buf)
    mean = sum(values) / len(values)
    return math.sqrt(sum((v - mean) ** 2 for v in values) / len(values))
