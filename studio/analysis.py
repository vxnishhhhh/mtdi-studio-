"""Instrument processing with bounded histories and explicit confidence terms."""
from __future__ import annotations

from collections import deque
from bisect import bisect_left
from copy import deepcopy
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import statistics
import threading
import time

from .content import T  # studio words (S1-06)

CHANNELS = {
    # The units are the studio's own sources (magnetometer in µT, probe in mV RMS, radio in dB, coil
    # current in A); a fed source passes its own unit to ingest(). Labels come from channel_label().
    "ch1": {"label": "Channel 1", "unit": "µT", "floor": 0.1, "stale": 2.0},
    "ch2": {"label": "Channel 2", "unit": "mV RMS relative", "floor": 0.008, "stale": 4.0},
    "ch3": {"label": "Channel 3", "unit": "dB", "floor": 0.5, "stale": 90.0},
    "current": {"label": "Current", "unit": "A", "floor": 0.02, "stale": 4.0, "optional": True},
}


def channel_label(key):
    """A channel's name in the project's words (S1-06): ch1 to ch3 from the content file, the rest as listed."""
    return T(f"{key}.name") if key in ("ch1", "ch2", "ch3") else CHANNELS[key]["label"]

# Ambient noise budget per channel: the noise floor a healthy sensor should sit under
# in a quiet room (median absolute deviation, scaled). Used by the resolution regime.
NOISE_BUDGET = {"ch1": 1.0, "ch2": 0.25, "ch3": 2.5, "current": 0.08}
# ── alert thresholds ──────────────────────────────────────────────────────────
# A channel alert must clear BOTH tests: a robust z score (the deviation over that
# channel's own measured MAD noise, so a quiet sensor is not judged against a loud
# one) AND an absolute change in the channel's physical unit.
#
# Either test alone is wrong, and the old ch1probe rule was wrong in both
# directions at once. It fired on a fixed 80 unit / 3 unit threshold, which in Durban's
# ~30 unit ambient meant a large real change could pass unreported while simply
# rotating the instrument tripped it. A pure z test is no better: on a very quiet
# channel a 0.2 unit wobble is statistically enormous and physically meaningless.
# Requiring both is what makes this fire for big changes only.
ALERT_LEVELS = (                       # (name, minimum z, multiple of ALERT_CHANGE)
    ("critical", 30.0, 6.0),
    ("alert",    14.0, 2.0),
    ("notice",    7.0, 1.0),
)
# The smallest change on each channel a person would call an event, in that
# channel's unit. Ch1 2 unit is roughly a phone charger at 10 cm; CH3 4 dB is
# comfortably outside sweep-to-sweep scatter on the src3.
ALERT_CHANGE = {"ch1": 2.0, "ch2": 0.25, "ch3": 4.0, "current": 0.15}
ALERT_REARM = 3.0      # z must fall back below this before a channel may fire again
ALERT_HOLD = 2         # consecutive qualifying samples, so one bad sample is not an event
ALERT_MIN_GAP = 6.0    # seconds between alerts on one channel
# Only these levels are worth interrupting the operator for.
ALERT_SUMMON = ("alert", "critical")

MTDI_WEIGHTS = {"availability": 0.20, "baseline": 0.15, "signal_to_noise": 0.20,
                "clipping": 0.15, "timing": 0.10, "transient": 0.10,
                "axial_consensus": 0.05, "correlation": 0.05}
SIGNATURE_RULES = (
    {"id": "ch1_dominance", "test": 'channel 1 SNR >= 6 and channel 2 SNR < 3',
     "condition": 'Channel 1 activity dominant', "text": 'Channel 1 activity with weak channel 2 activity suggests a nearby current loop or conductor. Probe sensitivity and geometry can also explain the difference.'},
    {"id": "ch2_dominance", "test": 'channel 2 SNR >= 6 and channel 1 SNR < 3',
     "condition": 'Channel 2 activity dominant', "text": 'Channel 2 activity with weak channel 1 activity suggests capacitive coupling or a voltage driven source. This is a relative probe comparison.'},
    {"id": "radiated_rf", "test": 'channel 3 SNR >= 6 and channel 1 SNR < 3 and channel 2 SNR < 3',
     "condition": 'Channel 3 activity dominant', "text": 'A channel 3 change with weak low frequency activity suggests a channel 3 source. Source coupling and a swept scan do not establish source location or protocol.'},
    {"id": "mixed", "test": "at least two channels have SNR >= 3",
     "condition": 'Mixed signal activity', "text": "Several channels changed relative to their ambient baselines. A common source is possible when the event timing agrees."},
    {"id": "ambient", "test": "no available channel has SNR >= 3",
     "condition": "Ambient conditions", "text": "Available channels show no clear change beyond their measured ambient variation."},
)


def finite(value, name="value"):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def bounded(value, lo=0.0, hi=1.0):
    return min(hi, max(lo, value))


