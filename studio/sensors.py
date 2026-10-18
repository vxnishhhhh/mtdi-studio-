"""Sensor constants and the original QMC5883P, ADS1115, tinySA Ultra, Wi Fi, Bluetooth and LAN readers."""
import socket
from ._shared import inherit
inherit(globals(), 'common')

# ════════════════════════════════════════════════════════
#  MTDI STUDIO  —  HOST BUILD
#  Magnetometer: QMC5883P on I2C-1 @ 0x2C  (GY-271 style board)
#    Wiring:  VCC->3.3V(pin1)  GND->GND(pin6)  SDA->GPIO2(pin3)  SCL->GPIO3(pin5)
#  E-field:    ADS1115 ADC on I2C-1 @ 0x48, A0 (plate/antenna front end)
#    gain=16 (+/-0.256V), 860 SPS, mean-relative RMS/peak = relative activity
#  Spectrum:   tinySA Ultra over USB CDC serial (VID 0483 / PID 5740), HT5 antenna
#    text `scan <start> <stop> <points> 3` -> "<freq> <level> <reserved>" per line
#  The server uses authenticated LAN mode by default; --local-only binds loopback.
# ════════════════════════════════════════════════════════

# ── QMC5883P register map ──
QMC_ADDR      = 0x2C
I2C_BUS       = 1
REG_CHIPID    = 0x00   # expected 0x80
REG_DATA      = 0x01   # X/Y/Z, 6 bytes, signed 16-bit little-endian
REG_STATUS    = 0x09   # bit0 DRDY, bit1 OVL
REG_CTRL1     = 0x0A   # 0xC5 = continuous 50Hz normal ; 0x00 = standby
REG_CTRL2     = 0x0B   # 0x80 soft reset ; 0x0C set/reset
REG_AXIS_SIGN = 0x29   # 0x06
LSB_PER_UT    = 150.0  # +/-2G -> 15000 LSB/gauss -> 150 LSB/uT
MAG_BASELINE_SECS = 5.0  # quiet-environment vector baseline window

# Installation-specific two-point magnitude calibration supplied from reference
# measurements in Durban: the observed quiet capture (3.704754 µT, displayed
# previously as about 3 µT) = 28 µT, and 120 µT raw = 2000 µT.
# The affine curve is applied to vector magnitude while preserving direction.
MAG_RAW_REF_LOW_UT = 3.704753703014547
MAG_TRUE_REF_LOW_UT = 28.0
MAG_RAW_REF_HIGH_UT = 120.0
MAG_TRUE_REF_HIGH_UT = 2000.0
MAG_MAGNITUDE_SLOPE = (
    (MAG_TRUE_REF_HIGH_UT - MAG_TRUE_REF_LOW_UT) /
    (MAG_RAW_REF_HIGH_UT - MAG_RAW_REF_LOW_UT)
)
MAG_MAGNITUDE_OFFSET_UT = MAG_TRUE_REF_LOW_UT - MAG_MAGNITUDE_SLOPE * MAG_RAW_REF_LOW_UT

mag_lock = threading.RLock()
# Raw sample rings for the D4 engine: the magnetometer vectors before any calibration
# (what an ellipsoid fit needs) and the last E-field ADC blocks at the true 860 SPS (what
# a mains FFT needs). Each entry carries its own timestamp so the real rate is known.
RAW_RING = {"magnetic_raw": deque(maxlen=12000), "magnetic": deque(maxlen=12000), "efield": deque(maxlen=8600), "current": deque(maxlen=8600)}
raw_ring_lock = threading.Lock()
# NOTE on "warning" vs "chip_warning" vs "calibration_warning":
#   chip_warning       -> a real fault (wrong chip ID). Degrades health, shows red.
#   calibration_warning-> informational. Running without a hard/soft-iron profile is
#                         the normal default; it means the vector is uncorrected, NOT
#                         that the link is unhealthy. It must never turn the status
#                         strip orange or drop MTDI health.
#   warning            -> the human-readable join of the two, for display only.
magnetic_data = {"x":0.0,"y":0.0,"z":0.0,"magnitude":0.0,
                 "history":deque(maxlen=200),"xyz_history":deque(maxlen=200),
                 "min_mag":float("inf"),"max_mag":0.0,
                 "raw_x":0.0,"raw_y":0.0,"raw_z":0.0,
                 "error":'Waiting for channel 1',"warning":None,
                 "chip_warning":None,"calibration_warning":"uncalibrated",
                 "calibrated":False,"calibration_metadata":{},"chip_id":None,
                 "baseline_x":0.0,"baseline_y":0.0,"baseline_z":0.0,
                 "baseline_magnitude":0.0,"baseline_delta":0.0,
                 "baseline_calibrated":False,"baseline_started_at":None,
                 "baseline_history":deque(maxlen=40),
                 "overflow_count":0,"reconnect_count":0,"last_rx":None}

# Environmental Intelligence command channel for the magnetic reader. This is
# deliberately separate from hard/soft-iron calibration: it learns the local quiet
# field after those corrections have been applied.
mag_cmd_lock = threading.Lock()
mag_cmd = {"recalibrate":False, "reload_calibration":False}
wifi_scan_now = threading.Event()
bt_scan_now = threading.Event()
# D4 burst capture: a positive count asks the E-field reader for that many contiguous samples
BURST_REQUEST = {"efield": 0, "current": 0}

# ── tinySA Ultra spectrum analyser (USB CDC serial) ──
# The device speaks a line-oriented shell terminated by the prompt "ch>". We use the
# TEXT `scan` command, not `scanraw`; measured duration is displayed for every sweep.
# IMPORTANT: `scan` emits THREE columns —
# "<freq_hz> <level_dbm> <reserved>" — so the parser must accept >= 2 fields, not == 2.
TINYSA_VID        = 0x0483
TINYSA_PID        = 0x5740
TSA_BAUD          = 115200
TSA_PROMPT        = b"ch>"
TSA_DEFAULT_START = 100_000            # 100 kHz — bottom of the tinySA Ultra range
TSA_DEFAULT_STOP  = 6_000_000_000      # 6 GHz   — top of the HT5 / Ultra range
TSA_DEFAULT_PTS   = 251                # conservative firmware-compatible point count
TSA_SWEEP_GAP     = 0.15               # breathing room between sweeps
TSA_SCAN_TIMEOUT  = 40.0               # a full 6 GHz sweep is much slower than a narrow one
TSA_PROBE_START   = 100_000_000        # conservative capability-test span
TSA_PROBE_STOP    = 101_000_000
TSA_PROBE_POINTS  = 11
TSA_PROBE_TIMEOUT = 15.0
TSA_WATERFALL_ROWS= 48                 # history depth of the waterfall
TSA_PEAK_COUNT    = 6
TSA_PEAK_MIN_PROM = 4.0                # dB a local maximum must clear the noise floor by
TSA_ULTRA_ABOVE   = 800_000_000        # >800 MHz needs the Ultra unlock on this firmware
# A median sweep level above this is suspicious for an ambient antenna survey.  It is
# not diagnosed automatically: parser, analyser state and RF setup must be verified.
TSA_SANE_MAX_DBM  = 0.0

# Frequency plan used to provide broad allocation hints. An allocation never identifies
# the protocol, device or transmitter represented by a measured bin.
BAND_PLAN = [
    (        0,      535_000, "VLF / LF"),
    (  535_000,    1_605_000, "AM broadcast"),
    (1_605_000,   26_960_000, "HF / shortwave"),
    (26_960_000,  27_410_000, "CB 27 MHz"),
    (27_410_000,  76_000_000, "VHF low"),
    (76_000_000, 108_000_000, "FM broadcast"),
    (108_000_000,137_000_000, "Airband"),
    (137_000_000,174_000_000, "VHF land mobile"),
    (174_000_000,230_000_000, "VHF TV / DAB"),
    (230_000_000,380_000_000, "VHF/UHF gap"),
    (380_000_000,400_000_000, "TETRA"),
    (400_000_000,470_000_000, "UHF land mobile"),
    (470_000_000,694_000_000, "UHF TV / DTT"),
    (694_000_000,803_000_000, "LTE 700 (B28)"),
    (803_000_000,880_000_000, "LTE 800"),
    (880_000_000,960_000_000, "GSM 900"),
    (960_000_000,1710_000_000,"L-band / GNSS"),
    (1710_000_000,1880_000_000,"GSM/LTE 1800"),
    (1880_000_000,1920_000_000,"DECT"),
    (1920_000_000,2170_000_000,"UMTS/LTE 2100"),
    (2170_000_000,2400_000_000,"LTE 2300"),
    (2400_000_000,2500_000_000,'Channel 5 2.4 / BT / ISM'),
    (2500_000_000,2690_000_000,"LTE 2600"),
    (2690_000_000,3300_000_000,"S-band"),
    (3300_000_000,3800_000_000,"5G n77/n78"),
    (3800_000_000,5150_000_000,"C-band"),
    (5150_000_000,5925_000_000,'Channel 5 5 GHz'),
    (5925_000_000,7000_000_000,"6 GHz / U-NII"),
]

# Range presets offered in the UI. (key, label, start_hz, stop_hz)
TSA_PRESETS = [
    ("full",  "FULL SPAN",  TSA_DEFAULT_START, TSA_DEFAULT_STOP),
    ("fm",    "FM 88-108",  88_000_000,        108_000_000),
    ("vhfuhf","VHF/UHF",    130_000_000,       700_000_000),
    ("cell",  "CELLULAR",   700_000_000,       2_700_000_000),
    ("wifi24",'CHANNEL 5 2.4',   2_400_000_000,     2_500_000_000),
    ("wifi5", 'CHANNEL 5 5G',    5_150_000_000,     5_925_000_000),
]

spectrum_lock = threading.RLock()
spectrum_data = {
    "freqs":[], "levels":[], "maxhold":[],           # current sweep + running max hold
    "peaks":[],                                       # [{"freq","level","band"}]
    "floor":0.0, "peak_level":0.0, "peak_freq":0.0,
    "span_start":TSA_DEFAULT_START, "span_stop":TSA_DEFAULT_STOP,
    "bands":{}, "focus":[],
    "points":TSA_DEFAULT_PTS, "sweep_s":0.0, "sweeps":0, "preset":"full",
    "waterfall":deque(maxlen=TSA_WATERFALL_ROWS),     # rows of levels, newest last
    "waterfall_times":deque(maxlen=TSA_WATERFALL_ROWS),
    "peak_history":deque(maxlen=200),                 # strongest peak level per sweep
    "device":"—", "device_info":"—", "help_summary":"—",
    "leveloffset":"—", "ultra":False, "port":"—",
    "level_sane":True, "trusted":False, "warnings":[], "level_note":"—", "present":False,
    "status":'searching for Source 3…', "error":'Waiting for Source 3', "last_rx":None,
}

