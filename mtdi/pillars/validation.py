"""Pillar 00 · Validation Chamber — evidence that a channel can be believed.

Before anything is interpreted, each channel has to prove it is present, fresh,
on time and inside its measurable range. Nothing here depends on what the sensor
measures: it works from arrival times, the declared raw range, the declared
expected rate and the noise the Environmental Intelligence pillar measured.

Detection limits follow one rule: derived from the channel's own
measured noise, LOD = 3σ and LOQ = 10σ. Never typed in.
"""
from collections import deque
import statistics

from .. import stats

DATA_SOURCES = ("HARDWARE", "REPLAY", "SIMULATED", "SOFTWARE")


class ChannelEvidence:
    def __init__(self, spec):
        self.spec = spec
        self.count = 0
        self.last_rx = None            # monotonic time of the newest sample
        self.last_wall = None
        self.intervals = deque(maxlen=200)
        self.clips = deque(maxlen=200)
        self.rejected_lines = 0
        self.data_source = None
        self.seq_gaps = 0
        self.last_seq = None

    def record(self, t, wall, clipped, data_source, seq=None):
        if self.last_rx is not None and t > self.last_rx:
            self.intervals.append(t - self.last_rx)
        self.last_rx, self.last_wall = t, wall
        self.count += 1
        self.clips.append(bool(clipped))
        self.data_source = data_source
        if seq is not None:
            if self.last_seq is not None and seq > self.last_seq + 1:
                self.seq_gaps += int(seq - self.last_seq - 1)
            self.last_seq = seq

    def snapshot(self, now, noise=None):
        spec = self.spec
        age = (now - self.last_rx) if self.last_rx is not None else None
        if self.last_rx is None:
            state = "waiting"
        elif age > spec["stale_after"]:
            state = "stale"
        else:
            state = "connected"
        intervals = list(self.intervals)
        rate = (len(intervals) / sum(intervals)) if intervals and sum(intervals) > 0 else 0.0
        timing = 1.0
        if len(intervals) >= 4:
            mean = statistics.fmean(intervals)
            timing = 1.0 / (1 + stats.pstdev(intervals) / max(mean, 1e-12))
        expected = spec.get("expected_rate")
        rate_ratio = (rate / expected) if expected and rate else None
        clip_share = (sum(self.clips) / len(self.clips)) if self.clips else 0.0
        out = {
            "state": state, "age": age, "samples": self.count, "rate": rate,
            "expected_rate": expected, "rate_ratio": rate_ratio, "timing": timing,
            "clipped": bool(self.clips and self.clips[-1]), "clip_share": clip_share,
            "data_source": self.data_source or "—", "sequence_gaps": self.seq_gaps,
        }
        if noise is not None:
            out["lod"] = 3 * noise
            out["loq"] = 10 * noise
        return out


def clipped(spec, raw_values):
    """A raw value at either end of the declared range is a lower bound, not a reading."""
    rng = spec.get("raw_range")
    if not rng:
        return False
    lo, hi = rng
    return any(v <= lo or v >= hi for v in raw_values)
