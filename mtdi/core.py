"""The MTDI core: fusing the pillars into one score that can be taken apart.

Ported from Inductra Vaion's AnalysisEngine.snapshot. The score is a weighted
index over eight named factors, computed per channel from measurable quantities,
then averaged over every channel the project declares (an offline channel scores
zero, so a missing sensor lowers the score instead of vanishing from it).

It is a heuristic evidence-quality score, not a calibrated probability, and it
says so wherever it is shown.
"""
import bisect
import math
import statistics

DEFAULT_WEIGHTS = {"availability": 0.20, "baseline": 0.15, "signal_to_noise": 0.20,
                   "clipping": 0.15, "timing": 0.10, "transient": 0.10,
                   "axial_consensus": 0.05, "correlation": 0.05}
FACTOR_LABELS = {"availability": "Availability", "baseline": "Baseline", "signal_to_noise": "Signal to noise",
                 "clipping": "Clipping", "timing": "Timing", "transient": "Transient behaviour",
                 "axial_consensus": "Axial consensus", "correlation": "Cross-channel correlation"}
METHOD = ("Heuristic evidence quality score (SNR when a signal is present, noise-floor resolution "
          "at rest); not a calibrated probability")


def weights_for(project):
    w = dict(DEFAULT_WEIGHTS)
    w.update({k: float(v) for k, v in project.get("weights", {}).items() if k in DEFAULT_WEIGHTS})
    total = sum(w.values())
    return {k: v / total for k, v in w.items()} if total > 0 else dict(DEFAULT_WEIGHTS)


def channel_terms(spec, evidence, env, positive_correlation):
    """The eight factors for one channel, each in 0..1."""
    active = evidence["state"] == "connected"
    snr = env.get("snr") or 0.0
    snr_term = min(1.0, math.log1p(snr) / math.log(11))
    # At rest there is nothing to stand above the noise, so the channel is judged on
    # resolution instead, worth at most half the SNR credit: quiet is proof of a clean
    # signal path, not of a working one.
    noise = env.get("noise") or spec["noise_budget"]
    quiet_term = 0.5 * max(0.0, min(1.0, 1.0 - noise / (spec["noise_budget"] * 2.0)))
    quiet = snr < 3
    agreement = env.get("agreement")
    return {
        "availability": float(active),
        "baseline": 0.3 if env.get("settling", True) else 1.0,
        "signal_to_noise": max(snr_term, quiet_term),
        "clipping": float(not evidence["clipped"]),
        "timing": evidence["timing"],
        "transient": 0.75 if env.get("transient", {}).get("state") == "Bursty / transient" else 1.0,
        "axial_consensus": agreement if agreement is not None else 1.0,
        # Correlation is only testable while a signal exists; at rest it is neither
        # confirmed nor contradicted, so partial credit.
        "correlation": 0.8 if quiet else 0.5 + 0.5 * positive_correlation,
    }


def score(terms, weights, active):
    return sum(terms[k] * w for k, w in weights.items()) * 100 if active else 0.0


def correlation(histories, span=8.0, align=0.3):
    """Pearson correlation of deviation between every pair of channels, time aligned."""
    matches = []
    keys = [k for k in histories if len(histories[k]) >= 6]
    for i, left in enumerate(keys):
        for right in keys[i + 1:]:
            lhs, rhs = histories[left], histories[right]
            times = [p[0] for p in rhs]
            end = min(lhs[-1][0], rhs[-1][0])
            pairs = []
            for t, value in lhs:
                if t < end - span or t > end:
                    continue
                pos = bisect.bisect_left(times, t)
                near = rhs[max(0, pos - 1):min(len(rhs), pos + 1)]
                sample = min(near, key=lambda e: abs(e[0] - t))
                if abs(sample[0] - t) <= align:
                    pairs.append((value, sample[1]))
            if len(pairs) < 6:
                continue
            mx = statistics.fmean(a for a, _ in pairs)
            my = statistics.fmean(b for _, b in pairs)
            cov = sum((a - mx) * (b - my) for a, b in pairs)
            den = math.sqrt(sum((a - mx) ** 2 for a, _ in pairs) * sum((b - my) ** 2 for _, b in pairs))
            if den > 1e-12:
                matches.append({"channels": [left, right], "coefficient": cov / den, "pairs": len(pairs)})
    return matches