# Command channel: UI buttons ask the reader thread to change range / resolution or
# clear the max-hold trace. Checked at the top of each sweep so there is never a
# concurrent write to the serial port.
tinysa_cmd_lock = threading.Lock()
tinysa_cmd = {
    "range":None, "points":None, "reset_hold":False,
    "preset":None, "paused":False,
    # Focus bands: a list of (start_hz, stop_hz) the analyser cycles through instead of one
    # span. Each band gets the full point count, so a narrow band means fine resolution and a
    # fast revisit; per-band live/previous/delta traces live in spectrum_data["bands"].
    "bands":None,
}

mtdi_lock = threading.RLock()
mtdi_data = {
    "mag_health":0.0, "efield_health":0.0, "rf_health":0.0,
    "active_health":0.0, "completeness":0.0,
    "mag_note":"—", "efield_note":"—", "rf_note":"—",
}

sys_lock = threading.RLock()
sys_data = {"cpu_temp":0.0,"cpu_usage":0.0,"ram_used_mb":0,"ram_total_mb":0,"ram_pct":0.0,
            "disk_used_gb":0.0,"disk_total_gb":0.0,"disk_pct":0.0,"uptime_str":"—",
            "load_1":0.0,"load_5":0.0,"load_15":0.0,"wifi_ip":"—","py_mem_mb":0.0,
            "app_version":APP_VERSION,"db_size_mb":0.0,"worker_count":0,"thread_count":0,
            "archive_queue":0,"last_db_write":None,"temperature_available":False,
            "telemetry_source":"starting","telemetry_error":None,"last_rx":None,
            "host_model":"detecting","raspberry_pi":False}

# One stored area for past signals: rolling archive + session statistics.
archive_lock = threading.RLock()
signal_archive = deque(maxlen=400)   # {"t","mag","x","y","z"}
session_stats = {"count":0, "min":float("inf"), "max":0.0, "sum":0.0, "started":time.time()}

# RF archive: the strongest peak of every sweep, so the session keeps a record of what
# was on air and when — the spectrum equivalent of the magnetic signal archive.
rf_archive_lock = threading.RLock()
rf_archive = deque(maxlen=400)       # {"t","freq","level","band"}
rf_stats = {"count":0, "min":float("inf"), "max":-999.0, "sum":0.0,
            "strongest":{"freq":0.0,"level":-999.0,"band":"—","t":0.0}}

def _s16(v):
    return v - 65536 if v >= 32768 else v


def _load_magnetometer_calibration():
    """Load and strictly validate optional hard/soft-iron JSON calibration."""
    path_text = os.environ.get("STUDIO_MAG_CALIBRATION", "").strip()
    if not path_text:
        # D4: iv_config.json (written by the ellipsoid calibration here or exported by MATLAB)
        try:
            from . import d4 as _d4
            cfg, err = _d4.load_config()
            offsets = [float(v) for v in cfg["mag_offsets"]]
            matrix = [[float(v) for v in row] for row in cfg["mag_soft_iron"]]
            identity = all(abs(offsets[i]) < 1e-9 for i in range(3)) and all(abs(matrix[i][j] - (1.0 if i == j else 0.0)) < 1e-9 for i in range(3) for j in range(3))
            if not err and not identity:
                return {"offsets": offsets, "matrix": matrix,
                        "metadata": {"source": "iv_config.json (D4 ellipsoid fit)", "quality": cfg.get("mag_calibration_quality")},
                        "path_name": "iv_config.json"}, None
        except Exception as exc:
            return None, f"iv_config.json calibration unusable: {exc}"
        return None, "uncalibrated — no hard/soft-iron profile configured"
    path = Path(path_text).expanduser()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        offsets = [float(v) for v in payload["hard_iron_offset_ut"]]
        matrix = [[float(v) for v in row] for row in payload["soft_iron_matrix"]]
        if len(offsets) != 3 or len(matrix) != 3 or any(len(row) != 3 for row in matrix):
            raise ValueError("expected 3 offsets and a 3x3 soft-iron matrix")
        values = offsets + [v for row in matrix for v in row]
        if not all(math.isfinite(v) for v in values):
            raise ValueError("calibration contains a non-finite value")
        determinant = (
            matrix[0][0]*(matrix[1][1]*matrix[2][2]-matrix[1][2]*matrix[2][1])
            - matrix[0][1]*(matrix[1][0]*matrix[2][2]-matrix[1][2]*matrix[2][0])
            + matrix[0][2]*(matrix[1][0]*matrix[2][1]-matrix[1][1]*matrix[2][0])
        )
        if abs(determinant) < 1e-9:
            raise ValueError("soft-iron matrix is singular")
        return {
            "offsets":offsets, "matrix":matrix,
            "metadata":payload.get("metadata", {}),
            "path_name":path.name,
        }, None
    except Exception as exc:
        return None, f"invalid calibration profile: {exc}"


def _apply_magnetometer_calibration(raw_x, raw_y, raw_z, profile):
    if profile is None:
        return raw_x, raw_y, raw_z
    vector = [
        raw_x-profile["offsets"][0],
        raw_y-profile["offsets"][1],
        raw_z-profile["offsets"][2],
    ]
    matrix = profile["matrix"]
    return tuple(sum(matrix[row][column]*vector[column] for column in range(3)) for row in range(3))


def _apply_magnetic_magnitude_curve(x, y, z):
    """Apply the installed two-point µT correction without changing direction."""
    measured = math.sqrt(x*x + y*y + z*z)
    if measured <= 1e-12:
        return 0.0, 0.0, 0.0
    corrected = max(0.0, MAG_MAGNITUDE_SLOPE * measured + MAG_MAGNITUDE_OFFSET_UT)
    factor = corrected / measured
    return x * factor, y * factor, z * factor


def qmc_reader():
    """Read the QMC5883P over I2C-1 and update magnetic_data. No fake data."""
    try:
        from smbus2 import SMBus
    except Exception:
        with mag_lock:
            magnetic_data["error"] = "smbus2 not installed  (pip install smbus2)"
        return
    calibration, calibration_warning = _load_magnetometer_calibration()
    if calibration is None:
        calibration_warning = "two-point magnitude calibration active; no directional hard/soft-iron profile"
    with mag_lock:
        magnetic_data["calibrated"] = True
        magnetic_data["calibration_warning"] = calibration_warning
        magnetic_data["calibration_metadata"] = (
            dict(calibration["metadata"]) if calibration else {}
        )
    if calibration is not None:
        ARCHIVE.put("calibration", {
            "sensor":"magnetometer", "active":True,
            "payload":{
                "hard_iron_offset_ut":calibration["offsets"],
                "soft_iron_matrix":calibration["matrix"],
                "metadata":calibration["metadata"],
                "source_file":calibration["path_name"],
            },
        })
    ARCHIVE.put("calibration", {
        "sensor":"magnetometer_magnitude", "active":True,
        "payload":{
            "raw_reference_ut":[MAG_RAW_REF_LOW_UT, MAG_RAW_REF_HIGH_UT],
            "true_reference_ut":[MAG_TRUE_REF_LOW_UT, MAG_TRUE_REF_HIGH_UT],
            "slope":MAG_MAGNITUDE_SLOPE,
            "offset_ut":MAG_MAGNITUDE_OFFSET_UT,
        },
    })
    baseline_samples = []
    baseline_started_at = time.time()
    baseline_vector = None
    with mag_lock:
        magnetic_data["baseline_started_at"] = baseline_started_at
        magnetic_data["baseline_calibrated"] = False
    while not STOP_EVENT.is_set():
        bus = None
        try:
            bus = SMBus(I2C_BUS)
            # Verify chip id before writing any configuration
            try:
                cid = bus.read_byte_data(QMC_ADDR, REG_CHIPID)
            except Exception as e:
                raise IOError(f"no source at 0x2C ({e})")
            # Init sequence
            bus.write_byte_data(QMC_ADDR, REG_CTRL2, 0x80); STOP_EVENT.wait(0.02)
            bus.write_byte_data(QMC_ADDR, REG_AXIS_SIGN, 0x06)                # axis sign
            bus.write_byte_data(QMC_ADDR, REG_CTRL2, 0x0C)                    # set/reset
            bus.write_byte_data(QMC_ADDR, REG_CTRL1, 0xC5)                    # continuous 50Hz normal
            STOP_EVENT.wait(0.05)
            with mag_lock:
                magnetic_data["chip_id"] = cid
                magnetic_data["chip_warning"] = (
                    None if cid == 0x80 else f"persistent chip-ID mismatch: 0x{cid:02X}, expected 0x80"
                )
                magnetic_data["warning"] = " · ".join(
                    warning for warning in (
                        magnetic_data["chip_warning"],
                        magnetic_data["calibration_warning"],
                    ) if warning
                ) or None
                magnetic_data["error"] = None
                magnetic_data["reconnect_count"] += 1
            while not STOP_EVENT.is_set():
                with mag_cmd_lock:
                    if mag_cmd.get("reload_calibration"):
                        mag_cmd["reload_calibration"] = False
                        calibration, calibration_warning = _load_magnetometer_calibration()
                        with mag_lock:
                            magnetic_data["calibration_warning"] = calibration_warning or None
                            magnetic_data["calibration_metadata"] = dict(calibration["metadata"]) if calibration else {}
                    if mag_cmd["recalibrate"]:
                        mag_cmd["recalibrate"] = False
                        baseline_samples = []
                        baseline_vector = None
                        baseline_started_at = time.time()
                        with mag_lock:
                            magnetic_data["baseline_started_at"] = baseline_started_at
                            magnetic_data["baseline_calibrated"] = False
                            magnetic_data["baseline_delta"] = 0.0
                st = bus.read_byte_data(QMC_ADDR, REG_STATUS)
                if not (st & 0x01):           # DRDY not set yet
                    STOP_EVENT.wait(0.005); continue
                if st & 0x02:                 # overflow -> skip this sample
                    with mag_lock:
                        magnetic_data["overflow_count"] += 1
                    STOP_EVENT.wait(0.02); continue
                d = bus.read_i2c_block_data(QMC_ADDR, REG_DATA, 6)
                raw_x = _s16(d[0] | (d[1] << 8)) / LSB_PER_UT
                raw_y = _s16(d[2] | (d[3] << 8)) / LSB_PER_UT
                raw_z = _s16(d[4] | (d[5] << 8)) / LSB_PER_UT
                x, y, z = _apply_magnetometer_calibration(
                    raw_x, raw_y, raw_z, calibration
                )
                x, y, z = _apply_magnetic_magnitude_curve(x, y, z)
                m = math.sqrt(x*x + y*y + z*z)
                sampled_at = time.time()
                with raw_ring_lock:
                    RAW_RING["magnetic_raw"].append((sampled_at, raw_x, raw_y, raw_z))
                    RAW_RING["magnetic"].append((sampled_at, x, y, z))
                if baseline_vector is None:
                    baseline_samples.append((x, y, z))
                    if sampled_at - baseline_started_at >= MAG_BASELINE_SECS and baseline_samples:
                        bx = statistics.median(v[0] for v in baseline_samples)
                        by = statistics.median(v[1] for v in baseline_samples)
                        bz = statistics.median(v[2] for v in baseline_samples)
                        baseline_vector = (bx, by, bz)
                        baseline_mag = math.sqrt(bx*bx + by*by + bz*bz)
                        deltas = [math.sqrt((vx-bx)**2 + (vy-by)**2 + (vz-bz)**2)
                                  for vx, vy, vz in baseline_samples]
                        spread = statistics.median(deltas)
                        with mag_lock:
                            magnetic_data.update({
                                "baseline_x":bx, "baseline_y":by, "baseline_z":bz,
                                "baseline_magnitude":baseline_mag,
                                "baseline_delta":math.sqrt((x-bx)**2 + (y-by)**2 + (z-bz)**2),
                                "baseline_calibrated":True,
                            })
                            magnetic_data["baseline_history"].append({
                                "t":sampled_at, "x":bx, "y":by, "z":bz,
                                "magnitude":baseline_mag, "spread_ut":spread,
                            })
                        ARCHIVE.put("calibration", {
                            "sensor":"magnetometer_environment", "active":True,
                            "payload":{"baseline_x_ut":bx,"baseline_y_ut":by,
                                       "baseline_z_ut":bz,"baseline_magnitude_ut":baseline_mag,
                                       "median_delta_spread_ut":spread,
                                       "sample_count":len(baseline_samples)},
                        })
                delta = (math.sqrt((x-baseline_vector[0])**2 +
                                   (y-baseline_vector[1])**2 +
                                   (z-baseline_vector[2])**2)
                         if baseline_vector is not None else 0.0)
                # Logged here, in the read loop, so the CSV carries every sample at
                # the ~20 Hz the sensor is actually polled. archive_loop() only
                # snapshots this channel every 3 s, which is a 60x decimation.
                CSV_LOG.log_mag(
                    sampled_at, x, y, z, m, (raw_x, raw_y, raw_z),
                    True,
                    magnetic_data["chip_warning"] is None,
                )
                with mag_lock:
                    magnetic_data.update({"raw_x":raw_x,"raw_y":raw_y,"raw_z":raw_z,
                                          "x":x,"y":y,"z":z,"magnitude":m,
                                          "baseline_delta":delta,
                                          "last_rx":sampled_at,"error":None})
                    magnetic_data["history"].append(m)
                    magnetic_data["xyz_history"].append((x, y, z))
                    if m < magnetic_data["min_mag"]: magnetic_data["min_mag"] = m
                    if m > magnetic_data["max_mag"]: magnetic_data["max_mag"] = m
                STOP_EVENT.wait(0.05)
        except Exception as e:
            with mag_lock:
                magnetic_data["error"] = f"I2C: {e}"
            LOG.exception('Channel 1 worker error')
        finally:
            if bus:
                try:
                    bus.write_byte_data(QMC_ADDR, REG_CTRL1, 0x00)
                except Exception:
                    LOG.debug('Channel 1 standby command failed', exc_info=True)
                try:
                    bus.close()
                except Exception:
                    LOG.exception('Channel 1 bus close failed')
        STOP_EVENT.wait(2)

