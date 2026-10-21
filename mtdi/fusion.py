"""Environmental Intelligence 2.0: sensor fusion and calibration (S1-11, owner brief).

MTDI 4 learned one baseline for one sensor at a time and had no calibration. This module adds
the two things the whiteboard asked for:

* fusion    combine several sensors (or several readings) into one better estimate, with an
            honest uncertainty: inverse-variance fusion, a 1-D Kalman filter, and a
            complementary filter (fast sensor + slow sensor, e.g. gyro + accelerometer)
* calibration  fit a sensor against a reference: two-point offset/gain, least-squares gain and
            offset over many points, and linear temperature compensation; apply and save it

The link to the Validation Chamber (ADR 0007) runs both ways: a fused estimate carries its
variance, so Validation can turn it into detection limits (LOD = 3 sigma), and Validation's
noise measurements feed back in as the per-sensor variances used here.

Pure Python on purpose: it runs on a Pi 5, inside the studio, and in an adopted project with
no extra installs. MATLAB twins can follow in matlab/+mtdi (S1-13).
(Aether: this is the file where two wrong sensors become one slightly less wrong sensor.
That is all engineering is. Hours lost to sign errors in the Kalman update: 0.75.)
"""
import json
import math
import pathlib


# ── fusion ──────────────────────────────────────────────────────────────────
def fuse(readings):
    """Inverse-variance weighted fusion of independent readings of the same quantity.

    readings: [(value, variance), ...] with variance > 0. Returns (value, variance).
    The fused variance is never larger than the best single sensor's: that is the point.
    """
    pts = [(float(v), float(var)) for v, var in readings if v is not None]
    if not pts:
        raise ValueError("fuse() needs at least one reading")
    if any(not (math.isfinite(v) and math.isfinite(var)) or var <= 0 for v, var in pts):
        raise ValueError("readings must be finite and every variance finite and > 0 "
                         "(use the sensor's measured noise, sigma squared)")
    weight = sum(1.0 / var for _, var in pts)
    return sum(v / var for v, var in pts) / weight, 1.0 / weight


class Kalman1D:
    """Scalar Kalman filter for a slowly changing quantity (random-walk model).

    q: process variance per step (how fast the truth may move); r: measurement variance.
    update(z, r=None) accepts a per-reading variance, so several sensors can feed one filter.
    """

    def __init__(self, q=1e-4, r=1.0, x0=None, p0=1e3):
        if q < 0 or r <= 0:
            raise ValueError("q must be >= 0 and r > 0")
        self.q, self.r, self.x, self.p = float(q), float(r), x0, float(p0)

    def update(self, z, r=None):
        r = self.r if r is None else float(r)
        if not math.isfinite(r) or r <= 0 or not math.isfinite(float(z)):
            raise ValueError("the reading must be finite and its variance finite and > 0")
        if self.x is None:
            self.x, self.p = float(z), r
            return self.x, self.p
        self.p += self.q                        # predict: the truth may have moved
        k = self.p / (self.p + r)               # gain: trust in the new reading
        self.x += k * (float(z) - self.x)       # correct
        self.p *= (1.0 - k)
        return self.x, self.p


class Complementary:
    """Complementary filter: integrate a fast rate sensor, correct drift with a slow absolute one.

    angle = alpha * (angle + rate * dt) + (1 - alpha) * absolute. alpha near 1 trusts the rate
    sensor over short times; the time constant is tau = alpha * dt / (1 - alpha).
    """

    def __init__(self, alpha=0.98, x0=0.0):
        if not 0.0 <= alpha < 1.0:
            raise ValueError("alpha must be in [0, 1)")
        self.alpha, self.x = float(alpha), float(x0)

    def update(self, rate, absolute, dt):
        self.x = self.alpha * (self.x + float(rate) * float(dt)) + (1.0 - self.alpha) * float(absolute)
        return self.x


