"""D4 live service: runs the d4 engine over the instrument's real sample streams.

Produces the MTDI 2.0 packet the interface shows: per channel z-scores and activity
scores, cross sensor consensus, weighted MTDI, a confidence built from measurable
factors, linefreq harmonics from the 860 SPS Ch2 ring, CH3 analysis of the latest
sweep, transient features, noise characterisation, calibration health, correlation,
an environmental fingerprint and an event log. Recomputed at most every 2 s.
"""
from __future__ import annotations

import json
import math
import os
import threading
import time
from collections import deque

import numpy as np

from . import d4


def longest_contiguous(rows, gap_factor=4.0):
    """Rows are (t, ...) at a nominal rate with gaps between hardware blocks; return the
    longest run without a gap larger than gap_factor × the median step."""
    if len(rows) < 3:
        return list(rows)
    t = np.array([r[0] for r in rows])
    dt = np.diff(t)
    step = float(np.median(dt))
    if step <= 0:
        return list(rows)
    cuts = np.flatnonzero(dt > gap_factor * step) + 1
    bounds = [0] + cuts.tolist() + [len(rows)]
    best = max(range(len(bounds) - 1), key=lambda i: bounds[i + 1] - bounds[i])
    return list(rows[bounds[best]:bounds[best + 1]])


def ch3_packet(sp, threshold_db, level_unit=None):
    """The D4 analysis of the latest channel 3 sweep. The radio's sweep is in hertz and dBm. A
    fed sweep keeps its own x unit, and is analysed only when its levels are in decibels: the
    floor threshold and the occupied width are decibel arithmetic, meaningless on other units."""
    xu = sp.get("x_unit")
    meta = {"trusted": sp["trusted"], "status": sp["status"], "x_unit": xu}
    if xu is None:
        return dict(d4.ch3_analysis(sp["freqs"], sp["levels"], threshold_db), **meta)
    if level_unit is None:
        from .content import T
        level_unit = T("ch3.unit")
    meta["level_unit"] = level_unit
    if "db" not in str(level_unit).lower():
        return dict(meta, error=f"The sweep analysis needs levels in decibels; this feed's levels are in {level_unit}, "
                                f"so only the sweep itself is shown.")
    return dict(d4.ch3_analysis(sp["freqs"], sp["levels"], threshold_db, digits=6), **meta)