class CalibrationStore:
    """Persist reference measurements atomically and retain the replaced profile."""

    def __init__(self, path=None):
        self.path = Path(path or os.environ.get("STUDIO_CALIBRATION_FILE", str(Path.home() / ".config/mtdi_studio/calibration.json"))).expanduser()
        self.lock = threading.RLock()
        self.data = {"profiles": {}, "history": []}
        self.error = None
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf8"))
                for channel, profile in data.get("profiles", {}).items():
                    if channel not in CHANNELS:
                        continue
                    for key in ("scale", "offset", "uncertainty", "timestamp"):
                        finite(profile[key], key)
                    if profile["scale"] <= 0 or profile["uncertainty"] < 0:
                        raise ValueError("Invalid calibration scale or uncertainty")
                    self.data["profiles"][channel] = profile
                self.data["history"] = data.get("history", [])[-100:]
            except (OSError, ValueError, TypeError, KeyError) as exc:
                self.error = f"Calibration file unavailable: {exc}"
                self.data = {"profiles": {}, "history": []}

    def get(self, channel):
        with self.lock:
            return dict(self.data["profiles"].get(channel, {}))

    def _write(self, candidate):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        with temporary.open("w", encoding="utf8") as stream:
            json.dump(candidate, stream, ensure_ascii=False, allow_nan=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, self.path)
        self.data = candidate
        self.error = None

    def put(self, channel, profile):
        if channel not in CHANNELS:
            raise ValueError("Unknown channel")
        with self.lock:
            candidate = deepcopy(self.data)
            old = candidate["profiles"].get(channel)
            candidate["history"].append({"channel": channel, "replaced_at": time.time(), "profile": old})
            candidate["history"] = candidate["history"][-100:]
            if profile is None:
                candidate["profiles"].pop(channel, None)
            else:
                candidate["profiles"][channel] = profile
            self._write(candidate)


class BaselineLock:
    """A time window median learns quiet values and rejects temporary excursions."""

    def __init__(self, window=10.0, noise_floor=0.01):
        self.window = finite(window)
        self.floor = finite(noise_floor)
        self.frozen = False
        # D4 dynamic baseline: 'moving_median' (original), 'moving_mean' or 'ema' with alpha
        self.method = 'moving_median'
        self.alpha = 0.025
        self.reset()

    def reset(self):
        self.samples = deque(maxlen=3001)
        self.started = None
        self.last_added = None
        self.value = None
        self.noise = self.floor
        self.settling = True
        self.rejected = 0
        self.accepted = 0
        # Stale-lock watch: excursions the lock refuses are kept for a while. When nearly
        # everything is refused and the refused values are themselves steady, the world
        # has moved (instrument moved, supply warmed up) and the lock is stale.
        self.refused = deque(maxlen=600)
        self.recent = deque(maxlen=600)
        self.stale = False
        self.stale_offset = 0.0
        self.stale_since = None

    def _watch(self, value, timestamp, accepted):
        self.recent.append((timestamp, accepted))
        if not accepted:
            self.refused.append((timestamp, value))
        cutoff = timestamp - 60.0
        while self.recent and self.recent[0][0] < cutoff:
            self.recent.popleft()
        while self.refused and self.refused[0][0] < cutoff:
            self.refused.popleft()
        if self.settling or len(self.recent) < 40:
            self.stale, self.stale_since = False, None
            return
        share = 1.0 - sum(1 for _, ok in self.recent if ok) / len(self.recent)
        if share >= 0.9 and len(self.refused) >= 30 and self.value is not None:
            values = [v for _, v in self.refused]
            centre = statistics.median(values)
            spread = 1.4826 * statistics.median(abs(v - centre) for v in values)
            if spread <= max(3 * self.noise, 3 * self.floor):
                if not self.stale:
                    self.stale_since = self.refused[0][0]
                self.stale = True
                self.stale_offset = centre - self.value
                return
        self.stale, self.stale_since = False, None

    def update(self, value, timestamp, valid=True):
        if self.started is None:
            self.started = timestamp
        if self.value is None:
            self.value = value
        elapsed = max(0.0, timestamp - self.started)
        self.settling = elapsed < self.window or self.accepted < 5
        if valid and not self.frozen and (self.last_added is None or timestamp - self.last_added >= 0.19):
            quiet = self.settling or abs(value - self.value) <= max(6 * self.noise, 6 * self.floor)
            if quiet:
                self.samples.append((timestamp, value))
                self.accepted += 1
                self.last_added = timestamp
                while len(self.samples) > 1 and self.samples[0][0] < timestamp - self.window:
                    self.samples.popleft()
                values = [v for _, v in self.samples]
                centre = statistics.median(values)
                if self.method == 'ema' and not self.settling:
                    self.value = self.value + self.alpha * (value - self.value)
                elif self.method == 'moving_mean' and not self.settling:
                    self.value = statistics.fmean(values)
                else:
                    self.value = centre
                self.noise = max(self.floor, 1.4826 * statistics.median(abs(v - centre) for v in values))
                self._watch(value, timestamp, True)
            else:
                self.rejected += 1
                self._watch(value, timestamp, False)
        return value - self.value

    def stale_for(self, timestamp):
        return (timestamp - self.stale_since) if self.stale and self.stale_since is not None else 0.0

    def snapshot(self):
        return {"value": self.value, "settling": self.settling, "frozen": self.frozen,
                "window": self.window, "noise": self.noise, "rejected": self.rejected,
                "samples": len(self.samples), "stale": self.stale, "stale_offset": self.stale_offset,
                "stale_since": self.stale_since}


