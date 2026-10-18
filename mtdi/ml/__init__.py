"""MTDI machine learning: small, dependency-free algorithms that run where the data is.

Everything here is pure Python (numpy is never required), deterministic, and works one
sample at a time, so the same code runs on a laptop, a server or a single-board computer.

    streaming anomaly   ZScore, EWMA, MAD (robust), CUSUM, PageHinkley        mtdi.ml.anomaly
    classification      KNN, NearestCentroid, LogisticRegression, GaussianNB  mtdi.ml.classify
    clustering          KMeans (k-means++ seeding)                            mtdi.ml.cluster
    forecasting         Holt (level + trend), OnlineLinear (least squares)    mtdi.ml.forecast
    features            window stats, DFT band power, dominant frequency      mtdi.ml.features
    monitor             one detector per channel over live MTDI packets       mtdi.ml.monitor
"""
from .anomaly import CUSUM, EWMA, MAD, PageHinkley, ZScore
from .classify import GaussianNB, KNN, LogisticRegression, NearestCentroid
from .cluster import KMeans
from .features import band_power, dominant_frequency, window_features
from .forecast import Holt, OnlineLinear
from .monitor import Monitor

__all__ = ["ZScore", "EWMA", "MAD", "CUSUM", "PageHinkley", "KNN", "NearestCentroid", "LogisticRegression",
           "GaussianNB", "KMeans", "Holt", "OnlineLinear", "window_features", "band_power", "dominant_frequency",
           "Monitor"]
