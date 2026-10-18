"""Pillar 01 · Environmental Intelligence — learn, lock, compare.

Every channel learns a reference from the real environment it is in, then that
reference can be locked. A baseline that keeps drifting toward a new signal
quietly erases the very change you are trying to see, so a locked baseline never
adapts on its own; it is re-learned only when asked, or when the stale-lock watch
proves the quiet level itself has moved.

Learned references can be saved as named environments (a room, a bench, a site)
and recalled later to compare against. A saved environment must come from real
measurements: anything recorded from the simulator is refused.

BaselineLock and TransientWatch come from the studio's analysis engine with every
instrument constant removed: each number they need comes from the channel's own
manifest entry, so the same code serves a three-axis sensor, a single probe, an
ultrasonic range finder, a server metric or anything else that emits numbers.
"""
from collections import deque
import json
import math
import pathlib
import re
import statistics
import time


class BaselineLock:
    """A time-window median learns quiet values and rejects temporary excursions."""

    def __init__(self, window=10.0, noise_floor=0.01):
        self.window = float(window)
        self.floor = float(noise_floor)
        self.frozen = False
        self.reset()

    def reset(self):
        self.samples = deque(maxlen=3001)
        self.started = None
        self.last_added = None
        self.value = None
        self.noise = self.floor
        self.settling = True
        self.pinned = False          # value came from a saved environment, not from learning
        self.rejected = 0
        self.accepted = 0
        # Stale-lock watch: when nearly everything is refused and the refused values
        # are themselves steady, the world has moved and the lock is stale.
        self.refused = deque(maxlen=600)
        self.recent = deque(maxlen=600)
        self.stale = False
        self.stale_offset = 0.0
        self.stale_since = None

    def pin(self, value, noise):
        """Adopt a saved reference and lock it."""
        self.reset()
        self.value = float(value)
        self.noise = max(self.floor, float(noise))
        self.frozen = True
        self.pinned = True
        self.settling = False

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
        if not self.pinned:
            self.settling = (timestamp - self.started) < self.window or self.accepted < 5
        if valid and (self.last_added is None or timestamp - self.last_added >= 0.19):
            quiet = self.settling or abs(value - self.value) <= max(6 * self.noise, 6 * self.floor)
            if quiet and not self.frozen:
                self.samples.append((timestamp, value))
                self.accepted += 1
                self.last_added = timestamp
                while len(self.samples) > 1 and self.samples[0][0] < timestamp - self.window:
                    self.samples.popleft()
                values = [v for _, v in self.samples]
                centre = statistics.median(values)
                self.value = centre
                self.noise = max(self.floor, 1.4826 * statistics.median(abs(v - centre) for v in values))
            elif not quiet:
                self.rejected += 1
            if self.frozen:
                self.last_added = timestamp
            self._watch(value, timestamp, quiet)
        return value - self.value

    def snapshot(self):
        return {"value": self.value, "settling": self.settling, "frozen": self.frozen, "pinned": self.pinned,
                "window": self.window, "noise": self.noise, "rejected": self.rejected,
                "samples": len(self.samples), "stale": self.stale, "stale_offset": self.stale_offset,
                "stale_since": self.stale_since}


class TransientWatch:
    """Classify a bounded time history against measured baseline variation."""

    def __init__(self, span=12.0):
        self.span = span
        self.history = deque(maxlen=1200)

    def update(self, timestamp, deviation, noise):
        self.history.append((timestamp, deviation, noise))
        while self.history and self.history[0][0] < timestamp - self.span:
            self.history.popleft()

    def snapshot(self):
        values = list(self.history)
        if not values:
            return {"state": "Unavailable", "variance": None, "threshold": None}
        deviations = [v for _, v, _ in values]
        noise = max(values[-1][2], 1e-12)
        variance = statistics.pvariance(deviations) if len(deviations) > 1 else 0.0
        threshold = (3.0 * noise) ** 2
        active = [abs(value) > 3 * local for _, value, local in values]
        duration = max(0.0, values[-1][0] - values[0][0])
        # Duration weights make the classification independent of sample rate.
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