class TransientWatch:
    """Classify a bounded time history against measured baseline variation."""

    def __init__(self):
        self.history = deque(maxlen=1200)

    def update(self, timestamp, deviation, noise):
        self.history.append((timestamp, deviation, noise))
        while self.history and self.history[0][0] < timestamp - 12:
            self.history.popleft()

    def snapshot(self, values=None):
        values = list(self.history) if values is None else values
        if not values:
            return {"state": "Unavailable", "variance": None, "threshold": None}
        deviations = [v for _, v, _ in values]
        noise = max(values[-1][2], 1e-12)
        variance = statistics.pvariance(deviations) if len(deviations) > 1 else 0.0
        threshold = (3.0 * noise) ** 2
        active = [abs(value) > 3 * local_noise for _, value, local_noise in values]
        duration = max(0.0, values[-1][0] - values[0][0])
        # Duration weights make classification independent of packet frequency.
        segments = [(values[i + 1][0] - values[i][0], active[i]) for i in range(len(values) - 1)]
        duty = sum(dt for dt, high in segments if high) / max(duration, 1e-12)
        transitions = sum(a != b for a, b in zip(active, active[1:]))
        if len(values) < 4 or duration < 1.0:
            state = "Settling"
        elif not any(active):
            state = "Stable / ambient"
        elif duty > 0.8 and transitions <= 2:
            state = "Continuous"
        elif variance > threshold and duty < 0.35:
            state = "Bursty / transient"
        else:
            state = "Intermittent"
        return {"state": state, "variance": variance, "threshold": threshold,
                "duty": duty, "transitions": transitions, "duration": duration,
                "method": "Variance and duration above three times ambient noise"}