class D4Service:
    def __init__(self, ns, engine):
        self.ns = ns
        self.engine = engine
        self.lock = threading.Lock()
        self.compute_lock = threading.Lock()   # one compute at a time: it appends to the histories below
        self.config, self.config_error = d4.load_config()
        self.packet = None
        self.computed_at = 0.0
        self.events = deque(maxlen=200)
        self.event_seq = 0
        self.open_event = None
        self.fingerprint_ref = None
        self.mtdi_history = deque(maxlen=600)   # (t, mtdi) for trend and repeatability
        self.last_calibration = None
        self.transient_times = deque(maxlen=200)
        self.store_dir = d4.config_path().parent
        self.references = self._load_json("reference_profiles.json", {})
        self.trials = self._load_json("validation_trials.json", [])
        self.repeat_run = None
        self.fingerprint_ref = self._load_json("fingerprint_reference.json", None)
        self.model = self._load_json("classifier.json", None)
        self._filter_state = None
        self.compute_seconds = None
        ns["_d4_config"] = lambda: self.config
        ns["_d4_filter"] = None
        self._apply_runtime_config()
        # the engine runs on its own clock so events, auto bursts and stores do not depend on
        # a browser being open; snapshots are cached, so page refreshes cost nothing extra
        threading.Thread(target=self._loop, name="d4-engine", daemon=True).start()

    def _loop(self):
        time.sleep(15)
        while True:
            try:
                self.snapshot()
            except Exception:
                pass
            time.sleep(5)

    # ── persistence ──────────────────────────────────────────────────────────
    def _load_json(self, name, default):
        path = self.store_dir / name
        try:
            return json.loads(path.read_text(encoding="utf8")) if path.exists() else default
        except Exception:
            return default

    def _save_json(self, name, data):
        self.store_dir.mkdir(parents=True, exist_ok=True)
        tmp = self.store_dir / (name + ".tmp")
        tmp.write_text(json.dumps(data, indent=1, allow_nan=False), encoding="utf8")
        os.replace(tmp, self.store_dir / name)

    def _apply_runtime_config(self):
        """Push config choices into the running instrument: baseline method and the optional
        ch1 filter (labelled, off unless filter.apply is true)."""
        cfg = self.config
        try:
            self.engine.set_baseline_method(cfg.get("baseline_method", "moving_median"), cfg.get("baseline_alpha", 0.025))
        except Exception:
            pass
        f = cfg.get("filter") or {}
        if f.get("apply") and f.get("b") and f.get("a"):
            b = np.asarray(f["b"], dtype=float); a = np.asarray(f["a"], dtype=float)
            xs = deque([0.0] * b.size, maxlen=b.size); ys = deque([0.0] * max(1, a.size - 1), maxlen=max(1, a.size - 1))
            def run(v):
                xs.appendleft(v)
                y = float(np.dot(b, np.array(xs)) - (np.dot(a[1:], np.array(ys)) if a.size > 1 else 0.0)) / a[0]
                ys.appendleft(y)
                return y
            self.ns["_d4_filter"] = run
        else:
            self.ns["_d4_filter"] = None

    # ── configuration ────────────────────────────────────────────────────────
    def reload_config(self):
        # after any compute in flight: its packet, made with the old config, is published first and
        # then cleared here, so no caller reuses it (lock order: compute_lock, then lock)
        with self.compute_lock, self.lock:
            self.config, self.config_error = d4.load_config()
            self.packet = None
        return self.config, self.config_error

    def update_config(self, patch):
        with self.lock:
            cfg = dict(self.config)
            for key, value in (patch or {}).items():
                if key in d4.CONFIG_DEFAULT and key not in ("version", "source"):
                    cfg[key] = value
            path = d4.save_config(cfg)
        self.reload_config()
        self._apply_runtime_config()
        # the ch1probe reader picks the new offsets and matrix up on its next sample
        try:
            with self.ns["c1_cmd_lock"]:
                self.ns["c1_cmd"]["reload_calibration"] = True
        except Exception:
            pass
        return path

    # The channel names differ between the acquisition side and the analysis side.
    BURST_ANALYSIS_CHANNEL = {"ch2f": "ch2", "current": "current"}

    def request_burst(self, samples=3440, channel="ch2f", seconds=None, rate=None):
        """Ask acquisition for one contiguous block, and warn the engine first.

        `samples` used to be a fixed 3440, chosen as 4 s at the SRC2's
        CONFIGURED 860 SPS. The hardware does not achieve that: measured on this host
        it runs at 306.7 SPS, so 3440 samples held the ADC for 11.2 s, not 4 s -
        matching the 12.5 s outage seen on both ADC channels every 60 s. The window
        the linefreq analysis actually got was nearly three times the one advertised.
        Sizing from the achieved rate makes "4 seconds" mean four seconds.
        """
        rate = rate if rate else self._achieved_rate(channel)
        if seconds is None and rate:
            seconds = float(samples) / 860.0          # what the caller meant
        if seconds and rate:
            samples = max(64, min(8600, int(round(seconds * rate))))
        expected = (samples / rate) if rate else (samples / 860.0)
        self.ns["BURST_REQUEST"][channel] = int(samples)
        engine = getattr(self.runtime, "engine", None) if hasattr(self, "runtime") else None
        engine = engine or getattr(self.ns.get("INSTRUMENT_RUNTIME"), "engine", None)
        if engine is not None:
            engine.expect_pause(
                self.BURST_ANALYSIS_CHANNEL.get(channel, channel), expected,
                f"Contiguous {expected:.1f} s capture for reference analysis")
        return samples

    @staticmethod
    def achieved_rate(channels, channel="ch2f"):
        """The rate the ADC really manages, read from a packet the caller already
        holds. Deliberately not fetched with engine.snapshot(): request_burst runs
        inside a d4 pass that is itself downstream of a snapshot, and a nested one
        would redo the correlation work on every burst."""
        key = {"ch2f": "ch2", "current": "current"}.get(channel, channel)
        try:
            rate = float(((channels.get(key) or {}).get("metadata") or {}).get("adc_sample_rate") or 0)
            return rate if rate > 20 else 0.0
        except Exception:
            return 0.0

    def _achieved_rate(self, channel):
        return 0.0

    # ── reference database (16), trials (17/37), classifier (38) ─────────────
    def record_reference(self, name, note=""):
        packet = self.snapshot(force=True)
        feats = d4.feature_vector(packet)
        with self.lock:
            self.references[name] = {"features": feats, "feature_names": d4.FEATURE_NAMES, "recorded_at": time.time(), "note": note,
                                     "simulated": bool(packet.get("simulated")),
                                     "summary": {"linefreq": (packet.get("linefreq") or {}).get("fundamental_hz"), "thd": (packet.get("linefreq") or {}).get("thd_pct"),
                                                 "ch3_peak_hz": (packet.get("ch3") or {}).get("primary_peak_hz"), "ch3_snr": (packet.get("ch3") or {}).get("snr_db")}}
            self._save_json("reference_profiles.json", self.references)
            self.packet = None
        return self.references[name]

    def delete_reference(self, name):
        with self.lock:
            self.references.pop(name, None)
            self._save_json("reference_profiles.json", self.references)
            self.packet = None

    def add_trial(self, trial):
        packet = self.snapshot()
        row = {"t": time.time(), "distance_cm": trial.get("distance_cm"), "source": (trial.get("source") or "unknown")[:40],
               "value": trial.get("value"), "reference": trial.get("reference"), "detected": bool(trial.get("detected")),
               "actual": bool(trial.get("actual")), "mtdi": packet.get("mtdi"), "confidence": packet.get("confidence"),
               "features": d4.feature_vector(packet), "note": (trial.get("note") or "")[:120], "simulated": bool(packet.get("simulated"))}
        with self.lock:
            self.trials.append(row)
            self.trials = self.trials[-2000:]
            self._save_json("validation_trials.json", self.trials)
        return row

    def clear_trials(self):
        with self.lock:
            self.trials = []
            self._save_json("validation_trials.json", self.trials)

    def train_model(self):
        samples = [{"label": r["source"], "features": r["features"]} for r in self.trials if r.get("actual") and r.get("features")]
        model = d4.train_nearest_centroid(samples)
        with self.lock:
            self.model = model
            if model:
                model["trained_at"] = time.time()
                self._save_json("classifier.json", model)
        counts = {}
        for smp in samples:
            counts[smp["label"]] = counts.get(smp["label"], 0) + 1
        return model, counts

    # ── data access ──────────────────────────────────────────────────────────
    def _ring(self, name, seconds):
        ring = self.ns.get("RAW_RING", {}).get(name)
        lock = self.ns.get("raw_ring_lock")
        if ring is None or lock is None:
            return []
        cutoff = time.time() - seconds
        with lock:
            rows = [r for r in ring if r[0] >= cutoff]
        return rows

    def _histories(self):
        with self.engine.lock:
            return {k: list(v) for k, v in self.engine.histories.items()}

    def _sweep3(self):
        lock = self.ns.get("sweep3_lock")
        data = self.ns.get("sweep3_data")
        if lock is None or data is None:
            return None
        with lock:
            return {"freqs": list(data.get("freqs") or []), "levels": list(data.get("levels") or []),
                    "trusted": bool(data.get("trusted")), "last_rx": data.get("last_rx"), "status": data.get("status"),
                    "x_unit": data.get("x_unit")}

    # ── repeatability on demand ──────────────────────────────────────────────
    REPEAT_CHANNELS = {
        "ch1": ('Channel 1 magnitude', "uT"),
        "ch2": ('Channel 2 block RMS', "ADC codes"),
    }

    def _repeat_reading(self, channel, window_s):
        """One reading: the mean of everything the channel produced in this window."""
        if channel == "ch1":
            rows = self._ring("ch1", window_s)
            if len(rows) < 3:
                return None
            return float(np.linalg.norm(np.array([r[1:4] for r in rows], dtype=float), axis=1).mean())
        rows = self._ring("ch2f", window_s)
        if len(rows) < 8:
            return None
        x = np.array([r[1] for r in rows], dtype=float)
        return float(np.sqrt(np.mean((x - x.mean()) ** 2)))

    def start_repeatability(self, channel="ch1", runs=10, window_s=3.0):
        """Take the same measurement `runs` times in a row and report the spread.

        Each reading is a real window of live data - nothing is resampled from one
        capture, because repeating an analysis of the same samples would measure the
        arithmetic rather than the instrument. That is why the run takes runs x window_s
        of wall-clock time and cannot be hurried.
        """
        channel = str(channel)
        if channel not in self.REPEAT_CHANNELS:
            raise ValueError(f"channel must be one of {', '.join(self.REPEAT_CHANNELS)}")
        runs = int(max(3, min(30, runs)))
        window_s = float(max(1.0, min(10.0, window_s)))
        with self.lock:
            state = getattr(self, "repeat_run", None)
            if state and state.get("running"):
                raise ValueError("a repeatability run is already in progress")
        label, unit = self.REPEAT_CHANNELS[channel]
        started = {"running": True, "channel": channel, "label": label, "unit": unit,
                   "runs": runs, "window_s": window_s, "done": 0, "readings": [],
                   "started_at": time.time(), "result": None, "error": None,
                   "eta_s": round(runs * window_s, 1)}
        with self.lock:
            self.repeat_run = started
        threading.Thread(target=self._repeatability_worker, args=(channel, runs, window_s),
                         name="d4-repeat", daemon=True).start()
        return dict(started)

    def _repeatability_worker(self, channel, runs, window_s):
        readings, skipped = [], 0
        try:
            for _ in range(runs):
                time.sleep(window_s)
                value = self._repeat_reading(channel, window_s)
                if value is None:
                    skipped += 1
                else:
                    readings.append(value)
                with self.lock:
                    self.repeat_run["done"] = len(readings) + skipped
                    self.repeat_run["readings"] = list(readings)
            label, unit = self.REPEAT_CHANNELS[channel]
            result = d4.repeatability_stats(readings, unit)
            result["channel"] = label
            result["window_s"] = window_s
            result["skipped"] = skipped
            result["conditions"] = (
                "Ambient conditions, not a controlled source: the spread includes any real "
                "change in the environment during the run as well as the instrument's own "
                "repeatability. Keep the instrument and its surroundings still for the "
                f"{round(runs * window_s)} s the run takes, or the number means less than it looks.")
            with self.lock:
                self.repeat_run.update(running=False, result=result, finished_at=time.time())
            note = self.ns.get("note")
            if callable(note) and not result.get("error"):
                note("d4", f"repeatability run on {label}: RSD {result.get('rsd_pct')} % over {result.get('n')} readings")
        except Exception as exc:                                  # pragma: no cover - defensive
            with self.lock:
                self.repeat_run.update(running=False, error=str(exc)[:160], finished_at=time.time())

    # ── calibration on demand ────────────────────────────────────────────────
    def calibrate_ch1probe(self, seconds=120):
        rows = self._ring("ch1_raw", seconds)
        pts = [r[1:4] for r in rows]
        result, err = d4.ellipsoid_fit(pts)
        if err:
            return None, err
        cfg_patch = {"c1_offsets": result["offsets_val"], "c1_soft_iron": result["soft_iron_matrix"],
                     "c1_scale": result["scale"], "c1_calibration_quality": result["quality"]}
        with self.lock:
            self.last_calibration = dict(result, computed_at=time.time(), window_s=seconds,
                                         simulated=bool(self.ns["RUNTIME"].get("demo")))
        return result, cfg_patch

    # ── the packet ───────────────────────────────────────────────────────────
    def snapshot(self, force=False):
        with self.lock:
            if self.packet is not None and not force and time.time() - self.computed_at < 2.0:
                return self.packet
            asked = time.time()
        # _compute_inner appends to and reads mtdi_history, transient_times and events. Two
        # callbacks computing at once made one iterate a deque the other was appending to
        # ("deque mutated during iteration", a 500 on the page). Computes now run one at a
        # time; a caller that waited reuses the packet computed while it waited.
        with self.compute_lock:
            with self.lock:
                if self.packet is not None and self.computed_at >= asked:
                    return self.packet
            packet = self._compute()
            with self.lock:   # published before the next waiter looks, so it reuses this packet
                self.packet = packet
                self.computed_at = time.time()
        return packet

    def _compute(self):
        started = time.perf_counter()
        try:
            return self._compute_inner(started)
        finally:
            self.compute_seconds = round(time.perf_counter() - started, 3)

    def _compute_inner(self, started):
        cfg = self.config
        now = time.time()
        simulated = bool(self.ns["RUNTIME"].get("demo"))
        out = {"timestamp": now, "simulated": simulated, "config_source": cfg.get("source"), "config_error": self.config_error,
               "weights": cfg["mtdi_weights"], "confidence_weights": cfg["confidence_weights"]}
        hist = self._histories()
        engine_snapshot = self.engine.snapshot()
        channels = engine_snapshot.get("channels", {})

        # per channel anomaly: current deviation against its own recent history (robust z)
        scores, zs, snr_terms, series = {}, {}, {}, {}
        for key in ("ch1", "ch2", "ch3"):
            rows = hist.get(key) or []
            vals = [v for _, v, _ in rows if v is not None and math.isfinite(v)]
            series[key] = vals
            item = channels.get(key, {})
            dev = item.get("deviation")
            avail = item.get("state") == "connected" and dev is not None
            z = d4.zscore(dev, vals[:-1]) if avail and len(vals) > 8 else None
            zs[key] = d4._f(z, 2)
            scores[key] = d4._f(d4.channel_score(z, cfg["anomaly_sigma"]), 1) if z is not None else None
            snr_terms[key] = min(1.0, (item.get("snr") or 0.0) / 12.0) if avail else None

        # transients from the ch1 deviation series (10 Hz), score from the count in the window
        c1_rows = hist.get("ch1") or []
        tr = d4.transient_features([t for t, _, _ in c1_rows], [v for _, v, _ in c1_rows], cfg["transient_threshold"], min_noise=0.35) if len(c1_rows) > 10 else {"events": [], "count": 0}
        for ev in tr.get("events", []):
            if not self.transient_times or ev["t"] > self.transient_times[-1]:
                self.transient_times.append(ev["t"])
        scores["transient"] = d4._f(min(100.0, 25.0 * tr.get("count", 0)), 1) if len(c1_rows) > 10 else None
        out["transients"] = tr

        mtdi, contrib = d4.mtdi2(scores, cfg["mtdi_weights"])
        agreement = d4.consensus({k: v for k, v in scores.items() if k != "transient"})
        self.mtdi_history.append((now, mtdi if mtdi is not None else float("nan")))
        recent = [m for t, m in self.mtdi_history if now - t < 30 and math.isfinite(m)]
        repeat = (1.0 - min(1.0, float(np.std(recent)) / 25.0)) if len(recent) >= 3 else None

        # calibration health from the calibrated ch1 ring
        c1_ring = self._ring("ch1_raw", 60)
        cal_health = d4.calibration_health([r[1:4] for r in c1_ring], cfg) if len(c1_ring) >= 30 else {"status": "insufficient", "samples": len(c1_ring)}
        cal_term = (cal_health.get("quality") or 0) / 100.0 if cal_health.get("quality") is not None else None
        base_dev = max([abs(z) for z in zs.values() if z is not None] or [0.0])
        conf, factors = d4.confidence2({"snr": max([v for v in snr_terms.values() if v is not None] or [None]) if any(v is not None for v in snr_terms.values()) else None,
                                        "repeatability": repeat, "agreement": (agreement / 100.0) if agreement is not None else None,
                                        "baseline_deviation": min(1.0, base_dev / (2 * cfg["anomaly_sigma"])) if base_dev else 0.0,
                                        "calibration": cal_term}, cfg["confidence_weights"])
        out.update({"scores": scores, "z": zs, "mtdi": d4._f(mtdi, 1), "contributions": contrib, "consensus": d4._f(agreement, 1),
                    "confidence": d4._f(conf, 1), "confidence_factors": factors, "calibration_health": cal_health,
                    "repeatability": d4._f(repeat, 3)})

        # linefreq harmonics from the Ch2 ADC ring (true 860 SPS)
        ef = self._ring("ch2f", 30.0)
        seg = longest_contiguous(ef)
        if len(seg) >= 256:
            t = np.array([r[0] for r in seg]); x = np.array([r[1] for r in seg], dtype=float)
            fs = (len(t) - 1) / max(1e-6, t[-1] - t[0])
            out["linefreq"] = dict(d4.harmonics(x, fs, cfg["linefreq_hz"]), source='Channel 2 ADC ring, longest contiguous block',
                                contiguous_s=d4._f(t[-1] - t[0], 3),
                                note=None if len(seg) >= 1500 else "short block: request a burst capture for finer resolution")
            out["noise_ch2"] = d4.noise_characterisation(x, fs)
            # Same samples, cut into overlapping windows: whether each line was present
            # for the whole block or only part of it. Capped at 400 Hz because everything
            # the linefreq analysis is about - the fundamental and its first harmonics - is
            # below it, and the rest is just a taller picture of the noise floor.
            spec = d4.spectrogram(x, fs, segments=28, max_hz=min(400.0, fs / 2))
            if spec:
                out["linefreq"]["spectrogram"] = spec
        else:
            out["linefreq"] = {"error": f"longest contiguous Ch2 block holds {len(seg)} samples; need 256 (request a burst)"}
        c1_cal = self._ring("ch1", 20.0)
        if len(c1_cal) >= 64:
            t = np.array([r[0] for r in c1_cal]); m = np.linalg.norm(np.array([r[1:4] for r in c1_cal], dtype=float), axis=1)
            fs = (len(t) - 1) / max(1e-6, t[-1] - t[0])
            out["linefreq_ch1"] = d4.harmonics(m, fs, cfg["linefreq_hz"])
            out["noise_ch1"] = d4.noise_characterisation(m, fs)
            out["ch1_rate_hz"] = d4._f(fs, 2)

        # keep the linefreq analysis fresh: an automatic 4 s contiguous capture every auto_burst_s
        # (the Ch2 channel pauses for those 4 s; the reading is labelled in the packet)
        period = float(cfg.get("auto_burst_s") or 0)
        if period > 0 and now - getattr(self, "_last_auto_burst", 0) > period and channels.get("ch2", {}).get("state") == "connected":
            self._last_auto_burst = now
            # Four seconds means four seconds: sized from the rate the ADC actually
            # achieves (measured 306.7 SPS against a configured 860), not from the
            # configured one, which made this a 11.2 s stall on both ADC channels.
            self.request_burst(seconds=4.0, channel="ch2f",
                               rate=self.achieved_rate(channels, "ch2f"))
        out["auto_burst_s"] = period
        # NOTE: "repeatability" is already taken in this packet - it is the 0-1 MTDI
        # stability that feeds the confidence engine. The on-demand run is a different
        # thing and gets its own key rather than shadowing that one.
        with self.lock:
            rep = getattr(self, "repeat_run", None)
            out["repeat_run"] = dict(rep) if rep else None
        out["power_network"] = d4.power_network(out.get("linefreq"), out.get("linefreq_ch1"), None, cfg["linefreq_hz"])

        # How small a change each channel can honestly claim to have seen, from its own
        # measured noise rather than a datasheet figure.
        limits = {}
        c1 = self.ns.get("ch1_data") or {}
        c1_unit = (str(c1.get("fed_unit") or "").strip() if c1.get("fed_source") else "") or "uT"
        for key, noise_key, unit in (("ch1", "noise_ch1", c1_unit),
                                     ("ch2", "noise_ch2", "ADC codes")):
            lim = d4.detection_limits(out.get(noise_key), unit)
            if lim:
                limits[key] = lim
        out["detection_limits"] = limits

        # Where the measured 50 Hz levels sit against the published exposure reference
        # levels. Only the 50 Hz ch1 component is compared - the bulk of the total
        # field is the Earth's steady field, which the reference levels are not about.
        c1_fund = (out.get("linefreq_ch1") or {}).get("fundamental_amp")
        e_fund = None
        probe_cal = bool(cfg.get("probe_calibrated"))
        if probe_cal:
            e_fund = (out.get("linefreq") or {}).get("fundamental_amp")
        out["exposure"] = d4.exposure_comparison(e_fund, c1_fund, calibrated=probe_cal)

        # CH3 analysis of the latest sweep
        sp = self._sweep3()
        if sp and len(sp["freqs"]) >= 8:
            out["ch3"] = ch3_packet(sp, cfg["ch3_threshold_db"])
        else:
            out["ch3"] = {"error": "no sweep yet"}

        # correlations between channel deviation series
        pairs = {}
        for a, b in (("ch3", "ch1"), ("ch3", "ch2"), ("ch1", "ch2"), ("current", "ch1")):
            r = d4.correlation(series.get(a, []), series.get(b, []))
            pairs[f"{a}_{b}"] = {"r": d4._f(r, 3), "text": d4.correlation_text(r)}
        out["correlation"] = pairs

        # adaptive baseline demonstration on the ch1 series
        if len(series.get("ch1", [])) >= 20:
            out["baseline_methods"] = d4.compare_baselines(series["ch1"], cfg["baseline_alpha"])

        # trend: MTDI over the last 10 minutes
        xs = [(t, m) for t, m in self.mtdi_history if math.isfinite(m)]
        if len(xs) >= 10:
            t0 = xs[0][0]
            tt = np.array([t - t0 for t, _ in xs]); mm = np.array([m for _, m in xs])
            slope = float(np.polyfit(tt, mm, 1)[0]) * 60
            out["trend"] = {"minutes": d4._f((xs[-1][0] - t0) / 60, 1), "mtdi_per_min": d4._f(slope, 2),
                            "text": "Stable" if abs(slope) < 1 else ("Rising interference" if slope > 0 else "Falling interference")}

        # history windows from the archive (10 / 60 min) for ch1, ch2 and CH3
        try:
            hist_long = self.ns["ARCHIVE"].history(minutes=60, points=240)
            windows = {}
            for key, field in (("ch1probe", "magnitude_val"), ("ch2f", "rms_mv"), ("ch3", "peak_dbm")):
                rows = hist_long.get(key) or []
                ts = [r.get("t") for r in rows if r.get("t") is not None and r.get(field) is not None]
                xs = [r.get(field) for r in rows if r.get("t") is not None and r.get(field) is not None]
                if len(xs) >= 8:
                    windows[key] = d4.trend_analysis(ts, xs)
            out["history"] = windows
        except Exception as exc:
            out["history"] = {"error": str(exc)[:120]}

        # reference database similarity, trials, classifier
        feats = d4.feature_vector(out)
        out["features"] = dict(zip(d4.FEATURE_NAMES, feats))
        out["similarity"] = d4.similarity_ranked(feats, self.references) if self.references else []
        out["references"] = {k: {"recorded_at": v.get("recorded_at"), "note": v.get("note"), "summary": v.get("summary"), "simulated": v.get("simulated")} for k, v in self.references.items()}
        out["trials_count"] = len(self.trials)
        out["recommendations"] = d4.test_recommendations(self.trials)
        if self.model:
            out["classifier"] = {"trained_at": self.model.get("trained_at"), "n": self.model.get("n"), "classes": {k: v["n"] for k, v in self.model["classes"].items()},
                                 "prediction": d4.classify(self.model, feats)}
        else:
            labelled = {}
            for r in self.trials:
                if r.get("actual"):
                    labelled[r["source"]] = labelled.get(r["source"], 0) + 1
            out["classifier"] = {"trained_at": None, "note": "Not trained: needs at least 2 sources with 5 labelled trials each", "labelled": labelled}

        # environmental fingerprint (rolling, compared with the reference)
        fp = d4.fingerprint([np.linalg.norm(r[1:4]) for r in c1_cal] if c1_cal else [], series.get("ch2", []),
                            out["ch3"].get("noise_floor_dbm"), out["ch3"].get("primary_peak_hz"),
                            len([t for t in self.transient_times if now - t < 600]) / 10.0,
                            {"fundamental_hz": out.get("linefreq", {}).get("fundamental_hz"), "thd_pct": out.get("linefreq", {}).get("thd_pct")},
                            ch3_x_unit=(sp or {}).get("x_unit"), ch3_level_unit=out["ch3"].get("level_unit"))
        out["fingerprint"] = fp
        out["fingerprint_reference"] = self.fingerprint_ref
        out["fingerprint_change"] = d4.compare_fingerprints(self.fingerprint_ref, fp)

        # events: open when MTDI crosses the threshold, close when it falls back
        level = lambda s: "HIGH" if (s or 0) >= 66 else "MEDIUM" if (s or 0) >= 33 else "LOW"
        if mtdi is not None and mtdi >= cfg["event_mtdi"] and self.open_event is None:
            self.event_seq += 1
            self.open_event = {"id": self.event_seq, "t": now, "time": time.strftime("%H:%M:%S", time.localtime(now)) + f".{int((now % 1) * 1000):03d}",
                               "ch3": level(scores.get("ch3")), "ch1": level(scores.get("ch1")), "ch2": level(scores.get("ch2")),
                               "mtdi": d4._f(mtdi, 0), "confidence": d4._f(conf, 0), "peak_mtdi": mtdi, "open": True}
            self.events.appendleft(self.open_event)
        elif self.open_event is not None:
            if mtdi is not None and mtdi > self.open_event["peak_mtdi"]:
                self.open_event.update(peak_mtdi=mtdi, mtdi=d4._f(mtdi, 0), confidence=d4._f(conf, 0))
            if mtdi is None or mtdi < cfg["event_mtdi"] * 0.7:
                self.open_event.update(open=False, duration_s=d4._f(now - self.open_event["t"], 1))
                self.open_event = None
        out["events"] = list(self.events)[:20]
        out["last_calibration"] = self.last_calibration
        return out

    def set_fingerprint_reference(self):
        packet = self.snapshot(force=True)
        with self.lock:
            self.fingerprint_ref = packet.get("fingerprint")
            self._save_json("fingerprint_reference.json", self.fingerprint_ref)
        return self.fingerprint_ref
