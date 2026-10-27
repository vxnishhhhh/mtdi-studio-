"""Verified sensor readers that preserve the existing worker lifecycle."""
from __future__ import annotations

from collections import deque
from bisect import bisect_left
import math
import random
import os
import re
import statistics
import socket
import threading
import time

from .content import T

# SRC1 Rev E sections 7 and 9 define these addresses and normal mode.
SRC1_ADDRESS = 0x2C
SRC1_NORMAL_50_HZ = 0xC5
# CTRL1: OSR2[7:6]=11, OSR1[5:4]=00, ODR[3:2], MODE[1:0]=01 (normal). 200 Hz puts the 50 Hz
# linefreq line well inside the ch1probe's Nyquist band for the D4 harmonics engine.
SRC1_ODR_CODES = {10: 0xC1, 50: 0xC5, 100: 0xC9, 200: 0xCD}
SRC1_RANGE_2_GAUSS = 0x0C
SRC1_LSB_PER_VAL = 150.0
# LSB per uT for each RNG code in control register 2 (datasheet table: 30 G, 12 G, 8 G, 2 G)
SRC1_LSB_PER_VAL_BY_RANGE = {0: 10.0, 1: 25.0, 2: 37.5, 3: 150.0}
# SRC2 SBAS444E table 8.3 defines the PGA and differential input codes.
ADS_ADDRESS = 0x48
# Key is the PGA gain, value is (register code, full scale volts). The +-4.096 V
# range is here because an AC-coupled probe sits at a DC bias -- measured 2.41 V
# on 2026-09-24 -- and every narrower range saturates on the bias alone, long
# before the signal is even considered. rms_mv is computed about the block mean,
# so that bias costs nothing as long as the range can contain it.
ADS_PGA = {16: (5, 0.256), 8: (4, 0.512), 4: (3, 1.024), 2: (2, 2.048), 1: (1, 4.096)}
# Retired compatibility constants remain so old archived configurations can load,
# but acquisition no longer opens or samples the former secondary SRC2 path.
# Which SRC2 input the Ch2 probe is on. 0 is the differential pair A0-A1,
# which is how the probe was built. A board that brings a single-ended channel out
# instead (signal on AINx, reference on the ADC's own GND) needs 4..7 for A0..A3;
# set STUDIO_CH2F_MUX rather than editing this, so a rewire does not need a
# code change. Table 8.3 of SBAS444E defines the codes.
CH2F_MUX = int(os.environ.get("STUDIO_CH2F_MUX", "0"))
# Full-scale range for the Ch2 probe. The original differential build put a
# few millivolts across A0-A1 and wanted gain 16; an AC-coupled single-ended
# build sits near mid-rail and needs gain 1 just to fit the bias. Neither is
# right for the other, so it is an environment setting rather than a constant.
CH2F_GAIN = float(os.environ.get("STUDIO_CH2F_GAIN", "2"))
if CH2F_GAIN in (16.0, 8.0, 4.0, 2.0, 1.0):
    CH2F_GAIN = int(CH2F_GAIN)
CH2F_MUX_NAME = {0: "differential A0 A1", 1: "differential A0 A3", 2: "differential A1 A3",
                   3: "differential A2 A3", 4: "single ended A0", 5: "single ended A1",
                   6: "single ended A2", 7: "single ended A3"}
# Triaxial probe. Three plate pads, one per SRC2 single-ended input,
# each mounted normal to one axis. A plate responds to the field component
# arriving perpendicular to its face, so three mutually perpendicular plates
# resolve a vector where one plate could only give a magnitude.
#
# Bandwidth note: the three axes share one I2C bus, so cycling them divides the
# achievable rate three ways -- about 160 SPS per axis against the ~480 SPS a
# single channel manages. That is still above the 100 SPS Nyquist needs for
# 50 Hz, but the margin is thin, and every frequency result is computed against
# the rate actually measured for that axis rather than an assumed one.
CH2F_TRIAXIAL = os.environ.get("STUDIO_CH2F_TRIAXIAL", "1") not in ("0", "false", "no")
CH2F_AXIS_MUX = {"x": int(os.environ.get("STUDIO_CH2F_MUX_X", "4")),
                   "y": int(os.environ.get("STUDIO_CH2F_MUX_Y", "5")),
                   "z": int(os.environ.get("STUDIO_CH2F_MUX_Z", "6"))}
# Per-axis scale. Hand-built plates are never identical -- measured 2026-09-25:
# 4.762, 6.120 and 10.027 mV on the same ambient field -- and an uncorrected
# spread like that tilts the reported direction toward whichever axis collects
# best. These are set from a calibration run; 1.0 means uncalibrated, which the
# UI states rather than hides.
CH2F_AXIS_SCALE = {a: float(os.environ.get("STUDIO_CH2F_SCALE_" + a.upper(), "1.0"))
                     for a in ("x", "y", "z")}
# ``auto`` is deliberately conservative: it selects a USB Arduino only when it
# can identify an Arduino-class serial port.  Otherwise the established SRC2
# reader remains the source.  Set this explicitly when a non-standard USB UART
# is used, rather than guessing at an arbitrary serial device.
CH2F_SOURCE = os.environ.get("STUDIO_CH2F_SOURCE", "auto").strip().lower()
ARDUINO_ADC_PORT = os.environ.get("STUDIO_ARDUINO_ADC_PORT", "").strip()
ARDUINO_ADC_BAUD = int(os.environ.get("STUDIO_ARDUINO_ADC_BAUD", "115200"))
# The project sensor node is an Uno attached either directly to this host or to
# the Mac bridge.  Listen by default when no local Arduino is present so a fresh
# checkout does not require a hidden environment switch.
ARDUINO_TCP_LISTEN = os.environ.get("STUDIO_ARDUINO_TCP_LISTEN", "0.0.0.0:8765").strip()
# Uno R3 DEFAULT uses AVcc as its ADC reference.  Until the prototype exposes a
# measured reference in its serial protocol, 5.0 V is the best documented
# estimate.  It is configurable so the prototype calibration can replace it
# without another code change.
ARDUINO_ADC_VREF_VOLTS = float(os.environ.get("STUDIO_ARDUINO_ADC_VREF_VOLTS", "5.0"))
ARDUINO_LINE = re.compile(r"^CH1=(\d{1,4}),CH2=(\d{1,4}),CH3=(\d{1,4})$")
ARDUINO_C1_LINE = re.compile(r"^MAGX=(-?\d{1,6}),MAGY=(-?\d{1,6}),MAGZ=(-?\d{1,6})$")
CLAMP_ENABLED = False
CLAMP_MUX = int(os.environ.get("STUDIO_CLAMP_MUX", "3"))
CLAMP_AMPS_PER_VOLT = float(os.environ.get("STUDIO_CLAMP_AMPS_PER_VOLT", "30"))
I2C_LOCK = threading.RLock()


class SocketLineReader:
    """Small serial-compatible newline reader for the Mac sensor bridge."""
    def __init__(self, connection):
        self.connection = connection
        self.buffer = bytearray()

    def readline(self):
        while b"\n" not in self.buffer:
            chunk = self.connection.recv(4096)
            if not chunk:
                raise ConnectionError('Mac source bridge disconnected')
            self.buffer.extend(chunk)
        line, _, remainder = self.buffer.partition(b"\n")
        self.buffer = bytearray(remainder)
        return bytes(line + b"\n")

    def close(self):
        self.connection.close()


def axis_block(adc, mux, count):
    """Read one axis and classify it. Returns (rms_mv, status, detail).

    status is "ok", "stuck" or "railed". An axis that cannot be trusted returns
    a None rms rather than a number, because the magnitude is a square root of
    squares -- a fabricated zero from an unwired plate is indistinguishable in
    the result from a genuine null, and would quietly swing the direction.
    """
    previous = adc.mux
    try:
        adc.mux = mux
        block = adc.read_block(count)
    finally:
        adc.mux = previous
    span = block["maximum"] - block["minimum"]
    if block["clipped"] or block["minimum"] >= 32000 or block["maximum"] <= -32000:
        return None, "railed", block
    if span <= 2:
        # A live plate always carries a little noise. Codes that do not move at
        # all mean nothing is connected, not that the field is perfectly still.
        return None, "stuck", block
    return block["rms_mv"], "ok", block


def signed16(value):
    return value - 65536 if value & 0x8000 else value


