"""Online forecasting."""


class Holt:
    """Double exponential smoothing: a level and a trend, updated one sample at a time.

        h = Holt(alpha=0.3, beta=0.1)
        for x in stream: h.update(x)
        h.forecast(steps=10)         # value expected 10 samples ahead
    """

    def __init__(self, alpha=0.3, beta=0.1):
        self.alpha, self.beta = float(alpha), float(beta)
        self.level = self.trend = None
        self.n = 0

    def update(self, x):
        x = float(x)
        self.n += 1
        if self.level is None:
            self.level, self.trend = x, 0.0
        elif self.n == 2:
            self.trend = x - self.level
            self.level = x
        else:
            previous = self.level
            self.level = self.alpha * x + (1 - self.alpha) * (self.level + self.trend)
            self.trend = self.beta * (self.level - previous) + (1 - self.beta) * self.trend
        return self.forecast(1)

    def forecast(self, steps=1):
        if self.level is None:
            return None
        return self.level + steps * self.trend


class OnlineLinear:
    """Least-squares line y = a + b·x, updated in O(1) per sample (no stored history).

    ``time_to(y)`` answers "when will the series reach this value?", e.g. a threshold.
    """

    def __init__(self):
        self.n = 0
        self.sx = self.sy = self.sxx = self.sxy = 0.0

    def update(self, x, y):
        x, y = float(x), float(y)
        self.n += 1
        self.sx += x
        self.sy += y
        self.sxx += x * x
        self.sxy += x * y
        return self.coefficients()

    def coefficients(self):
        denom = self.n * self.sxx - self.sx ** 2
        if self.n < 2 or denom == 0:
            return None
        b = (self.n * self.sxy - self.sx * self.sy) / denom
        a = (self.sy - b * self.sx) / self.n
        return a, b

    def predict(self, x):
        c = self.coefficients()
        return None if c is None else c[0] + c[1] * float(x)

    def time_to(self, y):
        c = self.coefficients()
        if c is None or c[1] == 0:
            return None
        return (float(y) - c[0]) / c[1]