# ── ADS1115 E-field sensor — DIFFERENTIAL A0-A1, auto-ranging, RMS (ports es2.py) ──
# One non-contact antenna on A0, biased to a stable ~1.634V VREF on A1. The ADC
# measures A0-A1, auto-ranges its PGA for headroom, and reports the AC RMS deviation
# from the block mean as a RELATIVE low-frequency E-field ACTIVITY index.
# This is a single SCALAR magnitude — no X/Y/Z. Physical V/m uses the configured
# probe calibration scale; 1 V/m is numerically equal to 1 N/C.
ADS_ADDR          = 0x48
SAMPLES_PER_BLOCK = 100
ADS_DATA_RATE     = 860
# Gain 16 = most sensitive (narrowest range); gain 2 = widest usable range.
GAINS = [16, 8, 4, 2]
# ADS1115 differential full-scale voltage for each gain.
FULL_SCALE_VOLTS  = {16: 0.256, 8: 0.512, 4: 1.024, 2: 2.048}
HIGH_UTILISATION  = 0.80   # >80% of full scale -> step gain DOWN for headroom
LOW_UTILISATION   = 0.18   # <18% for several blocks -> step gain UP for sensitivity
LOW_BLOCKS_TO_RAISE_GAIN = 4
POSITIVE_CLIP     = 32000
NEGATIVE_CLIP     = -32000
EF_BASELINE_SECS  = 10.0   # longer quiet baseline rejects short environmental changes
EF_REL_FULL_RATIO = 10.0   # AC RMS = 10x baseline -> 100% on the relative index
EF_EMA_ALPHA      = 0.12   # slower EMA for a steadier field-strength display
EF_MEDIAN_BLOCKS  = 5      # reject isolated block spikes before the EMA
# Probe scale: estimated electric-field strength (V/m) produced by one volt of AC RMS
# at the ADS1115 input. Determine this against a known fixture and set, for example:
#   STUDIO_EFIELD_V_PER_M_PER_VOLT=395.256917
# V/m and N/C are dimensionally and numerically equivalent. C/N is not an E-field unit.
try:
    # Field reference supplied for this probe: 5 V at 1 cm -> 500 V/m under the
    # uniform-field approximation. Observed AC input response was 1.265 V,
    # therefore 500 / 1.265 = 395.256917 V/m per input volt. _ef_v_per_m receives
    # millivolts and converts them to volts before applying this coefficient.
    # A nearby single conductor is not a uniform parallel-plate field, so this is
    # explicitly a reference-scaled estimate and must be re-established for a
    # different probe, antenna geometry or reference fixture.
    EF_V_PER_M_PER_VOLT = float(os.environ.get(
        "STUDIO_EFIELD_V_PER_M_PER_VOLT", "395.256917"
    ))
    if not math.isfinite(EF_V_PER_M_PER_VOLT) or EF_V_PER_M_PER_VOLT <= 0:
        raise ValueError("probe scale must be finite and positive")
except ValueError:
    EF_V_PER_M_PER_VOLT = 395.256917
    LOG.warning("Invalid STUDIO_EFIELD_V_PER_M_PER_VOLT; using reference scale 395.256917")

EF_SCALE_SOURCE = (
    "STUDIO_EFIELD_V_PER_M_PER_VOLT environment override"
    if os.environ.get("STUDIO_EFIELD_V_PER_M_PER_VOLT") else
    'reference estimate: 1.265 V AC RMS = 500 unit (5 V / 1 cm uniform-field fixture)'
)

# Installed E-field fixture calibration. In the observed setup the quiet reading
# was 3 V/m and the 5 V reference at 1 cm read 1.5 V/m. The probe response is
# directionless, so use the absolute change (1.5 V/m) and map it to the ideal
# fixture field E=V/d=5/0.01=500 V/m. This makes the learned environment zero.
EF_FIXTURE_REFERENCE_V_M = 500.0
EF_OBSERVED_QUIET_V_M = 3.0
EF_OBSERVED_REFERENCE_V_M = 1.5
EF_DELTA_GAIN = EF_FIXTURE_REFERENCE_V_M / abs(
    EF_OBSERVED_REFERENCE_V_M - EF_OBSERVED_QUIET_V_M
)
EF_PHONE_PREVIOUS_V_M = 1200.0
EF_PHONE_TARGET_V_M = 50.0
EF_PHONE_NORMALIZATION = EF_PHONE_TARGET_V_M / EF_PHONE_PREVIOUS_V_M
EF_SCALE_SOURCE += (
    ' · baseline-relative · installed phone reference: 1200 unit normalized to 50 unit at 1 cm'
)

def _ef_v_per_m(millivolts):
    return float(millivolts) * 0.001 * EF_V_PER_M_PER_VOLT


def _ef_calibrated_v_per_m(millivolts, baseline_millivolts):
    """Return absolute field change relative to the learned environment."""
    raw_field = _ef_v_per_m(millivolts)
    quiet_field = _ef_v_per_m(baseline_millivolts)
    return abs(raw_field - quiet_field) * EF_DELTA_GAIN * EF_PHONE_NORMALIZATION

efield_lock = threading.RLock()
efield_data = {"rms_mv":0.0,"mean_mv":0.0,"peak_mv":0.0,
               "field_v_m":0.0,"peak_v_m":0.0,"baseline_v_m":0.0,
               "baseline_mv":0.0,"rel_index":0.0,"ratio":0.0,"level":"—",
               "gain":GAINS[-1],"min_code":0,"max_code":0,"utilisation":0.0,
               "clipped":False,"status":"warming up",
               "history":deque(maxlen=200),"rel_history":deque(maxlen=200),
               "min_rms":float("inf"),"max_rms":0.0,"baseline_history":deque(maxlen=40),
               "warning":None,"last_calibration_reason":"startup",
               "probe_scale_v_per_m_per_volt":EF_V_PER_M_PER_VOLT,
               "probe_scale_source":EF_SCALE_SOURCE,
               "error":'Waiting for channel 2',"last_rx":None,"calibrated":False,
               # Transport identity is supplied by acquisition.  In particular,
               # a temporary Uno over USB reports real 10-bit ADC counts but has
               # no ADS1115 or field-strength calibration.
               "data_source":None,"provisional_adc":False,"rms_counts":None,
               # ── triaxial ──────────────────────────────────────────────────
               # Three plate electrodes on A0/A1/A2, each responding to the field
               # component normal to its face, give a vector rather than the single
               # directionless magnitude the probe reported when it had one input.
               # The per-axis values are AC RMS in mV about each block's own mean,
               # the same quantity the scalar path uses, so they are directly
               # comparable with rms_mv and with each other once scaled.
               #
               # An axis that is not wired reports None, never 0.0. Zero is a real
               # measurement -- "this axis sees no field" -- and an unwired axis
               # silently reading zero would drag the magnitude down and swing the
               # direction while looking perfectly healthy. axes_live says how many
               # actually contributed, so the UI can state it rather than imply three.
               "triaxial":False,
               "ex_mv":None,"ey_mv":None,"ez_mv":None,
               "ex_v_m":None,"ey_v_m":None,"ez_v_m":None,
               "e_magnitude_mv":None,"e_magnitude_v_m":None,
               "axis_status":{"x":"unwired","y":"unwired","z":"unwired"},
               "dc_axis_counts":{"x":None,"y":None,"z":None},
               "dc_baseline_counts":{"x":None,"y":None,"z":None},
               "dc_delta_counts":{"x":None,"y":None,"z":None},
               "static_activity_counts":None,
               "axes_live":0,
               "exyz_history":deque(maxlen=200),
               "emag_history":deque(maxlen=200)}

# Command channel: the "Environmental Intelligence" button asks the reader thread
# to re-learn the baseline on demand (thread-safe, checked at the top of each block).
efield_cmd_lock = threading.Lock()
efield_cmd = {"recalibrate": False}