class SRC2Reader:
    """Request one conversion and confirm its completion before reading data."""

    def __init__(self, bus, stop, address=ADS_ADDRESS, mux=0, gain=2):
        if not 0 <= mux <= 7 or gain not in ADS_PGA:
            raise ValueError('Invalid Source 2 input or gain')
        self.bus, self.stop, self.address = bus, stop, address
        self.mux, self.gain = mux, gain
        self.conversions = 0
        self.timeout_count = 0

    def _word(self, register):
        with I2C_LOCK:
            values = self.bus.read_i2c_block_data(self.address, register, 2)
        if len(values) != 2:
            raise IOError('Incomplete Source 2 register read')
        return (values[0] << 8) | values[1]

    def read(self):
        pga = ADS_PGA[self.gain][0]
        config = 0x8000 | (self.mux << 12) | (pga << 9) | 0x0100 | (7 << 5) | 3
        with I2C_LOCK:
            self.bus.write_i2c_block_data(self.address, 1, [config >> 8, config & 0xFF])
        deadline = time.monotonic() + 0.025
        # At 860 SPS the oscillator tolerance requires checking OS, not trusting a sleep.
        self.stop.wait(0.00105)
        while not self.stop.is_set():
            observed = self._word(1)
            if observed & 0x7FFF != config & 0x7FFF:
                raise IOError('Source 2 configuration changed during conversion')
            if observed & 0x8000:
                value = signed16(self._word(0))
                self.conversions += 1
                return value
            if time.monotonic() >= deadline:
                self.timeout_count += 1
                raise TimeoutError('Source 2 conversion did not complete')
            self.stop.wait(0.00015)
        raise InterruptedError("Acquisition stopped")

    def read_block(self, count=100):
        codes, timestamps = [], []
        for _ in range(count):
            codes.append(self.read())
            timestamps.append(time.monotonic())
        mean = statistics.fmean(codes)
        volts_per_code = ADS_PGA[self.gain][1] / 32768.0
        rms_mv = math.sqrt(statistics.fmean((value - mean) ** 2 for value in codes)) * volts_per_code * 1000
        peak_mv = max(abs(value - mean) for value in codes) * volts_per_code * 1000
        duration = timestamps[-1] - timestamps[0]
        return {"codes": codes, "monotonic_times": timestamps, "rms_mv": rms_mv,
                "peak_mv": peak_mv, "mean_mv": mean * volts_per_code * 1000,
                "minimum": min(codes), "maximum": max(codes),
                "clipped": min(codes) <= -32000 or max(codes) >= 32000,
                "utilisation": max(abs(min(codes)), abs(max(codes))) / 32768.0,
                "sample_rate": (len(codes) - 1) / duration if duration > 0 else 0.0,
                "gain": self.gain, "volts_per_code": volts_per_code}


def validate_text_sweep(freqs, levels, start_hz, stop_hz, points, error_type=ValueError):
    if int(points) != points or not 2 <= points <= 290:
        raise ValueError("Src3 point count must be between 2 and 290")
    if not all(math.isfinite(float(v)) for v in [start_hz, stop_hz]) or not 0 <= start_hz < stop_hz:
        raise ValueError("Src3 span is invalid")
    if len(freqs) != points or len(levels) != points:
        raise error_type("Incomplete Src3 sweep")
    if not all(math.isfinite(float(v)) for v in freqs + levels):
        raise error_type("Nonfinite Src3 measurement")
    if any(right <= left for left, right in zip(freqs, freqs[1:])):
        raise error_type("Src3 frequencies are not increasing")
    spacing = (stop_hz - start_hz) / (points - 1)
    tolerance = max(2.0, spacing * 0.001)
    if abs(freqs[0] - start_hz) > tolerance or abs(freqs[-1] - stop_hz) > tolerance:
        raise error_type("Src3 returned a different span")
    for index, frequency in enumerate(freqs):
        if abs(frequency - (start_hz + index * spacing)) > tolerance:
            raise error_type("Src3 frequency grid is incomplete or irregular")
    warnings = []
    if max(levels) > 10 or min(levels) < -180:
        warnings.append("CH3 levels outside the expected instrument range; verify analyser settings")
    return warnings