class ChannelEnvironment:
    """The environment of one channel: a baseline per axis, deviation, SNR, consensus.

    A scalar channel has one axis. A vector channel keeps one baseline per axis and
    reports the deviation as the length of the per-axis change, with axial consensus:
    whether the axes keep sharing the change the same way (the studio's channel 1
    vector logic, for any vector sensor).
    """

    def __init__(self, spec, window):
        self.spec = spec
        n = len(spec["keys"])
        self.axes = [BaselineLock(window, spec["noise_floor"] / math.sqrt(n)) for _ in range(n)]
        self.transient = TransientWatch()
        self.shares = None
        self.agreement = 1.0
        self.last_t = None
        self.state = {}

    def update(self, vector, t, valid=True):
        dt = (t - self.last_t) if self.last_t is not None else 0.0
        self.last_t = t
        delta = [b.update(v, t, valid) for b, v in zip(self.axes, vector)]
        noise = max(self.spec["noise_floor"], math.sqrt(sum(b.noise ** 2 for b in self.axes)))
        deviation = math.sqrt(sum(d * d for d in delta)) if len(delta) > 1 else delta[0]
        if len(delta) > 1:
            energy = sum(d * d for d in delta)
            if energy > noise ** 2:
                shares = [d * d / energy for d in delta]
                disagreement = 0.5 * sum(abs(a - b) for a, b in zip(shares, self.shares)) if self.shares else 0.0
                alpha = 1 - math.exp(-max(dt, 0.02) / 1.5)
                self.shares = shares if self.shares is None else [a + alpha * (b - a) for a, b in zip(self.shares, shares)]
                self.agreement = 1.0 - disagreement
        snr = abs(deviation) / max(noise, 1e-12)
        self.transient.update(t, deviation, noise)
        self.state = {"deviation": deviation, "delta": delta, "noise": noise, "snr": snr,
                      "settling": any(b.settling for b in self.axes)}
        return self.state

    def snapshot(self, now=None):
        stale = [b for b in self.axes if b.stale]
        stale_since = min((b.stale_since for b in stale), default=None)
        return {
            **self.state,
            "baseline": [b.value for b in self.axes],
            "frozen": all(b.frozen for b in self.axes),
            "pinned": all(b.pinned for b in self.axes),
            "settling": any(b.settling for b in self.axes),
            "stale": bool(stale),
            "stale_offset": math.sqrt(sum(b.stale_offset ** 2 for b in stale)) if stale else 0.0,
            "stale_for": (now - stale_since) if (stale and now is not None and stale_since is not None) else 0.0,
            "agreement": self.agreement if len(self.axes) > 1 else None,
            "transient": self.transient.snapshot(),
            "window": self.axes[0].window,
        }

    def learn(self):
        for b in self.axes:
            b.frozen = False
            b.reset()
        self.shares, self.agreement = None, 1.0

    def lock(self, frozen=True):
        for b in self.axes:
            b.frozen = frozen
            if not frozen:
                b.pinned = False

    def reference(self):
        return {"baseline": [b.value for b in self.axes], "noise": [b.noise for b in self.axes]}

    def pin(self, reference):
        for b, value, noise in zip(self.axes, reference["baseline"], reference["noise"]):
            b.pin(value, noise)


_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _\-]{0,47}$")


class EnvironmentLibrary:
    """Named, saved environments for one project (projects/<id>/environments/*.json)."""

    def __init__(self, folder):
        self.folder = pathlib.Path(folder)

    def _file(self, name):
        if not _NAME.match(name or ""):
            raise ValueError("environment names use letters, digits, spaces, - and _ (max 48)")
        return self.folder / (name.strip().replace(" ", "_") + ".json")

    def names(self):
        if not self.folder.exists():
            return []
        return sorted(p.stem for p in self.folder.glob("*.json"))

    def save(self, name, channels, sources, absent=()):
        """channels: {id: ChannelEnvironment}; sources: {id: data_source label};
        absent: optional channels left out because they never reported."""
        simulated = [cid for cid, src in sources.items() if src == "SIMULATED"]
        if simulated:
            raise ValueError("refused: simulated data is not a real environment (" + ", ".join(simulated) + ")")
        unready = [cid for cid, env in channels.items() if env.snapshot()["settling"] or env.axes[0].value is None]
        if unready:
            raise ValueError("refused: these channels have not learned a baseline yet: " + ", ".join(unready))
        record = {"name": name, "saved_at": time.time(), "mtdi": "5.0",
                  "sources": sources, "channels": {cid: env.reference() for cid, env in channels.items()},
                  "absent": list(absent)}
        file = self._file(name)
        file.parent.mkdir(parents=True, exist_ok=True)
        tmp = file.with_suffix(".tmp")
        tmp.write_text(json.dumps(record, indent=2), encoding="utf-8")
        tmp.replace(file)
        return record

    def load(self, name):
        return json.loads(self._file(name).read_text(encoding="utf-8"))