def efield_reader():
    """Differential A0-A1 auto-ranging RMS E-field reader (ports es2.py into a thread).
       Uses adafruit-circuitpython-ads1x15 exactly like the working standalone test:
       AnalogIn(ads, 0, 1) differential, PGA auto-ranges for headroom, AC RMS deviation
       from the block mean = relative low-frequency E-field activity. Scalar only."""
    try:
        import board, busio
        from adafruit_ads1x15.ads1115 import ADS1115
        from adafruit_ads1x15.analog_in import AnalogIn
    except Exception as e:
        with efield_lock:
            efield_data["error"] = (f"E-field libs missing ({e}) — "
                                    "pip install adafruit-blinka adafruit-circuitpython-ads1x15")
        return
    while not STOP_EVENT.is_set():
        i2c = None
        try:
            i2c = busio.I2C(board.SCL, board.SDA)
            ads = ADS1115(i2c, address=ADS_ADDR)
            ads.data_rate = ADS_DATA_RATE
            channel = AnalogIn(ads, 0, 1)          # DIFFERENTIAL: A0 minus A1 (VREF)

            state = {"active_gain": None}
            def set_gain(g):
                # Only reconfigure when the gain actually changes; discard the first few
                # conversions so the PGA/ADC settle before we trust the readings.
                if g != state["active_gain"]:
                    ads.gain = g
                    state["active_gain"] = g
                    STOP_EVENT.wait(0.05)
                    for _ in range(8):
                        _ = channel.value
            def read_block(g):
                set_gain(g)
                n = SAMPLES_PER_BLOCK
                if BURST_REQUEST["efield"] > 0:
                    n = min(8600, int(BURST_REQUEST["efield"])); BURST_REQUEST["efield"] = 0
                t0 = time.time()
                block = [channel.value for _ in range(n)]
                t1 = time.time()
                # the block is contiguous at the ADC rate; keep the codes with their times
                step = (t1 - t0) / max(1, len(block) - 1)
                with raw_ring_lock:
                    RAW_RING["efield"].extend((t0 + i * step, v) for i, v in enumerate(block))
                return block

            gain_index = len(GAINS) - 1            # start at the widest usable range
            low_signal_count = 0
            baseline_acc = []
            baseline_mv = 0.0
            calibrated = False
            rms_ema = None
            rms_window = deque(maxlen=EF_MEDIAN_BLOCKS)
            t_start = time.time()
            with efield_lock:
                efield_data.update({"error":None,"calibrated":False,"status":"calibrating"})

            while not STOP_EVENT.is_set():
                # Environmental Intelligence: re-learn the baseline on command.
                with efield_cmd_lock:
                    if efield_cmd["recalibrate"]:
                        efield_cmd["recalibrate"] = False
                        baseline_acc = []; baseline_mv = 0.0; calibrated = False
                        rms_window.clear(); rms_ema = None
                        t_start = time.time()
                        with efield_lock:
                            efield_data.update({
                                "calibrated":False, "status":"re-calibrating",
                                "last_calibration_reason":"manual UI request",
                            })
                gain = GAINS[gain_index]
                volts_per_code = FULL_SCALE_VOLTS[gain] / 32768.0
                samples = read_block(gain)
                mn = min(samples); mx = max(samples)
                mean_code = sum(samples) / len(samples)
                # AC signal strength = RMS deviation from the block mean.
                rms_code = math.sqrt(sum((s - mean_code) ** 2 for s in samples) / len(samples))
                # Normalise to real volts so a gain switch never makes the number jump.
                mean_mv = mean_code * volts_per_code * 1000
                rms_mv  = rms_code  * volts_per_code * 1000
                # Peak activity is deviation from the same mean used for RMS; absolute
                # biased ADC codes would falsely include the A1 reference voltage.
                peak_code = max(abs(sample - mean_code) for sample in samples)
                peak_mv = peak_code * volts_per_code * 1000
                clipped = mn <= NEGATIVE_CLIP or mx >= POSITIVE_CLIP
                utilisation = max(abs(mn), abs(mx)) / 32768.0
                # A short median window removes isolated capacitive/contact spikes;
                # the EMA then steadies ordinary readings. During overload the
                # live value must never freeze at the last good block: stream the
                # newly acquired saturated block immediately, then restart smoothing
                # from it. A clipped result is a lower bound, not an exact field.
                if clipped:
                    rms_ema = rms_mv
                    rms_disp = rms_mv
                else:
                    rms_window.append(rms_mv)
                    rms_filtered = statistics.median(rms_window)
                    rms_ema = (rms_filtered if rms_ema is None else
                               EF_EMA_ALPHA * rms_filtered + (1 - EF_EMA_ALPHA) * rms_ema)
                    rms_disp = rms_ema

                # ── AUTO-RANGING (identical policy to es2.py) ──
                if clipped:
                    low_signal_count = 0
                    if gain_index < len(GAINS) - 1:
                        gain_index += 1; status = "CLIPPED — RANGE LOWERED"
                    else:
                        status = "SIGNAL TOO STRONG — MOVE PROBE AWAY"
                elif utilisation > HIGH_UTILISATION:
                    low_signal_count = 0
                    if gain_index < len(GAINS) - 1:
                        gain_index += 1; status = "STRONG FIELD — RANGE LOWERED"
                    else:
                        status = "VERY HIGH FIELD"
                elif utilisation < LOW_UTILISATION and gain_index > 0:
                    low_signal_count += 1
                    if low_signal_count >= LOW_BLOCKS_TO_RAISE_GAIN:
                        gain_index -= 1; low_signal_count = 0; status = "WEAK FIELD — SENSITIVITY RAISED"
                    else:
                        status = "STABLE"
                else:
                    low_signal_count = 0; status = "STABLE"

                # ── startup baseline (relative reference), then relative index ──
                if not calibrated:
                    if not clipped:
                        baseline_acc.append(rms_mv)
                    if time.time() - t_start >= EF_BASELINE_SECS and baseline_acc:
                        baseline_mv = statistics.median(baseline_acc)
                        if baseline_mv <= 0: baseline_mv = 1e-6
                        calibrated = True
                        spread = statistics.pstdev(baseline_acc) if len(baseline_acc) > 1 else 0.0
                        warning = (
                            "baseline is unstable; relative index is untrusted"
                            if spread > max(baseline_mv * 0.5, 0.05) else
                            "baseline is extremely low; relative index is untrusted"
                            if baseline_mv < 0.001 else None
                        )
                        with efield_lock:
                            reason = efield_data["last_calibration_reason"]
                            efield_data["baseline_history"].append({
                                "t": time.time(), "baseline_mv": baseline_mv,
                                "spread_mv": spread,
                                "reason": reason,
                            })
                            efield_data["warning"] = warning
                        ARCHIVE.put("calibration", {
                            "sensor":"efield", "active":warning is None,
                            "payload":{
                                "baseline_mv":baseline_mv, "spread_mv":spread,
                                "reason":reason, "warning":warning,
                                "method":"median of unclipped startup blocks",
                            },
                        })
                    status_ui = "CALIBRATING BASELINE"
                else:
                    status_ui = status

                if calibrated:
                    ratio = rms_disp / baseline_mv if baseline_mv else 0.0
                    if   clipped:      level = "OVER"
                    elif ratio < 3.0:  level = "LOW"
                    elif ratio < 10.0: level = "MID"
                    else:              level = "HIGH"
                    rel = (ratio - 1.0) / (EF_REL_FULL_RATIO - 1.0) * 100.0
                    rel = max(0.0, min(100.0, rel))     # relative index, 0-100%
                else:
                    ratio = 0.0; level = "—"; rel = 0.0

                block_at = time.time()
                field_v_m = (_ef_calibrated_v_per_m(rms_disp, baseline_mv)
                             if calibrated else 0.0)
                peak_v_m = (_ef_calibrated_v_per_m(peak_mv, baseline_mv)
                            if calibrated else 0.0)
                # The displayed field is explicitly relative to this learned
                # environmental reference, so its calibrated baseline is zero.
                baseline_v_m = 0.0
                with efield_lock:
                    efield_data.update({"rms_mv":rms_disp,"mean_mv":mean_mv,"peak_mv":peak_mv,
                                        "field_v_m":field_v_m,"peak_v_m":peak_v_m,
                                        "baseline_v_m":baseline_v_m,
                                        "baseline_mv":baseline_mv,"rel_index":rel,"ratio":ratio,
                                        "level":level,"gain":gain,"min_code":mn,"max_code":mx,
                                        "utilisation":utilisation * 100.0,"clipped":clipped,
                                        "status":status_ui,"last_rx":block_at,
                                        "error":None,"calibrated":calibrated})
                    efield_data["history"].append(field_v_m)
                    efield_data["rel_history"].append(rel)
                    if rms_disp < efield_data["min_rms"]: efield_data["min_rms"] = rms_disp
                    if rms_disp > efield_data["max_rms"]: efield_data["max_rms"] = rms_disp
                    block_warning = efield_data["warning"]
                # One row per acquired block (SAMPLES_PER_BLOCK samples at ADS_DATA_RATE),
                # logged from the read loop rather than by the 3 s archive snapshot.
                # `block_warning` is read under the lock above, not re-read here.
                CSV_LOG.log_efield(
                    block_at, rms_disp, peak_mv, baseline_mv, ratio, rel,
                    gain, utilisation * 100.0, clipped, calibrated,
                    (not clipped) and calibrated and not block_warning,
                    note=block_warning,
                )

                STOP_EVENT.wait(0.15)
        except Exception as e:
            with efield_lock:
                efield_data["error"] = f"Source 2: {e}"
                efield_data["calibrated"] = False
            LOG.exception('Channel 2 worker error')
        finally:
            if i2c is not None and hasattr(i2c, "deinit"):
                try:
                    i2c.deinit()
                except Exception:
                    LOG.exception('Channel 2 bus close failed')
        STOP_EVENT.wait(2)

# ── tinySA Ultra spectrum reader ──────────────────────────────────────────────
class TinySAError(RuntimeError):
    pass


class TinySAProtocolError(TinySAError):
    pass


def _band_of(hz):
    """Return a conservative allocation hint, never a transmitter identification."""
    for lo, hi, name in BAND_PLAN:
        if lo <= hz < hi:
            return f"Possible band — {name}"
    return "—"

def _freq_label(hz):
    if hz >= 1e9:  return f"{hz/1e9:.3f} GHz"
    if hz >= 1e6:  return f"{hz/1e6:.3f} MHz"
    if hz >= 1e3:  return f"{hz/1e3:.1f} kHz"
    return f"{hz:.0f} Hz"

def _span_label(start_hz, stop_hz):
    return f"{_freq_label(start_hz)} – {_freq_label(stop_hz)}"

def _tsa_find_ports():
    """Rank serial candidates; identity is still verified after opening."""
    from serial.tools import list_ports
    override = os.environ.get("STUDIO_TINYSA_PORT", "").strip()
    if override:
        return [override]
    ranked = []
    for p in list_ports.comports():
        descriptor = " ".join(
            str(v or "") for v in (p.description, p.manufacturer, p.product, p.hwid)
        ).lower()
        score = 0
        if p.vid == TINYSA_VID and p.pid == TINYSA_PID:
            score += 10
        if "tinysa" in descriptor:
            score += 20
        if score:
            ranked.append((score, p.device))
    ranked.sort(reverse=True)
    return [device for _score, device in ranked]

