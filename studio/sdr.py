"""RTL-SDR acquisition: continuous IQ capture, power spectrum and waterfall.

The tinySA sweeps slowly across a very wide span and reports one level per point.
The RTL-SDR does the opposite: it streams continuous complex samples over a ~2 MHz
slice, so the fine structure inside one band, short bursts and exact carrier offsets
are visible where a sweep only ever sees a time average.

Levels are reported in dBFS (decibels relative to the receiver's full scale), never
in dBm. The dongle carries no calibration, no reference and no absolute scale, so an
absolute power figure would be invented. Differences between bins on one capture are
meaningful; the absolute number is not.
"""
from __future__ import annotations

from collections import deque
import math
import os
import shutil
import signal
import subprocess
import threading
import time

SDR_RATE = 2_048_000          # samples/s; the widest rate the dongle holds without loss here
SDR_NFFT = 2048               # ~1 kHz bins at 2.048 MS/s
SDR_SAMPLES = 131_072         # 0.064 s of IQ per burst: 64 frames is already a smooth average
SDR_IDLE_S = 5.0              # gap between bursts while someone is watching
SDR_DOZE_S = 30.0             # gap between bursts when nobody is
SDR_INTEREST_S = 20.0         # how long a view keeps the receiver awake
SDR_EDGE_TRIM = 0.80          # keep the middle 80 %: the tuner rolls off at the slice edges
SDR_DC_BINS = 3               # bins either side of centre killed (zero-IF LO leakage)
WATERFALL_ROWS = 90

# Fitipower FC0013 and R820T tune over roughly these limits. Values outside are refused
# rather than silently mistuned.
SDR_MIN_HZ = 24_000_000
SDR_MAX_HZ = 1_700_000_000

SDR_PRESETS = (
    ("FM broadcast", 88_000_000, 108_000_000),
    ("Airband", 118_000_000, 137_000_000),
    ("VHF marine / business", 150_000_000, 174_000_000),
    ("UHF business", 400_000_000, 470_000_000),
    ("ISM 433", 433_000_000, 435_000_000),
    ("LTE 800 downlink", 791_000_000, 821_000_000),
    ("GSM 900 downlink", 925_000_000, 960_000_000),
    ("ADS-B 1090", 1_089_000_000, 1_091_000_000),
)


def _blank():
    return {
        "present": False, "error": None, "status": "Starting",
        "device": None, "tuner": None, "serial": None,
        "gains_db": [], "gain_db": None, "gain_mode": "auto", "gain_note": "",
        "rms_fullscale": 0.0, "trusted": False, "untrusted_reason": None,
        "centre_hz": 100_000_000, "rate_hz": SDR_RATE, "span_hz": int(SDR_RATE * SDR_EDGE_TRIM),
        "freqs": [], "levels_dbfs": [], "floor_dbfs": None,
        "peak_dbfs": None, "peak_hz": None, "peaks": [],
        "waterfall": deque(maxlen=WATERFALL_ROWS), "waterfall_freqs": [],
        "waterfall_times": deque(maxlen=WATERFALL_ROWS),
        "bursts": 0, "short_reads": 0, "last_rx": None, "capture_s": None,
        "clipped": False, "clip_fraction": 0.0, "dc_offset": 0.0, "iq_balance": 0.0,
        "code_hist": [], "iq_grid": [], "iq_axis": [], "iq_span": 0.0,
        "iq_i": [], "iq_q": [], "iq_dt_s": 0.0, "envelope": [], "envelope_dt_s": 0.0,
        "papr_db": None, "phase_offset_hz": None,
        "sweep": None, "sweep_running": False, "sweep_progress": 0.0,
        "mode": "live", "bytes_total": 0,
    }


