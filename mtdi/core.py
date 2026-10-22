"""The MTDI core: fusing the pillars into one score that can be taken apart.

Ported from the studio's AnalysisEngine.snapshot. The score is a weighted
index over eight named factors, computed per channel from measurable quantities,
then averaged over every channel the project declares (an offline channel scores
zero, so a missing sensor lowers the score instead of vanishing from it).

It is a heuristic evidence-quality score, not a calibrated probability, and it
says so wherever it is shown.
"""
import bisect
import math
import operator

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
    """Pearson correlation of deviation between every pair of channels, time aligned.

    Channels fed by the same source share their timestamps exactly; for them alignment is the
    identity, so each channel's window is centred once and a pair costs one dot product. Pairs
    on different clocks use the general nearest-sample alignment. Results are identical either way.
    Each history must be in ascending time order (the engine's always is)."""
    # HOURS-WASTED: 0.5 - 691 ms per snapshot at 128 channels, found by tools/pi/measure.py
    keys = [k for k in histories if len(histories[k]) >= 6]
    series = {k: ([p[0] for p in histories[k]], [p[1] for p in histories[k]]) for k in keys}
    # Only strictly increasing timestamps align one-to-one with themselves (duplicates would not).
    strict = {k: all(a < b for a, b in zip(t, t[1:])) for k, (t, _) in series.items()}
    centred = {}   # (channel, window start, window end) -> (values, deviations from mean, sum of squares)

    def window(k, lo, hi):
        got = centred.get((k, lo, hi))
        if got is None:
            vals = series[k][1][lo:hi]
            m = math.fsum(vals) / len(vals)
            dev = [v - m for v in vals]
            got = centred[(k, lo, hi)] = (vals, dev, sum(d ** 2 for d in dev))
        return got

    matches = []
    for i, left in enumerate(keys):
        lt, lv = series[left]
        for right in keys[i + 1:]:
            rt, rv = series[right]
            end = min(lt[-1], rt[-1])
            lo, hi = bisect.bisect_left(lt, end - span), bisect.bisect_right(lt, end)
            if strict[left] and len(lt) == len(rt) and lt[0] == rt[0] and lt[-1] == rt[-1] and lt == rt:
                n = hi - lo                                    # shared clock: every sample aligns with itself
                if n < 6:
                    continue
                _, dx, sxx = window(left, lo, hi)
                _, dy, syy = window(right, lo, hi)
                cov = sum(map(operator.mul, dx, dy))
                den = math.sqrt(sxx * syy)
            else:
                xs, ys = [], []
                last = len(rt) - 1
                for j in range(lo, hi):
                    t = lt[j]
                    pos = bisect.bisect_left(rt, t)
                    # nearest of rt[pos-1] and rt[pos]; on a tie the earlier one
                    k = pos - 1 if pos > last or (pos > 0 and abs(rt[pos - 1] - t) <= abs(rt[pos] - t)) else pos
                    if abs(rt[k] - t) <= align:
                        xs.append(lv[j])
                        ys.append(rv[k])
                n = len(xs)
                if n < 6:
                    continue
                mx, my = math.fsum(xs) / n, math.fsum(ys) / n
                cov = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
                den = math.sqrt(sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys))
            if den > 1e-12:
                matches.append({"channels": [left, right], "coefficient": cov / den, "pairs": n})
    return matches
