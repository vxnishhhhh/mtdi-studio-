"""Streaming anomaly and change detection.

Every detector has the same interface:

    det = ZScore(threshold=3.0)
    for x in stream:
        result = det.update(x)      # {"score": float, "anomaly": bool, ...}

``score`` is in units of the detector's own threshold scale (a z-score, a CUSUM sum), so
results from different detectors can be shown side by side. Detectors warm up for
``warmup`` samples and never flag during warm-up.
"""
from collections import deque
import math
import statistics


class ZScore:
    """Rolling mean and standard deviation over a window (Welford within the window)."""

    def __init__(self, window=200, threshold=3.0, warmup=20):
        self.window, self.threshold, self.warmup = int(window), float(threshold), int(warmup)
        self.values = deque(maxlen=self.window)

    def update(self, x):
        x = float(x)
        n = len(self.values)
        if n >= max(2, self.warmup):
            mean = statistics.fmean(self.values)
            sd = statistics.pstdev(self.values)
            score = 0.0 if sd == 0 else (x - mean) / sd
        else:
            mean, sd, score = (statistics.fmean(self.values) if n else x), 0.0, 0.0
        anomaly = n >= self.warmup and abs(score) >= self.threshold
        if not anomaly:                    # anomalies do not drag the reference toward themselves
            self.values.append(x)
        return {"score": score, "anomaly": anomaly, "mean": mean, "sd": sd}


class EWMA:
    """Exponentially weighted mean and variance; reacts in about 1/alpha samples."""

    def __init__(self, alpha=0.05, threshold=3.0, warmup=20):
        self.alpha, self.threshold, self.warmup = float(alpha), float(threshold), int(warmup)
        self.mean, self.var, self.n = None, 0.0, 0

    def update(self, x):
        x = float(x)
        self.n += 1
        if self.mean is None:
            self.mean = x
            return {"score": 0.0, "anomaly": False, "mean": x, "sd": 0.0}
        sd = math.sqrt(self.var)
        score = 0.0 if sd == 0 else (x - self.mean) / sd
        anomaly = self.n > self.warmup and abs(score) >= self.threshold
        if not anomaly:
            delta = x - self.mean
            self.mean += self.alpha * delta
            self.var = (1 - self.alpha) * (self.var + self.alpha * delta * delta)
        return {"score": score, "anomaly": anomaly, "mean": self.mean, "sd": math.sqrt(self.var)}


class MAD:
    """Median and median absolute deviation: robust to the outliers it is looking for."""

    def __init__(self, window=200, threshold=3.5, warmup=20):
        self.window, self.threshold, self.warmup = int(window), float(threshold), int(warmup)
        self.values = deque(maxlen=self.window)

    def update(self, x):
        x = float(x)
        if len(self.values) >= max(3, self.warmup):
            med = statistics.median(self.values)
            mad = 1.4826 * statistics.median(abs(v - med) for v in self.values)
            score = 0.0 if mad == 0 else (x - med) / mad
        else:
            med, mad, score = x, 0.0, 0.0
        anomaly = len(self.values) >= self.warmup and abs(score) >= self.threshold
        if not anomaly:
            self.values.append(x)
        return {"score": score, "anomaly": anomaly, "median": med, "mad": mad}


class CUSUM:
    """Two-sided cumulative sum: catches small, persistent shifts a z-score misses.

    ``drift`` (k) and ``threshold`` (h) are in standard deviations of the warm-up data. The
    reference needs enough warm-up samples: a mean estimated from too few biases every
    later z and shortens the time between false alarms.
    """

    def __init__(self, drift=0.5, threshold=8.0, warmup=100):
        self.k, self.h, self.warmup = float(drift), float(threshold), int(warmup)
        self.reference = []
        self.mean = self.sd = None
        self.pos = self.neg = 0.0

    def update(self, x):
        x = float(x)
        if self.mean is None:
            self.reference.append(x)
            if len(self.reference) >= self.warmup:
                self.mean = statistics.fmean(self.reference)
                self.sd = statistics.pstdev(self.reference) or 1e-12
            return {"score": 0.0, "anomaly": False, "direction": None}
        z = (x - self.mean) / self.sd
        self.pos = max(0.0, self.pos + z - self.k)
        self.neg = max(0.0, self.neg - z - self.k)
        score = max(self.pos, self.neg)
        direction = "up" if self.pos >= self.h else "down" if self.neg >= self.h else None
        if direction:
            self.pos = self.neg = 0.0      # restart after an alarm
        return {"score": score, "anomaly": direction is not None, "direction": direction}


class PageHinkley:
    """Page-Hinkley test for a change in the mean (concept drift)."""

    def __init__(self, delta=0.005, threshold=50.0, alpha=0.9999, warmup=30):
        self.delta, self.lam, self.alpha, self.warmup = float(delta), float(threshold), float(alpha), int(warmup)
        self.n, self.mean, self.cum, self.min_cum = 0, 0.0, 0.0, 0.0

    def update(self, x):
        x = float(x)
        self.n += 1
        self.mean += (x - self.mean) / self.n
        self.cum = self.alpha * self.cum + (x - self.mean - self.delta)
        self.min_cum = min(self.min_cum, self.cum)
        score = self.cum - self.min_cum
        change = self.n > self.warmup and score > self.lam
        if change:
            self.n, self.mean, self.cum, self.min_cum = 0, 0.0, 0.0, 0.0
        return {"score": score, "anomaly": change}