def _tsa_read_until_prompt(tsa, timeout):
    """Read a complete shell response or raise; a timeout is never a partial success."""
    out = bytearray()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline and not STOP_EVENT.is_set():
        chunk = tsa.read(4096)
        if chunk:
            out.extend(chunk)
            if bytes(out).rstrip().endswith(TSA_PROMPT):
                return bytes(out)
            if len(out) > 4_000_000:
                raise TinySAProtocolError("TinySA response exceeded the 4 MB safety limit")
    raise TimeoutError(
        f"TinySA prompt was not received in {timeout:.1f}s; received {len(out)} bytes"
    )

def _tsa_cmd(tsa, cmd, timeout=6.0):
    if any(c in cmd for c in "\r\n"):
        raise ValueError("TinySA commands must be one line")
    tsa.reset_input_buffer()
    tsa.write((cmd + "\r").encode("ascii"))
    tsa.flush()
    raw = _tsa_read_until_prompt(tsa, timeout)
    text = raw.decode("utf-8", errors="replace")
    low = text.lower()
    if any(marker in low for marker in ("unknown command", "command error", "invalid command")):
        raise TinySAProtocolError(f"TinySA rejected command {cmd!r}: {text[:200]!r}")
    return text

def _tsa_reply_lines(text, cmd):
    """Strip the echoed command and the prompt, leaving the actual reply."""
    out = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s == cmd or s.startswith("ch>"):
            continue
        out.append(s)
    return out


def _help_advertises_command(help_text, command_name):
    """Best-effort help lookup across table, comma-list and prose formats."""
    return re.search(
        rf"(?<![A-Za-z0-9_]){re.escape(command_name)}(?![A-Za-z0-9_])",
        help_text,
        flags=re.IGNORECASE,
    ) is not None


def parse_text_scan(response):
    """Parse TinySA two- or three-column text output with finite-value checks."""
    freqs, levels = [], []
    for line_number, line in enumerate(response.splitlines(), 1):
        parts = line.strip().split()
        if len(parts) < 2:
            continue
        try:
            frequency = float(parts[0])
            level = float(parts[1])
        except ValueError:
            continue
        if not math.isfinite(frequency):
            raise TinySAProtocolError(f"non-finite frequency on line {line_number}")
        if not math.isfinite(level):
            raise TinySAProtocolError(f"non-finite level on line {line_number}")
        freqs.append(frequency)
        levels.append(level)
    if not freqs:
        raise TinySAProtocolError(
            f"scan returned no parseable points: {response[:240].replace(chr(10), ' | ')}"
        )
    return freqs, levels


def validate_sweep(freqs, levels, start_hz, stop_hz, points):
    """Reject truncated, reordered or silently clamped TinySA sweeps."""
    if not (2 <= int(points) <= 290):
        raise ValueError("TinySA points must be between 2 and 290")
    if start_hz < 0 or stop_hz <= start_hz:
        raise ValueError("TinySA range must have 0 <= start < stop")
    if len(freqs) != len(levels):
        raise TinySAProtocolError("frequency and level array lengths differ")
    if len(freqs) != points:
        raise TinySAProtocolError(
            f"incomplete TinySA sweep: requested {points}, received {len(freqs)}"
        )
    if any(right <= left for left, right in zip(freqs, freqs[1:])):
        raise TinySAProtocolError("TinySA frequencies are not strictly increasing")
    expected_bin = (stop_hz - start_hz) / max(points - 1, 1)
    tolerance = max(1_000.0, expected_bin * 2.0)
    if abs(freqs[0] - start_hz) > tolerance:
        raise TinySAProtocolError(
            f"returned start {freqs[0]:.0f} Hz does not match requested {start_hz} Hz"
        )
    if abs(freqs[-1] - stop_hz) > tolerance:
        raise TinySAProtocolError(
            f"returned stop {freqs[-1]:.0f} Hz does not match requested {stop_hz} Hz"
        )
    warnings = []
    if max(levels) > 10:
        warnings.append("implausibly high RF level; verify parser, units and analyser state")
    if min(levels) < -180:
        warnings.append("implausibly low RF level; verify parser, units and analyser state")
    return warnings


def _tsa_scan(tsa, start_hz, stop_hz, points, timeout=TSA_SCAN_TIMEOUT):
    """Validated text sweep -> frequencies, levels, raw response, warnings."""
    command = f"scan {int(start_hz)} {int(stop_hz)} {int(points)} 3"
    raw_text = _tsa_cmd(tsa, command, timeout)
    freqs, levels = parse_text_scan(raw_text)
    warnings = validate_sweep(freqs, levels, start_hz, stop_hz, points)
    return freqs, levels, raw_text, warnings

