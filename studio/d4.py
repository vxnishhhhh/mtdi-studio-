"""D4 analysis engine: the numerical core behind MTDI 2.0.

Everything here is plain numpy so it runs on this host without the laptop. The MATLAB
toolbox in ``matlab/`` implements the same functions with the same names and the same
JSON contract, so coefficients, weights and thresholds developed in MATLAB drop into
``i3_config.json`` and this host loads them. Nothing in this module invents a value: every
figure is computed from the samples it is given and every function reports the sample
rate, window length or count it worked from so the limits are visible.
"""
from __future__ import annotations

import json
import math
import os
import time
from pathlib import Path

import numpy as np

# ── configuration exchanged with MATLAB ──────────────────────────────────────
CONFIG_DEFAULT = {
    "version": 1,
    "source": "defaults",
    "c1_offsets": [0.0, 0.0, 0.0],
    "c1_soft_iron": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
    "c1_scale": [1.0, 1.0, 1.0],
    "c1_calibration_quality": None,
    "mtdi_weights": {"ch3": 0.30, "ch2": 0.25, "ch1": 0.30, "transient": 0.15},
    "confidence_weights": {"snr": 0.25, "repeatability": 0.15, "agreement": 0.25, "baseline_deviation": 0.20, "calibration": 0.15},
    "ch3_threshold_db": 10.0,          # dB above the noise floor that counts as activity
    "anomaly_sigma": 3.0,             # z-score that counts as an anomaly
    "event_mtdi": 60.0,               # MTDI 2.0 score that opens an event
    "transient_threshold": 3.4,       # multiples of the noise MAD
    "baseline_method": "ema",         # ema | moving_median | moving_mean
    "baseline_alpha": 0.025,
    "linefreq_hz": 50.0,
    "c1_odr_hz": 200,               # SRC1 output data rate (10/50/100/200)
    "auto_burst_s": 60,              # seconds between automatic 4 s Ch2 burst captures (0 = manual only)
    "d3_reference": {},              # metrics typed from the D3 report for the comparison table
    "filter": {"type": "butterworth", "order": 4, "cutoff_hz": 20.0, "kind": "low", "b": None, "a": None, "fs": None, "apply": False},
}


def config_path():
    return Path(os.environ.get("STUDIO_D4_CONFIG", str(Path.home() / ".config/mtdi_studio/i3_config.json"))).expanduser()


def load_config():
    """i3_config.json as exported by MATLAB (or saved from the instrument), validated."""
    cfg = json.loads(json.dumps(CONFIG_DEFAULT))
    path = config_path()
    if not path.exists():
        return cfg, None
    try:
        data = json.loads(path.read_text(encoding="utf8"))
        for key, value in data.items():
            if key in cfg:
                cfg[key] = value
        offsets = [float(v) for v in cfg["c1_offsets"]]
        matrix = np.array(cfg["c1_soft_iron"], dtype=float)
        if len(offsets) != 3 or matrix.shape != (3, 3) or not np.all(np.isfinite(matrix)) or abs(np.linalg.det(matrix)) < 1e-9:
            raise ValueError("c1_offsets must be 3 values and c1_soft_iron a non singular 3x3 matrix")
        w = cfg["mtdi_weights"]
        total = sum(float(v) for v in w.values())
        if total <= 0:
            raise ValueError("mtdi_weights must sum to a positive value")
        cfg["mtdi_weights"] = {k: float(v) / total for k, v in w.items()}
        cw = cfg["confidence_weights"]
        total = sum(float(v) for v in cw.values())
        cfg["confidence_weights"] = {k: float(v) / total for k, v in cw.items()}
        cfg["source"] = str(path)
        return cfg, None
    except Exception as exc:
        return json.loads(json.dumps(CONFIG_DEFAULT)), f"i3_config.json rejected: {exc}"


def save_config(cfg):
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    cfg = dict(cfg)
    cfg["saved_at"] = time.time()
    tmp.write_text(json.dumps(cfg, indent=2, allow_nan=False), encoding="utf8")
    os.replace(tmp, path)
    return str(path)


# ── helpers ──────────────────────────────────────────────────────────────────
def _f(x, nd=3):
    """Finite float rounded for JSON, else None."""
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return round(x, nd) if math.isfinite(x) else None


def _mad(x):
    x = np.asarray(x, dtype=float)
    med = np.median(x)
    return 1.4826 * np.median(np.abs(x - med)), med


