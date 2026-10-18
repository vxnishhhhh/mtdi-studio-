"""Batch analysis of a recorded session: the reference both implementations must match.

One rule: everything is recomputed from the same recorded samples by an
independent implementation, and two implementations agreeing on one capture is the
reason to believe either. `matlab/+mtdi/analyze.m` computes exactly this, field for
field, in MATLAB.

    python -m mtdi analyze projects/x session.jsonl      -> JSON summary per channel

Per channel: samples, mean, median, robust noise σ = 1.4826 × MAD of the physical
magnitude, LOD = 3σ, LOQ = 10σ, achieved rate, and the clipped share. For a vector
channel the magnitude is the Euclidean length of the scaled axes. Transforms
(ac_rms) are not applied: this summarises what was recorded, not what was derived.
"""
import json
import math
import pathlib
import statistics

from .project import offset_of, scale_of


def read_recording(path):
    rows = []
    for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def analyze(project, rows):
    out = {}
    for ch in project["channels"]:
        t, mags, clipped = [], [], 0
        for row in rows:
            if row.get("source") not in ch["sources"]:
                continue
            values = row.get("values", {})
            if not all(k in values for k in ch["keys"]):
                continue
            raw = [float(values[k]) for k in ch["keys"]]
            rng = ch.get("raw_range")
            if rng and any(v <= rng[0] or v >= rng[1] for v in raw):
                clipped += 1
            phys = [r * scale_of(ch, i) + offset_of(ch, i) for i, r in enumerate(raw)]
            mags.append(math.sqrt(sum(p * p for p in phys)) if len(phys) > 1 else phys[0])
            t.append(float(row["t"]))
        n = len(mags)
        if n == 0:
            out[ch["id"]] = {"samples": 0}
            continue
        median = statistics.median(mags)
        noise = 1.4826 * statistics.median(abs(m - median) for m in mags)
        span = (t[-1] - t[0]) if n > 1 else 0.0
        out[ch["id"]] = {
            "samples": n, "mean": statistics.fmean(mags), "median": median, "noise": noise,
            "lod": 3 * noise, "loq": 10 * noise,
            "rate": (n - 1) / span if span > 0 else 0.0,
            "clipped_share": clipped / n, "unit": ch["unit"],
        }
    return out
