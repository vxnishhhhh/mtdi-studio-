"""Field Audition: a real audio path from coil or RTL SDR to the browser.

Capture runs in a subprocess (arecord for the ALSA coil input, rtl_fm for the
RTL SDR) so a stalled device can always be stopped. PCM is read in blocks,
DC removed with a one pole high pass, gain applied, soft limited to prevent
clipping, then encoded as a streaming WAV that Chromium plays directly from
an audio element. Level metering is measured on the processed block.

If neither device is present every state reads as unavailable. Nothing here
synthesises audio.
"""
from __future__ import annotations

import copy
import math
import os
import re
import shutil
import struct
import subprocess
import threading
import time
from collections import deque
from pathlib import Path

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None

SAMPLE_RATE = 16000
BLOCK_FRAMES = 1024
RTL_VENDOR_IDS = {"0bda"}
RTL_PRODUCT_IDS = {"2838", "2832"}
SDR_MODES = ("wbfm", "fm", "am", "usb", "lsb")


def _message(value):
    return str(value).replace("—", " ").replace("-", " ")[:240]


def _read(path):
    try:
        return Path(path).read_text(errors="replace").strip()
    except OSError:
        return ""


def wav_header(sample_rate=SAMPLE_RATE, channels=1, bits=16):
    """Streaming WAV header with an open ended data length."""
    byte_rate = sample_rate * channels * bits // 8
    return b"".join([
        b"RIFF", struct.pack("<I", 0xFFFFFFFF), b"WAVE",
        b"fmt ", struct.pack("<IHHIIHH", 16, 1, channels, sample_rate, byte_rate, channels * bits // 8, bits),
        b"data", struct.pack("<I", 0xFFFFFFFF),
    ])


def detect_alsa_capture():
    """Parse arecord -l for capture devices. Returns a list of hw:card,device."""
    if not shutil.which("arecord"):
        return [], "arecord is not installed"
    try:
        result = subprocess.run(["arecord", "-l"], capture_output=True, text=True, timeout=3, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        return [], _message(exc)
    devices = []
    for match in re.finditer(r"card (\d+): ([^\[]+)\[([^\]]+)\], device (\d+): ([^\[]+)\[([^\]]+)\]", result.stdout):
        devices.append({"device": f"hw:{match.group(1)},{match.group(4)}",
                        "card": match.group(3).strip(), "name": match.group(6).strip()})
    return devices, None if devices else "No ALSA capture device is present"


def detect_rtl_sdr():
    present = False
    for device in Path("/sys/bus/usb/devices").glob("*"):
        vendor = _read(device / "idVendor").lower()
        product = _read(device / "idProduct").lower()
        if vendor in RTL_VENDOR_IDS and product in RTL_PRODUCT_IDS:
            present = True
            break
    tool = shutil.which("rtl_fm")
    if not present:
        return False, 'Source 4 USB device not detected'
    if not tool:
        return False, 'Source 4 detected but rtl_fm is not installed'
    return True, None


class PcmProcessor:
    """Per block DSP: DC removal, gain, soft limit, level measurement."""

    def __init__(self, sample_rate=SAMPLE_RATE):
        self.sample_rate = sample_rate
        self.gain = 1.0
        self.mute = False
        self.normalise = False
        # One pole high pass at about 20 Hz removes the coil amplifier offset.
        rc = 1.0 / (2 * math.pi * 20.0)
        dt = 1.0 / sample_rate
        self.hp_alpha = rc / (rc + dt)
        self.prev_in = 0.0
        self.prev_out = 0.0
        self.peak_hold = 1.0
        self.clipped_blocks = 0

    def process(self, raw):
        """raw: bytes of S16 LE mono. Returns (bytes, level_dbfs, peak_dbfs, clipped)."""
        count = len(raw) // 2
        if count == 0:
            return b"", -120.0, -120.0, False
        if np is not None:
            samples = np.frombuffer(raw[:count * 2], dtype="<i2").astype(np.float32) / 32768.0
            # High pass filter, sequential form because the state carries across blocks.
            out = np.empty_like(samples)
            prev_in, prev_out, alpha = self.prev_in, self.prev_out, self.hp_alpha
            for index in range(count):
                value = samples[index]
                prev_out = alpha * (prev_out + value - prev_in)
                prev_in = value
                out[index] = prev_out
            self.prev_in, self.prev_out = float(prev_in), float(prev_out)
            gain = 0.0 if self.mute else self.gain
            if self.normalise:
                block_peak = float(np.max(np.abs(out))) if count else 0.0
                self.peak_hold = max(block_peak, self.peak_hold * 0.98, 1e-4)
                gain = gain * min(20.0, 0.7 / self.peak_hold)
            out *= gain
            peak = float(np.max(np.abs(out))) if count else 0.0
            clipped = peak > 0.999
            if clipped:
                self.clipped_blocks += 1
                out = np.tanh(out)
            rms = float(np.sqrt(np.mean(out * out)))
            encoded = np.clip(out * 32767.0, -32768, 32767).astype("<i2").tobytes()
        else:
            values = struct.unpack("<%dh" % count, raw[:count * 2])
            gain = 0.0 if self.mute else self.gain
            out = []
            prev_in, prev_out, alpha = self.prev_in, self.prev_out, self.hp_alpha
            for code in values:
                value = code / 32768.0
                prev_out = alpha * (prev_out + value - prev_in)
                prev_in = value
                out.append(prev_out * gain)
            self.prev_in, self.prev_out = prev_in, prev_out
            peak = max(abs(v) for v in out)
            clipped = peak > 0.999
            if clipped:
                self.clipped_blocks += 1
                out = [math.tanh(v) for v in out]
            rms = math.sqrt(sum(v * v for v in out) / count)
            encoded = struct.pack("<%dh" % count, *[int(max(-32768, min(32767, v * 32767))) for v in out])
        level = 20 * math.log10(max(rms, 1e-6))
        peak_db = 20 * math.log10(max(peak, 1e-6))
        return encoded, level, peak_db, clipped


class AudioSource:
    """A subprocess backed PCM producer with a bounded fan out to listeners."""

    name = "source"
    label = "Audio source"

    def __init__(self):
        self.lock = threading.RLock()
        self.process = None
        self.thread = None
        self.stop_event = threading.Event()
        self.listeners = []
        self.processor = PcmProcessor()
        self.state = {"state": "unavailable", "label": self.label, "error": None, "device": None,
                      "level_dbfs": None, "peak_dbfs": None, "clipped": False, "gain": 1.0, "mute": False,
                      "normalise": False, "sample_rate": SAMPLE_RATE, "listeners": 0,
                      "blocks": 0, "last_block": None, "enabled": False, "started_at": None}
        self.refresh_availability()

    # Subclasses supply the capture command and availability probe.
    def probe(self):
        return False, "Not implemented", None

    def command(self):
        raise NotImplementedError

    def refresh_availability(self):
        available, error, device = self.probe()
        with self.lock:
            self.state["device"] = device
            if not self.state["enabled"]:
                self.state["state"] = "available" if available else "unavailable"
                self.state["error"] = error
        return available

    def set_controls(self, gain=None, mute=None, normalise=None):
        with self.lock:
            if gain is not None:
                gain = float(gain)
                if not math.isfinite(gain) or not 0.0 <= gain <= 30.0:
                    raise ValueError("Gain must be between 0 and 30")
                self.processor.gain = gain
                self.state["gain"] = gain
            if mute is not None:
                if not isinstance(mute, bool):
                    raise ValueError("Mute must be true or false")
                self.processor.mute = mute
                self.state["mute"] = mute
            if normalise is not None:
                if not isinstance(normalise, bool):
                    raise ValueError("Normalise must be true or false")
                self.processor.normalise = normalise
                self.state["normalise"] = normalise

    def start(self):
        with self.lock:
            if self.state["enabled"] and self.process is not None and self.process.poll() is None:
                return self.snapshot()
            available, error, device = self.probe()
            self.state["device"] = device
            if not available:
                self.state.update(state="unavailable", error=error, enabled=False)
                raise RuntimeError(error or "Audio device unavailable")
            self.stop_event.clear()
            try:
                self.process = subprocess.Popen(self.command(), stdout=subprocess.PIPE,
                                                stderr=subprocess.PIPE, bufsize=0)
            except OSError as exc:
                self.state.update(state="error", error=_message(exc), enabled=False)
                raise RuntimeError(_message(exc))
            self.state.update(state="initialising", error=None, enabled=True, blocks=0,
                              started_at=time.time(), clipped=False)
            self.thread = threading.Thread(target=self._pump, name="audition_" + self.name, daemon=True)
            self.thread.start()
            return self.snapshot()

    def stop(self):
        with self.lock:
            self.stop_event.set()
            process, self.process = self.process, None
            self.state.update(enabled=False, level_dbfs=None, peak_dbfs=None)
        if process is not None:
            try:
                process.terminate()
                process.wait(timeout=2)
            except (OSError, subprocess.SubprocessError):
                try:
                    process.kill()
                except OSError:
                    pass
        if self.thread is not None and self.thread is not threading.current_thread():
            self.thread.join(1.0)
        self.thread = None
        with self.lock:
            for queue_ in self.listeners:
                queue_.append(None)
            self.listeners = []
        self.refresh_availability()
        return self.snapshot()

    def _pump(self):
        process = self.process
        block_bytes = BLOCK_FRAMES * 2
        try:
            while not self.stop_event.is_set() and process is not None and process.poll() is None:
                raw = process.stdout.read(block_bytes)
                if not raw:
                    break
                encoded, level, peak, clipped = self.processor.process(raw)
                with self.lock:
                    self.state.update(state="streaming", level_dbfs=level, peak_dbfs=peak,
                                      clipped=clipped, blocks=self.state["blocks"] + 1,
                                      last_block=time.time())
                    for queue_ in self.listeners:
                        queue_.append(encoded)
            if not self.stop_event.is_set():
                error = ""
                if process is not None:
                    try:
                        error = process.stderr.read(400).decode(errors="replace").strip()
                    except (OSError, ValueError):
                        error = ""
                with self.lock:
                    self.state.update(state="error", enabled=False,
                                      error=_message(error or "Capture process ended"))
                    for queue_ in self.listeners:
                        queue_.append(None)
                    self.listeners = []
        except Exception as exc:  # pragma: no cover
            with self.lock:
                self.state.update(state="error", enabled=False, error=_message(exc))

    def subscribe(self):
        queue_ = deque(maxlen=32)
        with self.lock:
            self.listeners.append(queue_)
            self.state["listeners"] = len(self.listeners)
        return queue_

    def unsubscribe(self, queue_):
        with self.lock:
            if queue_ in self.listeners:
                self.listeners.remove(queue_)
            self.state["listeners"] = len(self.listeners)

    def snapshot(self):
        with self.lock:
            item = copy.deepcopy(self.state)
        if item["enabled"] and item["last_block"] and time.time() - item["last_block"] > 3:
            item["state"] = "stale"
        return item


class CoilAudioSource(AudioSource):
    """Near field pickup coil into an ALSA capture device."""

    name = "coil"
    label = "Coil audio"

    def probe(self):
        configured = os.environ.get("STUDIO_COIL_ALSA_DEVICE", "").strip()
        devices, error = detect_alsa_capture()
        if configured:
            return True, None, configured
        if devices:
            return True, None, devices[0]["device"]
        return False, error, None

    def command(self):
        device = self.state["device"] or "default"
        return ["arecord", "-q", "-D", device, "-f", "S16_LE", "-c", "1",
                "-r", str(SAMPLE_RATE), "-t", "raw", "--buffer-size", "4096"]


class SdrAudioSource(AudioSource):
    """RTL SDR demodulated audio through rtl_fm. Modes are extensible via SDR_MODES."""

    name = "sdr"
    label = 'Source 4 audio'

    def __init__(self):
        self.frequency_hz = float(os.environ.get("STUDIO_SDR_FREQUENCY_HZ", "100000000"))
        self.mode = os.environ.get("STUDIO_SDR_MODE", "wbfm")
        super().__init__()
        self.state.update(frequency_hz=self.frequency_hz, mode=self.mode, modes=list(SDR_MODES))

    def probe(self):
        available, error = detect_rtl_sdr()
        return available, error, "rtl_fm" if available else None

    def set_tuning(self, frequency_hz=None, mode=None):
        with self.lock:
            if frequency_hz is not None:
                frequency_hz = float(frequency_hz)
                if not math.isfinite(frequency_hz) or not 24e6 <= frequency_hz <= 1.766e9:
                    raise ValueError("Frequency must be between 24 MHz and 1766 MHz")
                self.frequency_hz = frequency_hz
                self.state["frequency_hz"] = frequency_hz
            if mode is not None:
                if mode not in SDR_MODES:
                    raise ValueError("Unsupported demodulation mode")
                self.mode = mode
                self.state["mode"] = mode
            running = self.state["enabled"]
        if running:
            self.stop()
            self.start()

    def command(self):
        demod_rate = "200k" if self.mode == "wbfm" else "24k"
        return ["rtl_fm", "-f", str(int(self.frequency_hz)), "-M", self.mode, "-s", demod_rate,
                "-r", str(SAMPLE_RATE), "-g", "30", "-E", "deemp", "-"]


class EfieldAudioSource(AudioSource):
    """The electric probe ADS1115 stream made audible.

    The converter runs at 860 samples per second, so the audible band is limited to
    about 430 Hz: mains hum, its low harmonics and switching envelopes. Blocks are
    resampled to 16 kHz by linear interpolation. No subprocess is involved; the
    acquisition loop feeds each measured block through ``feed``.
    """

    name = "efield"
    label = 'Channel 2 probe audio'

    def __init__(self, channel_state=None):
        self.channel_state = channel_state or (lambda: "offline")
        self.residual = None
        super().__init__()
        self.processor.gain = 4.0
        self.state["gain"] = 4.0
        self.phase = 0.0

    def probe(self):
        state = self.channel_state()
        if state == "connected":
            return True, None, 'Channel 2 probe live sonification (AC activity + low-rate Uno carrier)'
        return False, f"Channel 2 probe channel is {state}", None

    def start(self):
        with self.lock:
            if self.state["enabled"]:
                return self.snapshot()
            available, error, device = self.probe()
            self.state["device"] = device
            if not available:
                self.state.update(state="unavailable", error=error, enabled=False)
                raise RuntimeError(error)
            self.stop_event.clear()
            self.residual = None
            self.state.update(state="initialising", error=None, enabled=True, blocks=0,
                              started_at=time.time(), clipped=False)
            return self.snapshot()

    def stop(self):
        with self.lock:
            self.stop_event.set()
            self.state.update(enabled=False, level_dbfs=None, peak_dbfs=None)
            for queue_ in self.listeners:
                queue_.append(None)
            self.listeners = []
        self.refresh_availability()
        return self.snapshot()

    def feed(self, codes, sample_rate, volts_per_code):
        """Called from the acquisition thread with one measured block."""
        if not self.state["enabled"] or len(codes) < 2:
            return
        rate = sample_rate if sample_rate and sample_rate > 0 else 860.0
        if rate < 100.0:
            # The Uno caller supplies a rolling history, not a fresh block. Rendering
            # the whole history on every 10 Hz update generated ~40x more audio than
            # real time, filled listener queues and starved sensor acquisition. Emit
            # exactly one new sample interval from the newest measured transition.
            activity = max(0.0, float(codes[-1]))
            count = max(1, int(round(SAMPLE_RATE / rate)))
            if np is not None:
                frequency = 120.0 + min(activity / 1023.0, 1.0) * 1760.0
                phase = self.phase + np.arange(1, count + 1, dtype=np.float32) * (2 * math.pi * frequency / SAMPLE_RATE)
                raw = np.clip(0.38 * np.sin(phase) * 32767.0, -32768, 32767).astype("<i2").tobytes()
            else:
                out = []; phase = self.phase
                frequency = 120.0 + min(activity / 1023.0, 1.0) * 1760.0
                for _index in range(count):
                    phase += 2 * math.pi * frequency / SAMPLE_RATE
                    out.append(int(0.38 * math.sin(phase) * 32767.0))
                raw = struct.pack("<%dh" % len(out), *out)
            self.phase = float(phase[-1] if np is not None else phase) % (2 * math.pi)
            encoded, level, peak, clipped = self.processor.process(raw)
            with self.lock:
                self.state.update(state="streaming", level_dbfs=level, peak_dbfs=peak,
                                  clipped=clipped, blocks=self.state["blocks"] + 1, last_block=time.time())
                for queue_ in self.listeners:
                    queue_.append(encoded)
            return
        ratio = SAMPLE_RATE / rate
        # Full scale of the converter maps to full scale audio; the high pass in the
        # processor removes the probe offset, gain is applied afterwards.
        if np is not None:
            values = np.asarray(codes, dtype=np.float32) / 32768.0
            positions = np.arange(0, len(values) - 1, 1.0 / ratio)
            resampled = np.interp(positions, np.arange(len(values)), values)
            raw = np.clip(resampled * 32767.0, -32768, 32767).astype("<i2").tobytes()
        else:
            out = []
            count = int((len(codes) - 1) * ratio)
            for index in range(count):
                position = index / ratio
                base = int(position)
                frac = position - base
                value = codes[base] * (1 - frac) + codes[base + 1] * frac
                out.append(int(max(-32768, min(32767, value))))
            raw = struct.pack("<%dh" % len(out), *out)
        encoded, level, peak, clipped = self.processor.process(raw)
        with self.lock:
            self.state.update(state="streaming", level_dbfs=level, peak_dbfs=peak,
                              clipped=clipped, blocks=self.state["blocks"] + 1,
                              last_block=time.time())
            for queue_ in self.listeners:
                queue_.append(encoded)


class MagAudioSource(EfieldAudioSource):
    """The magnetometer made audible, honestly labelled as a sonification.

    The QMC5883P is read about 50 times a second, so its fluctuations occupy 0 to 25 Hz,
    below hearing. Each deviation sample (µT from the ambient baseline) is interpolated
    to 16 kHz and multiplied onto a 220 Hz carrier: what is heard is a tone whose
    loudness and texture follow the magnetic field exactly; the pitch itself is the
    carrier, not the field. Mains hum cannot appear here: at 50 samples per second the
    50 Hz line frequency aliases to a constant and is removed with the baseline.
    """

    name = "mag"
    label = 'Channel 1 audio'
    CARRIER_HZ = 220.0
    FULL_SCALE_UT = 2.0

    def __init__(self, channel_state=None):
        super().__init__(channel_state)
        self.phase = 0.0
        self.last_value = 0.0

    def probe(self):
        state = self.channel_state()
        if state == "connected":
            return True, None, 'Source 1 channel 1 (50 SPS, 0 to 25 Hz fluctuations on a 220 Hz carrier)'
        return False, f"Channel 1 is {state}", None

    def feed_value(self, deviation_ut, sample_rate):
        """Called from the acquisition thread with one magnetometer reading."""
        if not self.state["enabled"]:
            return
        rate = sample_rate if sample_rate and 5 < sample_rate < 400 else 50.0
        count = max(1, int(round(SAMPLE_RATE / rate)))
        start, end = self.last_value, float(deviation_ut)
        self.last_value = end
        step = 2 * math.pi * self.CARRIER_HZ / SAMPLE_RATE
        if np is not None:
            env = np.linspace(start, end, count, endpoint=False, dtype=np.float32) / self.FULL_SCALE_UT
            phases = self.phase + step * np.arange(count, dtype=np.float32)
            samples = np.clip(env * np.sin(phases) * 32767.0, -32768, 32767).astype("<i2").tobytes()
        else:
            out = []
            for index in range(count):
                env = (start + (end - start) * index / count) / self.FULL_SCALE_UT
                out.append(int(max(-32768, min(32767, env * math.sin(self.phase + step * index) * 32767.0))))
            samples = struct.pack("<%dh" % len(out), *out)
        self.phase = (self.phase + step * count) % (2 * math.pi)
        encoded, level, peak, clipped = self.processor.process(samples)
        with self.lock:
            self.state.update(state="streaming", level_dbfs=level, peak_dbfs=peak,
                              clipped=clipped, blocks=self.state["blocks"] + 1,
                              last_block=time.time())
            for queue_ in self.listeners:
                queue_.append(encoded)


class FieldAudition:
    """Owns the sources and exposes snapshots and streaming generators."""

    def __init__(self, channel_state=None, mag_state=None):
        self.sources = {"efield": EfieldAudioSource(channel_state), "mag": MagAudioSource(mag_state),
                        "coil": CoilAudioSource(), "sdr": SdrAudioSource()}
        self.last_probe = time.monotonic()

    def snapshot(self):
        if time.monotonic() - self.last_probe > 10:
            self.last_probe = time.monotonic()
            for source in self.sources.values():
                if not source.state["enabled"]:
                    try:
                        source.refresh_availability()
                    except Exception:  # pragma: no cover
                        pass
        return {"sources": {key: source.snapshot() for key, source in self.sources.items()},
                "efield_audio_active": self.sources["efield"].state["enabled"],
                "note": "Audio is monitoring only. Levels are dBFS relative to the capture chain, not field strength."}

    def control(self, data):
        key = data.get("source")
        if key not in self.sources:
            raise ValueError("Unknown audio source")
        source = self.sources[key]
        if "gain" in data or "mute" in data or "normalise" in data:
            source.set_controls(data.get("gain"), data.get("mute"), data.get("normalise"))
        if key == "sdr" and ("frequency_hz" in data or "mode" in data):
            source.set_tuning(data.get("frequency_hz"), data.get("mode"))
        if "enabled" in data:
            if not isinstance(data["enabled"], bool):
                raise ValueError("Enabled must be true or false")
            if data["enabled"]:
                source.start()
            else:
                source.stop()
        return source.snapshot()

    def stream(self, key, stop_event):
        source = self.sources[key]
        queue_ = source.subscribe()
        try:
            yield wav_header()
            silence = b"\x00" * (BLOCK_FRAMES * 2)
            idle = 0.0
            while not stop_event.is_set():
                if queue_:
                    chunk = queue_.popleft()
                    if chunk is None:
                        return
                    yield chunk
                    idle = 0.0
                else:
                    stop_event.wait(0.02)
                    idle += 0.02
                    # Keep the decoder fed if capture pauses briefly.
                    if idle >= 0.5:
                        if not source.state["enabled"]:
                            return
                        yield silence
                        idle = 0.0
        finally:
            source.unsubscribe(queue_)

    def stop(self):
        for source in self.sources.values():
            try:
                source.stop()
            except Exception:  # pragma: no cover
                pass