def install(ns):
    """Register the RTL-SDR reader, its data block and its command channel."""
    import numpy as np

    stop = ns["STOP_EVENT"]
    logger = ns["LOG"]

    sdr_data = _blank()
    sdr_lock = threading.Lock()
    sdr_cmd = {"centre_hz": None, "gain_db": None, "sweep": None, "cancel_sweep": False}
    sdr_cmd_lock = threading.Lock()
    # The receiver only streams at full rate while someone is looking at it. Converting and
    # transforming its samples costs the sensor threads measurable time, and there is no point
    # paying that for a waterfall nobody is watching. Every read of the state counts as a view.
    interest = {"last": 0.0}

    # ── capture ────────────────────────────────────────────────────────────
    def capture(centre_hz, gain_db, samples=SDR_SAMPLES, timeout=12.0):
        """One burst of IQ from the dongle as a complex64 array, DC removed.

        rtl_sdr's -n flag is ignored by the packaged build, so the burst is bounded by
        reading an exact byte count from the pipe and then ending the process group.
        A gain of exactly 0 is rtl_sdr's sentinel for the dongle's own AGC, which hunts
        and drives the front end into clipping on a strong local transmitter; the gain
        here is always an explicit value from the tuner's table (see manage_gain).
        """
        gain = f"{float(gain_db):.1f}"
        if gain == "0.0":
            gain = "0.1"
        # The sensors are the instrument; the receiver is an accessory. rtl_sdr is niced so
        # that a burst can never delay the magnetometer or the E-field converter reads, which
        # are timing-sensitive and cannot be re-run.
        argv = ["nice", "-n", "10", "rtl_sdr", "-f", str(int(centre_hz)),
                "-s", str(int(SDR_RATE)), "-g", gain, "-"]
        started = time.time()
        proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                start_new_session=True)
        try:
            os.nice(0)
        except OSError:
            pass
        want = samples * 2
        chunks, got = [], 0
        try:
            while got < want:
                if time.time() - started > timeout or stop.is_set():
                    break
                chunk = proc.stdout.read(min(65536, want - got))
                if not chunk:
                    break
                chunks.append(chunk)
                got += len(chunk)
        finally:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                pass
            try:
                err = proc.communicate(timeout=4)[1]
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
                err = b""
        raw = np.frombuffer(b"".join(chunks), dtype=np.uint8)
        if raw.size < 4096:
            message = (err.decode("utf8", "replace").strip().splitlines() or ["no samples"])[-1]
            raise IOError(message[:120])
        raw = raw[: (raw.size // 2) * 2]
        # 8-bit unsigned offset binary; 0 and 255 mean the ADC ran out of range
        clip = float(np.count_nonzero((raw == 0) | (raw == 255))) / raw.size
        centred = raw.astype(np.float32) - 127.5
        iq = (centred[0::2] + 1j * centred[1::2]).astype(np.complex64) / 127.5
        dc = complex(iq.mean())
        iq = iq - dc
        rms = float(np.std(centred)) / 127.5
        # The 8-bit codes themselves, before any maths. How much of the converter's range
        # the signal actually occupies is the one honest picture of whether the gain is
        # right: a narrow spike wastes the ADC, a distribution touching 0 or 255 is
        # clipping, and a twin-peaked one means the front end is being overdriven.
        codes = np.bincount(raw, minlength=256)[:256]
        return iq, {"clip_fraction": clip, "dc_offset": abs(dc), "rms_fullscale": rms,
                    "capture_s": time.time() - started, "bytes": raw.size,
                    "code_hist": codes.astype(np.int64)}

    window = np.hanning(SDR_NFFT).astype(np.float32)
    window_gain = float((window ** 2).sum())

    def spectrum(iq):
        """Welch-averaged power spectrum of one burst, in dBFS, centre bins removed."""
        frames = len(iq) // SDR_NFFT
        if frames < 1:
            raise IOError('burst too short for a channel 3')
        block = iq[: frames * SDR_NFFT].reshape(frames, SDR_NFFT) * window
        power = (np.abs(np.fft.fft(block, axis=1)) ** 2).mean(axis=0) / window_gain
        power = np.fft.fftshift(power)
        levels = 10.0 * np.log10(power + 1e-20)
        mid = SDR_NFFT // 2
        # The zero-IF tuner leaks its own local oscillator into the centre bin. It is an
        # artefact of the receiver, not a signal, so it is replaced by the local median
        # instead of being allowed to masquerade as the strongest carrier in the band.
        neighbourhood = np.concatenate([levels[mid - 40:mid - SDR_DC_BINS],
                                        levels[mid + SDR_DC_BINS + 1:mid + 40]])
        levels[mid - SDR_DC_BINS:mid + SDR_DC_BINS + 1] = float(np.median(neighbourhood))
        return levels

    def trim(levels, centre_hz):
        """Drop the rolled-off slice edges and return (freqs_hz, levels)."""
        keep = int(SDR_NFFT * SDR_EDGE_TRIM) // 2 * 2
        start = (SDR_NFFT - keep) // 2
        levels = levels[start:start + keep]
        offsets = (np.arange(keep) - keep / 2) * (SDR_RATE / SDR_NFFT)
        return offsets + centre_hz, levels

    IQ_PREVIEW = 1500             # samples kept for the I/Q trajectory
    IQ_GRID = 72                  # constellation density is IQ_GRID x IQ_GRID

    def iq_detail(iq):
        """What a burst looks like as raw complex samples rather than as a spectrum.

        A spectrum throws the phase away. These views keep it, and they are the only
        place in the instrument where the receiver's actual samples are visible:

        * constellation - a 2-D density of I against Q over every sample in the burst.
          Noise alone is a round blob centred on the origin; a strong carrier pulls it
          into a ring, and a clipping front end flattens its edges into straight lines.
        * trajectory - a decimated run of consecutive samples, which is a path through
          the I/Q plane over time rather than a static cloud.
        * envelope - |iq| against time, the amplitude the spectrum averages away.
        * phase slope - residual frequency offset between the tuner and the signal.
        """
        if iq.size < 64:
            return {}
        i_all = np.real(iq).astype(np.float32)
        q_all = np.imag(iq).astype(np.float32)
        span = float(max(np.abs(i_all).max(), np.abs(q_all).max(), 1e-6))
        edges = np.linspace(-span, span, IQ_GRID + 1)
        density, _, _ = np.histogram2d(i_all, q_all, bins=(edges, edges))
        centres = ((edges[:-1] + edges[1:]) / 2).astype(np.float32)

        step = max(1, iq.size // IQ_PREVIEW)
        keep = iq[: IQ_PREVIEW * step: step]
        env_step = max(1, iq.size // 600)
        envelope = np.abs(iq[: (iq.size // env_step) * env_step].reshape(-1, env_step)).mean(axis=1)

        # Phase slope over the burst: a steady rotation is a frequency offset, in hertz.
        phase = np.unwrap(np.angle(iq[::step] + 1e-12))
        offset_hz = 0.0
        if phase.size > 8:
            dt = step / SDR_RATE
            offset_hz = float(np.polyfit(np.arange(phase.size) * dt, phase, 1)[0] / (2 * math.pi))
        return {
            "iq_span": round(span, 5),
            "iq_grid": [[int(v) for v in row] for row in density],
            "iq_axis": [round(float(v), 5) for v in centres],
            "iq_i": [round(float(v), 5) for v in np.real(keep)],
            "iq_q": [round(float(v), 5) for v in np.imag(keep)],
            "iq_dt_s": step / SDR_RATE,
            "envelope": [round(float(v), 5) for v in envelope],
            "envelope_dt_s": env_step / SDR_RATE,
            "papr_db": round(float(20 * np.log10((np.abs(iq).max() + 1e-12) /
                                                 (np.sqrt((np.abs(iq) ** 2).mean()) + 1e-12))), 2),
            "phase_offset_hz": round(offset_hz, 1),
        }

    def find_peaks(freqs, levels, limit=8, separation_hz=30_000):
        """Local maxima that stand clear of the noise floor.

        The floor and its spread are taken from the quiet part of the trace only. Using the
        median of everything let a band full of broadcast carriers raise its own threshold
        above its own signals, so a sweep of the FM band reported nothing in it at all.
        """
        floor = float(np.percentile(levels, 20))
        quiet = levels[levels <= np.percentile(levels, 50)]
        spread = float(np.median(np.abs(quiet - floor))) if quiet.size else 0.5
        spread = spread or 0.5
        threshold = floor + max(6.0, min(20.0, 4.0 * spread))
        peaks = []
        # Two bins closer together than this are treated as one signal. A broadcast FM
        # carrier is +/-75 kHz wide before its subcarriers, so at a narrow separation its
        # own sidebands are listed as if they were separate stations.
        bin_hz = float(np.median(np.diff(freqs))) if freqs.size > 1 else SDR_RATE / SDR_NFFT
        guard = max(3, int(separation_hz / max(bin_hz, 1.0)))
        order = np.argsort(levels)[::-1]
        for index in order:
            level = float(levels[index])
            if level < threshold or len(peaks) >= limit:
                break
            if any(abs(int(index) - p["index"]) < guard for p in peaks):
                continue
            peaks.append({"index": int(index), "freq": float(freqs[index]),
                          "separation_hz": separation_hz,
                          "level_dbfs": round(level, 2),
                          "over_floor_db": round(level - floor, 2),
                          "band": ns["_band_of"](float(freqs[index])) if "_band_of" in ns else ""})
        peaks.sort(key=lambda p: -p["level_dbfs"])
        for peak in peaks:
            peak.pop("index", None)
            peak.pop("separation_hz", None)
        return peaks, floor

    # ── device identity ────────────────────────────────────────────────────
    def probe():
        """Ask rtl_test which dongle and tuner are attached, and its gain table."""
        out = subprocess.run(["rtl_test", "-t"], capture_output=True, timeout=30)
        text = (out.stdout + out.stderr).decode("utf8", "replace")
        info = {"device": None, "tuner": None, "serial": None, "gains_db": []}
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("0:"):
                parts = [p.strip() for p in line[2:].split(",")]
                info["device"] = ", ".join(parts[:2]) if len(parts) > 1 else line[2:].strip()
                for part in parts:
                    if part.upper().startswith("SN:"):
                        info["serial"] = part[3:].strip()
            elif "tuner" in line.lower() and line.lower().startswith("found"):
                info["tuner"] = line[len("Found"):].strip().rstrip(".")
            elif line.startswith("Supported gain values"):
                try:
                    info["gains_db"] = [float(v) for v in line.split(":", 1)[1].split()]
                except ValueError:
                    pass
        if not info["device"]:
            raise IOError((text.strip().splitlines() or ['no Source 4 found'])[-1][:120])
        return info

    # ── sweep ──────────────────────────────────────────────────────────────
    def run_sweep(start_hz, stop_hz, gain_db):
        """Step the tuner across a range and stitch the usable middle of each slice."""
        step = int(SDR_RATE * SDR_EDGE_TRIM)
        centres = []
        centre = int(start_hz) + step // 2
        while centre - step // 2 < int(stop_hz):
            centres.append(centre)
            centre += step
        if not centres:
            raise ValueError("sweep range is narrower than one slice")
        if len(centres) > 400:
            raise ValueError(f"sweep needs {len(centres)} slices; narrow the range")
        freqs_all, levels_all = [], []
        for position, centre in enumerate(centres):
            with sdr_cmd_lock:
                if sdr_cmd["cancel_sweep"]:
                    sdr_cmd["cancel_sweep"] = False
                    raise InterruptedError("sweep cancelled")
            if stop.is_set():
                raise InterruptedError("shutting down")
            with sdr_lock:
                step_gain = gain_db if gain_db is not None else (sdr_data["gain_db"] or 7.1)
            iq, stats = capture(centre, step_gain, samples=SDR_SAMPLES)
            manage_gain(stats)
            freqs, levels = trim(spectrum(iq), centre)
            freqs_all.append(freqs)
            levels_all.append(levels)
            with sdr_lock:
                sdr_data["sweep_progress"] = round((position + 1) / len(centres) * 100, 1)
                sdr_data["bytes_total"] += stats["bytes"]
        freqs = np.concatenate(freqs_all)
        levels = np.concatenate(levels_all)
        # The last slice reaches past the requested stop so the range is fully covered; the
        # part beyond it is discarded rather than reported as if it had been asked for.
        inside = (freqs >= float(start_hz)) & (freqs <= float(stop_hz))
        if inside.any():
            freqs, levels = freqs[inside], levels[inside]
        order = np.argsort(freqs)
        freqs, levels = freqs[order], levels[order]
        full_points = int(freqs.size)
        # Carriers are found at the receiver's real resolution, before the trace is thinned
        # for transport: a kilohertz-wide bin survives decimation as a smeared bump whose
        # frequency and height are both wrong.
        peaks, floor = find_peaks(freqs, levels, limit=12, separation_hz=150_000)
        target = 3000
        if freqs.size > target:
            group = int(math.ceil(freqs.size / target))
            usable = (freqs.size // group) * group
            freqs = freqs[:usable].reshape(-1, group).mean(axis=1)
            levels = levels[:usable].reshape(-1, group).max(axis=1)
        return {"start_hz": int(start_hz), "stop_hz": int(stop_hz),
                "slices": len(centres), "points": int(freqs.size),
                "measured_points": full_points,
                "note": ("plotted at " + str(int(freqs.size)) + " points, strongest of each group; "
                         "carriers were found at the full " + str(full_points) + " points"),
                "freqs": [round(float(f), 1) for f in freqs],
                "levels_dbfs": [round(float(v), 2) for v in levels],
                "floor_dbfs": round(floor, 2), "peaks": peaks,
                "finished": time.time()}

    # ── gain management ────────────────────────────────────────────────────
    # The receiver's own automatic gain chases the loudest thing in the slice and, next to
    # a broadcast transmitter, holds the ADC hard against its rails. A clipped capture is
    # not a weak measurement, it is a wrong one: the spectrum fills with mixing products
    # that were never on the air. So the gain is stepped here against what the samples
    # actually show, and a capture that still clips is published as untrusted rather than
    # quietly plotted.
    CLIP_LIMIT = 0.002        # 0.2 % of samples at the rail
    RMS_TARGET_LOW = 0.08     # below this the ADC's range is being wasted
    RMS_TARGET_HIGH = 0.30    # above this a peak is close to the rail

    def manage_gain(stats):
        """Step the tuner gain towards a capture that uses the ADC without clipping."""
        with sdr_lock:
            if sdr_data["gain_mode"] != "auto":
                return sdr_data["gain_db"], None
            table = list(sdr_data["gains_db"]) or [0.0]
            current = sdr_data["gain_db"]
        if current is None:
            current = table[len(table) // 2]
        index = min(range(len(table)), key=lambda i: abs(table[i] - current))
        note = None
        if stats["clip_fraction"] > CLIP_LIMIT and index > 0:
            index -= 1
            note = f"gain reduced to {table[index]:.1f} dB; the previous capture clipped"
        elif stats["rms_fullscale"] < RMS_TARGET_LOW and index < len(table) - 1 \
                and stats["clip_fraction"] <= CLIP_LIMIT:
            index += 1
            note = f"gain raised to {table[index]:.1f} dB; the receiver had spare range"
        chosen = table[index]
        with sdr_lock:
            sdr_data["gain_db"] = chosen
            if note:
                sdr_data["gain_note"] = note
        return chosen, note

    def trust(stats):
        """Whether this capture may be presented as a measurement."""
        if stats["clip_fraction"] > CLIP_LIMIT:
            return False, (f"{stats['clip_fraction']*100:.1f}% of samples hit the converter's "
                           "limit; this slice contains mixing products, not only real signals")
        if stats["rms_fullscale"] > RMS_TARGET_HIGH:
            return False, "the strongest signal is close to the converter's limit; reduce the gain"
        if stats["rms_fullscale"] < 0.01:
            return False, "almost no signal reached the converter; check the antenna connection"
        return True, None

    # ── reader thread ──────────────────────────────────────────────────────
    def sdr_reader():
        if shutil.which("rtl_sdr") is None:
            with sdr_lock:
                sdr_data.update(present=False, status="Not installed",
                                error="rtl-sdr tools are not installed on this instrument")
            return
        backoff = 2.0
        while not stop.is_set():
            try:
                info = probe()
                gains = info["gains_db"]
                with sdr_lock:
                    sdr_data.update(present=True, error=None, status="Live acquisition", **info)
                    if sdr_data["gain_db"] is None and gains:
                        # start mid-table: the top of the range clips instantly near a broadcaster
                        sdr_data["gain_db"] = gains[len(gains) // 2]
                logger.info('Source 4 ready: %s, tuner %s', info["device"], info["tuner"])
                backoff = 2.0

                while not stop.is_set():
                    with sdr_cmd_lock:
                        new_centre = sdr_cmd.pop("centre_hz", None)
                        sdr_cmd["centre_hz"] = None
                        new_gain = sdr_cmd.pop("gain_db", None)
                        sdr_cmd["gain_db"] = None
                        sweep_request = sdr_cmd.pop("sweep", None)
                        sdr_cmd["sweep"] = None
                    with sdr_lock:
                        if new_centre:
                            sdr_data["centre_hz"] = int(new_centre)
                            sdr_data["waterfall"].clear()
                            sdr_data["waterfall_times"].clear()
                        if new_gain is not None:
                            sdr_data["gain_db"] = None if new_gain == "auto" else float(new_gain)
                            sdr_data["gain_mode"] = "auto" if new_gain == "auto" else "manual"
                        centre = sdr_data["centre_hz"]
                        gain = sdr_data["gain_db"] if sdr_data["gain_mode"] == "manual" else None

                    if sweep_request:
                        with sdr_lock:
                            sdr_data.update(sweep_running=True, sweep_progress=0.0, mode="sweep",
                                            status="Sweeping")
                        try:
                            result = run_sweep(sweep_request["start_hz"], sweep_request["stop_hz"], gain)
                            with sdr_lock:
                                sdr_data["sweep"] = result
                                sdr_data["status"] = "Live acquisition"
                        except InterruptedError as exc:
                            with sdr_lock:
                                sdr_data["status"] = f"Sweep stopped: {exc}"
                        except (ValueError, IOError) as exc:
                            with sdr_lock:
                                sdr_data["status"] = f"Sweep failed: {str(exc)[:80]}"
                        finally:
                            with sdr_lock:
                                sdr_data.update(sweep_running=False, mode="live", sweep_progress=0.0)
                        continue

                    iq, stats = capture(centre, gain if gain is not None else
                                        (sdr_data["gain_db"] or 7.1))
                    ok, why = trust(stats)
                    manage_gain(stats)
                    freqs, levels = trim(spectrum(iq), centre)
                    peaks, floor = find_peaks(freqs, levels)
                    # The I/Q views cost a 2-D histogram and a phase unwrap over the whole
                    # burst. That is real interpreter time, so it is only spent when someone
                    # is actually looking at the page; unwatched, the receiver stays as cheap
                    # as it was before these views existed.
                    detail = iq_detail(iq) if time.time() - interest["last"] < SDR_INTEREST_S else {}
                    row = levels.reshape(-1, max(1, levels.size // 256)).mean(axis=1) \
                        if levels.size >= 256 else levels
                    with sdr_lock:
                        sdr_data.update(
                            freqs=[round(float(f), 1) for f in freqs],
                            levels_dbfs=[round(float(v), 2) for v in levels],
                            floor_dbfs=round(floor, 2),
                            peak_dbfs=round(float(levels.max()), 2),
                            peak_hz=float(freqs[int(levels.argmax())]),
                            peaks=peaks, last_rx=time.time(), error=None,
                            status="Live acquisition",
                            bursts=sdr_data["bursts"] + 1,
                            bytes_total=sdr_data["bytes_total"] + stats["bytes"],
                            capture_s=round(stats["capture_s"], 3),
                            clip_fraction=round(stats["clip_fraction"], 5),
                            clipped=stats["clip_fraction"] > 0.001,
                            dc_offset=round(stats["dc_offset"], 5),
                            rms_fullscale=round(stats["rms_fullscale"], 4),
                            trusted=ok, untrusted_reason=why,
                            span_hz=int(freqs[-1] - freqs[0]),
                            code_hist=[int(v) for v in stats["code_hist"]],
                            **detail,
                        )
                        sdr_data["waterfall_freqs"] = [round(float(f), 1) for f in
                                                       freqs.reshape(-1, max(1, freqs.size // 256)).mean(axis=1)] \
                            if freqs.size >= 256 else sdr_data["freqs"]
                        sdr_data["waterfall"].append([round(float(v), 1) for v in row])
                        # the real capture time of each row: the gap between bursts changes with
                        # how busy the instrument is and whether anyone is watching, so an
                        # assumed spacing would mislabel the axis
                        sdr_data["waterfall_times"].append(time.time())
                    # Measured on the instrument: a burst every 2.5 s pulled the E-field and
                    # current block rate from 1.48 to 1.17 per second, because converting and
                    # transforming the samples holds the interpreter while the sensor threads
                    # wait. Half the samples, twice the gap, and the sensors keep their rate.
                    # The receiver is an accessory; the sensors are the instrument.
                    watched = time.time() - interest["last"] < SDR_INTEREST_S
                    with sdr_lock:
                        sdr_data["status"] = ("Live acquisition" if watched
                                              else "Idle; streams when the tab is open")
                    stop.wait(max(SDR_IDLE_S if watched else SDR_DOZE_S,
                                  stats["capture_s"] * 3))
            except Exception as exc:                       # noqa: BLE001 - reader must never die
                message = str(exc).replace("—", ";")[:140] or exc.__class__.__name__
                with sdr_lock:
                    sdr_data.update(present=False, error=message, status="Offline; retry pending",
                                    sweep_running=False)
                logger.warning('Source 4 unavailable: %s', message)
                stop.wait(backoff)
                backoff = min(backoff * 2, 60.0)

    def snapshot(include_trace=True, viewing=False):
        if viewing:
            interest["last"] = time.time()
        with sdr_lock:
            data = dict(sdr_data)
        data["waterfall"] = list(data["waterfall"])
        data["waterfall_times"] = list(data["waterfall_times"])
        data["age_s"] = round(time.time() - data["last_rx"], 2) if data["last_rx"] else None
        data["megabytes"] = round(data["bytes_total"] / 1_048_576, 2)
        data["presets"] = [{"label": n, "start_hz": a, "stop_hz": b} for n, a, b in SDR_PRESETS]
        data["limits"] = {"min_hz": SDR_MIN_HZ, "max_hz": SDR_MAX_HZ,
                          "rate_hz": SDR_RATE, "bin_hz": SDR_RATE / SDR_NFFT}
        data["watched"] = time.time() - interest["last"] < SDR_INTEREST_S
        if data["watched"] and data["status"].startswith("Idle"):
            data["status"] = "Resuming; the next burst is a few seconds away"
        if not include_trace:
            for key in ("freqs", "levels_dbfs", "waterfall", "waterfall_freqs", "waterfall_times",
                        "code_hist", "iq_grid", "iq_axis", "iq_i", "iq_q", "envelope"):
                data.pop(key, None)
        return data

    def command(centre_hz=None, gain=None, sweep=None, cancel_sweep=False):
        interest["last"] = time.time()
        """Accept a retune, gain change or sweep request; every value is validated here."""
        with sdr_cmd_lock:
            if centre_hz is not None:
                value = float(centre_hz)
                if not (SDR_MIN_HZ <= value <= SDR_MAX_HZ):
                    raise ValueError(f"centre must be {SDR_MIN_HZ/1e6:.0f}-{SDR_MAX_HZ/1e6:.0f} MHz")
                sdr_cmd["centre_hz"] = value
            if gain is not None:
                if gain != "auto":
                    gain = float(gain)
                sdr_cmd["gain_db"] = gain
            if sweep is not None:
                start_hz, stop_hz = float(sweep[0]), float(sweep[1])
                if not (SDR_MIN_HZ <= start_hz < stop_hz <= SDR_MAX_HZ):
                    raise ValueError(f"sweep must lie inside {SDR_MIN_HZ/1e6:.0f}-{SDR_MAX_HZ/1e6:.0f} MHz")
                sdr_cmd["sweep"] = {"start_hz": start_hz, "stop_hz": stop_hz}
            if cancel_sweep:
                sdr_cmd["cancel_sweep"] = True
        return snapshot(include_trace=False)

    ns["sdr_data"] = sdr_data
    ns["sdr_lock"] = sdr_lock
    ns["sdr_reader"] = sdr_reader
    ns["sdr_snapshot"] = snapshot
    ns["sdr_command"] = command
    ns["SDR_PRESETS"] = SDR_PRESETS
    return sdr_reader
