"""Declared-simulated data, generated from the manifest itself.

Every value carries data_source SIMULATED: the interface watermarks it, NVTRA
prefixes its interpretation with it, the recorder skips it, and Environmental
Intelligence refuses to save it as an environment. It exists so a project can be
integrated and its interface checked before the hardware is on the bench.

Values are produced in RAW key units (the inverse of the channel's scale and
offset), so the whole pipeline is exercised exactly as real firmware would.

Per channel, optional "simulate": {"mean": [...], "noise": n, "wave": {"amp": a, "hz": f},
"events": true} in physical units. Without it, a quiet signal at the noise floor.
"""
import math
import random
import time

from . import Adapter
from ..project import offset_of, scale_of


class Signal:
    """The simulated values for a set of channels at time t (raw key units)."""

    def __init__(self, channels, seed=7):
        self.channels = channels
        self.rng = random.Random(seed)
        self.event_until, self.event_shift = 0.0, 0.0
        self.n = 0

    def values(self, t):
        rng = self.rng
        if t > self.event_until and rng.random() < 0.004:
            self.event_until, self.event_shift = t + rng.uniform(1.5, 4.0), rng.choice([-1, 1]) * rng.uniform(8, 20)
        values = {}
        for c in self.channels:
            sim = c.get("simulate", {})
            n_axes = len(c["keys"])
            mean = sim.get("mean", [0.0] * n_axes)
            mean = mean if isinstance(mean, list) else [mean] * n_axes
            noise = sim.get("noise", c["noise_floor"])
            wave = sim.get("wave")
            for i, key in enumerate(c["keys"]):
                v = mean[i] + rng.gauss(0, noise)
                if wave:
                    v += wave.get("amp", 0) * math.sin(2 * math.pi * wave.get("hz", 1) * t + i)
                if sim.get("events", True) and t < self.event_until and i == 0:
                    v += self.event_shift * noise
                raw = (v - offset_of(c, i)) / (scale_of(c, i) or 1.0)
                rng_raw = c.get("raw_range")
                if rng_raw:
                    raw = min(max(raw, rng_raw[0]), rng_raw[1])
                values[key] = round(raw, 4)
        values["_SEQ"] = self.n
        self.n += 1
        return values


def channels_of(project, source_id):
    """A channel with several interchangeable sources is simulated once, on its first."""
    return [c for c in project["channels"] if c["sources"][0] == source_id]


def rate_of(spec, channels):
    return min(float(spec.get("rate", 0) or max([c.get("expected_rate") or 20 for c in channels] or [20])), 200.0)


class SimulatorAdapter(Adapter):
    data_source = "SIMULATED"

    def run(self):
        engine = self.engine
        channels = channels_of(engine.project, self.id)
        if not channels:
            engine.set_source_state(self.id, "idle", "SIMULATED · no channels of its own")
            self.stop_event.wait()
            return
        rate = rate_of(self.spec, channels)
        signal = Signal(channels, self.spec.get("seed", 7))
        engine.set_source_state(self.id, "connected", f"SIMULATED · {rate:g} lines/s")
        start = time.monotonic()
        while not self.stop_event.is_set():
            engine.ingest_values(self.id, signal.values(time.monotonic() - start), self.data_source)
            self.stop_event.wait(max(0.0, start + signal.n / rate - time.monotonic()))
