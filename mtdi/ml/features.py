"""Feature extraction from a window of samples."""
import cmath
import math
import statistics


def window_features(values):
    """Summary features of one window: the usual inputs to a classifier or clusterer."""
    v = [float(x) for x in values]
    if len(v) < 2:
        raise ValueError("need at least two samples")
    mean = statistics.fmean(v)
    sd = statistics.pstdev(v)
    centred = [x - mean for x in v]
    rms = math.sqrt(statistics.fmean(x * x for x in v))
    skew = 0.0 if sd == 0 else statistics.fmean(c ** 3 for c in centred) / sd ** 3
    kurt = 0.0 if sd == 0 else statistics.fmean(c ** 4 for c in centred) / sd ** 4 - 3.0
    crossings = sum(1 for a, b in zip(centred, centred[1:]) if (a < 0) != (b < 0))
    slope = None
    n = len(v)
    xm = (n - 1) / 2
    denom = sum((i - xm) ** 2 for i in range(n))
    slope = sum((i - xm) * c for i, c in enumerate(centred)) / denom
    return {"mean": mean, "sd": sd, "min": min(v), "max": max(v), "range": max(v) - min(v), "rms": rms,
            "skew": skew, "kurtosis": kurt, "zero_crossings": crossings, "slope": slope,
            "median": statistics.median(v)}


def _dft(values):
    n = len(values)
    mean = statistics.fmean(values)
    x = [v - mean for v in values]
    try:
        import numpy as np            # fast path when numpy is present; identical results
        return list(np.fft.rfft(np.asarray(x)))
    except ImportError:
        return [sum(x[t] * cmath.exp(-2j * math.pi * k * t / n) for t in range(n)) for k in range(n // 2 + 1)]


def band_power(values, rate, bands):
    """Power in each frequency band. ``bands``: {name: (low_hz, high_hz)}; ``rate`` in Hz."""
    bins = _dft([float(v) for v in values])
    n = len(values)
    out = {}
    for name, (lo, hi) in bands.items():
        out[name] = sum(abs(c) ** 2 for k, c in enumerate(bins) if lo <= k * rate / n < hi) / n
    return out


def dominant_frequency(values, rate):
    """The strongest frequency (Hz) in the window, excluding DC."""
    bins = _dft([float(v) for v in values])
    n = len(values)
    k = max(range(1, len(bins)), key=lambda i: abs(bins[i]))
    return k * rate / n
