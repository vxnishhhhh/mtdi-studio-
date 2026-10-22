"""Small float statistics for hot paths (every channel, every snapshot).

The standard library's statistics.pvariance/pstdev are exact (they convert every value to a
fraction), which costs milliseconds per channel at live rates. These agree with them to about
1e-15 relative and are shifted by the first sample, so a large common offset keeps its spread.
"""
import math


def pvariance(values):
    """Population variance of a non-empty sequence of floats."""
    n = len(values)
    if n < 2:
        return 0.0
    ref = values[0]
    shifted = [v - ref for v in values]
    mean = math.fsum(shifted) / n
    return math.fsum((d - mean) ** 2 for d in shifted) / n


def pstdev(values):
    return math.sqrt(pvariance(values))