def install(ns, engine):
    """Replace acquisition entry points before the existing lifecycle starts workers."""
    stop = ns["STOP_EVENT"]
    logger = ns["LOG"]
    last_error_log = {}

    def publish_error(channel, data_key, lock_key, error, retry):
        message = str(error).replace("—", ";").replace("-", " ")
        with ns[lock_key]:
            ns[data_key]["error"] = message
            ns[data_key]["status"] = "Offline; retry pending"
        engine.status(channel, "offline", message)
        previous_message, logged_at = last_error_log.get(channel, (None, 0.0))
        mono = time.monotonic()
        if previous_message != message or mono - logged_at >= 60:
            logger.warning("%s acquisition unavailable: %s", channel, message)
            last_error_log[channel] = (message, mono)

    def src1_reader():
        if (ARDUINO_TCP_LISTEN or CH2F_SOURCE == "arduino" or
                (CH2F_SOURCE == "auto" and arduino_adc_ports())):
            engine.status("ch1", "initialising", 'Waiting for combined Source 6 source stream')
            return
        try:
            from smbus2 import SMBus
        except ImportError as exc:
            publish_error("ch1", "ch1_data", "c1_lock", exc, 0)
            return
        profile, warning = ns["_load_ch1probe_calibration"]()
        warning = str(warning or "Factory nominal sensitivity; vector accuracy requires calibration").replace("—", ";").replace("-", " ")
        attempts = 0
        while not stop.is_set():
            bus = None
            identity_ok = False
            try:
                engine.status("ch1", "initialising", 'Opening Source 1')
                bus = SMBus(ns.get("I2C_BUS", 1))
                with I2C_LOCK:
                    identity = bus.read_byte_data(SRC1_ADDRESS, 0x00)
                if identity != 0x80:
                    raise IOError(f"Unexpected device identity 0x{identity:02X} at Source 1 address")
                identity_ok = True
                with I2C_LOCK:
                    bus.write_byte_data(SRC1_ADDRESS, 0x0B, 0x80)
                # The soft reset takes longer than the 20 ms this used to wait: the range and
                # set/reset writes that followed were silently dropped, the chip stayed on its
                # 30 G power-on range and every uT figure was 15x too small. Write, read back,
                # retry, and scale by the range the chip actually reports.
                stop.wait(0.1)
                lsb_per_val = SRC1_LSB_PER_VAL
                for attempt in range(6):
                    with I2C_LOCK:
                        bus.write_byte_data(SRC1_ADDRESS, 0x29, 0x06)
                        bus.write_byte_data(SRC1_ADDRESS, 0x0B, SRC1_RANGE_2_GAUSS)
                    stop.wait(0.01)
                    with I2C_LOCK:
                        rng_back = bus.read_byte_data(SRC1_ADDRESS, 0x0B)
                        srp_back = bus.read_byte_data(SRC1_ADDRESS, 0x29)
                    if rng_back == SRC1_RANGE_2_GAUSS and srp_back == 0x06:
                        break
                    stop.wait(0.05)
                lsb_per_val = SRC1_LSB_PER_VAL_BY_RANGE.get((rng_back >> 2) & 3, SRC1_LSB_PER_VAL)
                if rng_back != SRC1_RANGE_2_GAUSS:
                    logger.warning("SRC1 range register reads 0x%02X after %d attempts; scaling by %.1f LSB/uT", rng_back, attempt + 1, lsb_per_val)
                with I2C_LOCK:
                    odr_hz = int(ns.get("_d4_config", lambda: {})().get("c1_odr_hz", 200) or 200)
                    ctrl1 = SRC1_ODR_CODES.get(odr_hz, SRC1_NORMAL_50_HZ)
                    bus.write_byte_data(SRC1_ADDRESS, 0x0A, ctrl1)
                    if bus.read_byte_data(SRC1_ADDRESS, 0x0A) != ctrl1:
                        raise IOError('Source 1 mode readback did not match')
                configured_rate = odr_hz if ctrl1 != SRC1_NORMAL_50_HZ else 50
                with ns["c1_lock"]:
                    ns["ch1_data"].update(chip_id=identity, chip_warning=None, calibration_warning=warning,
                                                calibrated=bool(profile), calibration_metadata=profile.get("metadata", {}) if profile else {},
                                                error=None, reconnect_count=ns["ch1_data"]["reconnect_count"] + 1)
                engine.baseline("ch1", relock=True)
                last_sample = time.monotonic()
                missed_estimate = 0
                attempts = 0
                while not stop.is_set():
                    with ns["c1_cmd_lock"]:
                        relock = bool(ns["c1_cmd"].get("recalibrate"))
                        ns["c1_cmd"]["recalibrate"] = False
                    if relock:
                        engine.baseline("ch1", relock=True)
                    with I2C_LOCK:
                        status = bus.read_byte_data(SRC1_ADDRESS, 0x09)
                        data = bus.read_i2c_block_data(SRC1_ADDRESS, 0x01, 6) if status & 1 else None
                    if data is None:
                        if time.monotonic() - last_sample > 2:
                            raise TimeoutError('Source 1 data ready signal stopped')
                        # Status reads clear DRDY; limit bus traffic while checking within one conversion period.
                        stop.wait(0.005)
                        continue
                    if len(data) != 6:
                        raise IOError('Incomplete Source 1 vector')
                    now, mono = time.time(), time.monotonic()
                    codes = [signed16(data[index] | data[index + 1] << 8) for index in (0, 2, 4)]
                    raw = [value / lsb_per_val for value in codes]
                    with ns["c1_cmd_lock"]:
                        if ns["c1_cmd"].get("reload_calibration"):
                            ns["c1_cmd"]["reload_calibration"] = False
                            profile, reload_warning = ns["_load_ch1probe_calibration"]()
                            warning = str(reload_warning or "i3_config.json hard/soft iron profile active").replace("—", ";").replace("-", " ")
                    vector = ns["_apply_ch1probe_calibration"](*raw, profile)
                    with ns["raw_ring_lock"]:
                        ns["RAW_RING"]["ch1_raw"].append((now, *raw))
                        ns["RAW_RING"]["ch1"].append((now, *vector))
                    clipped = bool(status & 2) or any(abs(code) >= 30000 for code in codes)
                    missed_estimate += max(0, round((mono - last_sample) * configured_rate) - 1)
                    last_sample = mono
                    magnitude = math.sqrt(sum(v * v for v in vector))
                    filt = ns.get("_d4_filter")
                    if filt is not None:
                        magnitude = filt(magnitude)
                    item = engine.ingest("ch1", magnitude, now, "unit", raw=raw, vector=vector,
                                         clipped=clipped, metadata={"monotonic": mono, "codes": codes,
                                         "configured_rate": configured_rate, "missed_estimate": missed_estimate,
                                         "missed_estimate_note": "Timing estimate; sensor exposes no sample counter",
                                         "vector_profile": bool(profile), "resolution_val": 1 / lsb_per_val, "range_register": rng_back})
                    axial = item["axial"]
                    baseline = item["baseline"]
                    bx, by, bz = item["baseline_vector"]
                    x, y, z = axial["x"], axial["y"], axial["z"]
                    m = item["deviation"]
                    c1_feed = ns.get("_v238_c1_feed")
                    if c1_feed is not None:
                        c1_feed(m, item["sample_rate"])
                    with ns["c1_lock"]:
                        target = ns["ch1_data"]
                        target.update(x=x, y=y, z=z, magnitude=m, raw_x=raw[0], raw_y=raw[1], raw_z=raw[2],
                                      baseline_x=bx, baseline_y=by, baseline_z=bz, baseline_magnitude=math.sqrt(bx*bx + by*by + bz*bz),
                                      baseline_delta=m, baseline_calibrated=not baseline["settling"],
                                      calibrated=bool(profile) or item["calibration"]["calibrated"],
                                      last_rx=now, error=None, warning=warning, clipped=clipped,
                                      sample_rate=item["sample_rate"], uncertainty=item["uncertainty"],
                                      raw_magnitude=magnitude, missed_estimate=missed_estimate,
                                      fed_source=None, fed_unit=None)
                        target["history"].append(m)
                        target["xyz_history"].append((x, y, z))
                        target["min_c1"] = min(target["min_c1"], m)
                        target["max_c1"] = max(target["max_c1"], m)
                        target["overflow_count"] += int(clipped)
                    trusted = not clipped
                    ns["CSV_LOG"].log_c1(now, *vector, magnitude, raw, bool(profile) or item["calibration"]["calibrated"], trusted)
                    ns["ARCHIVE"].put("c1", {"t": now, "x": raw[0], "y": raw[1], "z": raw[2], "c1": math.sqrt(sum(v*v for v in raw)),
                                              "trusted": trusted, "warning": "Clipped" if clipped else warning,
                                              "raw_codes": codes, "monotonic": mono, "deviation": m,
                                              "calibration": item["calibration"]})
            except Exception as exc:
                if not stop.is_set():
                    publish_error("ch1", "ch1_data", "c1_lock", exc, attempts)
                    attempts += 1
            finally:
                if bus is not None:
                    if identity_ok:
                        try:
                            with I2C_LOCK:
                                bus.write_byte_data(SRC1_ADDRESS, 0x0A, 0x00)
                        except OSError:
                            logger.debug('Channel 1 suspend failed', exc_info=True)
                    try:
                        bus.close()
                    except OSError:
                        logger.debug('bus handle close failed', exc_info=True)
            stop.wait(min(15.0, 2.0 + attempts))

    if not CLAMP_ENABLED:
        engine.status("current", "unavailable", 'Channel 4 disabled by configuration')
    else:
        engine.status("current", "offline", 'Waiting for Source 2')

    def arduino_adc_ports():
        """Return only credible Arduino USB serial candidates.

        The sweep3 analyser is also serial, so this must never probe every
        port and accidentally consume its text shell.  Uno boards normally use
        ttyACM; the explicit override covers clones that present differently.
        """
        if ARDUINO_ADC_PORT:
            return [ARDUINO_ADC_PORT]
        try:
            from serial.tools import list_ports
        except ImportError:
            return []
        ranked = []
        for port in list_ports.comports():
            description = " ".join(str(value or "") for value in (
                port.description, port.manufacturer, port.product, port.hwid
            )).lower()
            device = str(port.device)
            arduino = ((port.vid, port.pid) in {(0x2341, 0x0043), (0x2A03, 0x0043),
                                                 (0x1A86, 0x7523)} or
                       "arduino" in description or "ch340" in description)
            if arduino and ("ttyacm" in device.lower() or "ttyusb" in device.lower()):
                ranked.append(device)
        return ranked

    def arduino_ch2f_reader():
        """Read the Uno's three real 10-bit ADC channels over USB serial.

        Raw counts remain the primary measurement.  For the requested provisional
        field display they are also mapped through the configured Uno reference
        and existing probe coefficient.  The UI labels that result as a reference
        estimate and never treats it as prototype calibration.
        """
        try:
            import serial
        except ImportError as exc:
            publish_error("ch2", "ch2f_data", "ch2f_lock", exc, 0)
            return
        attempts = 0
        c1_profile, c1_warning = ns["_load_ch1probe_calibration"]()
        c1_warning = str(c1_warning or "Factory nominal sensitivity; vector accuracy requires calibration").replace("—", ";").replace("-", " ")
        while not stop.is_set():
            port_handle = None
            listener = None
            try:
                candidates = arduino_adc_ports()
                if candidates:
                    port = candidates[0]
                    engine.status("ch2", "initialising", 'Opening Source 6 USB ADC')
                    port_handle = serial.Serial(port, ARDUINO_ADC_BAUD, timeout=0.4,
                                                write_timeout=1)
                    port_handle.reset_input_buffer()
                elif ARDUINO_TCP_LISTEN:
                    host, port_text = ARDUINO_TCP_LISTEN.rsplit(":", 1)
                    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    listener.bind((host, int(port_text)))
                    listener.listen(1)
                    listener.settimeout(1.0)
                    engine.status("ch2", "initialising", 'Waiting for Mac source bridge')
                    while not stop.is_set():
                        try:
                            connection, _peer = listener.accept()
                            break
                        except socket.timeout:
                            continue
                    if stop.is_set():
                        break
                    # Opening an Uno toggles DTR and resets it; its sensor setup
                    # deliberately waits before the first line.  Allow that boot
                    # interval so reconnects do not create a reset/timeout loop.
                    connection.settimeout(3.0)
                    port_handle = SocketLineReader(connection)
                else:
                    raise IOError('no local Source 6 or Mac source bridge configured')
                samples = deque(maxlen=40)
                static_baseline = None
                engine.baseline("ch2", relock=True)
                engine.baseline("ch1", relock=True)
                attempts = 0
                while not stop.is_set():
                    raw = port_handle.readline().decode("ascii", errors="ignore").strip()
                    c1_match = ARDUINO_C1_LINE.fullmatch(raw)
                    if c1_match:
                        now, mono = time.time(), time.monotonic()
                        codes = tuple(int(part) for part in c1_match.groups())
                        raw_vector = tuple(value / SRC1_LSB_PER_VAL for value in codes)
                        vector = ns["_apply_ch1probe_calibration"](*raw_vector, c1_profile)
                        magnitude = math.sqrt(sum(value * value for value in vector))
                        item = engine.ingest("ch1", magnitude, now, "unit", raw=raw_vector,
                                             vector=vector, clipped=any(abs(value) >= 30000 for value in codes),
                                             metadata={"monotonic": mono, "codes": codes,
                                                       "configured_rate": 50, "vector_profile": bool(c1_profile),
                                                       "resolution_val": 1 / SRC1_LSB_PER_VAL,
                                                       "transport": "ARDUINO_UNO_USB"})
                        axial, baseline = item["axial"], item["baseline"]
                        bx, by, bz = item["baseline_vector"]
                        with ns["raw_ring_lock"]:
                            ns["RAW_RING"]["ch1_raw"].append((now, *raw_vector))
                            ns["RAW_RING"]["ch1"].append((now, *vector))
                        with ns["c1_lock"]:
                            target = ns["ch1_data"]
                            target.update(x=axial["x"], y=axial["y"], z=axial["z"],
                                          magnitude=item["deviation"], raw_x=raw_vector[0],
                                          raw_y=raw_vector[1], raw_z=raw_vector[2], baseline_x=bx,
                                          baseline_y=by, baseline_z=bz,
                                          baseline_magnitude=math.sqrt(bx*bx + by*by + bz*bz),
                                          baseline_delta=item["deviation"],
                                          baseline_calibrated=not baseline["settling"],
                                          calibrated=bool(c1_profile) or item["calibration"]["calibrated"],
                                          last_rx=now, error=None, warning=c1_warning,
                                          clipped=item["clipped"], sample_rate=item["sample_rate"],
                                          uncertainty=item["uncertainty"], raw_magnitude=magnitude,
                                          fed_source=None, fed_unit=None)
                            target["history"].append(item["deviation"])
                            target["xyz_history"].append((axial["x"], axial["y"], axial["z"]))
                            target["min_c1"] = min(target["min_c1"], item["deviation"])
                            target["max_c1"] = max(target["max_c1"], item["deviation"])
                        continue
                    match = ARDUINO_LINE.fullmatch(raw)
                    if not match:
                        continue
                    values = tuple(int(part) for part in match.groups())
                    if any(value > 1023 for value in values):
                        continue
                    now, mono = time.time(), time.monotonic()
                    # The prototype PCB is physically ordered top-to-bottom as
                    # X, Y, Z.  The Uno firmware labels its three wires CH1,
                    # CH2, CH3 from the bottom upward, so CH3 is logical X and
                    # CH1 is logical Z.  Store the logical order once here so
                    # RMS, plots, raw ring, and audio all use the same axes.
                    samples.append((mono, (values[2], values[1], values[0])))
                    # Ten independent reports are enough to say the cable and
                    # all three channels are alive, but no fewer: one partial
                    # USB line must not become a dashboard measurement.
                    if len(samples) < 10:
                        continue
                    columns = tuple([row[1][axis] for row in samples] for axis in range(3))
                    means = tuple(statistics.fmean(column) for column in columns)
                    rms = tuple(math.sqrt(statistics.fmean((value - mean) ** 2
                                                           for value in column))
                                for column, mean in zip(columns, means))
                    magnitude = math.sqrt(sum(value * value for value in rms))
                    millivolts_per_count = ARDUINO_ADC_VREF_VOLTS * 1000.0 / 1023.0
                    axis_mv = tuple(value * millivolts_per_count for value in rms)
                    magnitude_mv = magnitude * millivolts_per_count
                    to_vu = ns.get("_c2_scale") or (lambda mv: None)
                    axis_vu = tuple(to_vu(value) for value in axis_mv)
                    magnitude_vu = to_vu(magnitude_mv)
                    times = [row[0] for row in samples]
                    duration = times[-1] - times[0]
                    sample_rate = (len(times) - 1) / duration if duration > 0 else 0.0
                    codes = [value for column in columns for value in column]
                    axis_clipped = {axis: any(value in (0, 1023) for value in column)
                                    for axis, column in zip(("x", "y", "z"), columns)}
                    clipped_axes = [axis.upper() for axis, is_clipped in axis_clipped.items() if is_clipped]
                    clipped = bool(clipped_axes)
                    with ns["raw_ring_lock"]:
                        ns["RAW_RING"]["ch2f"].extend((now - mono + timestamp, value)
                                                          for timestamp, value in zip(times, columns[0]))
                    audio_feed = ns.get("_v238_audio_feed")
                    if audio_feed is not None and bool(ns.get("_v238_audio_active", lambda: False)()):
                        # A 10 Hz Uno cannot reproduce linefreq audio.  This is an
                        # honest low-rate sonification of its first analogue axis,
                        # centred on mid-scale; the UI states the limitation.
                        # Map the real three-axis RMS magnitude directly to the
                        # audible carrier pitch. Analysis still receives only
                        # the measured samples below.
                        audio_feed([magnitude, magnitude], sample_rate, 1.0)
                    item = engine.ingest(
                        "ch2", magnitude, now, "ADC counts RMS relative", clipped=clipped,
                        metadata={"monotonic": mono, "adc_sample_rate": sample_rate,
                                  "sample_count": len(samples), "peak_mv": None, "gain": None,
                                  "data_source": "ARDUINO_UNO_USB", "raw_unit": "10-bit ADC counts",
                                  "axis_rms_counts": {"x": rms[0], "y": rms[1], "z": rms[2]},
                                  "axis_vu": {"x": axis_vu[0], "y": axis_vu[1], "z": axis_vu[2]},
                                  "magnitude_vu": magnitude_vu,
                                  "provisional": True,
                                  "note": "Uno USB ADC; nominal-reference V/m estimate pending prototype calibration"},
                    )
                    base = item["baseline"]
                    baseline = base["value"]
                    if static_baseline is None or base["settling"]:
                        static_baseline = means
                    static_delta = tuple(value - reference for value, reference in zip(means, static_baseline))
                    static_activity = math.sqrt(sum(value * value for value in static_delta))
                    ratio = magnitude / max(abs(baseline), 1e-9)
                    relative = min(100.0, max(0.0, (ratio - 1.0) / 9.0 * 100.0))
                    with ns["ch2f_lock"]:
                        target = ns["ch2f_data"]
                        target.update(rms_mv=magnitude, raw_rms_mv=magnitude, rms_counts=magnitude,
                                      mean_mv=statistics.fmean(means) * millivolts_per_count, peak_mv=None,
                                      field_vu=magnitude_vu, peak_vu=None, baseline_vu=0.0,
                                      baseline_mv=baseline, rel_index=relative, ratio=ratio,
                                      level="OVER" if clipped else "HIGH" if item["snr"] >= 6 else "LOW",
                                      gain=None, min_code=min(codes), max_code=max(codes),
                                      utilisation=None, clipped=clipped,
                                      status="Baseline settling" if base["settling"] else "Live raw-count acquisition",
                                      last_rx=now, error=None, calibrated=not base["settling"],
                                      probe_calibrated=False, provisional_adc=True,
                                      data_source="ARDUINO_UNO_USB", fed_source=None,
                                      warning=(("Uno %s reached 0 or 1023; reference-estimated V/m = N/C and raw activity are lower bounds"
                                                % "/".join(clipped_axes))
                                               if clipped else
                                               "Uno USB ADC: the V/m figure is a nominal-reference estimate pending prototype calibration"),
                                      probe_health="railed" if clipped else "ok",
                                      unit="ADC counts RMS relative", uncertainty=item["uncertainty"],
                                      sample_rate=sample_rate,
                                      probe_scale_source=("Uno nominal %.3f V ADC reference × existing probe coefficient; "
                                                          "prototype calibration required" % ARDUINO_ADC_VREF_VOLTS))
                        # The Uno's three physical analogue inputs are the E
                        # vector axes for this fallback.  They are independently
                        # measured AC-RMS count values, not volts and not a
                        # calibrated spatial field direction.
                        target.update(triaxial=True, ex_mv=rms[0], ey_mv=rms[1], ez_mv=rms[2],
                                      ex_vu=axis_vu[0], ey_vu=axis_vu[1], ez_vu=axis_vu[2],
                                      e_magnitude_mv=magnitude, e_magnitude_vu=magnitude_vu,
                                      uno_vref_v=ARDUINO_ADC_VREF_VOLTS,
                                      axis_status={axis: ("railed" if axis_clipped[axis] else "raw counts")
                                                   for axis in ("x", "y", "z")},
                                      axis_clipped=axis_clipped,
                                      dc_axis_counts={"x": means[0], "y": means[1], "z": means[2]},
                                      dc_baseline_counts={"x": static_baseline[0], "y": static_baseline[1], "z": static_baseline[2]},
                                      dc_delta_counts={"x": static_delta[0], "y": static_delta[1], "z": static_delta[2]},
                                      static_activity_counts=static_activity,
                                      axes_live=3)
                        target["history"].append(magnitude)
                        target["rel_history"].append(relative)
                        target["exyz_history"].append((rms[0], rms[1], rms[2]))
                        target["sgm_history"].append(magnitude)
                        target["min_rms"] = min(target["min_rms"], magnitude)
                        target["max_rms"] = max(target["max_rms"], magnitude)
                # There is deliberately no CSV/Archive V/m record for this
                # temporary source.  Those schemas have mV/V/m columns and
                # writing counts into either would corrupt future analysis.
            except Exception as exc:
                if not stop.is_set():
                    publish_error("ch2", "ch2f_data", "ch2f_lock", exc, attempts)
                    attempts += 1
            finally:
                if port_handle is not None:
                    try:
                        port_handle.close()
                    except OSError:
                        logger.debug('Source 6 USB serial close failed', exc_info=True)
                if listener is not None:
                    listener.close()
            stop.wait(min(15.0, 2.0 + attempts))

    def src2_ch2f_reader():
        try:
            from smbus2 import SMBus
        except ImportError as exc:
            publish_error("ch2", "ch2f_data", "ch2f_lock", exc, 0)
            if CLAMP_ENABLED:
                engine.status("current", "offline", "smbus2 unavailable")
            return
        attempts = 0
        while not stop.is_set():
            bus = None
            try:
                engine.status("ch2", "initialising",
                              'Opening Source 2 %s at +-%.3f V'
                              % (CH2F_MUX_NAME.get(CH2F_MUX, "input %d" % CH2F_MUX),
                                 ADS_PGA[CH2F_GAIN][1]))
                bus = SMBus(ns.get("I2C_BUS", 1))
                adc = SRC2Reader(bus, stop, mux=CH2F_MUX, gain=CH2F_GAIN)
                clamp = SRC2Reader(bus, stop, mux=CLAMP_MUX, gain=2) if CLAMP_ENABLED else None
                if clamp is not None:
                    engine.baseline("current", relock=True)
                # +-4.096 V (gain 1) is on the ladder because an AC-coupled probe
                # rests at a DC bias -- 2.29 V measured on 2026-09-24 -- and every
                # coarser-than-2 range used to be unreachable, so auto-range would
                # walk down to +-2.048 V, clip on the bias alone, and stay clipped
                # forever. It also used to overwrite CH2F_GAIN on the first block,
                # which made that setting look like it did nothing.
                gains = [16, 8, 4, 2, 1]
                gain_index = gains.index(CH2F_GAIN) if CH2F_GAIN in gains else len(gains) - 1
                low_blocks = 0
                engine.baseline("ch2", relock=True)
                attempts = 0
                stuck_blocks = railed_blocks = 0
                while not stop.is_set():
                    with ns["ch2f_cmd_lock"]:
                        relock = bool(ns["ch2f_cmd"].get("recalibrate"))
                        ns["ch2f_cmd"]["recalibrate"] = False
                    if relock:
                        engine.baseline("ch2", relock=True)
                    adc.gain = gains[gain_index]
                    count = ns.get("SAMPLES_PER_BLOCK", 100)
                    if ns["BURST_REQUEST"]["ch2f"] > 0:
                        count = min(8600, int(ns["BURST_REQUEST"]["ch2f"])); ns["BURST_REQUEST"]["ch2f"] = 0
                    block = adc.read_block(count)
                    now, mono = time.time(), block["monotonic_times"][-1]
                    wall = now - mono
                    with ns["raw_ring_lock"]:
                        ns["RAW_RING"]["ch2f"].extend((wall + tm, code) for tm, code in zip(block["monotonic_times"], block["codes"]))
                    audio_feed = ns.get("_v238_audio_feed")
                    audio_active = bool(ns.get("_v238_audio_active", lambda: False)())
                    if audio_feed is not None and audio_active:
                        audio_feed(block["codes"], block["sample_rate"], block["volts_per_code"])
                    clipped = block["clipped"]
                    # Probe health from the raw codes. A live probe always carries a little noise;
                    # a block whose codes barely move for several seconds is a floating or shorted
                    # input (probe unplugged), and a block pinned at a rail is a saturated input.
                    codes = block["codes"]
                    span = (block["maximum"] - block["minimum"]) if codes else 0
                    stuck_blocks = stuck_blocks + 1 if codes and span <= 2 else 0
                    railed_blocks = railed_blocks + 1 if codes and (block["minimum"] >= 32000 or block["maximum"] <= -32000) else 0
                    if railed_blocks >= 3:
                        probe_health = "railed: input pinned at the ADC limit; check probe wiring and gain"
                    elif stuck_blocks >= 8:
                        probe_health = "stuck: codes not moving; probe disconnected or shorted"
                    else:
                        probe_health = "ok"
                    probe_ok = probe_health == "ok"
                    item = engine.ingest("ch2", block["rms_mv"], now, "mV RMS relative", clipped=clipped or not probe_ok,
                                         metadata={"monotonic": mono, "adc_sample_rate": block["sample_rate"],
                                                   "configured_adc_rate": 860, "sample_count": len(block["codes"]),
                                                   "mean_mv": block["mean_mv"], "peak_mv": block["peak_mv"],
                                                   "gain": adc.gain, "conversion_timeouts": adc.timeout_count,
                                                   "probe_health": probe_health,
                                                   "bandwidth_note": "Host timed conversions; sample rate measured; input anti alias filter not verified"})
                    base = item["baseline"]
                    profile = item["calibration"]["profile"]
                    scale = profile.get("scale", 1.0)
                    baseline_mv = (base["value"] - profile.get("offset", 0.0)) / scale
                    ratio = block["rms_mv"] / max(abs(baseline_mv), 0.008)
                    relative = min(100.0, max(0.0, (ratio - 1) / 9 * 100))
                    calibrated = bool(profile)
                    note = "Probe calibration required for field units" if not calibrated else "Reference calibrated at stated conditions"
                    if clipped:
                        note = "ADC clipped; value is a lower bound"
                    if not probe_ok:
                        note = "Probe " + probe_health
                    # ── triaxial ─────────────────────────────────────────
                    tri = {"triaxial": False}
                    if CH2F_TRIAXIAL:
                        # Resolved per block rather than imported at module level:
                        # acquisition is not one of _shared.ORDER's modules, so its
                        # namespace is handed in rather than injected. A missing key
                        # here would raise inside the reader thread and take the whole
                        # Ch2 channel down, so it degrades to raw mV instead.
                        to_vu = ns.get("_c2_scale") or (lambda mv: None)
                        axis_mv, axis_status = {}, {}
                        for name, mux in CH2F_AXIS_MUX.items():
                            if mux == CH2F_MUX:
                                # Reuse the block already read rather than paying
                                # for a fourth conversion set per cycle.
                                mv = None if not probe_ok else block["rms_mv"]
                                axis_mv[name] = mv
                                axis_status[name] = "ok" if probe_ok else probe_health.split(":")[0]
                            else:
                                mv, status, _ = axis_block(adc, mux, min(count, 100))
                                axis_mv[name] = mv
                                axis_status[name] = status
                        scaled = {a: (axis_mv[a] * CH2F_AXIS_SCALE[a]) if axis_mv[a] is not None else None
                                  for a in axis_mv}
                        live = [v for v in scaled.values() if v is not None]
                        # Magnitude over the axes that actually reported. With fewer
                        # than three it is a projection onto those axes, not the full
                        # vector, so axes_live travels with it and the UI says so.
                        magnitude = math.sqrt(sum(v * v for v in live)) if live else None
                        tri = {"triaxial": True,
                               "ex_mv": scaled["x"], "ey_mv": scaled["y"], "ez_mv": scaled["z"],
                               "ex_vu": None if scaled["x"] is None else to_vu(scaled["x"]),
                               "ey_vu": None if scaled["y"] is None else to_vu(scaled["y"]),
                               "ez_vu": None if scaled["z"] is None else to_vu(scaled["z"]),
                               "e_magnitude_mv": magnitude,
                               "e_magnitude_vu": None if magnitude is None else to_vu(magnitude),
                               "axis_status": axis_status, "axes_live": len(live)}

                    with ns["ch2f_lock"]:
                        target = ns["ch2f_data"]
                        target.update(rms_mv=block["rms_mv"], raw_rms_mv=block["rms_mv"], mean_mv=block["mean_mv"],
                                      peak_mv=block["peak_mv"], field_vu=max(0.0, item["deviation"]),
                                      peak_vu=(block["peak_mv"] - baseline_mv) * scale, baseline_vu=0.0,
                                      baseline_mv=baseline_mv, rel_index=relative, ratio=ratio,
                                      level="OVER" if clipped else "HIGH" if item["snr"] >= 6 else "LOW",
                                      gain=adc.gain, min_code=block["minimum"], max_code=block["maximum"],
                                      utilisation=block["utilisation"] * 100, clipped=clipped,
                                      status="Baseline settling" if base["settling"] else "Live acquisition",
                                      last_rx=now, error=None, calibrated=not base["settling"],
                                      probe_calibrated=calibrated, warning=note if (clipped or not probe_ok) else None,
                                      probe_health=probe_health,
                                      unit=item["unit"], uncertainty=item["uncertainty"],
                                      sample_rate=block["sample_rate"], probe_scale_source=note,
                                      fed_source=None)
                        # The live graph and numbers show the direct RMS reading; deviation
                        # from Baseline Lock stays available to the analysis engine.
                        target.update(tri)
                        target["history"].append(block["rms_mv"])
                        target["rel_history"].append(relative)
                        if tri["triaxial"]:
                            # Same shape the ch1probe publishes, so every chart
                            # written for its xyz_history works on this unchanged.
                            # None becomes 0.0 only here, at the plotting boundary,
                            # because a chart cannot draw a gap in a 3D vector --
                            # axis_status and axes_live carry the truth.
                            target["exyz_history"].append((tri["ex_mv"] or 0.0,
                                                           tri["ey_mv"] or 0.0,
                                                           tri["ez_mv"] or 0.0))
                            if tri["e_magnitude_mv"] is not None:
                                target["sgm_history"].append(tri["e_magnitude_mv"])
                        target["min_rms"] = min(target["min_rms"], block["rms_mv"])
                        target["max_rms"] = max(target["max_rms"], block["rms_mv"])
                    trusted = not clipped and probe_ok
                    # Empty physical field columns preserve scientific meaning before calibration.
                    ns["CSV_LOG"]._put({"unix_time": now, "channel": "ch2f", "c2_rms_mv": block["rms_mv"],
                                       "c2_peak_mv": block["peak_mv"], "c2_baseline_mv": baseline_mv,
                                       "c2_field_vu": item["deviation"] if profile.get("unit") == "V/m" else None,
                                       "c2_peak_vu": (block["peak_mv"] - baseline_mv) * scale if profile.get("unit") == "V/m" else None,
                                       "c2_baseline_vu": 0.0 if profile.get("unit") == "V/m" else None,
                                       "c2_ratio": ratio, "c2_rel_index_pct": relative, "c2_gain": adc.gain,
                                       "c2_utilisation_pct": block["utilisation"] * 100, "c2_clipped": int(clipped),
                                       "c2_calibrated": int(calibrated), "c2_trusted": int(trusted), "note": note})
                    ns["ARCHIVE"].put("ch2f", {"t": now, "rms_mv": block["rms_mv"], "peak_mv": block["peak_mv"],
                                                 "baseline_mv": baseline_mv, "ratio": ratio, "rel_index": relative,
                                                 "gain": adc.gain, "clipped": clipped, "trusted": trusted, "warning": note,
                                                 "raw_codes": block["codes"], "sample_times": block["monotonic_times"],
                                                 "sample_rate": block["sample_rate"], "monotonic": mono,
                                                 "calibration": item["calibration"]})
                    if clamp is not None and audio_active:
                        engine.status("current", "paused", 'Paused while Field Audition streams the channel 2 probe')
                    elif clamp is not None:
                        # Conducted Path shares the converter; blocks alternate with the probe.
                        ccount = ns.get("SAMPLES_PER_BLOCK", 100)
                        if ns["BURST_REQUEST"].get("current", 0) > 0:
                            ccount = min(8600, int(ns["BURST_REQUEST"]["current"])); ns["BURST_REQUEST"]["current"] = 0
                        cblock = clamp.read_block(ccount)
                        amps = cblock["rms_mv"] / 1000.0 * CLAMP_AMPS_PER_VOLT
                        cnow, cmono = time.time(), cblock["monotonic_times"][-1]
                        cwall = cnow - cmono
                        with ns["raw_ring_lock"]:
                            ns["RAW_RING"]["current"].extend((cwall + tm, code) for tm, code in zip(cblock["monotonic_times"], cblock["codes"]))
                        citem = engine.ingest("current", amps, cnow, "A", raw=cblock["rms_mv"], clipped=cblock["clipped"],
                                              metadata={"monotonic": cmono, "adc_sample_rate": cblock["sample_rate"],
                                                        "rms_mv": cblock["rms_mv"], "peak_mv": cblock["peak_mv"],
                                                        "nominal_amps_per_volt": CLAMP_AMPS_PER_VOLT, "mux": CLAMP_MUX,
                                                        "sample_count": len(cblock["codes"]), "gain": clamp.gain,
                                                        "conversion_timeouts": clamp.timeout_count,
                                                        "note": "RMS of a host timed block; nominal ratio until calibrated"})
                        ns["ARCHIVE"].put("current", {"t": cnow, "rms_mv": cblock["rms_mv"], "peak_mv": cblock["peak_mv"],
                                                      "amps_nominal": amps, "deviation_a": citem["deviation"],
                                                      "clipped": cblock["clipped"], "sample_rate": cblock["sample_rate"],
                                                      "monotonic": cmono, "calibration": citem["calibration"]})
                    if clipped or block["utilisation"] > 0.8:
                        low_blocks = 0
                        gain_index = min(gain_index + 1, len(gains) - 1)
                    elif block["utilisation"] < 0.18 and gain_index > 0:
                        low_blocks += 1
                        if low_blocks >= 4:
                            gain_index -= 1
                            low_blocks = 0
                    else:
                        low_blocks = 0
            except Exception as exc:
                if not stop.is_set():
                    publish_error("ch2", "ch2f_data", "ch2f_lock", exc, attempts)
                    if CLAMP_ENABLED:
                        engine.status("current", "offline", str(exc).replace("-", " ")[:200])
                    attempts += 1
            finally:
                if bus is not None:
                    try:
                        bus.close()
                    except OSError:
                        logger.debug('bus handle close failed', exc_info=True)
            stop.wait(min(15.0, 2.0 + attempts))

    def read_until_prompt(s3, timeout):
        output = bytearray()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline and not stop.is_set():
            chunk = s3.read(max(1, min(4096, getattr(s3, "in_waiting", 0) or 1)))
            if chunk:
                output.extend(chunk)
                if output.rstrip().endswith(b"ch>"):
                    return bytes(output)
                if len(output) > 4_000_000:
                    raise ns["Src3ProtocolError"]("Src3 response exceeded its size limit")
        raise TimeoutError(f"Src3 response incomplete after {timeout:.1f} seconds; received {len(output)} bytes")

    def command(s3, cmd, timeout=6.0):
        if any(c in cmd for c in "\r\n"):
            raise ValueError("Src3 commands must contain one line")
        s3.reset_input_buffer()
        data = (cmd + "\r").encode("ascii")
        count = s3.write(data)
        if count != len(data):
            raise ns["Src3ProtocolError"]("Incomplete Src3 command write")
        reply = read_until_prompt(s3, timeout).decode("utf8", errors="replace")
        if any(marker in reply.lower() for marker in ("unknown command", "command error", "invalid command")):
            raise ns["Src3ProtocolError"]("Src3 rejected the requested command")
        return reply

    def validate(freqs, levels, start_hz, stop_hz, points):
        return validate_text_sweep(freqs, levels, start_hz, stop_hz, points, ns["Src3ProtocolError"])

    original_scan = ns["_s3_scan"]
    ch3_grid = [None]
    ch3_baselines = []
    ch3_history = deque(maxlen=400)
    ch3_summary = {"count": 0, "min": float("inf"), "max": float("-inf"), "sum": 0.0, "strongest": {"level": 0.0, "freq": 0.0, "t": 0.0}}

    def scan(s3, start_hz, stop_hz, points, timeout=40.0):
        started = time.monotonic()
        try:
            result = original_scan(s3, start_hz, stop_hz, points, timeout)
        except Exception as exc:
            engine.status("ch3", "offline", str(exc).replace("—", ";").replace("-", " "))
            raise
        freqs, levels, raw_reply, warnings = result
        if (start_hz, stop_hz, points) == (ns["S3_PROBE_START"], ns["S3_PROBE_STOP"], ns["S3_PROBE_POINTS"]):
            return result
        if warnings or statistics.median(levels) > ns.get("S3_SANE_MAX_DBM", 0.0):
            engine.status("ch3", "error", "Sweep levels require verification")
            return result
        publish_sweep(freqs, levels, started)
        return result

    def publish_sweep(freqs, levels, started, source="HARDWARE"):
        grid = tuple(freqs)
        mono = time.monotonic()
        if ch3_grid[0] != grid:
            from .analysis import BaselineLock
            ch3_grid[0] = grid
            with engine.lock:
                window = engine.baselines["ch3"].window
            ch3_baselines[:] = [BaselineLock(window, 0.5) for _ in grid]
            engine.baseline("ch3", relock=True)
        with engine.lock:
            scalar_base = engine.baselines["ch3"]
            for baseline in ch3_baselines:
                if baseline.window != scalar_base.window or scalar_base.started is None:
                    baseline.window = scalar_base.window
                    baseline.reset()
                baseline.frozen = scalar_base.frozen
        deviations = [baseline.update(level, mono) for baseline, level in zip(ch3_baselines, levels)]
        strongest_index = max(range(len(deviations)), key=lambda i: abs(deviations[i]))
        delta = deviations[strongest_index]
        with engine.lock:
            ch3_history.append(delta)
            ch3_summary["count"] += 1
            ch3_summary["min"] = min(ch3_summary["min"], delta)
            ch3_summary["max"] = max(ch3_summary["max"], delta)
            ch3_summary["sum"] += delta
            if abs(delta) >= abs(ch3_summary["strongest"]["level"]):
                ch3_summary["strongest"] = {"level": delta, "freq": freqs[strongest_index], "t": time.time()}
        item = engine.ingest("ch3", max(levels), time.time(), "dB", raw={"frequencies": freqs, "levels_dbm": levels},
                             metadata={"monotonic": mono, "sweep_seconds": mono - started, "data_source": source,
                                       "frequencies": freqs, "deviations_db": deviations,
                                       "deviation_db": max(deviations, key=abs),
                                       "noise_db": statistics.median(b.noise for b in ch3_baselines),
                                       "bin_baselines_dbm": [baseline.value for baseline in ch3_baselines],
                                       "sweep3_settling": any(b.settling for b in ch3_baselines),
                                       "peak_frequency_hz": freqs[levels.index(max(levels))],
                                       "noise_floor_dbm": statistics.median(levels),
                                       "measurement_note": "Swept bins acquired sequentially; absolute CH3 accuracy unknown until reference calibration"})
        return item

    # ── external feed: any program, SDK or MTDI project drives the channels ────────
    # These publish into exactly the structures the pages, NVTRA and MTDI read, so data
    # from a feed looks the same everywhere as data from an attached instrument. Each
    # sample carries the label it was given (default EXTERNAL); nothing is synthesised.
    feed_lock = threading.Lock()
    feed_clock = {"ch1": 0.0, "ch2": 0.0, "ch3": 0.0}

    def _feed_mono(channel):
        # strictly increasing per channel, even for posts that arrive in one burst
        with feed_lock:
            mono = max(time.monotonic(), feed_clock[channel] + 1e-6)
            feed_clock[channel] = mono
            return mono

    def feed_ch1(values, unit="unit", source="EXTERNAL", now=None):
        """Channel 1: a three-axis vector [x, y, z] or a single number."""
        vector = [float(v) for v in (values if isinstance(values, (list, tuple)) else [values])]
        if len(vector) == 1:
            vector = [vector[0], 0.0, 0.0]
        if len(vector) != 3 or not all(math.isfinite(v) for v in vector):
            raise ValueError("ch1 takes one number or three finite numbers")
        now = time.time() if now is None else float(now)
        mono = _feed_mono("ch1")
        with ns["raw_ring_lock"]:
            ns["RAW_RING"]["ch1_raw"].append((now, *vector))
            ns["RAW_RING"]["ch1"].append((now, *vector))
        size = math.sqrt(sum(v * v for v in vector))
        c1 = engine.ingest("ch1", size, now, str(unit), raw=vector, vector=vector,
                           metadata={"monotonic": mono, "data_source": source})
        with ns["c1_lock"]:
            data = ns["ch1_data"]
            x, y, z = [c1["axial"][key] for key in ("x", "y", "z")]
            data.update(x=x, y=y, z=z, magnitude=c1["deviation"], raw_x=vector[0], raw_y=vector[1],
                        raw_z=vector[2], raw_magnitude=size, error=None, warning=None, chip_warning=None,
                        chip_id=source, calibrated=False, calibration_warning=None, last_rx=now,
                        fed_source=str(source), fed_unit=str(unit),
                        baseline_delta=c1["deviation"], baseline_calibrated=not c1["baseline"]["settling"],
                        baseline_magnitude=math.sqrt(sum(v * v for v in c1["baseline_vector"])))
            data["history"].append(c1["deviation"])
            data["xyz_history"].append((x, y, z))
            data["min_c1"] = min(data["min_c1"], c1["deviation"])
            data["max_c1"] = max(data["max_c1"], c1["deviation"])
        ns["ARCHIVE"].put("c1", {"t": now, "x": vector[0], "y": vector[1], "z": vector[2], "c1": size,
                                 "trusted": False, "warning": None, "data_source": source, "monotonic": mono})
        return c1

    def _scalar_feed_fields():
        # A fed reading is one number from someone else. Clear what the Uno or the triaxial probe
        # left behind, or the status keeps naming the Uno and the axis numbers stay frozen on it.
        return {"data_source": None, "provisional_adc": False, "rms_counts": None, "triaxial": False,
                "ex_mv": None, "ey_mv": None, "ez_mv": None, "ex_vu": None, "ey_vu": None, "ez_vu": None,
                "e_magnitude_mv": None, "e_magnitude_vu": None, "axis_clipped": {}, "axes_live": 0,
                "axis_status": {"x": "unwired", "y": "unwired", "z": "unwired"},
                "dc_axis_counts": {"x": None, "y": None, "z": None},
                "dc_baseline_counts": {"x": None, "y": None, "z": None},
                "dc_delta_counts": {"x": None, "y": None, "z": None}, "static_activity_counts": None}

    def feed_ch2(value, unit="mV RMS relative", source="EXTERNAL", now=None):
        """Channel 2: one number per sample (a level, a rate, an RMS, anything scalar)."""
        value = float(value)
        if not math.isfinite(value):
            raise ValueError("ch2 takes one finite number")
        now = time.time() if now is None else float(now)
        unit = "mV RMS relative" if unit is None else str(unit)   # an explicit null is the default, never "None"
        mono = _feed_mono("ch2")
        ch2 = engine.ingest("ch2", value, now, unit, metadata={"monotonic": mono, "data_source": source})
        profile = ch2["calibration"]["profile"]
        baseline = (ch2["baseline"]["value"] - profile.get("offset", 0)) / profile.get("scale", 1)
        ratio = value / baseline if abs(baseline) > 1e-12 else 1.0
        relative = min(100.0, max(0.0, (ratio - 1) / 9 * 100))
        with ns["raw_ring_lock"]:
            ns["RAW_RING"]["ch2f"].append((now, value))
        with ns["ch2f_lock"]:
            data = ns["ch2f_data"]
            data.update(rms_mv=value, raw_rms_mv=value, mean_mv=value, peak_mv=value,
                        field_vu=ch2["deviation"], peak_vu=ch2["deviation"], baseline_vu=0.0, baseline_mv=baseline,
                        ratio=ratio, rel_index=relative, level="LOW", gain=1, clipped=False, error=None,
                        warning=None, last_rx=now, status=source, calibrated=not ch2["baseline"]["settling"],
                        probe_calibrated=False, unit=ch2["unit"],
                        input_unit=unit, fed_source=str(source),
                        **_scalar_feed_fields())
            data["history"].append(ch2["deviation"])
            data["rel_history"].append(relative)
            data["min_rms"] = min(data["min_rms"], value)
            data["max_rms"] = max(data["max_rms"], value)
        ns["ARCHIVE"].put("ch2f", {"t": now, "rms_mv": value, "peak_mv": value, "baseline_mv": baseline,
                                   "ratio": ratio, "rel_index": relative, "gain": 1, "clipped": False,
                                   "trusted": False, "warning": None, "data_source": source, "monotonic": mono})
        return ch2

    def feed_ch3(xs, ys, source="EXTERNAL", now=None):
        """Channel 3: one sweep, a series of (x, y) points (a frequency sweep, a profile, a histogram)."""
        xs, ys = [float(v) for v in xs], [float(v) for v in ys]
        if len(xs) != len(ys) or len(xs) < 3 or not all(math.isfinite(v) for v in xs + ys):
            raise ValueError("ch3 takes two equal-length lists of at least three finite numbers")
        if any(b <= a for a, b in zip(xs, xs[1:])):
            raise ValueError("ch3 x values must increase")
        now = time.time() if now is None else float(now)
        started = time.monotonic()
        floor = statistics.median(ys)
        peaks = ns["_s3_peaks"](xs, ys, floor)
        for p in peaks:
            p["band"] = "—"          # radio band names mean nothing on a fed x axis
        peak_index = ys.index(max(ys))
        item = publish_sweep(xs, ys, started, source=source)
        duration = time.monotonic() - started
        with ns["sweep3_lock"]:
            sweep3 = ns["sweep3_data"]
            previous = sweep3["maxhold"]
            hold = [max(a, b) for a, b in zip(previous, ys)] if len(previous) == len(ys) else list(ys)
            sweep3.update(freqs=xs, levels=ys, maxhold=hold, peaks=peaks, floor=floor, x_unit=T("ch3.axis_unit"),
                          peak_level=ys[peak_index], peak_freq=xs[peak_index], sweep_s=duration,
                          sweeps=sweep3["sweeps"] + 1, device=source, device_info=source,
                          help_summary="External feed", port=source, leveloffset="Not applicable", level_sane=True,
                          trusted=False, warnings=[], level_note=None, present=True, span_start=xs[0], span_stop=xs[-1],
                          points=len(xs), status=source, error=None, last_rx=now)
            sweep3["waterfall"].append(list(ys))
            sweep3["waterfall_times"].append(now)
            sweep3["peak_history"].append(ys[peak_index])
        ns["ARCHIVE"].put("ch3", {"started_at": now, "completed_at": now + duration, "duration_s": duration,
                                  "profile": "external", "start_hz": xs[0], "stop_hz": xs[-1],
                                  "requested_points": len(xs), "repeat": 1, "bin_width_hz": (xs[-1] - xs[0]) / (len(xs) - 1),
                                  "frequencies": xs, "levels": ys, "peaks": peaks, "warnings": [],
                                  "trusted": False, "firmware": source, "port": source, "transport": "feed",
                                  "raw_response": None, "data_source": source})
        return item

    def ch3_rows(rows, freqs):
        if tuple(freqs) != ch3_grid[0] or not ch3_baselines:
            return []
        with engine.lock:
            reference = [baseline.value for baseline in ch3_baselines]
            scale = engine.calibrations.get("ch3").get("scale", 1.0)
        return [[(level - baseline) * scale for level, baseline in zip(row, reference)]
                for row in rows if len(row) == len(reference)]

    def ch3_display(snapshot):
        result = dict(snapshot)
        with engine.lock:
            metadata = dict(engine.channels["ch3"]["metadata"])
            scalar = engine.baselines["ch3"].value
            scale = engine.calibrations.get("ch3").get("scale", 1.0)
        freqs = result.get("freqs", [])
        if tuple(freqs) != ch3_grid[0] or not ch3_baselines:
            result.update(levels=[], maxhold=[], peaks=[], waterfall=[], peak_history=[],
                          peak_level=0.0, floor=0.0, level_note="Baseline settling")
            return result
        reference = [baseline.value for baseline in ch3_baselines]
        result["levels"] = [(level - baseline) * scale for level, baseline in zip(result.get("levels", []), reference)]
        result["maxhold"] = [(level - baseline) * scale for level, baseline in zip(result.get("maxhold", []), reference)]
        result["waterfall"] = ch3_rows(result.get("waterfall", []), freqs)
        result["floor"] = statistics.median(result["levels"]) if result["levels"] else 0.0
        peaks = []
        for peak in result.get("peaks", []):
            peak = dict(peak)
            index = min(range(len(freqs)), key=lambda i: abs(freqs[i] - peak["freq"]))
            peak["level"] = (peak["level"] - reference[index]) * scale
            peaks.append(peak)
        result["peaks"] = peaks
        result["peak_level"] = max(result["levels"], key=abs) if result["levels"] else 0.0
        result["peak_history"] = [value * scale for value in ch3_history]
        result["level_note"] = "Deviation from Baseline Lock in dB"
        result["baseline_settling"] = metadata.get("sweep3_settling", True)
        return result

    def ch3_stats():
        with engine.lock:
            result = dict(ch3_summary)
            result["strongest"] = dict(ch3_summary["strongest"])
            scale = engine.calibrations.get("ch3").get("scale", 1.0)
            for key in ("min", "max", "sum"):
                result[key] *= scale
            result["strongest"]["level"] *= scale
            return result

    def ch2_unit():
        return engine.calibrations.get("ch2").get("unit", "mV RMS relative")

    def ch2_calibration_label():
        profile = engine.calibrations.get("ch2")
        return (f"Reference scale {profile['scale']:.4g} {profile['unit']} per mV" if profile else "Not calibrated")

    def health(channel):
        snapshot = engine.snapshot()
        item = snapshot["channels"][channel]
        note = f"{item['state']}; {item['transient']['state']}; {item['uncertainty']}"
        return item["confidence"], note

    def ch3_health():
        score, note = health("ch3")
        with ns["sweep3_lock"]:
            present = bool(ns["sweep3_data"].get("present"))
        return score, note, present

    def mtdi_loop():
        while not stop.is_set():
            snapshot = engine.snapshot()
            channels, fusion = snapshot["channels"], snapshot["fusion"]
            with ns["mtdi_lock"]:
                target = ns["mtdi_data"]
                target.update(active_health=fusion["confidence"], completeness=fusion["breakdown"]["completeness"],
                              confidence_breakdown=fusion["breakdown"])
                for channel, prefix in (("ch1", "c1"), ("ch2", "ch2f"), ("ch3", "ch3")):
                    item = channels[channel]
                    target[prefix + "_health"] = item["confidence"]
                    target[prefix + "_note"] = f"{item['state']}; {item['transient']['state']}; {item['uncertainty']}"
            stop.wait(0.8)

    def aligned_histories():
        with engine.lock:
            ch1 = list(engine.histories["ch1"])
            ch2 = list(engine.histories["ch2"])
        if not ch1 or not ch2:
            return [], []
        end = min(ch1[-1][0], ch2[-1][0])
        pairs = []
        ch1_times = [point[0] for point in ch1]
        for timestamp, value, _noise in ch2:
            if not end - 20 <= timestamp <= end:
                continue
            position = bisect_left(ch1_times, timestamp)
            candidates = ch1[max(0, position - 1):min(len(ch1), position + 1)]
            nearest = min(candidates, key=lambda point: abs(point[0] - timestamp))
            if abs(nearest[0] - timestamp) <= 0.3:
                pairs.append((nearest[1], value))
        return [b for b, _ in pairs], [e for _, e in pairs]

    def ch2f_reader():
        """Select the measured Ch2 transport once, before acquisition starts."""
        source = CH2F_SOURCE
        if source not in {"auto", "src2", "arduino"}:
            publish_error("ch2", "ch2f_data", "ch2f_lock",
                          ValueError("STUDIO_CH2F_SOURCE must be auto, src2, or arduino"), 0)
            return
        if source == "arduino" or (source == "auto" and (arduino_adc_ports() or ARDUINO_TCP_LISTEN)):
            arduino_ch2f_reader()
        else:
            src2_ch2f_reader()

    ns["_v238_aligned_histories"] = aligned_histories
    ns["_c1_health"] = lambda: health("ch1")
    ns["_ch2f_health"] = lambda: health("ch2")
    ns["_ch3_health"] = ch3_health
    ns["mtdi_loop"] = mtdi_loop
    ns["_v238_ch2_unit"] = ch2_unit
    ns["_v238_ch2_calibration_label"] = ch2_calibration_label
    ns["_v238_ch3_stats"] = ch3_stats
    ns["_v238_ch3_display"] = ch3_display
    ns["_v238_ch3_rows"] = ch3_rows
    ns["feed_ch1"] = feed_ch1
    ns["feed_ch2"] = feed_ch2
    ns["feed_ch3"] = feed_ch3
    ns["src1_reader"] = src1_reader
    ns["ch2f_reader"] = ch2f_reader
    ns["_s3_read_until_prompt"] = read_until_prompt
    ns["_s3_cmd"] = command
    ns["validate_sweep"] = validate
    ns["_s3_scan"] = scan
    return {"src1_reader": src1_reader, "ch2f_reader": ch2f_reader}