# ── calibration ─────────────────────────────────────────────────────────────
class Calibration:
    """true = gain * raw + offset + temp_coeff * (temperature - temp_ref). Fit, apply, save, load."""

    def __init__(self, gain=1.0, offset=0.0, temp_coeff=0.0, temp_ref=25.0, residual_sd=None, method="identity", n=0,
                 temperature_key=None):
        self.gain, self.offset = float(gain), float(offset)
        self.temperature_key = temperature_key   # protocol key carrying temperature, so a saved fit is usable as-is
        self.temp_coeff, self.temp_ref = float(temp_coeff), float(temp_ref)
        self.residual_sd, self.method, self.n = residual_sd, method, int(n)

    def apply(self, raw, temperature=None):
        value = self.gain * float(raw) + self.offset
        if temperature is not None and self.temp_coeff:
            value += self.temp_coeff * (float(temperature) - self.temp_ref)
        return value

    # Two known points (e.g. 0 and full scale): exact offset and gain, no noise estimate.
    @classmethod
    def two_point(cls, raw_low, true_low, raw_high, true_high):
        if raw_high == raw_low:
            raise ValueError("the two calibration points need different raw readings")
        gain = (true_high - true_low) / (raw_high - raw_low)
        return cls(gain=gain, offset=true_low - gain * raw_low, method="two-point", n=2)

    # Many paired readings against a reference instrument: least squares.
    @classmethod
    def fit(cls, raw, reference, temperature=None, temp_ref=25.0, temperature_key=None):
        x = [float(v) for v in raw]
        y = [float(v) for v in reference]
        if len(x) != len(y) or len(x) < 3:
            raise ValueError("need at least 3 paired readings of equal length")
        if temperature is None:
            gain, offset = _least_squares_line(x, y)
            cal = cls(gain=gain, offset=offset, method="least-squares", n=len(x))
        else:
            t = [float(v) - temp_ref for v in temperature]
            if len(t) != len(x):
                raise ValueError("temperature must pair with every reading")
            gain, coeff, offset = _least_squares_plane(x, t, y)
            cal = cls(gain=gain, offset=offset, temp_coeff=coeff, temp_ref=temp_ref,
                      method="least-squares+temperature", n=len(x), temperature_key=temperature_key)
        residuals = [yi - cal.apply(xi, None if temperature is None else temperature[i])
                     for i, (xi, yi) in enumerate(zip(x, y))]
        cal.residual_sd = math.sqrt(sum(r * r for r in residuals) / max(1, len(residuals) - 2))
        return cal

    def to_dict(self):
        return {k: getattr(self, k) for k in ("gain", "offset", "temp_coeff", "temp_ref", "residual_sd", "method", "n",
                                            "temperature_key")}

    def save(self, path):
        pathlib.Path(path).write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path):
        return cls(**json.loads(pathlib.Path(path).read_text(encoding="utf-8")))


# ── drift: the Environmental -> Validation link ─────────────────────────────
DRIFT_MIN_CHECKS = 3
DRIFT_FACTOR = 3.0


def drift_summary(residuals, residual_sd):
    """Spot checks against a reference (reference - calibrated reading) vs the fit's own residual.

    A sensor's own readings cannot reveal its drift; only a reference can. Drift is flagged when
    at least DRIFT_MIN_CHECKS checks have an RMS error above DRIFT_FACTOR x the fit's residual sd.
    Without a residual sd there is no promise to break, so drift stays None (unknown)."""
    r = [float(v) for v in residuals]
    if not r:
        return {"checks": 0, "rms": None, "bias": None, "limit": None, "drift": None}
    rms = math.sqrt(sum(v * v for v in r) / len(r))
    limit = DRIFT_FACTOR * residual_sd if residual_sd else None
    drift = None if limit is None or len(r) < DRIFT_MIN_CHECKS else rms > limit
    return {"checks": len(r), "rms": rms, "bias": sum(r) / len(r), "limit": limit, "drift": drift}


def _least_squares_line(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxx = sum((a - mx) ** 2 for a in x)
    if sxx == 0:
        raise ValueError("raw readings do not vary; cannot fit a gain")
    gain = sum((a - mx) * (b - my) for a, b in zip(x, y)) / sxx
    return gain, my - gain * mx


def _least_squares_plane(x, t, y):
    """y = a*x + b*t + c. Centring first keeps the 2x2 system well conditioned at any scale."""
    n = len(x)
    mx, mt, my = sum(x) / n, sum(t) / n, sum(y) / n
    xc, tc, yc = [a - mx for a in x], [b - mt for b in t], [c - my for c in y]
    sxx = sum(a * a for a in xc)
    stt = sum(b * b for b in tc)
    sxt = sum(a * b for a, b in zip(xc, tc))
    det = sxx * stt - sxt * sxt
    if sxx == 0 or stt == 0 or det <= 1e-12 * sxx * stt:  # relative test: scale-independent
        raise ValueError("raw readings and temperature are collinear; vary them independently")
    sxy = sum(a * c for a, c in zip(xc, yc))
    sty = sum(b * c for b, c in zip(tc, yc))
    a = (sxy * stt - sty * sxt) / det
    b = (sty * sxx - sxy * sxt) / det
    return a, b, my - a * mx - b * mt


# ── the Environmental ↔ Validation loop (ADR 0007) ──────────────────────────
def detection_limits(variance):
    """What Validation reports back from a fused variance: LOD = 3 sigma, LOQ = 10 sigma."""
    sd = math.sqrt(float(variance))
    return {"sd": sd, "lod": 3 * sd, "loq": 10 * sd}
