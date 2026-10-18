"""K-means with k-means++ seeding and a fixed random seed (reproducible)."""
import math
import random


class KMeans:
    def __init__(self, k=3, iterations=100, seed=0):
        self.k, self.iterations, self.seed = int(k), int(iterations), seed

    @staticmethod
    def _d2(a, b):
        return sum((p - q) ** 2 for p, q in zip(a, b))

    def fit(self, X):
        X = [[float(v) for v in r] for r in X]
        if len(X) < self.k:
            raise ValueError("fewer samples than clusters")
        rng = random.Random(self.seed)
        centres = [rng.choice(X)]
        while len(centres) < self.k:
            d = [min(self._d2(x, c) for c in centres) for x in X]
            total = sum(d)
            if total == 0:
                centres.append(rng.choice(X))
                continue
            r, acc = rng.random() * total, 0.0
            for x, w in zip(X, d):
                acc += w
                if acc >= r:
                    centres.append(x)
                    break
        for _ in range(self.iterations):
            labels = [min(range(self.k), key=lambda i: self._d2(x, centres[i])) for x in X]
            new = []
            for i in range(self.k):
                members = [x for x, label in zip(X, labels) if label == i]
                new.append([sum(c) / len(members) for c in zip(*members)] if members else centres[i])
            if new == centres:
                break
            centres = new
        self.centres = centres
        self.labels = [min(range(self.k), key=lambda i: self._d2(x, centres[i])) for x in X]
        self.inertia = sum(self._d2(x, centres[label]) for x, label in zip(X, self.labels))
        return self

    def predict(self, row):
        row = [float(v) for v in row]
        return min(range(self.k), key=lambda i: self._d2(row, self.centres[i]))

    def distance(self, row):
        return math.sqrt(self._d2([float(v) for v in row], self.centres[self.predict(row)]))