def _tsa_peaks(freqs, levels, floor, count=TSA_PEAK_COUNT, min_prom=TSA_PEAK_MIN_PROM):
    """Local maxima using a rolling-median floor and conservative separation."""
    n = len(levels)
    if n < 3:
        return []
    radius = min(8, max(2, n // 20))
    local_floors = []
    for i in range(n):
        neighbours = levels[max(0, i-radius):i] + levels[i+1:min(n, i+radius+1)]
        local_floors.append(statistics.median(neighbours or [levels[i]]))
    cands = [
        i for i in range(1, n - 1)
        if levels[i] >= levels[i - 1] and levels[i] > levels[i + 1]
        and (levels[i] - local_floors[i]) >= min_prom
    ]
    cands.sort(key=lambda i: levels[i], reverse=True)
    min_bins = max(2, n // 100)
    picked = []
    for i in cands:
        if all(abs(i - j) >= min_bins for j in picked):
            picked.append(i)
        if len(picked) >= count:
            break
    return [
        {
            "freq": freqs[i],
            "level": levels[i],
            "local_floor": local_floors[i],
            "prominence": levels[i] - local_floors[i],
            "bin_index": i,
            "band": _band_of(freqs[i]),
        }
        for i in picked
    ]

def tinysa_reader():
    """Sweep the tinySA Ultra continuously and publish into spectrum_data.

    No synthetic data: if the device is absent or errors, the dashboard says so."""
    try:
        import serial  # noqa: F401  (probe only — the class is used below)
    except Exception as e:
        with spectrum_lock:
            spectrum_data["error"] = f"pyserial missing ({e}) — pip install pyserial"
            spectrum_data["status"] = "library missing"
        return
    import serial
    retry_delay = 2.0
    last_logged_error = None
    last_error_log_at = 0.0
    while not STOP_EVENT.is_set():
        tsa = None
        try:
            candidates = _tsa_find_ports()
            if not candidates:
                with spectrum_lock:
                    spectrum_data.update({"error":"no TinySA serial candidate found",
                                          "status":"searching…", "port":"—"})
                STOP_EVENT.wait(3)
                continue
            verified = None
            verify_errors = []
            version_text = info_text = help_text = ""
            for port in candidates:
                candidate = None
                try:
                    candidate = serial.Serial(
                        port, TSA_BAUD, timeout=0.25, write_timeout=2
                    )
                    STOP_EVENT.wait(0.35)
                    candidate.reset_input_buffer()
                    version_text = "\n".join(
                        _tsa_reply_lines(_tsa_cmd(candidate, "version", 5.0), "version")
                    )
                    info_text = "\n".join(
                        _tsa_reply_lines(_tsa_cmd(candidate, "info", 5.0), "info")
                    )
                    help_text = "\n".join(
                        _tsa_reply_lines(_tsa_cmd(candidate, "help", 7.0), "help")
                    )
                    identity = " ".join((version_text, info_text, help_text)).lower()
                    if "tinysa" not in identity:
                        raise TinySAProtocolError(
                            "serial device answered but did not identify as TinySA"
                        )
                    verified = (candidate, port)
                    break
                except Exception as exc:
                    verify_errors.append(f"{port}: {exc}")
                    try:
                        if candidate is not None:
                            candidate.close()
                    except Exception:
                        LOG.debug("Candidate serial close failed", exc_info=True)
            if verified is None:
                raise TinySAError(
                    "no verified TinySA found: " + "; ".join(verify_errors)
                )
            tsa, port = verified
            # The reply can carry leftover sweep lines; the identity is the line naming the device.
            _lines = [line.strip() for line in version_text.splitlines() if line.strip()]
            dev = next((line for line in _lines if "tinysa" in line.lower() or "version" in line.lower()), _lines[0] if _lines else "TinySA")[:80]

            scan_advertised = _help_advertises_command(help_text, "scan")
            ultra_advertised = _help_advertises_command(help_text, "ultra")
            capability_note = (
                "help advertises text scan"
                if scan_advertised
                else "help does not list scan; validating capability with an actual strict text sweep"
            )
            if not scan_advertised:
                LOG.info(
                    "TinySA %s help did not advertise scan; proceeding to a strict "
                    "text-sweep capability test",
                    port,
                )

            loff = "—"
            loff_warning = None
            try:
                lines = _tsa_reply_lines(_tsa_cmd(tsa, "leveloffset", 5.0), "leveloffset")
                if lines:
                    loff = " / ".join(lines)[:48]
                    # A non-zero device offset shifts every level the analyser reports; say so once.
                    for token in re.findall(r"-?\d+(?:\.\d+)?", " ".join(lines)):
                        if abs(float(token)) >= 0.5:
                            loff_warning = f"tinySA leveloffset is {token} dB; reported levels are shifted by that amount"
                            LOG.warning("TinySA %s", loff_warning)
                            ARCHIVE.put("event", {"severity": "WARNING", "source": "tinysa", "message": loff_warning})
                            break
            except Exception as exc:
                loff = f"unavailable: {exc}"
                LOG.warning("TinySA leveloffset query failed: %s", exc)

            with spectrum_lock:
                start_hz = spectrum_data["span_start"]
                stop_hz  = spectrum_data["span_stop"]
                pts      = spectrum_data["points"]
                spectrum_data.update({
                    "device":dev, "device_info":info_text[:240] or "—",
                    "help_summary":(
                        f"{capability_note}; "
                        f"ultra command {'advertised' if ultra_advertised else 'not advertised'} · "
                        f"{' '.join(help_text.split())[:180] or 'empty help response'}"
                    ),
                    "leveloffset":loff, "port":port,
                    "leveloffset_warning":loff_warning,
                    "error":None,
                    "status":"serial connected; identity verified; testing text sweep",
                })

            ultra_on = False
            ultra_checked = False
            maxhold = None

            # Prove the baseline text transport on a small, sub-800 MHz span before
            # any optional Ultra-mode command can obscure whether `scan` itself works.
            probe_freqs, _probe_levels, _probe_raw, probe_warnings = _tsa_scan(
                tsa,
                TSA_PROBE_START,
                TSA_PROBE_STOP,
                TSA_PROBE_POINTS,
                timeout=TSA_PROBE_TIMEOUT,
            )
            retry_delay = 2.0
            last_logged_error = None
            ARCHIVE.put("event", {
                "severity":"INFO",
                "source":"tinysa",
                "message":(
                    "text scan capability verified "
                    f"({len(probe_freqs)} points, "
                    f"{probe_freqs[0]:.0f}..{probe_freqs[-1]:.0f} Hz"
                    f"{'; ' + '; '.join(probe_warnings) if probe_warnings else ''})"
                ),
            })
            with spectrum_lock:
                spectrum_data["status"] = (
                    "text scan verified; beginning requested sweep"
                )

            focus_bands = []
            focus_idx = -1
            while not STOP_EVENT.is_set():
                # ── UI commands (range / resolution / max-hold reset) ──
                with tinysa_cmd_lock:
                    new_range  = tinysa_cmd["range"];  tinysa_cmd["range"]  = None
                    new_points = tinysa_cmd["points"]; tinysa_cmd["points"] = None
                    new_preset = tinysa_cmd["preset"]; tinysa_cmd["preset"] = None
                    clear_hold = tinysa_cmd["reset_hold"]; tinysa_cmd["reset_hold"] = False
                    paused = tinysa_cmd["paused"]
                    new_bands = tinysa_cmd["bands"]; tinysa_cmd["bands"] = None
                if new_bands is not None:
                    focus_bands = [(int(a), int(b)) for a, b in new_bands if int(b) > int(a)]
                    focus_idx = -1
                    maxhold = None
                    with spectrum_lock:
                        spectrum_data["bands"] = {}
                        spectrum_data["focus"] = [list(b) for b in focus_bands]
                        spectrum_data["waterfall"].clear()
                        spectrum_data["waterfall_times"].clear()
                if focus_bands:
                    focus_idx = (focus_idx + 1) % len(focus_bands)
                    start_hz, stop_hz = focus_bands[focus_idx]
                    if maxhold is not None and focus_idx != 0:
                        maxhold = None   # max hold is meaningless across different bands
                if new_range:
                    validate_sweep(
                        [float(new_range[0]), float(new_range[1])],
                        [-100.0, -100.0],
                        new_range[0], new_range[1], 2,
                    )
                    start_hz, stop_hz = new_range
                    maxhold = None
                    with spectrum_lock:
                        spectrum_data["waterfall"].clear()
                        spectrum_data["waterfall_times"].clear()
                        spectrum_data["span_start"] = start_hz
                        spectrum_data["span_stop"]  = stop_hz
                        if new_preset:
                            spectrum_data["preset"] = new_preset
                if new_points:
                    if not 2 <= int(new_points) <= 290:
                        raise ValueError("requested TinySA point count must be 2..290")
                    pts = new_points
                    maxhold = None
                    with spectrum_lock:
                        spectrum_data["waterfall"].clear()
                        spectrum_data["waterfall_times"].clear()
                        spectrum_data["points"] = pts
                if clear_hold:
                    maxhold = None
                if paused:
                    with spectrum_lock:
                        spectrum_data["status"] = "paused by operator"
                    STOP_EVENT.wait(0.5)
                    continue

                # Above ~800 MHz the Ultra unlock has to be on or the sweep is clamped.
                # As a special command, it is sent only when advertised by device help.
                # Whether the requested range really worked is still proven by the
                # returned scan endpoints below.
                need_ultra = stop_hz > TSA_ULTRA_ABOVE
                if need_ultra and not ultra_checked:
                    ultra_checked = True
                    if ultra_advertised:
                        _tsa_cmd(tsa, "ultra on", 5.0)
                        ultra_on = True
                    else:
                        LOG.info(
                            "TinySA help did not advertise the optional ultra command; "
                            "attempting the requested span without it and validating endpoints"
                        )
                    with spectrum_lock:
                        spectrum_data["ultra"] = ultra_on

                started_at = time.time()
                freqs, levels, raw_text, warnings = _tsa_scan(
                    tsa, start_hz, stop_hz, pts
                )
                completed_at = time.time()
                dt = completed_at - started_at
                # A complete, range-correct scan is authoritative capability evidence.
                retry_delay = 2.0
                last_logged_error = None

                floor = statistics.median(levels)  # broad summary only
                # The tinySA's first bin at the very bottom of a wide sweep carries LO / DC
                # leakage (~0 dBm at 100 kHz while everything else sits at -80 dBm). It is kept
                # in the trace but never reported as the strongest signal.
                cand = [i for i in range(len(levels))
                        if not (i == 0 and freqs[i] < 200e3 and len(levels) > 4
                                and levels[i] > floor + 40 and levels[i] > levels[1] + 25)]
                pk_i = max(cand or range(len(levels)), key=lambda i: levels[i])
                pk_level = levels[pk_i]; pk_freq = freqs[pk_i]
                peaks = _tsa_peaks(freqs, levels, floor)

                sane = floor <= TSA_SANE_MAX_DBM
                if not sane:
                    # +20 to +25 dBm across the whole span is the tinySA Ultra with no antenna or a
                    # stale `leveloffset`; anything else that high is a parser or unit problem.
                    if 15.0 <= floor <= 30.0:
                        warnings.append(
                            f"median {floor:+.1f} dBm across the span: no antenna connected or a stale "
                            "leveloffset on the tinySA (send `leveloffset 0`, reconnect the antenna)"
                        )
                    else:
                        warnings.append(
                            f"suspicious median {floor:+.1f} dBm; parser and analyser state require verification"
                        )
                    note = warnings[-1]
                else:
                    note = f"broad estimated noise floor {floor:+.1f} unit"
                trusted = sane and not warnings

                # Untrusted sweeps remain visible and archived, but never contaminate
                # max hold, waterfall, peak trend or MTDI health.
                if trusted:
                    if maxhold is None or len(maxhold) != len(levels):
                        maxhold = list(levels)
                    else:
                        maxhold = [max(a, b) for a, b in zip(maxhold, levels)]

                with spectrum_lock:
                    spectrum_data.update({
                        "freqs":list(freqs), "levels":list(levels),
                        "maxhold":list(maxhold or []),
                        "peaks":peaks, "floor":floor,
                        "peak_level":pk_level, "peak_freq":pk_freq,
                        "span_start":start_hz, "span_stop":stop_hz, "points":pts,
                        "sweep_s":dt, "sweeps":spectrum_data["sweeps"] + 1,
                        "level_sane":sane, "trusted":trusted,
                        "warnings":list(warnings), "level_note":note,
                        "status":"sweeping", "error":None,
                        "last_rx":completed_at, "present":True,
                    })
                    if trusted:
                        spectrum_data["waterfall"].append(list(levels))
                        spectrum_data["waterfall_times"].append(completed_at)
                        spectrum_data["peak_history"].append(pk_level)
                    active_profile = spectrum_data["preset"]
                    if focus_bands:
                        key = f"{start_hz}-{stop_hz}"
                        band = spectrum_data.setdefault("bands", {}).get(key) or {
                            "start": start_hz, "stop": stop_hz, "freqs": [], "levels": [], "prev": [],
                            "delta": [], "waterfall": deque(maxlen=48), "times": deque(maxlen=48),
                            "sweeps": 0, "last_rx": None, "sweep_s": None, "peak_level": None, "peak_freq": None,
                        }
                        prev = band["levels"] if len(band["levels"]) == len(levels) else []
                        band.update({
                            "freqs": list(freqs), "levels": list(levels), "prev": list(prev),
                            "delta": [a - b for a, b in zip(levels, prev)] if prev else [],
                            "sweeps": band["sweeps"] + 1, "last_rx": completed_at, "sweep_s": dt,
                            "peak_level": pk_level, "peak_freq": pk_freq, "trusted": trusted, "floor": floor,
                        })
                        if trusted:
                            band["waterfall"].append(list(levels)); band["times"].append(completed_at)
                        spectrum_data["bands"][key] = band

                # One row per completed sweep. The full per-bin arrays stay in
                # SQLite (rf_sweeps.frequencies_json / levels_json); export them
                # flattened with export_rf_csv_bytes() when per-bin data is needed.
                CSV_LOG.log_rf(
                    completed_at, start_hz, stop_hz, len(freqs), dt,
                    pk_freq, pk_level, floor, trusted,
                    note="; ".join(warnings) if warnings else None,
                )
                bin_width = (freqs[-1] - freqs[0]) / max(len(freqs) - 1, 1)
                ARCHIVE.put("rf", {
                    "started_at":started_at, "completed_at":completed_at,
                    "duration_s":dt, "profile":active_profile,
                    "start_hz":start_hz, "stop_hz":stop_hz,
                    "requested_points":pts, "repeat":3, "bin_width_hz":bin_width,
                    "frequencies":list(freqs), "levels":list(levels),
                    "peaks":peaks, "warnings":list(warnings), "trusted":trusted,
                    "firmware":version_text, "port":port,
                    "transport":"serial-text-scan", "raw_response":raw_text,
                })

                if trusted:
                    with rf_archive_lock:
                        band = _band_of(pk_freq)
                        rf_archive.append({"t":time.time(), "freq":pk_freq, "level":pk_level, "band":band})
                        rf_stats["count"] += 1
                        rf_stats["sum"]   += pk_level
                        rf_stats["min"] = min(rf_stats["min"], pk_level)
                        rf_stats["max"] = max(rf_stats["max"], pk_level)
                        if pk_level > rf_stats["strongest"]["level"]:
                            rf_stats["strongest"] = {"freq":pk_freq, "level":pk_level,
                                                     "band":band, "t":time.time()}

                STOP_EVENT.wait(TSA_SWEEP_GAP)
        except Exception as e:
            error_signature = f"{type(e).__name__}: {e}"
            now_mono = time.monotonic()
            should_log_traceback = (
                error_signature != last_logged_error
                or now_mono - last_error_log_at >= 60.0
            )
            with spectrum_lock:
                spectrum_data["error"] = f"Source 3: {e}"
                spectrum_data["status"] = (
                    f"link/capability test failed; retry in {retry_delay:.0f}s"
                )
                spectrum_data["trusted"] = False
            if should_log_traceback:
                ARCHIVE.put("event", {
                    "severity":"ERROR", "source":"tinysa",
                    "message":error_signature[:1000],
                })
                LOG.exception("TinySA worker error")
                last_logged_error = error_signature
                last_error_log_at = now_mono
            else:
                LOG.warning(
                    "TinySA still unavailable (%s); retrying in %.0fs",
                    error_signature, retry_delay,
                )
        finally:
            if tsa:
                try:
                    tsa.close()
                except Exception:
                    LOG.exception("TinySA serial close failed")
        STOP_EVENT.wait(retry_delay)
        retry_delay = min(30.0, retry_delay * 1.8)


def _local_ip():
    """Resolve the address selected by the default route, then safe interface fallbacks."""
    def usable(address):
        try:
            value = ipaddress.ip_address(address)
            return not (
                value.is_loopback
                or value.is_unspecified
                or value.is_link_local
                or value.is_multicast
            )
        except ValueError:
            return False

    # UDP connect selects a route but sends no packet. This avoids choosing an
    # unplugged Ethernet, Docker or link-local interface ahead of active Wi-Fi.
    route_socket = None
    try:
        route_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        route_socket.connect(("192.0.2.1", 9))
        routed_address = route_socket.getsockname()[0]
        if usable(routed_address):
            return routed_address
    except OSError:
        LOG.debug("Default-route address lookup failed", exc_info=True)
    finally:
        if route_socket is not None:
            route_socket.close()

    candidates = []
    try:
        for _idx, name in socket.if_nameindex():
            if name == "lo":
                continue
            interface_socket = None
            try:
                import fcntl
                import struct
                interface_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                packed = fcntl.ioctl(
                    interface_socket.fileno(),
                    0x8915,
                    struct.pack("256s", name[:15].encode()),
                )
                address = socket.inet_ntoa(packed[20:24])
                if usable(address):
                    address_value = ipaddress.ip_address(address)
                    hardware_name = name.lower()
                    score = 100 if address_value.is_private else 20
                    if hardware_name.startswith(("wlan", "wl", "eth", "en")):
                        score += 30
                    if hardware_name.startswith(("docker", "veth", "br-", "virbr")):
                        score -= 80
                    candidates.append((score, address))
            except Exception:
                continue
            finally:
                if interface_socket is not None:
                    interface_socket.close()
    except Exception:
        LOG.debug("Interface address lookup failed", exc_info=True)
    if candidates:
        candidates.sort(reverse=True)
        return candidates[0][1]
    try:
        hostname_address = socket.gethostbyname(socket.gethostname())
        if usable(hostname_address):
            return hostname_address
    except Exception:
        LOG.debug("Hostname address lookup failed", exc_info=True)
    return "127.0.0.1"

# ── WiFi / Bluetooth / LAN discovery ──────────────────────────────────────────
# Wi-Fi and Bluetooth discovery use their host computer protocol radios. Scan mode is
# disclosed below; neither source is attributed to TinySA.
WIFI_SCAN_PERIOD = float(os.environ.get("STUDIO_WIFI_SCAN_PERIOD", "20"))
# BLE discovery shares this host's combo radio with Wi Fi. Eight seconds in every twenty
# (40 percent duty) stalled the link; four seconds in every sixty keeps discovery
# meaningful while leaving the antenna to Wi Fi most of the time.
BT_SCAN_SECONDS  = float(os.environ.get("STUDIO_BT_SCAN_SECONDS", "4"))
BT_SCAN_PERIOD   = float(os.environ.get("STUDIO_BT_SCAN_PERIOD", "60"))
LAN_SCAN_PERIOD  = 20.0

# Bluetooth SIG company identifiers — only the handful that show up on a bench, so a
# nameless advertiser can still be attributed to a vendor.
BT_COMPANY = {0x004C:"Apple", 0x0006:"Microsoft", 0x0075:"Samsung", 0x00E0:"Google",
              0x0087:"Garmin", 0x000F:"Broadcom", 0x0001:"Ericsson", 0x012D:"Sony",
              0x0157:"Huawei", 0x038F:"Xiaomi", 0x0499:"Ruuvi", 0x0059:"Nordic",
              0x02E5:"Espressif", 0x0171:"Amazon", 0x0224:"Fitbit", 0x001D:"Qualcomm",
              0x009E:"Bose", 0x0057:"Harman (JBL)", 0x00C4:"LG", 0x0131:"Cypress",
              0x0310:"SGL", 0x03DA:"Oura", 0x0154:"Polar", 0x0110:"Nike", 0x0397:"Sonos",
              0x0822:"adafruit", 0x05A7:"Sonos", 0x0104:"Tesla", 0x0141:"Anhui Huami (Amazfit)",
              0x0201:"Meta", 0x01DA:"Logitech", 0x000A:"Cambridge Silicon Radio", 0x000D:"Texas Instruments",
              0x004F:"Withings", 0x0301:"Oppo", 0x0078:"Nike", 0x03C2:"Realme", 0x0BAA:"Nothing"}
# Apple advertisement subtypes (Continuity protocol) reveal what kind of device is talking.
APPLE_ADV_TYPES = {0x02: "iBeacon", 0x05: "AirDrop", 0x07: "AirPods or headphones", 0x09: "AirPlay target",
                   0x0A: "AirPlay source", 0x0B: "Watch or magic switch", 0x0C: "Handoff (iPhone or Mac)",
                   0x0D: "Wi Fi settings", 0x0E: "Hotspot", 0x0F: "Wi Fi join", 0x10: "Nearby (iPhone, iPad or Mac)",
                   0x12: "Find My", 0x0F: "Wi Fi join"}
# Common MAC prefixes (OUI) for the LAN table when reverse lookup gives nothing.
MAC_VENDORS = {"88:A2:9E": "host computer", "B8:27:EB": "host computer", "DC:A6:32": "host computer", "E4:5F:01": "host computer", "D8:3A:DD": "host computer", "2C:CF:67": "host computer",
               "C8:EA:F8": "Huawei (router)", "F4:F5:D8": "Google", "3C:5A:B4": "Google", "94:65:2D": "OnePlus", "A4:83:E7": "Apple", "F0:18:98": "Apple", "3C:22:FB": "Apple", "8C:85:90": "Apple", "DC:A9:04": "Apple", "F8:FF:C2": "Apple", "14:7D:DA": "Apple", "BC:D0:74": "Apple", "A8:66:7F": "Apple", "48:A9:1C": "Apple", "9C:F4:8E": "Apple", "D0:03:DF": "Samsung", "8C:F5:A3": "Samsung", "50:32:75": "Samsung", "34:BE:00": "Samsung", "F4:7B:5E": "Samsung",
               "FC:AA:14": "Gigabyte", "00:1A:79": "Ubiquiti", "24:5A:4C": "Ubiquiti", "74:AC:B9": "Ubiquiti", "AC:84:C6": "TP Link", "50:C7:BF": "TP Link", "C0:06:C3": "TP Link", "B0:BE:76": "TP Link", "1C:61:B4": "TP Link", "E8:48:B8": "TP Link", "18:FE:34": "Espressif", "24:6F:28": "Espressif", "A4:CF:12": "Espressif", "3C:71:BF": "Espressif", "84:F3:EB": "Espressif", "B4:E6:2D": "Espressif",
               "00:17:88": "Philips Hue", "EC:B5:FA": "Philips Hue", "44:65:0D": "Amazon", "A0:02:DC": "Amazon", "FC:65:DE": "Amazon", "40:B4:CD": "Amazon", "F0:F0:A4": "Amazon", "00:0C:29": "VMware", "00:50:56": "VMware", "3C:E9:F7": "Intel", "8C:8D:28": "Intel", "AC:12:03": "Intel", "48:51:C5": "Intel", "00:1E:C2": "Apple", "B0:4A:39": "Beijing Roborock", "58:D9:D5": "Tenda", "C8:3A:35": "Tenda", "F0:9F:C2": "Ubiquiti", "78:8A:20": "Ubiquiti", "28:6C:07": "Xiaomi", "64:09:80": "Xiaomi", "F8:A2:D6": "Liteon", "D4:6E:0E": "TP Link", "DC:56:E7": "Apple", "E0:2B:96": "Apple", "00:04:4B": "Nvidia", "48:B0:2D": "Nvidia"}


def mac_vendor(mac):
    return MAC_VENDORS.get(str(mac).upper()[:8], "")


def resolve_host_names(ips):
    """mDNS and reverse DNS names for LAN hosts; empty strings where nothing answers."""
    names = {ip: "" for ip in ips}
    if not ips:
        return names
    ok, out, _ = _run(["avahi-resolve", "-a"] + list(ips), timeout=6)
    if ok:
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0] in names:
                names[parts[0]] = parts[1].rstrip(".")
    for ip in ips:
        if names[ip]:
            continue
        try:
            names[ip] = socket.gethostbyaddr(ip)[0]
        except (socket.herror, socket.gaierror, OSError):
            pass
    return names

wifi_lock = threading.RLock()
wifi_data = {"networks":[], "iface":"—", "backend":"—", "connected":None,
             "scan_mode":"cached result read", "paused":False, "scanning":False, "scan_started":None,
             "error":'Waiting for Channel 5 discovery', "last_rx":None, "scans":0}

bt_lock = threading.RLock()
bt_data = {"devices":[], "adapter":"—", "backend":"—",
           "scan_mode":"active discovery", "paused":False, "scanning":False, "scan_started":None,
           "error":'Waiting for Channel 6 discovery', "last_rx":None, "scans":0}

lan_lock = threading.RLock()
lan_data = {"hosts":[], "gateway":"—", "self_ip":"—", "ssid":"—",
            "error":None, "last_rx":None}

ALLOW_ACTIVE_WIFI = os.environ.get(
    "STUDIO_ALLOW_ACTIVE_WIFI_DISCOVERY", ""
).lower() in {"1", "true", "yes"}
PAUSE_RADIOS_FOR_RF = os.environ.get(
    "STUDIO_PAUSE_RADIOS_FOR_RF", "true"
).lower() in {"1", "true", "yes"}


def _precision_rf_overlaps(low_hz, high_hz):
    if not PAUSE_RADIOS_FOR_RF:
        return False
    with spectrum_lock:
        if not spectrum_data["present"] or spectrum_data["error"]:
            return False
        start = spectrum_data["span_start"]
        stop = spectrum_data["span_stop"]
    return (stop - start) <= 250_000_000 and start < high_hz and stop > low_hz

def _run(cmd, timeout=25):
    """Run a command. Returns (ok, stdout, note). Never raises."""
    import subprocess
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if p.returncode != 0:
            # The first line of stderr is the useful part; fall back to the exit code
            # so the caller always gets something printable.
            stderr_lines = (p.stderr or "").strip().splitlines()
            note = stderr_lines[0][:80] if stderr_lines else f"exit {p.returncode}"
            return False, p.stdout or "", note
        return True, p.stdout or "", ""
    except FileNotFoundError:
        return False, "", f"{cmd[0]} not installed"
    except subprocess.TimeoutExpired:
        return False, "", f"{cmd[0]} timed out"
    except Exception as e:
        return False, "", f"{cmd[0]}: {e}"[:80]

def _nmcli_split(line):
    """Split one nmcli terse line on ':' while honouring backslash escapes.

    Terse output escapes the colons inside a BSSID as '\\:', so a plain split(':')
    shreds every MAC address into six empty-ish fields."""
    out, cur, esc = [], [], False
    for ch in line:
        if esc:
            cur.append(ch); esc = False
        elif ch == "\\":
            esc = True
        elif ch == ":":
            out.append("".join(cur)); cur = []
        else:
            cur.append(ch)
    out.append("".join(cur))
    return out

def _wifi_band(mhz):
    if mhz <= 0:            return "—"
    if mhz < 2500:          return "2.4 GHz"
    if mhz < 5900:          return "5 GHz"
    return "6 GHz"

def _signal_to_dbm(pct):
    """NetworkManager reports link quality 0-100, not power. Its own conversion is
    dBm = quality/2 - 100, so 100% ~ -50 dBm and 0% ~ -100 dBm. Shown as an estimate
    (with '≈') because it is a derived figure, unlike the tinySA's measured dBm."""
    return float(pct) / 2.0 - 100.0

def _parse_nmcli_wifi(text):
    """IN-USE:SSID:BSSID:CHAN:FREQ:SIGNAL:SECURITY:RATE -> list of dicts."""
    nets = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        f = _nmcli_split(line)
        if len(f) < 8:
            continue
        inuse, ssid, bssid, chan, freq, signal, sec, rate = f[:8]
        try:    mhz = int(str(freq).split()[0])
        except Exception: mhz = 0
        try:    sig = int(signal)
        except Exception: sig = 0
        nets.append({
            "ssid": ssid if ssid else "(hidden)",
            "bssid": bssid.upper(),
            "chan": chan,
            "mhz": mhz,
            "band": _wifi_band(mhz),
            "signal": sig,
            "dbm": _signal_to_dbm(sig),
            "sec": sec if sec else "OPEN",
            "rate": rate,
            "active": inuse.strip() == "*",
        })
    nets.sort(key=lambda n: n["signal"], reverse=True)
    return nets

def wifi_reader():
    """Read protocol-level Wi-Fi discovery through NetworkManager with scan disclosure."""
    while not STOP_EVENT.is_set():
        try:
            if _precision_rf_overlaps(2_400_000_000, 5_925_000_000) and ALLOW_ACTIVE_WIFI:
                with wifi_lock:
                    wifi_data.update({
                        "paused":True,
                        "scan_mode":'paused to reduce local CH 3 activity',
                        "error":None,
                    })
                STOP_EVENT.wait(WIFI_SCAN_PERIOD)
                continue
            wifi_data["_cycle"] = wifi_data.get("_cycle", 0) + 1
            # Cached results go stale; ask the driver for a fresh scan every third cycle
            # (about once a minute), which keeps the list current without starving Wi Fi.
            rescan = "yes" if (ALLOW_ACTIVE_WIFI or wifi_data["_cycle"] % 3 == 1) else "no"
            mode = (
                "OS scan requested; active/passive mode not verified"
                if ALLOW_ACTIVE_WIFI else "cached result read; no rescan requested"
            )
            with wifi_lock:
                wifi_data.update({"scanning":True, "scan_started":time.time()})
            try:
                ok, out, note = _run(["nmcli", "-t", "-f",
                                      "IN-USE,SSID,BSSID,CHAN,FREQ,SIGNAL,SECURITY,RATE",
                                      "dev", "wifi", "list", "--rescan", rescan], timeout=30)
            finally:
                with wifi_lock:
                    wifi_data["scanning"] = False
            if not ok:
                # Older images without NetworkManager still answer to iw/iwlist, but the
                # output is unstructured; say so plainly rather than half-parsing it.
                with wifi_lock:
                    wifi_data.update({"error": f"nmcli unavailable ({note})", "backend":"—"})
                STOP_EVENT.wait(WIFI_SCAN_PERIOD); continue
            nets = _parse_nmcli_wifi(out)
            seen, unique = set(), []
            for net in nets:
                key = net.get("bssid") or net.get("ssid")
                if key in seen:
                    continue
                seen.add(key)
                unique.append(net)
            nets = unique
            iface = "—"
            ok2, out2, _ = _run(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "dev"], timeout=10)
            if ok2:
                for line in out2.splitlines():
                    p = _nmcli_split(line)
                    if len(p) >= 2 and p[1] == "wifi":
                        iface = p[0]; break
            active = next((n for n in nets if n["active"]), None)
            with wifi_lock:
                wifi_data.update({"networks":nets, "iface":iface, "backend":"nmcli",
                                  "connected":active, "error":None,
                                  "scan_mode":mode, "paused":False,
                                  "last_rx":time.time(), "scans":wifi_data["scans"] + 1})
            ARCHIVE.put("wifi", {
                "t":time.time(), "mode":mode, "iface":iface, "records":nets
            })
        except Exception as e:
            with wifi_lock:
                wifi_data["error"] = f"Channel 5 scan: {e}"[:90]
            LOG.exception('Channel 5 discovery failed')
        wifi_scan_now.wait(WIFI_SCAN_PERIOD)
        wifi_scan_now.clear()

def _ble_scan_once(seconds):
    """BLE advertising sweep via bleak. Returns (devices, backend, error)."""
    import asyncio
    from bleak import BleakScanner
    async def go():
        return await BleakScanner.discover(timeout=seconds, return_adv=True)
    found = asyncio.run(go())
    devs = []
    for addr, (dev, adv) in found.items():
        vendor = "—"
        kind = "BLE"
        if adv.manufacturer_data:
            cid = next(iter(adv.manufacturer_data))
            vendor = BT_COMPANY.get(cid, f"ID 0x{cid:04X}")
            payload = adv.manufacturer_data.get(cid) or b""
            if cid == 0x004C and payload:
                kind = "Apple · " + APPLE_ADV_TYPES.get(payload[0], "device")
            elif cid == 0x0075:
                kind = "Samsung device"
            elif cid == 0x00E0:
                kind = "Google device"
        if adv.service_uuids:
            uuids = " ".join(adv.service_uuids).lower()
            if "fe9f" in uuids:
                kind = "Google Fast Pair"
            elif "180d" in uuids:
                kind = 'Heart rate source'
            elif "fd6f" in uuids:
                kind = "Exposure notification (phone)"
            elif "fea0" in uuids:
                kind = "Google Nest"
        name = adv.local_name or getattr(dev, "name", None)
        if not name:
            name = "(no name · " + (vendor if vendor != "—" else "unknown vendor") + ")"
        devs.append({
            "addr": str(addr).upper(),
            "name": name,
            "rssi": adv.rssi if adv.rssi is not None else -127,
            "vendor": vendor,
            "services": len(adv.service_uuids or []),
            "tx": adv.tx_power,
            "kind": kind,
        })
    devs.sort(key=lambda d: d["rssi"], reverse=True)
    return devs, "bleak (BLE)", None

def _btctl_scan_once(seconds):
    """Fallback: drive bluetoothctl. Gives names and addresses but no RSSI."""
    _run(["bluetoothctl", "--timeout", str(int(seconds)), "scan", "on"], timeout=seconds + 12)
    ok, out, note = _run(["bluetoothctl", "devices"], timeout=12)
    if not ok:
        return [], "—", f"bluetoothctl unavailable ({note})"
    devs = []
    for line in out.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) >= 2 and parts[0] == "Device":
            devs.append({"addr":parts[1].upper(), "name":(parts[2] if len(parts) > 2 else "(no name)"),
                         "rssi":None, "vendor":"—", "services":0, "tx":None, "kind":"BT"})
    return devs, "bluetoothctl (no RSSI)", None

