"""Supervised classifiers with a common interface.

    model = KNN(k=3).fit(X, y)          # X: list of feature lists, y: list of labels
    model.predict([1.2, 3.4])           # -> label
    model.predict_proba([1.2, 3.4])     # -> {label: probability}

All models standardise features with the training mean and standard deviation, so
features measured in different units can be mixed. ``reject`` on KNN and
NearestCentroid returns "UNKNOWN" for inputs far from everything seen in training,
which is the honest answer for a sample from a class that was never taught.
"""
from collections import Counter, defaultdict
import math
import statistics


class _Scaler:
    def fit(self, X):
        cols = list(zip(*X))
        self.mean = [statistics.fmean(c) for c in cols]
        self.sd = [statistics.pstdev(c) or 1.0 for c in cols]
        return self

    def __call__(self, row):
        return [(v - m) / s for v, m, s in zip(row, self.mean, self.sd)]


def _check(X, y=None):
    if not X:
        raise ValueError("no training samples")
    width = len(X[0])
    if any(len(r) != width for r in X):
        raise ValueError("every sample needs the same number of features")
    if y is not None and len(y) != len(X):
        raise ValueError("X and y lengths differ")
    return [[float(v) for v in r] for r in X]


def _dist(a, b):
    return math.sqrt(sum((p - q) ** 2 for p, q in zip(a, b)))


class KNN:
    def __init__(self, k=3, reject=None):
        self.k, self.reject = int(k), reject

    def fit(self, X, y):
        X = _check(X, y)
        self.scale = _Scaler().fit(X)
        self.points = [(self.scale(r), label) for r, label in zip(X, y)]
        return self

    def neighbours(self, row):
        z = self.scale([float(v) for v in row])
        return sorted(((_dist(z, p), label) for p, label in self.points), key=lambda t: t[0])[:self.k]

    def predict_proba(self, row):
        near = self.neighbours(row)
        weights = Counter()
        for d, label in near:
            weights[label] += 1.0 / (d + 1e-9)
        total = sum(weights.values())
        return {label: w / total for label, w in weights.items()}

    def predict(self, row):
        near = self.neighbours(row)
        if self.reject is not None and near[0][0] > self.reject:
            return "UNKNOWN"
        proba = self.predict_proba(row)
        return max(proba, key=proba.get)


class NearestCentroid:
    def __init__(self, reject=None):
        self.reject = reject

    def fit(self, X, y):
        X = _check(X, y)
        self.scale = _Scaler().fit(X)
        groups = defaultdict(list)
        for r, label in zip(X, y):
            groups[label].append(self.scale(r))
        self.centroids = {label: [statistics.fmean(c) for c in zip(*rows)] for label, rows in groups.items()}
        return self

    def distances(self, row):
        z = self.scale([float(v) for v in row])
        return {label: _dist(z, c) for label, c in self.centroids.items()}

    def predict_proba(self, row):
        inv = {label: 1.0 / (d + 1e-9) for label, d in self.distances(row).items()}
        total = sum(inv.values())
        return {label: w / total for label, w in inv.items()}

    def predict(self, row):
        d = self.distances(row)
        label = min(d, key=d.get)
        return "UNKNOWN" if self.reject is not None and d[label] > self.reject else label


class LogisticRegression:
    """Multinomial (softmax) logistic regression trained by full-batch gradient descent."""

    def __init__(self, lr=0.5, epochs=400, l2=1e-3):
        self.lr, self.epochs, self.l2 = float(lr), int(epochs), float(l2)

    def fit(self, X, y):
        X = _check(X, y)
        self.scale = _Scaler().fit(X)
        Z = [self.scale(r) + [1.0] for r in X]
        self.labels = sorted(set(y), key=str)
        index = {label: i for i, label in enumerate(self.labels)}
        k, d, n = len(self.labels), len(Z[0]), len(Z)
        self.W = [[0.0] * d for _ in range(k)]
        for _ in range(self.epochs):
            grad = [[0.0] * d for _ in range(k)]
            for z, label in zip(Z, y):
                p = self._softmax(z)
                for c in range(k):
                    err = p[c] - (1.0 if index[label] == c else 0.0)
                    for j in range(d):
                        grad[c][j] += err * z[j]
            for c in range(k):
                for j in range(d):
                    self.W[c][j] -= self.lr * (grad[c][j] / n + self.l2 * self.W[c][j])
        return self

    def _softmax(self, z):
        logits = [sum(w * v for w, v in zip(row, z)) for row in self.W]
        top = max(logits)
        exps = [math.exp(v - top) for v in logits]
        total = sum(exps)
        return [e / total for e in exps]

    def predict_proba(self, row):
        p = self._softmax(self.scale([float(v) for v in row]) + [1.0])
        return dict(zip(self.labels, p))

    def predict(self, row):
        proba = self.predict_proba(row)
        return max(proba, key=proba.get)


class GaussianNB:
    def fit(self, X, y):
        X = _check(X, y)
        groups = defaultdict(list)
        for r, label in zip(X, y):
            groups[label].append(r)
        n = len(X)
        self.stats = {}
        for label, rows in groups.items():
            cols = list(zip(*rows))
            self.stats[label] = (math.log(len(rows) / n),
                                 [statistics.fmean(c) for c in cols],
                                 [max(statistics.pvariance(c), 1e-9) for c in cols])
        return self

    def _log_likelihood(self, row):
        out = {}
        for label, (prior, means, variances) in self.stats.items():
            ll = prior
            for x, m, v in zip(row, means, variances):
                ll += -0.5 * math.log(2 * math.pi * v) - (x - m) ** 2 / (2 * v)
            out[label] = ll
        return out

    def predict_proba(self, row):
        ll = self._log_likelihood([float(v) for v in row])
        top = max(ll.values())
        exps = {label: math.exp(v - top) for label, v in ll.items()}
        total = sum(exps.values())
        return {label: e / total for label, e in exps.items()}

    def predict(self, row):
        proba = self.predict_proba(row)
        return max(proba, key=proba.get)
