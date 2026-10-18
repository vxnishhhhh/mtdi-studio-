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


class SimulatorAdapter(Adapter):
    data_source = "SIMULATED"

    def run(self):
        engine = self.engine
        # A channel with several interchangeable sources is simulated once, on its first.
        channels = [c for c in engine.project["channels"] if c["sources"][0] == self.id]
        if not channels:
            engine.set_source_state(self.id, "idle", "SIMULATED · no channels of its own")
            self.stop_event.wait()
            return
        rate = float(self.spec.get("rate", 0) or max([c.get("expected_rate") or 20 for c in channels] or [20]))
        rate = min(rate, 200.0)
        rng = random.Random(self.spec.get("seed", 7))
        engine.set_source_state(self.id, "connected", f"SIMULATED · {rate:g} lines/s")
        start, n = time.monotonic(), 0
        event_until, event_shift = 0.0, 0.0
        while not self.stop_event.is_set():
            t = time.monotonic() - start
            if t > event_until and rng.random() < 0.004:
                event_until, event_shift = t + rng.uniform(1.5, 4.0), rng.choice([-1, 1]) * rng.uniform(8, 20)
            values = {}
            for c in channels:
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
                    if sim.get("events", True) and t < event_until and i == 0:
                        v += event_shift * noise
                    s = scale_of(c, i) or 1.0
                    raw = (v - offset_of(c, i)) / s
                    rng_raw = c.get("raw_range")
                    if rng_raw:
                        raw = min(max(raw, rng_raw[0]), rng_raw[1])
                    values[key] = round(raw, 4)
            values["_SEQ"] = n
            engine.ingest_values(self.id, values, self.data_source)
            n += 1
            self.stop_event.wait(max(0.0, start + n / rate - time.monotonic()))