def bt_reader():
    """Perform disclosed Bluetooth discovery; it never pairs or connects."""
    prefer_bleak = True
    while not STOP_EVENT.is_set():
        try:
            if _precision_rf_overlaps(2_400_000_000, 2_500_000_000):
                with bt_lock:
                    bt_data.update({
                        "paused":True,
                        "scan_mode":"paused during precision 2.4 GHz TinySA sweep",
                        "error":None,
                    })
                STOP_EVENT.wait(BT_SCAN_PERIOD)
                continue
            with bt_lock:
                bt_data.update({"scanning":True, "scan_started":time.time()})
            if prefer_bleak:
                try:
                    devs, backend, err = _ble_scan_once(BT_SCAN_SECONDS)
                except ImportError:
                    prefer_bleak = False
                    with bt_lock:
                        bt_data["error"] = ("bleak not installed — falling back to bluetoothctl "
                                            "(no RSSI).  pip install bleak")
                    continue
            else:
                devs, backend, err = _btctl_scan_once(BT_SCAN_SECONDS)
                with bt_lock:
                    bt_data["scanning"] = False
                if err:
                    # Don't let the fallback's error bury the fact that the good path
                    # (bleak, the only one that reports RSSI) is simply not installed.
                    err += "  ·  install bleak for BLE scanning with signal strength"
            with bt_lock:
                bt_data["scanning"] = False
            if err:
                with bt_lock:
                    bt_data.update({"error":err, "backend":"—"})
            else:
                adapter = "—"
                ok, out, _ = _run(["hciconfig"], timeout=8)
                if ok and out.strip():
                    adapter = out.strip().splitlines()[0].split(":")[0]
                with bt_lock:
                    bt_data.update({"devices":devs, "adapter":adapter, "backend":backend,
                                    "error":None, "last_rx":time.time(), "paused":False,
                                    "scan_mode":'active Channel 6 discovery',
                                    "scans":bt_data["scans"] + 1})
                ARCHIVE.put("bluetooth", {
                    "t":time.time(), "mode":'active Channel 6 discovery',
                    "adapter":adapter, "records":devs,
                })
        except Exception as e:
            with bt_lock:
                bt_data["error"] = f"Channel 6 scan: {e}"[:90]
                bt_data["scanning"] = False
            LOG.exception('Channel 6 discovery failed')
        bt_scan_now.wait(BT_SCAN_PERIOD)
        bt_scan_now.clear()