# ── 1/2. ch1probe calibration (hard iron, soft iron, scale, misalignment) ─
def ellipsoid_fit(points):
    """Least squares ellipsoid fit to raw XYZ samples.

    Solves the general quadric  Ax²+By²+Cz²+2Dxy+2Exz+2Fyz+2Gx+2Hy+2Iz = 1  and
    factors it into a centre (hard iron offset), a symmetric correction matrix
    (soft iron, which carries scale and axis misalignment) and per axis scale
    factors. Returns None when the samples do not cover enough of the sphere.
    """
    P = np.asarray(points, dtype=float)
    P = P[np.all(np.isfinite(P), axis=1)]
    if P.shape[0] < 60:
        return None, f"need at least 60 samples, have {P.shape[0]}"
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    # coverage: the samples must spread over all three axes, not sit in one pose
    span = P.max(axis=0) - P.min(axis=0)
    if np.min(span) < 0.15 * np.max(span):
        return None, "rotate the instrument through every orientation; coverage on one axis is too small"
    D = np.column_stack([x * x, y * y, z * z, 2 * x * y, 2 * x * z, 2 * y * z, 2 * x, 2 * y, 2 * z])
    try:
        v, *_ = np.linalg.lstsq(D, np.ones(P.shape[0]), rcond=None)
    except np.linalg.LinAlgError as exc:
        return None, f"fit failed: {exc}"
    A = np.array([[v[0], v[3], v[4]], [v[3], v[1], v[5]], [v[4], v[5], v[2]]])
    g = v[6:9]
    try:
        centre = -np.linalg.solve(A, g)
    except np.linalg.LinAlgError:
        return None, "fit is degenerate"
    # translate to the centre: (p-c)ᵀ A (p-c) = r²
    # the quadric was fitted with the constant on the right, so A and r² share a sign;
    # dividing cancels it and leaves a positive definite matrix for a real ellipsoid
    r2 = 1.0 + centre @ A @ centre
    if abs(r2) < 1e-15:
        return None, "fit did not produce an ellipsoid"
    A_n = A / r2
    evals, evecs = np.linalg.eigh(A_n)
    if np.any(evals <= 0):
        return None, "fit is not a closed ellipsoid (a hyperboloid): more orientations are needed"
    radii = 1.0 / np.sqrt(evals)
    # map the ellipsoid onto a sphere of the mean radius: W = R diag(1/radii) Rᵀ · mean radius
    target = float(np.mean(radii))
    W = evecs @ np.diag(target / radii) @ evecs.T
    corrected = (P - centre) @ W.T
    c1_before = np.linalg.norm(P - centre, axis=1)
    c1_after = np.linalg.norm(corrected, axis=1)
    # quality: how close the corrected magnitudes are to one sphere (1 - relative spread)
    spread_before = float(np.std(c1_before) / max(1e-9, np.mean(c1_before)))
    spread_after = float(np.std(c1_after) / max(1e-9, np.mean(c1_after)))
    # coverage: how evenly the corrected directions fill the sphere (covariance of the unit
    # vectors is isotropic, 1/3 per axis, for a full tumble); a one pose capture scores low
    units = corrected / np.maximum(1e-9, c1_after)[:, None]
    ev = np.linalg.eigvalsh(np.cov(units.T))
    coverage = float(max(0.0, min(1.0, (ev.min() / max(1e-12, ev.max())))))
    quality = float(max(0.0, min(1.0, (1.0 - spread_after * 4.0) * min(1.0, coverage / 0.6))))
    scale = np.diag(W)
    off_diag = W - np.diag(scale)
    misalignment_deg = float(np.degrees(np.arctan(np.max(np.abs(off_diag)))))
    return {
        "samples": int(P.shape[0]),
        "offsets_val": [_f(c) for c in centre],
        "soft_iron_matrix": [[_f(W[i, j], 5) for j in range(3)] for i in range(3)],
        "scale": [_f(s, 4) for s in scale],
        "radii_val": [_f(r) for r in radii],
        "field_magnitude_val": _f(target),
        "misalignment_deg": _f(misalignment_deg, 2),
        "residual_before_pct": _f(spread_before * 100, 2),
        "residual_after_pct": _f(spread_after * 100, 2),
        "quality": _f(quality * 100, 1),
        "coverage": _f(coverage * 100, 1),
        "raw": [[_f(a, 2) for a in p] for p in P[:: max(1, P.shape[0] // 400)]],
        "corrected": [[_f(a, 2) for a in p] for p in corrected[:: max(1, P.shape[0] // 400)]],
    }, None


def apply_calibration(vec, cfg):
    W = np.array(cfg["c1_soft_iron"], dtype=float)
    return (W @ (np.asarray(vec, dtype=float) - np.asarray(cfg["c1_offsets"], dtype=float))).tolist()


def calibration_health(recent_points, cfg, noise_val=None):
    """Is the stored calibration still good? Uses recent samples: magnitude spread after
    correction and the drift of the centre versus the stored offsets."""
    P = np.asarray(recent_points, dtype=float)
    if P.shape[0] < 30:
        return {"status": "insufficient", "samples": int(P.shape[0]), "text": "Need 30 recent samples"}
    corrected = np.array([apply_calibration(p, cfg) for p in P])
    c1 = np.linalg.norm(corrected, axis=1)
    spread = float(np.std(c1) / max(1e-9, np.mean(c1)))
    quality = max(0.0, min(100.0, 100.0 * (1 - spread * 4)))
    drift = float(np.linalg.norm(P.mean(axis=0) - np.asarray(cfg["c1_offsets"]) - corrected.mean(axis=0)))
    recal = quality < 80 or spread > 0.08
    return {"status": "degraded" if recal else "ok", "samples": int(P.shape[0]), "quality": _f(quality, 1),
            "magnitude_spread_pct": _f(spread * 100, 2), "offset_drift_val": _f(drift, 2), "noise_val": _f(noise_val, 3),
            "recalibration": 'Recommended: run channel 1 recalibration' if recal else "Not required"}


# ── 4/5. FFT engine and linefreq harmonics ──────────────────────────────────────
def sweep3(x, fs):
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = x.size
    if n < 16 or not fs or fs <= 0:
        return None
    x = x - x.mean()
    win = np.hanning(n)
    X = np.fft.rfft(x * win)
    f = np.fft.rfftfreq(n, 1.0 / fs)
    amp = 2.0 * np.abs(X) / np.sum(win)
    return f, amp


def _refine_peak(f, amp, i):
    """Parabolic interpolation of a density peak: sub-bin frequency and amplitude."""
    if 0 < i < amp.size - 1 and amp[i] > 0:
        a, b, c = np.log(amp[i - 1] + 1e-30), np.log(amp[i] + 1e-30), np.log(amp[i + 1] + 1e-30)
        den = a - 2 * b + c
        if abs(den) < 1e-12:
            return float(f[i]), float(amp[i])
        d = 0.5 * (a - c) / den
        d = float(np.clip(d, -1, 1))
        return float(f[i] + d * (f[1] - f[0])), float(np.exp(b - 0.25 * (a - c) * d))
    return float(f[i]), float(amp[i])


def spectrogram(x, fs, segments=24, overlap=0.5, max_hz=None):
    """Short-time FFT of one channel: how its sweep3 changes across the capture.

    ``harmonics`` gives one sweep3 for the whole block, which answers "what
    frequencies are present" but not "were they present the whole time". A linefreq line
    is there from end to end; a switching supply coming on is a stripe that starts
    partway through. Only the second question separates a steady source from an
    intermittent one, and a single FFT cannot answer it.

    Returns dB relative to the strongest bin in the whole picture - a relative scale,
    because the channel it is given may itself be uncalibrated.
    """
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = x.size
    if n < 128 or not fs or fs <= 0:
        return None
    segments = int(max(4, min(segments, n // 32)))
    step = max(1, int(n / (segments * (1 - overlap) + overlap)))
    win_n = min(n, int(step / max(1e-6, 1 - overlap)))
    win_n = max(32, win_n - (win_n % 2))
    starts = list(range(0, n - win_n + 1, max(1, int(win_n * (1 - overlap)))))
    if not starts:
        return None
    win = np.hanning(win_n)
    freqs = np.fft.rfftfreq(win_n, 1.0 / fs)
    keep = freqs <= (max_hz if max_hz else fs / 2)
    rows = []
    for start in starts:
        seg = x[start:start + win_n]
        seg = seg - seg.mean()
        amp = 2.0 * np.abs(np.fft.rfft(seg * win)) / win.sum()
        rows.append(amp[keep])
    grid = np.asarray(rows)
    peak = float(grid.max()) or 1.0
    db = 20.0 * np.log10(grid / peak + 1e-12)
    times = [_f((start + win_n / 2) / fs, 3) for start in starts]
    return {"hz": [_f(v, 2) for v in freqs[keep]], "times_s": times,
            "db": [[_f(v, 1) for v in row] for row in db],
            "window_s": _f(win_n / fs, 3), "segments": len(starts),
            "resolution_hz": _f(fs / win_n, 2),
            "note": "dB relative to the strongest bin in this picture, not an absolute level"}


def harmonics(x, fs, linefreq_hz=50.0, max_harmonics=8):
    """Fundamental near the linefreq frequency, its harmonics, THD and switching peaks.
    Honest about bandwidth: a series sampled below 2×linefreq cannot show the linefreq line."""
    out = {"fs": _f(fs, 2), "samples": int(np.size(x)), "nyquist_hz": _f(fs / 2 if fs else 0, 2)}
    sp = sweep3(x, fs)
    if sp is None:
        out["error"] = "not enough samples"
        return out
    f, amp = sp
    out["resolution_hz"] = _f(f[1] - f[0], 3)
    if fs / 2 < linefreq_hz * 1.05:
        out["error"] = f"sampled at {fs:.1f} Hz: the {linefreq_hz:.0f} Hz linefreq component is above the Nyquist limit ({fs/2:.1f} Hz); use the burst capture"
        i = int(np.argmax(amp[1:]) + 1)
        out["dominant_hz"], out["dominant_amp"] = [_f(v) for v in _refine_peak(f, amp, i)]
        return out
    noise, _ = _mad(amp)
    res = f[1] - f[0]
    band = max(2, int(round(linefreq_hz * 0.06 / res)))
    i0 = int(np.argmin(np.abs(f - linefreq_hz)))
    lo, hi = max(1, i0 - band), min(amp.size - 1, i0 + band)
    ip = lo + int(np.argmax(amp[lo:hi + 1]))
    f_fund, a_fund = _refine_peak(f, amp, ip)
    # the line must stand out of its own neighbourhood (±10 Hz), not only of the global MAD:
    # a quiet ch1probe has a tiny MAD and would otherwise call any ripple a fundamental
    nb = max(3, int(round(10.0 / res)))
    neigh = np.concatenate([amp[max(1, ip - nb): max(1, ip - 2)], amp[ip + 3: ip + nb + 1]])
    local = float(np.median(neigh)) if neigh.size else noise
    fund_ok = a_fund > noise * 6 and a_fund > local * 4
    out["fundamental_hz"] = _f(f_fund, 2) if fund_ok else None
    out["fundamental_amp"] = _f(a_fund, 4) if fund_ok else None
    out["fundamental_detected"] = bool(fund_ok)
    harm = []
    sq = 0.0
    if fund_ok:
        for k in range(2, max_harmonics + 1):
            fk = f_fund * k
            if fk >= f[-1]:
                break
            j0 = int(np.argmin(np.abs(f - fk)))
            lo, hi = max(1, j0 - band), min(amp.size - 1, j0 + band)
            jp = lo + int(np.argmax(amp[lo:hi + 1]))
            fh, ah = _refine_peak(f, amp, jp)
            present = ah > noise * 8 and ah > 0.005 * a_fund
            harm.append({"order": k, "hz": _f(fh, 2), "amp": _f(ah, 4), "rel_db": _f(20 * np.log10(ah / a_fund + 1e-12), 1), "present": bool(present)})
            if present:
                sq += ah * ah
        out["thd_pct"] = _f(100 * math.sqrt(sq) / a_fund, 2)
    out["harmonics"] = harm
    # other peaks (switching frequencies): local maxima well above the noise, not at harmonics
    mask = amp > max(noise * 10, 0.01 * float(np.max(amp[1:])))
    peaks = []
    for i in np.flatnonzero(mask):
        if 0 < i < amp.size - 1 and amp[i] >= amp[i - 1] and amp[i] >= amp[i + 1]:
            fi, ai = _refine_peak(f, amp, i)
            if fund_ok and abs(fi / f_fund - round(fi / f_fund)) < 0.06:
                continue
            if fund_ok and fi < 1.5 * f_fund:
                continue   # below the linefreq line is drift or motion, not switching noise
            peaks.append({"hz": _f(fi, 2), "amp": _f(ai, 4)})
    peaks.sort(key=lambda p: -(p["amp"] or 0))
    out["other_peaks"] = peaks[:6]
    i = int(np.argmax(amp[1:]) + 1)
    out["dominant_hz"], out["dominant_amp"] = [_f(v) for v in _refine_peak(f, amp, i)]
    out["noise_amp"] = _f(noise, 5)
    step = max(1, f.size // 512)
    out["sweep3"] = {"hz": [_f(v, 2) for v in f[::step]], "amp": [_f(v, 5) for v in amp[::step]]}
    return out


# ── 3. CH3 sweep3 analysis ──────────────────────────────────────────────────
CH3_BANDS = [
    (87.5e6, 108e6, "FM broadcast band"),
    (174e6, 230e6, "VHF band III (DAB / TV)"),
    (380e6, 400e6, "TETRA public safety band"),
    (433.05e6, 434.79e6, "433 MHz ISM band"),
    (470e6, 694e6, "UHF TV band"),
    (703e6, 803e6, "700 MHz cellular band"),
    (791e6, 862e6, "800 MHz cellular band"),
    (868e6, 870e6, "868 MHz SRD band"),
    (880e6, 960e6, "900 MHz cellular band"),
    (1710e6, 1880e6, "1800 MHz cellular band"),
    (1920e6, 2170e6, "2100 MHz cellular band"),
    (2400e6, 2483.5e6, '2.4 GHz ISM band (Channel 5, Channel 6, microwave ovens)'),
    (2500e6, 2690e6, "2600 MHz cellular band"),
    (3300e6, 3800e6, "3.5 GHz band"),
    (5150e6, 5875e6, "5 GHz U-NII / ISM band"),
]


def ch3_analysis(freqs, levels, threshold_db=10.0, digits=0):
    """Peak, robust noise floor, SNR, occupied bandwidth, peaks, harmonics of the primary
    peak, occupancy and interference density from one sweep in dBm. Band wording is
    'consistent with', never an identification. Positions are rounded to `digits`: whole
    hertz for the radio, more for a fed sweep whose x axis is in its own unit."""
    f = np.asarray(freqs, dtype=float)
    L = np.asarray(levels, dtype=float)
    ok = np.isfinite(f) & np.isfinite(L)
    f, L = f[ok], L[ok]
    if f.size < 8:
        return {"error": "not enough points"}
    mad, floor = _mad(L)
    ip = int(np.argmax(L))
    peak_f, peak_l = float(f[ip]), float(L[ip])
    snr = peak_l - floor
    above = L > floor + threshold_db
    occupancy = float(np.mean(above) * 100)
    # occupied bandwidth: 99 % of the linear power of the primary peak's own island (the bins
    # contiguous with the peak that stay above floor + threshold/2), so noise bins far away
    # cannot stretch it to the whole span
    p = 10 ** (L / 10)
    lo = hi = ip
    limit = floor + threshold_db / 2
    while lo > 0 and L[lo - 1] > limit:
        lo -= 1
    while hi < L.size - 1 and L[hi + 1] > limit:
        hi += 1
    island = np.arange(lo, hi + 1)
    pi = p[island]
    order = island[np.argsort(-pi)]
    cum = np.cumsum(p[order]) / pi.sum()
    keep = order[: int(np.searchsorted(cum, 0.99)) + 1]
    obw = float(f[keep].max() - f[keep].min() + (f[1] - f[0])) if keep.size else 0.0
    # density peaks: local maxima above the threshold, separated by at least 3 bins
    peaks = []
    for i in np.flatnonzero(above):
        if 0 < i < L.size - 1 and L[i] >= L[i - 1] and L[i] >= L[i + 1]:
            if peaks and i - peaks[-1]["i"] < 3:
                if L[i] > peaks[-1]["level"]:
                    peaks[-1] = {"i": int(i), "hz": float(f[i]), "level": float(L[i])}
                continue
            peaks.append({"i": int(i), "hz": float(f[i]), "level": float(L[i])})
    peaks.sort(key=lambda q: -q["level"])
    # harmonics of the primary peak that are themselves peaks
    harm = []
    for q in peaks:
        ratio = q["hz"] / max(1.0, peak_f)
        k = round(ratio)
        if k >= 2 and abs(ratio - k) < 0.02:
            harm.append({"order": int(k), "hz": _f(q["hz"], digits), "level_dbm": _f(q["level"], 1)})
    # interference density: activity islands per 100 MHz
    islands = int(np.sum(np.diff(above.astype(int)) == 1) + (1 if above[0] else 0))
    span_mhz = max(1e-3, (f.max() - f.min()) / 1e6)
    bands = [name for lo, hi, name in CH3_BANDS if lo <= peak_f <= hi]
    return {
        "points": int(f.size), "span_hz": [_f(f.min(), digits), _f(f.max(), digits)],
        "primary_peak_hz": _f(peak_f, digits), "primary_peak_dbm": _f(peak_l, 1),
        "noise_floor_dbm": _f(floor, 1), "noise_mad_db": _f(mad, 2), "snr_db": _f(snr, 1),
        "occupied_bandwidth_hz": _f(obw, digits), "occupancy_pct": _f(occupancy, 1),
        "interference_islands": islands, "interference_density_per_100mhz": _f(islands / span_mhz * 100, 3),
        "peaks": [{"hz": _f(q["hz"], digits), "level_dbm": _f(q["level"], 1), "snr_db": _f(q["level"] - floor, 1)} for q in peaks[:10]],
        "harmonics_of_primary": harm[:5],
        "unexpected": [{"hz": _f(q["hz"], digits), "level_dbm": _f(q["level"], 1)} for q in peaks[:10]
                       if not any(lo <= q["hz"] <= hi for lo, hi, _ in CH3_BANDS)][:5],
        "band_note": ("Signal characteristics are consistent with activity in the " + bands[0] + ".") if bands and snr >= threshold_db
                     else ("Primary peak falls outside the listed allocations; source not identified." if snr >= threshold_db else "No peak clears the activity threshold above the noise floor."),
        "activity": bool(snr >= threshold_db),
    }


# ── 9. adaptive baseline ────────────────────────────────────────────────────
def adaptive_baseline(x, method="ema", alpha=0.025, window=50):
    x = np.asarray(x, dtype=float)
    if x.size == 0:
        return np.array([])
    if method == "ema":
        out = np.empty_like(x)
        out[0] = x[0]
        for i in range(1, x.size):
            out[i] = out[i - 1] + alpha * (x[i] - out[i - 1])
        return out
    w = max(3, int(window))
    out = np.empty_like(x)
    for i in range(x.size):
        seg = x[max(0, i - w + 1): i + 1]
        out[i] = np.median(seg) if method == "moving_median" else np.mean(seg)
    return out


def compare_baselines(x, alpha=0.025, window=50, disturbance=None):
    """How each baseline behaves against a short disturbance (a phone walking in): the
    smaller the residual after the disturbance the better it rejected it."""
    x = np.asarray(x, dtype=float)
    if x.size < 20:
        return {"error": "need 20 samples"}
    res = {}
    for m in ("ema", "moving_median", "moving_mean"):
        b = adaptive_baseline(x, m, alpha, window)
        res[m] = {"final": _f(b[-1], 4), "tracking_rmse": _f(np.sqrt(np.mean((x - b) ** 2)), 4),
                  "max_excursion": _f(np.max(np.abs(b - np.median(x))), 4)}
    best = min(res, key=lambda k: res[k]["max_excursion"] or 1e9)
    return {"methods": res, "most_disturbance_resistant": best, "samples": int(x.size)}


# ── 10. transients ───────────────────────────────────────────────────────────
def transient_features(t, x, threshold_mad=3.4, min_noise=0.0):
    """Short events above threshold×MAD of the series: rise/fall time (10–90 %),
    duration, peak, energy (∫(x-base)² dt) and repetition rate."""
    t = np.asarray(t, dtype=float)
    x = np.asarray(x, dtype=float)
    ok = np.isfinite(t) & np.isfinite(x)
    t, x = t[ok], x[ok]
    if x.size < 10:
        return {"events": [], "samples": int(x.size)}
    mad, base = _mad(x)
    # a quiet sensor has a tiny MAD; the channel's own noise floor stops noise being called an event
    thr = base + threshold_mad * max(mad, min_noise, 1e-9)
    above = x > thr
    events = []
    i = 0
    while i < x.size:
        if above[i]:
            j = i
            while j < x.size and above[j]:
                j += 1
            seg = x[i:j] - base
            ts = t[i:j]
            ip = int(np.argmax(seg))
            peak = float(seg[ip])
            def cross(level, a, b, step):
                k = a
                while 0 <= k < x.size and k != b and (x[k] - base) > level:
                    k += step
                return t[max(0, min(x.size - 1, k))]
            t10r = cross(0.1 * peak, i + ip, -1, -1); t90r = cross(0.9 * peak, i + ip, -1, -1)
            t90f = cross(0.9 * peak, i + ip, x.size, 1); t10f = cross(0.1 * peak, i + ip, x.size, 1)
            dt = float(np.mean(np.diff(t))) if t.size > 1 else 0.0
            energy = float(np.sum(seg ** 2) * dt)
            events.append({"t": _f(t[i + ip], 3), "peak": _f(peak, 3), "duration_ms": _f((t[j - 1] - t[i] + dt) * 1000, 1),
                           "rise_ms": _f(abs(t90r - t10r) * 1000, 2), "fall_ms": _f(abs(t10f - t90f) * 1000, 2), "energy": _f(energy, 4)})
            i = j
        else:
            i += 1
    rep = None
    if len(events) >= 2:
        gaps = np.diff([e["t"] for e in events])
        if np.all(gaps > 0):
            rep = float(1.0 / np.median(gaps))
    return {"events": events[-20:], "count": len(events), "threshold": _f(thr, 4), "baseline": _f(base, 4),
            "noise_mad": _f(mad, 4), "repetition_hz": _f(rep, 2), "samples": int(x.size), "window_s": _f(t[-1] - t[0], 1)}


# ── 12/8/6/7. anomaly, consensus, MTDI 2.0, confidence 2.0 ───────────────────
def zscore(value, history):
    h = np.asarray(history, dtype=float)
    h = h[np.isfinite(h)]
    if h.size < 8 or value is None or not math.isfinite(value):
        return None
    mad, med = _mad(h)
    sigma = max(mad, np.std(h) * 0.25, 1e-9)
    return float((value - med) / sigma)


def channel_score(z, sigma_threshold=3.0):
    """0–100 activity score from a z-score: 0 below 1σ, 50 at the threshold, saturating."""
    if z is None:
        return None
    a = abs(z)
    if a <= 1:
        return 0.0
    return float(100 * (1 - math.exp(-(a - 1) / max(0.5, sigma_threshold - 1) * math.log(2))))


def consensus(scores):
    """Cross sensor agreement: 100 when every available channel reports the same activity
    level, lower as they disagree (1 - normalised spread), weighted by how many agree."""
    vals = [v for v in scores.values() if v is not None]
    if len(vals) < 2:
        return None
    vals = np.array(vals) / 100.0
    spread = float(np.std(vals))
    agree = 1 - min(1.0, spread * 2.5)
    return float(100 * agree)


def mtdi2(scores, weights):
    """MTDI = Σ wᵢ·scoreᵢ over available channels, weights renormalised to those present."""
    avail = {k: v for k, v in scores.items() if v is not None and k in weights}
    if not avail:
        return None, {}
    total = sum(weights[k] for k in avail)
    contrib = {k: float(weights[k] / total * v) for k, v in avail.items()}
    return float(sum(contrib.values())), {k: _f(v, 1) for k, v in contrib.items()}


def confidence2(factors, weights):
    """Detection confidence from measurable factors, each already 0–1:
    snr, repeatability, agreement, baseline_deviation, calibration."""
    avail = {k: float(v) for k, v in factors.items() if v is not None and k in weights}
    if not avail:
        return None, []
    total = sum(weights[k] for k in avail)
    c = sum(weights[k] / total * min(1.0, max(0.0, v)) for k, v in avail.items())
    labels = {"snr": "Signal to noise", "repeatability": "Repeatability", "agreement": 'Source agreement',
              "baseline_deviation": "Deviation from baseline", "calibration": "Calibration health"}
    words = []
    for k, v in sorted(avail.items(), key=lambda kv: -kv[1]):
        grade = "Strong" if v >= 0.75 else "Moderate" if v >= 0.45 else "Weak"
        words.append(f"{grade} {labels.get(k, k).lower()}")
    return float(100 * c), words


# ── 15. correlation ──────────────────────────────────────────────────────────
def correlation(a, b):
    a = np.asarray(a, dtype=float); b = np.asarray(b, dtype=float)
    n = min(a.size, b.size)
    if n < 8:
        return None
    a, b = a[-n:], b[-n:]
    if np.std(a) < 1e-12 or np.std(b) < 1e-12:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def correlation_text(r):
    if r is None:
        return "Not enough overlapping samples"
    a = abs(r)
    return ("Strong" if a >= 0.7 else "Moderate" if a >= 0.4 else "Weak") + " temporal relationship" + (" (inverse)" if r < -0.4 else "")


# ── 20. noise characterisation ───────────────────────────────────────────────
def noise_characterisation(x, fs=None):
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if x.size < 8:
        return {"error": "need 8 samples"}
    d = x - np.median(x)
    out = {"samples": int(x.size), "rms": _f(np.sqrt(np.mean(d ** 2)), 4), "peak": _f(np.max(np.abs(d)), 4),
           "std": _f(np.std(x), 4), "mad": _f(_mad(x)[0], 4)}
    if fs and fs > 0 and x.size >= 32:
        sp = sweep3(x, fs)
        if sp:
            f, amp = sp
            # single sided noise density density in unit/√Hz
            psd = (amp ** 2) / 2 / max(1e-9, f[1] - f[0])
            out["nsd_per_sqrt_hz"] = _f(np.sqrt(np.median(psd[1:])), 5)
            out["fs"] = _f(fs, 2)
    return out


# ── repeatability ────────────────────────────────────────────────────────────
def repeatability_stats(values, unit="", nominal=None):
    """Spread of repeated measurements of the same thing under the same conditions.

    The question a judge asks is "do it again - do you get the same answer?" The
    answer is the relative standard deviation: the standard deviation of the repeated
    readings as a percentage of their mean. A low RSD means the instrument returns the
    same number when nothing has changed; it says nothing about whether that number is
    correct, which is accuracy and is a different measurement.

    Bessel's correction is used (n-1), because these are a sample of the readings the
    instrument could have produced, not the whole population of them.
    """
    vals = [float(v) for v in (values or []) if v is not None and math.isfinite(float(v))]
    n = len(vals)
    if n < 2:
        return {"error": f"need at least 2 readings, have {n}"}
    mean = sum(vals) / n
    var = sum((v - mean) ** 2 for v in vals) / (n - 1)
    sd = math.sqrt(var)
    sem = sd / math.sqrt(n)
    # Student's t at 95 % for small n, so a 10-run test is not given a normal-theory
    # interval it has not earned.
    t95 = {2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776, 6: 2.571, 7: 2.447, 8: 2.365,
           9: 2.306, 10: 2.262, 11: 2.228, 12: 2.201, 15: 2.145, 20: 2.093}
    t = t95.get(n - 1, 2.086 if n > 20 else 2.262)
    rsd = 100.0 * sd / abs(mean) if abs(mean) > 1e-12 else float("nan")
    out = {"n": n, "unit": unit, "mean": _f(mean, 5), "sd": _f(sd, 5), "sem": _f(sem, 5),
           "rsd_pct": _f(rsd, 3) if math.isfinite(rsd) else None,
           "min": _f(min(vals), 5), "max": _f(max(vals), 5), "range": _f(max(vals) - min(vals), 5),
           "ci95_half_width": _f(t * sem, 5), "t_factor": t,
           "readings": [_f(v, 5) for v in vals],
           "basis": "sample standard deviation (n-1); 95 % interval uses Student's t for this n"}
    out["text"] = f"{out['mean']} ± {out['ci95_half_width']} {unit} (95 %, n = {n})"
    if out["rsd_pct"] is not None:
        r = out["rsd_pct"]
        out["verdict"] = ("repeatable to well under a percent" if r < 1 else
                          "repeatable to a few percent" if r < 5 else
                          "spread is large; the environment moved during the run or the "
                          "readings sit near the detection limit")
    if nominal is not None and math.isfinite(nominal) and abs(nominal) > 1e-12:
        out["nominal"] = _f(nominal, 5)
        out["bias_pct"] = _f(100.0 * (mean - nominal) / abs(nominal), 3)
        out["note_accuracy"] = ("bias against the stated nominal; repeatability and accuracy "
                                "are separate claims")
    return out


# ── limits of detection ──────────────────────────────────────────────────────
def detection_limits(noise, unit, k_lod=3.0, k_loq=10.0):
    """The smallest change this channel can honestly claim to have seen.

    Standard analytical convention: the limit of detection is k·σ of the blank
    (here, the channel's own noise on a quiet capture) and the limit of
    quantification is 10σ. Below the LOD a reading is indistinguishable from the
    instrument's own noise; between LOD and LOQ something is there but its size
    cannot be stated. This is the number that answers "how sensitive is it", and
    it is derived from the measured noise rather than quoted from a datasheet.
    """
    if not isinstance(noise, dict) or noise.get("error"):
        return {"error": (noise or {}).get("error", "no noise measurement")}
    sigma = noise.get("std")
    if sigma is None or not math.isfinite(sigma) or sigma <= 0:
        return {"error": "noise standard deviation not available"}
    out = {"unit": unit, "sigma": _f(sigma, 5), "samples": noise.get("samples"),
           "lod": _f(k_lod * sigma, 5), "loq": _f(k_loq * sigma, 5),
           "k_lod": k_lod, "k_loq": k_loq,
           "basis": "k x standard deviation of the channel's own quiet-capture noise"}
    nsd = noise.get("nsd_per_sqrt_hz")
    if nsd:
        out["nsd_per_sqrt_hz"] = nsd
        out["note_nsd"] = (f"{nsd} {unit}/\u221aHz: averaging for longer lowers the detectable "
                           "change as the square root of the time")
    return out


# ── exposure reference comparison ────────────────────────────────────────────
# ICNIRP Guidelines for Limiting Exposure to Time-Varying Ch2 and Ch1
# Fields (1 Hz - 100 kHz), Health Physics 99(6):818-836, 2010. Reference levels at
# 50 Hz. The 1998 public ch1 value of 100 uT is carried too, because a number
# of national regulations still cite it and a reading can sit between the two.
EXPOSURE_REFERENCES = {
    "ch2_vu": {
        "public": 5000.0, "occupational": 10000.0,
        "source": "ICNIRP 2010 reference levels at 50 Hz",
    },
    "ch1_val": {
        "public": 200.0, "occupational": 1000.0, "public_1998": 100.0,
        "source": 'ICNIRP 2010 reference levels at 50 Hz (ICNIRP 1998 public level was 100 uT)',
    },
}


def exposure_comparison(linefreq_ch2_vu, linefreq_ch1_val, calibrated=False):
    """Where a measured 50 Hz level sits against the published exposure reference levels.

    Two things this deliberately does not do. It does not compare the *total*
    ch1 field, because most of that is the Earth's steady ~30 uT field and the
    reference levels are for the time-varying component - only the 50 Hz ch1
    component is compared. And it does not present the ch2-field figure as a
    compliance statement while the probe is uncalibrated, because a percentage of a
    legal limit computed from an uncalibrated probe would be a false claim.

    A reference level is not a safety threshold: exceeding it triggers an assessment
    against the basic restriction, it does not by itself mean harm.
    """
    out = {"source": EXPOSURE_REFERENCES["ch1_val"]["source"], "channels": [],
           "basis": "50 Hz component only, not the total field",
           "caveat": ("Reference levels are screening values, not a safety threshold: a level "
                      "above one calls for assessment against the basic restriction, it is not "
                      "itself a finding of harm.")}
    c1_ref = EXPOSURE_REFERENCES["ch1_val"]
    if linefreq_ch1_val is not None and math.isfinite(linefreq_ch1_val):
        pct = 100.0 * linefreq_ch1_val / c1_ref["public"]
        out["channels"].append({
            "key": "ch1", "channel": 'Channel 1, 50 Hz component', "value": _f(linefreq_ch1_val, 4), "unit": "uT",
            "public_limit": c1_ref["public"], "occupational_limit": c1_ref["occupational"],
            "pct_of_public": _f(pct, 4), "quantitative": True,
            "reading": ("below the public reference level" if pct < 100 else
                        "above the public reference level; assess against the basic restriction"),
            "note": (f"{_f(100.0 * linefreq_ch1_val / c1_ref['public_1998'], 4)} % of the older "
                     "ICNIRP 1998 public level of 100 uT"),
        })
    else:
        out["channels"].append({"key": "ch1", "channel": 'Channel 1, 50 Hz component', "quantitative": False,
                                "reading": 'no 50 Hz channel 1 fundamental stands above the noise',
                                "unit": "uT", "public_limit": c1_ref["public"]})
    e_ref = EXPOSURE_REFERENCES["ch2_vu"]
    if linefreq_ch2_vu is not None and math.isfinite(linefreq_ch2_vu) and calibrated:
        pct = 100.0 * linefreq_ch2_vu / e_ref["public"]
        out["channels"].append({
            "key": "ch2", "channel": 'Channel 2, 50 Hz component', "value": _f(linefreq_ch2_vu, 3), "unit": "V/m",
            "public_limit": e_ref["public"], "occupational_limit": e_ref["occupational"],
            "pct_of_public": _f(pct, 4), "quantitative": True,
            "reading": ("below the public reference level" if pct < 100 else
                        "above the public reference level; assess against the basic restriction"),
        })
    else:
        out["channels"].append({
            "key": "ch2", "channel": 'Channel 2, 50 Hz component', "quantitative": False, "unit": "V/m",
            "public_limit": e_ref["public"],
            "reading": ("the probe carries no absolute calibration, so no percentage of a "
                        "reference level is claimed. The published public level is 5 kV/m at 50 Hz; "
                        "stating where this reading sits against it needs a known-field fixture."),
        })
    return out


# ── 35/36. error and uncertainty ─────────────────────────────────────────────
def sensor_error(measured, reference):
    m = np.asarray(measured, dtype=float); r = np.asarray(reference, dtype=float)
    n = min(m.size, r.size)
    if n == 0:
        return {"error": "no pairs"}
    m, r = m[:n], r[:n]
    err = m - r
    pct = 100 * err / np.where(np.abs(r) < 1e-12, np.nan, r)
    return {"pairs": int(n), "mean_abs_error": _f(np.mean(np.abs(err)), 3), "mean_pct_error": _f(np.nanmean(np.abs(pct)), 2),
            "bias": _f(np.mean(err), 3), "rmse": _f(np.sqrt(np.mean(err ** 2)), 3), "max_abs_error": _f(np.max(np.abs(err)), 3)}


def uncertainty(value, reference_error=0.0, repeatability_std=0.0, noise_rms=0.0, calibration_error=0.0, k=2.0):
    """Combined standard uncertainty (root sum of squares) expanded with coverage factor k."""
    u = math.sqrt(reference_error ** 2 + repeatability_std ** 2 + noise_rms ** 2 + calibration_error ** 2)
    return {"value": _f(value, 3), "u_combined": _f(u, 3), "U_expanded": _f(k * u, 3), "k": k,
            "text": f"{value:.1f} ± {k*u:.1f}" if value is not None and math.isfinite(value) else "—",
            "budget": {"reference": _f(reference_error, 3), "repeatability": _f(repeatability_std, 3), "noise": _f(noise_rms, 3), "calibration": _f(calibration_error, 3)}}


# ── 21/22. filter design and comparison ──────────────────────────────────────
def butterworth(order, cutoff_hz, fs, kind="low"):
    """Digital Butterworth via analogue prototype + bilinear transform (no scipy).
    Returns b, a coefficients for lfilter style use."""
    if not (fs and fs > 0 and 0 < cutoff_hz < fs / 2):
        raise ValueError("cutoff must lie between 0 and Nyquist")
    order = int(order)
    # analogue prototype poles
    poles = [np.exp(1j * np.pi * (2 * k + order + 1) / (2 * order)) for k in range(order)]
    wc = 2 * fs * np.tan(np.pi * cutoff_hz / fs)   # pre-warped
    if kind == "low":
        zeros = []
        poles = [p * wc for p in poles]
        gain = wc ** order
    elif kind == "high":
        zeros = [0.0] * order
        poles = [wc / p for p in poles]
        gain = 1.0
    else:
        raise ValueError("kind must be low or high")
    # bilinear: z = (2fs + s) / (2fs - s)
    fs2 = 2 * fs
    zd = [(fs2 + z) / (fs2 - z) for z in zeros] + [-1.0] * (order - len(zeros))
    pd = [(fs2 + p) / (fs2 - p) for p in poles]
    kd = gain * np.real(np.prod([fs2 - z for z in zeros]) / np.prod([fs2 - p for p in poles])) if zeros or True else gain
    b = np.real(kd * np.poly(zd))
    a = np.real(np.poly(pd))
    # normalise the passband gain exactly (DC for low pass, Nyquist for high pass)
    w = 0.0 if kind == "low" else np.pi
    zz = np.exp(-1j * w * np.arange(b.size))
    g = abs(np.sum(b * zz) / np.sum(a * zz))
    b = b / g
    return b.tolist(), a.tolist()


def notch(f0, fs, q=30.0):
    """Second order IIR notch at f0 (the 50 Hz notch)."""
    w0 = 2 * np.pi * f0 / fs
    alpha = np.sin(w0) / (2 * q)
    b = np.array([1, -2 * np.cos(w0), 1]); a = np.array([1 + alpha, -2 * np.cos(w0), 1 - alpha])
    return (b / a[0]).tolist(), (a / a[0]).tolist()


def lfilter(b, a, x):
    b = np.asarray(b, dtype=float); a = np.asarray(a, dtype=float); x = np.asarray(x, dtype=float)
    y = np.zeros_like(x)
    for n in range(x.size):
        acc = np.dot(b[: min(b.size, n + 1)], x[n::-1][: b.size])
        if a.size > 1:
            acc -= np.dot(a[1: min(a.size, n + 1)], y[n - 1:: -1][: a.size - 1]) if n > 0 else 0.0
        y[n] = acc / a[0]
    return y


def kalman1d(x, q=1e-3, r=None):
    x = np.asarray(x, dtype=float)
    if r is None:
        r = max(1e-9, np.var(x)) * 0.5
    est = x[0]; p = 1.0
    out = np.empty_like(x)
    for i, z in enumerate(x):
        p += q
        k = p / (p + r)
        est += k * (z - est)
        p *= (1 - k)
        out[i] = est
    return out


def compare_filters(x, fs, truth=None, cutoff_hz=None):
    """RMSE of raw, moving average, Butterworth and Kalman against a reference (the
    smoothed series when no truth is supplied, which then measures noise removal only)."""
    x = np.asarray(x, dtype=float)
    if x.size < 32 or not fs:
        return {"error": "need 32 samples and a sample rate"}
    cutoff = cutoff_hz or min(fs / 8, 20.0)
    b, a = butterworth(4, cutoff, fs, "low")
    cands = {"raw": x, "moving_average": np.convolve(x, np.ones(9) / 9, mode="same"),
             "butterworth": lfilter(b, a, x), "kalman": kalman1d(x)}
    ref = np.asarray(truth, dtype=float) if truth is not None else np.convolve(x, np.ones(25) / 25, mode="same")
    out = {k: _f(np.sqrt(np.mean((v - ref) ** 2)), 4) for k, v in cands.items()}
    best = min((k for k in out if k != "raw"), key=lambda k: out[k] or 1e9)
    return {"rmse": out, "best": best, "reference": "supplied truth" if truth is not None else "25 point moving mean (noise removal only)",
            "fs": _f(fs, 2), "butterworth": {"order": 4, "cutoff_hz": _f(cutoff, 2), "b": [_f(v, 8) for v in b], "a": [_f(v, 8) for v in a]}}


# ── 17. validation statistics ────────────────────────────────────────────────
def validation_stats(values=None, detections=None):
    """values: list of measurements; detections: list of (predicted_bool, actual_bool)."""
    out = {}
    if values:
        v = np.asarray(values, dtype=float)
        v = v[np.isfinite(v)]
        if v.size:
            n = v.size
            sd = float(np.std(v, ddof=1)) if n > 1 else 0.0
            se = sd / math.sqrt(n) if n > 1 else 0.0
            t = 1.96 if n > 30 else {2: 12.71, 3: 4.30, 4: 3.18, 5: 2.78, 6: 2.57, 7: 2.45, 8: 2.36, 9: 2.31, 10: 2.26}.get(n, 2.1)
            out["measurements"] = {"n": int(n), "mean": _f(v.mean()), "median": _f(np.median(v)), "std": _f(sd), "variance": _f(sd ** 2),
                                   "cv_pct": _f(100 * sd / v.mean() if v.mean() else None, 2), "ci95": [_f(v.mean() - t * se), _f(v.mean() + t * se)],
                                   "min": _f(v.min()), "max": _f(v.max())}
    if detections:
        tp = sum(1 for p, a in detections if p and a); fp = sum(1 for p, a in detections if p and not a)
        fn = sum(1 for p, a in detections if not p and a); tn = sum(1 for p, a in detections if not p and not a)
        n = tp + fp + fn + tn
        prec = tp / (tp + fp) if tp + fp else None; rec = tp / (tp + fn) if tp + fn else None
        out["detection"] = {"n": n, "tp": tp, "fp": fp, "fn": fn, "tn": tn,
                            "accuracy_pct": _f(100 * (tp + tn) / n if n else None, 1), "precision_pct": _f(100 * prec if prec is not None else None, 1),
                            "recall_pct": _f(100 * rec if rec is not None else None, 1),
                            "detection_rate_pct": _f(100 * rec if rec is not None else None, 1),
                            "false_positive_rate_pct": _f(100 * fp / (fp + tn) if fp + tn else None, 1),
                            "f1_pct": _f(100 * 2 * prec * rec / (prec + rec) if prec and rec else None, 1)}
    return out


# ── 13. environmental fingerprint ────────────────────────────────────────────
def fingerprint(c1_mags, e_values, ch3_floor, ch3_peak_hz, transient_rate_per_min, harmonics_summary=None, ch3_x_unit=None):
    """ch3_x_unit: None for the radio (hertz, dBm), else a fed sweep's own x unit."""
    def band(x):
        x = np.asarray([v for v in x if v is not None and math.isfinite(v)], dtype=float)
        return [_f(np.percentile(x, 10), 2), _f(np.percentile(x, 90), 2)] if x.size else None
    return {"taken_at": time.time(), "ch1_val": band(c1_mags), "ch2": band(e_values), "ch3_floor_dbm": _f(ch3_floor, 1),
            "ch3_peak_hz": _f(ch3_peak_hz, 0 if ch3_x_unit is None else 6), "ch3_x_unit": ch3_x_unit,
            "transient_rate_per_min": _f(transient_rate_per_min, 2), "linefreq": harmonics_summary}


def compare_fingerprints(old, new):
    if not old or not new:
        return None
    def pct(a, b):
        try:
            a = float(np.mean(a)); b = float(np.mean(b))
            return _f(100 * (b - a) / abs(a), 1) if a else None
        except (TypeError, ValueError):
            return None
    # a channel 3 floor is compared only with one in the same kind of sweep (a reference taken on
    # the radio says nothing about a fed sweep's floor) and only when both have one
    a, b = old.get("ch3_floor_dbm"), new.get("ch3_floor_dbm")
    same = old.get("ch3_x_unit") == new.get("ch3_x_unit")
    return {"ch3_floor_db": _f(b - a, 1) if same and a is not None and b is not None else None,
            "ch1_pct": pct(old.get("ch1_val"), new.get("ch1_val")),
            "ch2_pct": pct(old.get("ch2"), new.get("ch2")),
            "transient_rate_pct": pct(old.get("transient_rate_per_min"), new.get("transient_rate_per_min"))}


# ── 16. similarity against reference profiles (not identification) ───────────
def profile_similarity(sample, references):
    """Cosine similarity between a feature vector and stored reference profiles.
    Returns ranked similarities; the caller must word it as similarity."""
    s = np.asarray(sample, dtype=float)
    out = []
    for name, vec in references.items():
        r = np.asarray(vec, dtype=float)
        n = min(s.size, r.size)
        if n == 0 or np.linalg.norm(s[:n]) == 0 or np.linalg.norm(r[:n]) == 0:
            continue
        out.append({"name": name, "similarity_pct": _f(100 * float(np.dot(s[:n], r[:n]) / (np.linalg.norm(s[:n]) * np.linalg.norm(r[:n]))), 1)})
    out.sort(key=lambda q: -(q["similarity_pct"] or 0))
    return out


# ── 5. Power Network Analysis (50 Hz systems) ────────────────────────────────
def power_network(linefreq_e=None, linefreq_m=None, linefreq_c=None, linefreq_hz=50.0):
    """Combine the Ch2, ch1 and conducted harmonic analyses into one 50 Hz
    assessment with findings worded as 'consistent with'. Rules, in order:
    even-harmonic dominance → asymmetry/half-wave loads; high THD → non-linear loads
    (switch mode supplies, inverters); a ch1 2nd harmonic that exceeds the fundamental
    → consistent with a transformer core; strong non-harmonic peaks → switching noise."""
    out = {"linefreq_hz": linefreq_hz, "channels": {}, "findings": [], "abnormal": []}
    for name, m in (("ch2", linefreq_e), ("ch1", linefreq_m), ("conducted", linefreq_c)):
        if not m or m.get("error") or not m.get("fundamental_detected"):
            out["channels"][name] = {"present": False, "note": (m or {}).get("error") or "no fundamental above the noise"}
            continue
        harm = {h["order"]: h for h in m.get("harmonics", []) if h.get("present")}
        even = sum((harm[k]["amp"] or 0) ** 2 for k in harm if k % 2 == 0) ** .5
        odd = sum((harm[k]["amp"] or 0) ** 2 for k in harm if k % 2 == 1) ** .5
        out["channels"][name] = {"present": True, "fundamental_hz": m.get("fundamental_hz"), "fundamental_amp": m.get("fundamental_amp"),
                                 "thd_pct": m.get("thd_pct"), "even_amp": _f(even, 4), "odd_amp": _f(odd, 4),
                                 "harmonics": [h["hz"] for h in m.get("harmonics", []) if h.get("present")],
                                 "switching_peaks": [p["hz"] for p in m.get("other_peaks", [])[:4]], "fs": m.get("fs")}
        f0 = m.get("fundamental_hz") or linefreq_hz
        if abs(f0 - linefreq_hz) > 0.5:
            out["abnormal"].append(f"{name}: fundamental {f0:.2f} Hz is {f0 - linefreq_hz:+.2f} Hz from nominal")
        thd = m.get("thd_pct") or 0
        if thd > 8:
            out["findings"].append(f"{name}: THD {thd:.1f} % — consistent with non-linear loads such as switch mode supplies or inverters")
            if thd > 20:
                out["abnormal"].append(f"{name}: THD {thd:.1f} % exceeds 20 %")
        if even > odd and even > 0:
            out["findings"].append(f"{name}: even harmonics dominate — consistent with asymmetric or half-wave loads")
        if name == "ch1" and 2 in harm and (harm[2]["amp"] or 0) > 0.5 * (m.get("fundamental_amp") or 1e9):
            out["findings"].append('channel 1: strong 100 Hz component — consistent with transformer or strain emissions')
        if m.get("other_peaks"):
            top = m["other_peaks"][0]
            if (top.get("amp") or 0) > 0.1 * (m.get("fundamental_amp") or 1e9):
                out["findings"].append(f"{name}: non-harmonic peak at {top['hz']} Hz — consistent with switching noise (bandwidth limited to {m.get('nyquist_hz')} Hz)")
    if not any(c.get("present") for c in out["channels"].values()):
        out["findings"].append('No reference fundamental detected on any channel')
    return out


# ── 14. history and trend analysis ───────────────────────────────────────────
def trend_analysis(t, x, windows=((10, "last 10 minutes"), (60, "last 60 minutes"))):
    """Percent change over each window (first vs last quarter), linear drift, and a periodic
    pattern search by autocorrelation. t in seconds, x any series."""
    t = np.asarray(t, dtype=float); x = np.asarray(x, dtype=float)
    ok = np.isfinite(t) & np.isfinite(x); t, x = t[ok], x[ok]
    out = {"samples": int(x.size), "windows": []}
    if x.size < 8:
        return out
    now = t[-1]
    for minutes, label in windows:
        m = t >= now - minutes * 60
        if m.sum() < 8:
            out["windows"].append({"label": label, "text": "not enough history"})
            continue
        seg = x[m]; q = max(2, seg.size // 4)
        a, b = float(np.mean(seg[:q])), float(np.mean(seg[-q:]))
        pct = 100 * (b - a) / abs(a) if abs(a) > 1e-9 else None
        sigma = float(np.std(seg)) or 1e-9
        stable = abs(b - a) < 1.0 * sigma
        out["windows"].append({"label": label, "change_pct": _f(pct, 1), "start": _f(a, 3), "end": _f(b, 3),
                               "text": "Stable" if stable else (f"{'Rising' if b > a else 'Falling'} {abs(pct):.0f} %" if pct is not None else "Changing")})
    slope = float(np.polyfit(t - t[0], x, 1)[0]) if x.size >= 3 and t[-1] > t[0] else 0.0
    out["drift_per_min"] = _f(slope * 60, 4)
    # periodicity: autocorrelation peak beyond lag 2
    d = x - x.mean()
    if d.size >= 32 and np.std(d) > 1e-12:
        ac = np.correlate(d, d, "full")[d.size - 1:] / (np.dot(d, d))
        lag = 2 + int(np.argmax(ac[2: d.size // 2])) if d.size // 2 > 3 else None
        if lag and ac[lag] > 0.5:
            dt = float(np.median(np.diff(t)))
            out["periodic"] = {"period_s": _f(lag * dt, 2), "strength": _f(ac[lag], 2), "text": f"Repeating pattern every {lag * dt:.1f} s (r = {ac[lag]:.2f})"}
        else:
            out["periodic"] = {"text": "No repeating pattern found"}
    return out


# ── 37. automated test recommendations ───────────────────────────────────────
def test_recommendations(trials, min_per_bin=5, bins=((0, 10), (10, 25), (25, 50), (50, 75), (75, 100), (100, 10 ** 9))):
    """trials: list of dicts with distance_cm, value, reference, detected, actual, source.
    Recommends where measurements are thin, distances not covered, sources with one trial,
    and negative controls if all trials are positives."""
    recs = []
    if not trials:
        return [{"text": "No trials recorded yet. Record at least 5 trials per distance for each source, plus 5 ambient (no source) controls."}]
    counts = {}
    for tr in trials:
        d = tr.get("distance_cm")
        if d is None:
            continue
        for lo, hi in bins:
            if lo <= float(d) < hi:
                counts[(lo, hi)] = counts.get((lo, hi), 0) + 1
    for lo, hi in bins:
        n = counts.get((lo, hi), 0)
        label = f">{lo} cm" if hi >= 10 ** 9 else f"{lo}–{hi} cm"
        if n < min_per_bin:
            recs.append({"text": f"Insufficient measurements at {label}: {n} trial(s). Recommended: {min_per_bin - n} additional trial(s)" + (f" at {int((lo + hi) / 2)} cm" if hi < 10 ** 9 else " at 75 cm and 100 cm")})
    sources = {}
    for tr in trials:
        sources[tr.get("source") or "unknown"] = sources.get(tr.get("source") or "unknown", 0) + 1
    for src, n in sources.items():
        if n < 3:
            recs.append({"text": f"Source '{src}' has {n} trial(s); 3 or more are needed for a repeatability figure"})
    if trials and all(tr.get("actual") for tr in trials):
        recs.append({"text": "Every trial is a positive: record ambient controls (no source) so the false positive rate is measurable"})
    values = [tr.get("value") for tr in trials if tr.get("value") is not None and tr.get("reference") is not None]
    if len(values) < 5:
        recs.append({"text": f"{len(values)} trial(s) carry a reference value; 5 or more are needed for the uncertainty budget"})
    return recs or [{"text": "Coverage is adequate for the current design: every distance band and source has enough trials"}]


# ── feature vector for the reference database / similarity / ML ─────────────
FEATURE_NAMES = ["linefreq_fund_e", "thd_e", "h2_rel_e", "h3_rel_e", "linefreq_fund_m", "thd_m", "h2_rel_m",
                 "ch3_snr", "ch3_occupancy", "ch3_peak_ghz", "transient_rate", "e_level", "h_level", "c_level"]


def feature_vector(packet):
    """Numeric features from a D4 packet, NaN where a channel is absent."""
    def rel(m, k):
        for h in (m or {}).get("harmonics", []) or []:
            if h.get("order") == k and h.get("present"):
                return h.get("rel_db")
        return -60.0
    me = packet.get("linefreq") or {}; mm = packet.get("linefreq_ch1") or {}; ch3 = packet.get("ch3") or {}
    sc = packet.get("scores") or {}
    v = [me.get("fundamental_amp") if me.get("fundamental_detected") else 0.0, me.get("thd_pct") or 0.0, rel(me, 2), rel(me, 3),
         mm.get("fundamental_amp") if mm.get("fundamental_detected") else 0.0, mm.get("thd_pct") or 0.0, rel(mm, 2),
         ch3.get("snr_db"), ch3.get("occupancy_pct"), (ch3.get("primary_peak_hz") or 0) / 1e9,
         (packet.get("fingerprint") or {}).get("transient_rate_per_min"), sc.get("ch2"), sc.get("ch1"), sc.get("conducted")]
    # None (not NaN) for JSON safety; consumers convert back with _nanvec
    return [_f(x, 4) if x is not None else None for x in v]


def _nanvec(v):
    return np.array([float("nan") if x is None else float(x) for x in (v or [])], dtype=float)


def similarity_ranked(sample, references):
    """Cosine similarity over the features both vectors have, per reference profile."""
    s = _nanvec(sample)
    out = []
    for name, ref in references.items():
        r = _nanvec(ref.get("features") or [])
        n = min(s.size, r.size)
        if n == 0:
            continue
        ok = np.isfinite(s[:n]) & np.isfinite(r[:n])
        if ok.sum() < 3:
            continue
        a, b = s[:n][ok], r[:n][ok]
        scale = np.maximum(1e-9, np.maximum(np.abs(a), np.abs(b)))
        a, b = a / scale, b / scale
        if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
            continue
        out.append({"name": name, "similarity_pct": _f(100 * float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))), 1),
                    "features_compared": int(ok.sum()), "recorded_at": ref.get("recorded_at")})
    out.sort(key=lambda q: -(q["similarity_pct"] or 0))
    return out


# ── 38. minimal classifier (nearest centroid with z-scored features) ─────────
def train_nearest_centroid(samples):
    """samples: list of {'label', 'features'}. Returns a model dict or None when a class has
    fewer than 5 samples. Deliberately simple: it is honest about its data, not clever."""
    by = {}
    for smp in samples:
        by.setdefault(smp["label"], []).append(smp["features"])
    if len(by) < 2 or any(len(v) < 5 for v in by.values()):
        return None
    X = np.array([_nanvec(f) for v in by.values() for f in v], dtype=float)
    with np.errstate(all="ignore"):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            mu = np.nanmean(X, axis=0); sd = np.nanstd(X, axis=0) + 1e-9
    clean = lambda arr: [None if not math.isfinite(float(v)) else float(v) for v in arr]
    model = {"mu": clean(mu), "sd": clean(sd), "classes": {}, "n": int(X.shape[0])}
    for label, feats in by.items():
        Z = (np.array([_nanvec(f) for f in feats], dtype=float) - mu) / sd
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model["classes"][label] = {"centroid": clean(np.nanmean(Z, axis=0)), "n": len(feats)}
    return model


def classify(model, features):
    z = (_nanvec(features) - _nanvec(model["mu"])) / _nanvec(model["sd"])
    dists = {}
    for label, c in model["classes"].items():
        cz = _nanvec(c["centroid"]); ok = np.isfinite(z) & np.isfinite(cz)
        dists[label] = float(np.linalg.norm(z[ok] - cz[ok])) if ok.any() else float("inf")
    w = {k: math.exp(-d) for k, d in dists.items()}
    tot = sum(w.values()) or 1.0
    return sorted(({"label": k, "probability_pct": _f(100 * v / tot, 1)} for k, v in w.items()), key=lambda q: -(q["probability_pct"] or 0))