class AnalysisEngine:
    """Acquisition feeds this service; snapshots contain presentation ready values."""

    def __init__(self, calibration_path=None, window=10.0):
        self.lock = threading.RLock()
        self.calibrations = CalibrationStore(calibration_path)
        self.channels = {}
        self.baselines = {key: BaselineLock(window, cfg["floor"]) for key, cfg in CHANNELS.items()}
        self.axis_baselines = [BaselineLock(window, 0.03) for _ in range(3)]
        self.transients = {key: TransientWatch() for key in CHANNELS}
        self.histories = {key: deque(maxlen=300) for key in CHANNELS}
        self.intervals = {key: deque(maxlen=64) for key in CHANNELS}
        self.last_mono = {}
        self.events = deque(maxlen=300)
        self.previous_event = {}
        # Per channel alert arming: a channel that has fired stays disarmed until
        # its z score falls back under ALERT_REARM, so one sustained source produces
        # one alert instead of an alert on every packet for as long as it is present.
        self.alert_state = {key: {"armed": True, "streak": 0, "last": 0.0, "peak": 0.0} for key in CHANNELS}
        # A channel can be taken off line deliberately - the D4 engine's contiguous
        # capture holds the ADC for seconds at a time. That is planned work, not a
        # dropout, and must not be reported as one. Acquisition announces it here
        # BEFORE it happens, because during the gap there are no samples arriving to
        # carry the news.
        self.expected_pause = {}
        self.condition_state = {}
        self.axis_shares = None
        self.filtered_vector = None
        self.axial = None
        self.vector = None
        self.sequence = 0
        # A lock that has been stale this long is re-learned automatically and the
        # event is recorded, so a moved instrument or a warmed-up supply cannot leave
        # every later reading measured against a reference that no longer exists.
        self.auto_relock_after = 120.0
        self.relock_log = deque(maxlen=64)
        for channel, cfg in CHANNELS.items():
            self.channels[channel] = {"label": channel_label(channel), "state": "offline", "message": "Waiting for data",
                                      "deviation": None, "unit": cfg["unit"], "raw": None, "last_rx": None,
                                      "uncertainty": "Unknown until calibrated", "uncertainty_value": None,
                                      "clipped": False, "sample_count": 0, "sample_rate": 0.0, "snr": 0.0,
                                      "metadata": {}, "calibration": {"timestamp": None, "calibrated": False, "method": "None"}}

    def expect_pause(self, channel, seconds, reason=""):
        """Tell the engine a channel is about to stop reporting on purpose."""
        if channel not in CHANNELS or seconds <= 0:
            return
        with self.lock:
            self.expected_pause[channel] = {
                "until": time.monotonic() + float(seconds) + 2.0,
                "reason": str(reason or "planned capture"),
                "seconds": float(seconds),
            }

    def set_baseline_method(self, method, alpha):
        method = method if method in ('moving_median', 'moving_mean', 'ema') else 'moving_median'
        with self.lock:
            for lock in list(self.baselines.values()) + list(self.axis_baselines):
                lock.method = method
                lock.alpha = max(0.001, min(0.5, float(alpha)))

    def status(self, channel, state, message=""):
        if channel not in self.channels:
            return
        if state not in {"offline", "unavailable", "initialising", "calibrating", "connected", "stale", "error", "paused"}:
            raise ValueError('Unknown source state')
        with self.lock:
            self.channels[channel].update(state=state, message=str(message))

    def baseline(self, channel=None, window=None, freeze=None, relock=False):
        if freeze is not None and not isinstance(freeze, bool):
            raise ValueError("Freeze must be true or false")
        if not isinstance(relock, bool):
            raise ValueError("Relock must be true or false")
        channels = list(CHANNELS) if channel is None or channel == "all" else [channel]
        if any(key not in CHANNELS for key in channels):
            raise ValueError("Unknown channel")
        if window is not None and not 2 <= finite(window) <= 600:
            raise ValueError("Baseline window must be between 2 and 600 seconds")
        with self.lock:
            for key in channels:
                instances = [self.baselines[key]] + (self.axis_baselines if key == "ch1" else [])
                for baseline in instances:
                    if window is not None:
                        baseline.window = float(window)
                    if relock or window is not None:
                        baseline.reset()
                    if freeze is not None:
                        baseline.frozen = bool(freeze)
                if relock or window is not None:
                    self.transients[key] = TransientWatch()
                    self.histories[key].clear()
                    if key == "ch1":
                        self.axis_shares = None
                        self.filtered_vector = None
            return {key: self.baselines[key].snapshot() for key in channels}

    def calibrate(self, channel, raw_reference, known_reference, uncertainty, unit=None, method="Two reference measurements"):
        if channel not in CHANNELS:
            raise ValueError("Unknown channel")
        if len(raw_reference) != 2 or len(known_reference) != 2:
            raise ValueError("Two observed and two known reference values are required")
        raw = [finite(x, "Observed reference") for x in raw_reference]
        known = [finite(x, "Known reference") for x in known_reference]
        if abs(raw[1] - raw[0]) < 1e-12:
            raise ValueError("Observed references must differ")
        scale = (known[1] - known[0]) / (raw[1] - raw[0])
        offset = known[0] - scale * raw[0]
        uncertainty = finite(uncertainty, "Reference uncertainty")
        if scale <= 0 or uncertainty < 0:
            raise ValueError("Scale must be positive and uncertainty cannot be negative")
        output_unit = unit or {"ch1": "µT", "ch2": "V/m", "ch3": "dB", "current": "A"}[channel]
        allowed = {"ch1": {"µT", "uT"}, "ch2": {"V/m", "mV RMS relative"}, "ch3": {"dB"}, "current": {"A", "mA"}}
        if output_unit not in allowed[channel]:
            raise ValueError("Unsupported calibration unit")
        # A scalar calibration cannot correct ch1 vector offsets.
        if channel == "ch1" and abs(offset) > max(uncertainty, 1e-6):
            raise ValueError("Ch1 scalar calibration requires proportional reference values; use the vector profile for axis offsets")
        profile = {"scale": scale, "offset": 0.0 if channel == "ch1" else offset,
                   "uncertainty": uncertainty, "unit": output_unit, "method": str(method),
                   "timestamp": time.time(), "raw_reference": raw, "known_reference": known,
                   "scope": "Provided reference conditions only"}
        self.calibrations.put(channel, profile)
        self.baseline(channel, relock=True)
        return profile

    def reset_calibration(self, channel):
        self.calibrations.put(channel, None)
        self.baseline(channel, relock=True)
        return {"channel": channel, "calibrated": False}

    def ingest(self, channel, value, timestamp=None, unit=None, raw=None, vector=None, clipped=False, metadata=None):
        if channel not in CHANNELS:
            raise ValueError("Unknown channel")
        value = finite(value)
        timestamp = time.time() if timestamp is None else finite(timestamp)
        metadata = dict(metadata or {})
        mono = finite(metadata.get("monotonic", time.monotonic()))
        vector = None if vector is None else [finite(v) for v in vector]
        if vector is not None and len(vector) != 3:
            raise ValueError("Three vector components are required")
        with self.lock:
            item = self.channels[channel]
            previous = self.last_mono.get(channel)
            if previous is not None and mono <= previous:
                return deepcopy(item)
            dt = mono - previous if previous is not None else 0.0
            self.last_mono[channel] = mono
            if dt > 0:
                self.intervals[channel].append(dt)
            profile = self.calibrations.get(channel)
            scale = profile.get("scale", 1.0)
            corrected = value * scale + profile.get("offset", 0.0)
            base = self.baselines[channel]
            base.floor = CHANNELS[channel]["floor"] * scale
            deviation = base.update(corrected, mono, valid=not clipped)
            if channel == "ch1" and vector is not None:
                corrected_vector = [v * scale for v in vector]
                for baseline in self.axis_baselines:
                    baseline.floor = 0.03 * scale
                delta_vector = [baseline.update(v, mono, valid=not clipped) for baseline, v in zip(self.axis_baselines, corrected_vector)]
                deviation = math.sqrt(sum(v * v for v in delta_vector))
                base.settling = any(b.settling for b in self.axis_baselines)
                base.noise = math.sqrt(sum(b.noise * b.noise for b in self.axis_baselines))
                energy = sum(v * v for v in delta_vector)
                shares = [v * v / energy for v in delta_vector] if energy > base.noise ** 2 else [0.0] * 3
                disagreement = 0.0
                if self.axis_shares is not None and energy > base.noise ** 2:
                    disagreement = 0.5 * sum(abs(a - b) for a, b in zip(shares, self.axis_shares))
                if energy > base.noise ** 2:
                    alpha = 1 - math.exp(-max(dt, 0.02) / 1.5)
                    self.axis_shares = shares if self.axis_shares is None else [a + alpha * (b - a) for a, b in zip(self.axis_shares, shares)]
                agreement = 1.0 - disagreement
                alpha = 1 - math.exp(-max(dt, 0.02) / 0.15)
                self.filtered_vector = delta_vector if self.filtered_vector is None else [a + alpha * (b - a) for a, b in zip(self.filtered_vector, delta_vector)]
                self.axial = {"x": delta_vector[0], "y": delta_vector[1], "z": delta_vector[2],
                              "magnitude": deviation, "disagreement": disagreement * 100,
                              "agreement": agreement * 100, "contribution": [v * 100 for v in shares],
                              "confidence_contribution": agreement * MTDI_WEIGHTS["axial_consensus"] * 100,
                              "unit": profile.get("unit", unit or CHANNELS[channel]["unit"]), "method": "Half the sum of changes in squared axis contribution against a temporal reference"}
                fx, fy, fz = self.filtered_vector
                self.vector = {"x": fx, "y": fy, "z": fz, "raw": delta_vector,
                               "bearing": math.degrees(math.atan2(fy, fx)) % 360 if deviation > 3 * base.noise else None,
                               "elevation": math.degrees(math.atan2(fz, math.hypot(fx, fy))),
                               "confidence": bounded(deviation / max(6 * base.noise, 1e-12)) * agreement * 100,
                               "reference": "Relative sensor axes; no geographic heading or source bearing"}
            if channel == "ch3" and "deviation_db" in metadata:
                deviation = finite(metadata["deviation_db"]) * scale
                base.noise = max(base.floor, finite(metadata.get("noise_db", 0.5)) * scale)
                base.settling = bool(metadata.get("sweep3_settling", base.settling))
            noise = max(base.noise, base.floor)
            snr = abs(deviation) / max(noise, 1e-12)
            self.transients[channel].update(mono, deviation, noise)
            if not self.histories[channel] or mono - self.histories[channel][-1][0] >= 0.09:
                self.histories[channel].append((mono, deviation, noise))
            instrument_uncertainty = metadata.get("uncertainty")
            numeric_uncertainty = profile.get("uncertainty", instrument_uncertainty)
            uncertainty_text = (f"±{numeric_uncertainty:.3g} {profile.get('unit', unit or CHANNELS[channel]['unit'])}; reference uncertainty only"
                                if numeric_uncertainty is not None else "Absolute accuracy unknown; ambient variation measured separately")
            if channel == "ch2" and not profile:
                uncertainty_text = "Relative input activity; field strength uncertainty unknown until probe calibration"
            if channel == "current" and not profile:
                uncertainty_text = "Nominal clamp ratio only; ampere accuracy unknown until clamp calibration"
            if clipped:
                uncertainty_text = "Clipped sample; magnitude is a lower bound and uncertainty is unknown"
            intervals = self.intervals[channel]
            rate = len(intervals) / sum(intervals) if intervals and sum(intervals) > 0 else 0.0
            item.update({"state": "connected", "message": "Baseline settling" if base.settling else "Live acquisition",
                         "deviation": deviation, "unit": profile.get("unit", unit or CHANNELS[channel]["unit"]),
                         "raw": value if raw is None else raw, "corrected_raw": corrected,
                         "last_rx": timestamp, "clipped": bool(clipped), "sample_count": item["sample_count"] + 1,
                         "sample_rate": rate, "snr": snr, "uncertainty": uncertainty_text,
                         "uncertainty_value": numeric_uncertainty, "metadata": metadata,
                         "calibration": {"timestamp": profile.get("timestamp"), "calibrated": bool(profile),
                                         "method": profile.get("method", "Factory nominal scaling" if channel == "ch1" else "None"),
                                         "profile": profile}})
            display = {"direct": corrected, "deviation": deviation, "activity": max(0.0, deviation)}
            if channel == "ch1" and vector is not None:
                cx, cy, cz = corrected_vector
                display.update({"x": cx, "y": cy, "z": cz, "magnitude": math.sqrt(cx * cx + cy * cy + cz * cz),
                                "dx": delta_vector[0], "dy": delta_vector[1], "dz": delta_vector[2]})
            if channel == "ch2":
                display.update({"rms_mv": value, "peak_mv": metadata.get("peak_mv"), "gain": metadata.get("gain"),
                                "axes": metadata.get("axis_rms_counts"),
                                "axes_vu": metadata.get("axis_vu"),
                                "magnitude_vu": metadata.get("magnitude_vu")})
            item["display"] = display
            item["data_source"] = metadata.get("data_source", "HARDWARE")
            if item["data_source"] == "SIMULATED":
                item["message"] = "SIMULATED DATA; no physical measurement"
                item["uncertainty"] = "SIMULATED DATA; physical accuracy is not applicable"
            snap = base.snapshot()
            if channel == "ch1" and vector is not None:
                # For the vector lock the per-axis watches decide; the stale offset is the vector distance.
                stale_axes = [b for b in self.axis_baselines if b.stale]
                snap["stale"] = bool(stale_axes)
                snap["stale_offset"] = math.sqrt(sum(b.stale_offset ** 2 for b in stale_axes)) if stale_axes else 0.0
                snap["stale_since"] = min(b.stale_since for b in stale_axes) if stale_axes else None
            snap["stale_for"] = (mono - snap["stale_since"]) if snap.get("stale") and snap.get("stale_since") is not None else 0.0
            item["baseline"] = snap
            if snap["stale"] and self.auto_relock_after and snap["stale_for"] >= self.auto_relock_after and not base.frozen:
                self.relock_log.append({"timestamp": timestamp, "channel": channel, "offset": snap["stale_offset"],
                                        "stale_for": snap["stale_for"], "unit": item["unit"]})
                self.baseline(channel, relock=True)
                item["message"] = "Baseline re-learned: the quiet level had moved"
            if channel == "ch1" and vector is not None:
                item["axial"] = dict(self.axial)
                item["baseline_vector"] = [baseline.value for baseline in self.axis_baselines]
            self.sequence += 1
            self._magnitude_alert(channel, item, deviation, snr, mono, timestamp,
                                  settling=base.settling, clipped=clipped)
            return deepcopy(item)

    # ── the alert engine ──────────────────────────────────────────────────────
    # Everything the instrument wants to interrupt the operator about goes through
    # _emit_alert, so there is exactly one place that decides what an event looks
    # like and exactly one severity vocabulary. The UI reads `severity` and nothing
    # else; it never re-applies a threshold of its own.

    def _emit_alert(self, *, channel, severity, kind, message, **extra):
        row = {"timestamp": time.time(), "channel": channel, "severity": severity,
               "kind": kind, "message": message, "source": channel}
        row.update(extra)
        self.events.append(row)
        return row

    def _magnitude_alert(self, channel, item, deviation, snr, mono, timestamp, *, settling, clipped):
        """Fire when a channel moves by an amount that is both statistically and
        physically large. Called on every accepted sample, under self.lock."""
        state = self.alert_state.setdefault(channel, {"armed": True, "streak": 0, "last": 0.0, "peak": 0.0})
        change = abs(finite(deviation))
        unit = item["unit"]
        step = ALERT_CHANGE.get(channel, CHANNELS[channel]["floor"] * 20)
        # A settling baseline has no trustworthy reference to deviate from, and a
        # clipped sample is a lower bound of unknown size. Neither can be an event,
        # but both re-arm the channel so a real change right after is not swallowed.
        if settling or clipped:
            state.update(armed=True, streak=0, peak=0.0)
            return None
        if snr < ALERT_REARM:
            state["armed"] = True
            state["streak"] = 0
            state["peak"] = 0.0
            return None
        level = None
        for name, z_min, multiple in ALERT_LEVELS:
            if snr >= z_min and change >= step * multiple:
                level = name
                break
        if level is None:
            state["streak"] = 0
            return None
        state["streak"] += 1
        state["peak"] = max(state["peak"], change)
        # Require the change to survive consecutive samples, and require the channel
        # to have returned to ambient since its last alert.
        if state["streak"] < ALERT_HOLD or not state["armed"] or mono - state["last"] < ALERT_MIN_GAP:
            return None
        state["armed"] = False
        state["last"] = mono
        transient = self.transients[channel].snapshot()
        label = channel_label(channel)
        direction = "rose" if finite(deviation) > 0 else "fell"
        return self._emit_alert(
            channel=channel, severity=level, kind="magnitude",
            message=f"{label} {direction} {change:.3g} {unit} from its quiet baseline "
                    f"({snr:.0f}× the measured ambient noise)",
            deviation=deviation, unit=unit, state=transient["state"], z=snr)

    def _condition_alerts(self, channels, now):
        """Alerts that are not about magnitude at all: a channel that dropped out,
        started clipping, or drifted away from a reference it is still using. These
        matter as much as a spike and used to be reported nowhere."""
        for key, item in channels.items():
            previous = self.condition_state.setdefault(key, {"state": None, "clipped": False, "stale": False})
            label = channel_label(key)
            state = item["state"]
            if state != previous["state"]:
                # An optional channel that was never fitted is not a fault.
                if previous["state"] is not None and state in ("offline", "error", "stale"):
                    self._emit_alert(channel=key, severity="alert", kind="availability",
                                     message=f"{label} stopped reporting: {state}"
                                             + (f" — {item['message']}" if item.get("message") else ""),
                                     state=state)
                elif previous["state"] in ("offline", "error", "stale") and state == "connected":
                    self._emit_alert(channel=key, severity="notice", kind="availability",
                                     message=f"{label} is reporting again", state=state)
                previous["state"] = state
            clipped = bool(item.get("clipped"))
            if clipped and not previous["clipped"]:
                self._emit_alert(channel=key, severity="alert", kind="clipping",
                                 message=f"{label} is clipping: the reading is a lower bound, not a measurement",
                                 state="Clipped")
            previous["clipped"] = clipped
            stale = bool(item.get("baseline", {}).get("stale"))
            if stale and not previous["stale"]:
                offset = item["baseline"].get("stale_offset") or 0.0
                self._emit_alert(channel=key, severity="notice", kind="baseline",
                                 message=f"{label} quiet level has moved {offset:.3g} {item['unit']} away "
                                         f"from its lock; deviations are measured against a stale reference",
                                 state="Baseline stale")
            previous["stale"] = stale

    def _correlation(self, histories):
        matches = []
        keys = [key for key in histories if len(histories[key]) >= 6]
        for i, left in enumerate(keys):
            for right in keys[i + 1:]:
                lhs, rhs = histories[left], histories[right]
                right_times = [point[0] for point in rhs]
                end = min(lhs[-1][0], rhs[-1][0])
                pairs = []
                for t, value, _ in lhs:
                    if t < end - 8 or t > end:
                        continue
                    position = bisect_left(right_times, t)
                    candidates = rhs[max(0, position - 1):min(len(rhs), position + 1)]
                    sample = min(candidates, key=lambda entry: abs(entry[0] - t))
                    if abs(sample[0] - t) <= 0.3:
                        pairs.append((value, sample[1]))
                if len(pairs) < 6:
                    continue
                mx = statistics.fmean(a for a, _ in pairs)
                my = statistics.fmean(b for _, b in pairs)
                covariance = sum((a - mx) * (b - my) for a, b in pairs)
                denominator = math.sqrt(sum((a - mx) ** 2 for a, _ in pairs) * sum((b - my) ** 2 for _, b in pairs))
                if denominator > 1e-12:
                    matches.append({"channels": [left, right], "coefficient": covariance / denominator, "pairs": len(pairs), "max_alignment_seconds": 0.3})
        return matches

    def snapshot(self, now=None):
        now = time.monotonic() if now is None else float(now)
        with self.lock:
            channels = deepcopy(self.channels)
            histories = {key: list(value) for key, value in self.histories.items()}
            intervals_by_channel = {key: list(value) for key, value in self.intervals.items()}
            baselines = {key: value.snapshot() for key, value in self.baselines.items()}
            transient_values = {key: list(value.history) for key, value in self.transients.items()}
            profiles = {key: self.calibrations.get(key) for key in CHANNELS}
            last_mono = dict(self.last_mono)
            axial, vector = deepcopy(self.axial), deepcopy(self.vector)
            sequence, events = self.sequence, list(self.events)
            calibration_error = self.calibrations.error
        # The current-clamp path has been retired. Keep the internal key readable for
        # old calibration/archive files, but never publish or score it as a live channel.
        channels.pop("current", None)
        histories.pop("current", None)
        intervals_by_channel.pop("current", None)
        baselines.pop("current", None)
        transient_values.pop("current", None)
        profiles.pop("current", None)
        # Work on a coherent copy so correlation and statistics cannot hold acquisition.
        correlation = self._correlation(histories)
        positive_correlation = max([max(0.0, c["coefficient"]) for c in correlation] or [0.0])
        per_channel = {}
        for key, item in channels.items():
            profile = profiles[key]
            item["calibration"] = {"timestamp": profile.get("timestamp"), "calibrated": bool(profile),
                "method": profile.get("method", "Factory nominal scaling" if key == "ch1" else "None"), "profile": profile}
            item["baseline"] = baselines[key]
            item["transient"] = TransientWatch().snapshot(transient_values[key])
            item["history"] = [{"t": t, "deviation": v} for t, v, _ in histories[key]]
            age = now - last_mono.get(key, now)
            limit = max(CHANNELS[key]["stale"], float(item["metadata"].get("sweep_seconds", 0)) * 2.5)
            pause = self.expected_pause.get(key)
            if pause and now < pause["until"]:
                # Deliberate: report it as paused, with why, and raise no fault.
                if item["last_rx"] is not None and age > limit and item["state"] == "connected":
                    item["state"] = "paused"
                    item["message"] = pause["reason"]
            elif item["last_rx"] is not None and age > limit and item["state"] == "connected":
                item["state"] = "stale"
                item["message"] = "No recent sample"
            active = item["state"] == "connected"
            item["age_seconds"] = age if item["last_rx"] is not None else None
            intervals = intervals_by_channel[key]
            timing = 1.0
            if len(intervals) >= 4:
                mean = statistics.fmean(intervals)
                timing = 1.0 / (1 + statistics.pstdev(intervals) / max(mean, 1e-12))
            item["timing_quality"] = timing
            # Evidence quality has two regimes. With a signal present, the log SNR term
            # measures how clearly it stands above the ambient noise. At rest there is
            # nothing to stand above, so the channel is judged on resolution instead:
            # how far its measured noise floor sits below the ambient budget for that
            # sensor. A quiet channel can earn at most half the SNR credit, because
            # quiet is not proof of a working signal path, only of a clean one.
            snr_term = bounded(math.log1p(item["snr"]) / math.log(11))
            budget = NOISE_BUDGET.get(key, CHANNELS[key]["floor"] * 10)
            noise = float(item["baseline"].get("noise") or budget)
            quiet_term = 0.5 * bounded(1.0 - noise / (budget * 2.0))
            quiet = item["snr"] < 3
            terms = {"availability": float(active), "baseline": 0.3 if item["baseline"]["settling"] else 1.0,
                     "signal_to_noise": max(snr_term, quiet_term),
                     "clipping": float(not item["clipped"]), "timing": timing,
                     "transient": 0.75 if item["transient"]["state"] == "Bursty / transient" else 1.0,
                     "axial_consensus": (axial["agreement"] / 100) if key == "ch1" and axial else 1.0,
                     # Cross channel correlation is only testable while a signal exists; at
                     # rest it is neither confirmed nor contradicted, so partial credit.
                     "correlation": 0.8 if quiet else 0.5 + 0.5 * positive_correlation}
            score = sum(terms[k] * weight for k, weight in MTDI_WEIGHTS.items()) * 100 if active else 0.0
            per_channel[key] = {"score": score, "terms": {k: {"value": v * 100, "weight": MTDI_WEIGHTS[k], "contribution": v * MTDI_WEIGHTS[k] * 100} for k, v in terms.items()}}
            item["confidence"] = score
        # State, clipping and baseline staleness are only final here, after the loop
        # above has applied the stale-sample rule, so availability alerts are raised
        # from the snapshot rather than from ingest.
        with self.lock:
            self._condition_alerts(channels, now)
            events = list(self.events)
        available = [key for key, item in channels.items() if item["state"] == "connected"]
        snrs = {key: channels[key]["snr"] if key in available else 0 for key in channels}
        evidence = [f"{channel_label(key)}: deviation {channels[key]['deviation']:.3g} {channels[key]['unit']}, signal to ambient noise {snrs[key]:.1f}, {channels[key]['transient']['state']}" for key in available]
        condition = 'Sources offline'
        interpretation = 'No live measurement is available. Connect the configured sources to begin analysis.'
        rule = None
        if available:
            if any(channels[key]["baseline"]["settling"] for key in available):
                condition, interpretation = "Baseline settling", "The ambient reference is still forming. Wait for Baseline Lock before interpreting deviations."
            else:
                selected = None
                rule_by_id = {rule["id"]: rule for rule in SIGNATURE_RULES}
                if snrs["ch1"] >= 6 and "ch2" in available and snrs["ch2"] < 3:
                    selected = rule_by_id["ch1_dominance"]
                elif snrs["ch2"] >= 6 and "ch1" in available and snrs["ch1"] < 3:
                    selected = rule_by_id["ch2_dominance"]
                elif snrs["ch3"] >= 6 and all(key in available and snrs[key] < 3 for key in ("ch1", "ch2")):
                    selected = rule_by_id["radiated_rf"]
                elif sum(s >= 3 for s in snrs.values()) >= 2:
                    selected = rule_by_id["mixed"]
                elif max(snrs.values()) < 3:
                    selected = rule_by_id["ambient"]
                if selected:
                    condition, interpretation, rule = selected["condition"], selected["text"], selected["id"]
                else:
                    condition, interpretation = "Channel activity detected", 'At least one source changed. Additional live channels are needed to assess channel 2 versus channel 1 dominance.'
        simulated = any(channels[key].get("data_source") == "SIMULATED" for key in available)
        if simulated:
            condition = "SIMULATED · " + condition
            interpretation = "SIMULATED DATA. " + interpretation
        fitted = list(channels)
        completeness = len(available) / len(fitted)
        confidence = sum(per_channel[key]["score"] for key in fitted) / len(fitted)
        warnings = [f"{item['label']}: {item['state']}" for item in channels.values() if item["state"] != "connected"]
        warnings += [f"{item['label']}: clipping" for item in channels.values()
                     if item["clipped"] and item.get("metadata", {}).get("probe_health", "ok") == "ok"]
        warnings += [f"{item['label']}: probe {item['metadata']['probe_health']}" for item in channels.values()
                     if item.get("metadata", {}).get("probe_health", "ok") != "ok"]
        warnings += [f"{item['label']}: baseline stale by {item['baseline']['stale_offset']:.2f} {item['unit']} for {item['baseline'].get('stale_for', 0):.0f} s; relock or wait for auto relock"
                     for item in channels.values() if item.get("baseline", {}).get("stale")]
        if channels["ch1"]["state"] != "connected":
            if vector:
                vector["confidence"] = 0.0
                vector["bearing"] = None
            if axial:
                axial["confidence_contribution"] = 0.0
        return {"sequence": sequence, "timestamp": time.time(), "channels": channels,
                "fusion": {"data_source": "SIMULATED" if simulated else "HARDWARE", "condition": condition, "interpretation": interpretation, "confidence": confidence,
                           "evidence": evidence, "warnings": warnings, "rule": rule,
                           "breakdown": {"channels": per_channel, "weights": MTDI_WEIGHTS,
                                         "completeness": completeness * 100, "correlation": correlation,
                                         "method": "Heuristic evidence quality score (SNR when a signal is present, noise floor resolution at rest); not a calibrated probability"},
                           "axial": axial, "vector": vector},
                "events": events, "calibration_error": calibration_error,
                "rules": list(SIGNATURE_RULES)}