def lan_reader():
    """Read this host's own ARP/neighbour cache and default route.

    This is the kernel's existing record of hosts it has already exchanged traffic
    with — it is a local lookup, not a network sweep. IP addresses only exist for
    devices on the network this host has joined; a WiFi survey of nearby access points
    cannot produce them."""
    while not STOP_EVENT.is_set():
        try:
            gateway = "—"; ssid = "—"
            ok, out, _ = _run(["ip", "route", "show", "default"], timeout=8)
            if ok:
                for line in out.splitlines():
                    p = line.split()
                    if "via" in p:
                        gateway = p[p.index("via") + 1]; break
            ok2, out2, note = _run(["ip", "neigh", "show"], timeout=8)
            hosts = []
            if ok2:
                for line in out2.splitlines():
                    p = line.split()
                    if len(p) < 2:
                        continue
                    ip = p[0]
                    mac = p[p.index("lladdr") + 1].upper() if "lladdr" in p else "—"
                    state = p[-1] if p[-1].isupper() else "—"
                    dev = p[p.index("dev") + 1] if "dev" in p else "—"
                    if mac == "—":
                        continue                      # incomplete entry, nothing to show
                    hosts.append({"ip":ip, "mac":mac, "dev":dev, "state":state,
                                  "gw":(ip == gateway)})
                names = resolve_host_names([h["ip"] for h in hosts][:40])
                for h in hosts:
                    h["name"] = names.get(h["ip"], "")
                    h["vendor"] = mac_vendor(h["mac"])
                hosts.sort(key=lambda h: (not h["gw"], h["ip"]))
            with wifi_lock:
                ssid = (wifi_data["connected"] or {}).get("ssid", "—")
            with lan_lock:
                lan_data.update({"hosts":hosts, "gateway":gateway, "self_ip":_local_ip(),
                                 "ssid":ssid,
                                 "error":None if ok2 else f"ip neigh unavailable ({note})",
                                 "last_rx":time.time()})
        except Exception as e:
            with lan_lock:
                lan_data["error"] = f"LAN: {e}"[:90]
            LOG.exception("Neighbour-cache reader failed")
        STOP_EVENT.wait(LAN_SCAN_PERIOD)
