"""Optional camera capture and measured host telemetry for the instrument."""

from __future__ import annotations

import copy
import json
import math
import multiprocessing
import os
import platform
import queue
import re
import shutil
import socket
import subprocess
import threading
import time
from pathlib import Path


def _message(value):
    return str(value).replace("\u2014", " ").replace("\u002d", " ")[:240]


def _read(path, default=None):
    try:
        return Path(path).read_text(errors="replace").replace("\x00", "").strip()
    except OSError:
        return default


def _run(command, timeout=1.5):
    try:
        result = subprocess.run(command, capture_output=True, text=True,
                                timeout=timeout, check=False)
        return result.stdout.strip(), result.returncode
    except (OSError, subprocess.SubprocessError):
        return "", None


class OneEuroFilter:
    """Adaptive cutoff preserves fast gestures while suppressing resting jitter."""

    def __init__(self, min_cutoff=1.5, beta=3.0, derivative_cutoff=1.0):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.derivative_cutoff = derivative_cutoff
        self.previous_time = None
        self.previous_raw = None
        self.value = None
        self.derivative = 0.0

    @staticmethod
    def alpha(cutoff, dt):
        return 1.0 / (1.0 + 1.0 / (2.0 * math.pi * cutoff * dt))

    def __call__(self, value, timestamp):
        if self.previous_time is None or timestamp <= self.previous_time:
            self.value = float(value)
            self.previous_raw = float(value)
            self.previous_time = timestamp
            self.derivative = 0.0
            return self.value
        dt = timestamp - self.previous_time
        velocity = (value - self.previous_raw) / dt
        a = self.alpha(self.derivative_cutoff, dt)
        self.derivative += a * (velocity - self.derivative)
        cutoff = self.min_cutoff + self.beta * abs(self.derivative)
        self.value += self.alpha(cutoff, dt) * (value - self.value)
        self.previous_raw = value
        self.previous_time = timestamp
        return self.value


class TrackingEstimator:
    """Derive normalized image coordinates and derivatives from measured time."""

    def __init__(self):
        self.filters = [OneEuroFilter() for _ in range(3)]
        self.last = None
        self.last_time = None
        self.last_velocity = [0.0, 0.0, 0.0]

    def update(self, position, timestamp, wall_time=None):
        detected = position is not None
        gap = self.last_time is None or timestamp - self.last_time > 0.3
        if detected:
            if gap:
                self.filters = [OneEuroFilter() for _ in range(3)]
            filtered = [f(float(v), timestamp) for f, v in zip(self.filters, position)]
            dt = timestamp - self.last_time if self.last_time is not None else 0.0
            if self.last is not None and not gap and dt > 0.001:
                velocity = [(v - p) / dt for v, p in zip(filtered, self.last)]
                acceleration = [(v - p) / dt for v, p in zip(velocity, self.last_velocity)]
            else:
                velocity = [0.0, 0.0, 0.0]
                acceleration = [0.0, 0.0, 0.0]
            self.last = filtered
            self.last_time = timestamp
            self.last_velocity = velocity
        else:
            filtered = self.last
            velocity = self.last_velocity[:]
            acceleration = [0.0, 0.0, 0.0]
        return {"position": filtered, "raw_position": position, "filtered": True,
                "x": filtered[0] if filtered else None,
                "y": filtered[1] if filtered else None,
                "z": filtered[2] if filtered else None,
                "velocity": velocity, "acceleration": acceleration,
                "confidence": 1.0 if detected else 0.0,
                "confidence_kind": "landmark presence only",
                "timestamp": time.time() if wall_time is None else wall_time,
                "monotonic": timestamp, "units": "normalized image coordinates",
                "uncertainty": "Camera geometry is not calibrated"}


def _latest_put(outbox, value):
    try:
        outbox.put_nowait(value)
        return False
    except queue.Full:
        try:
            outbox.get_nowait()
        except queue.Empty:
            return True
        try:
            outbox.put_nowait(value)
        except queue.Full:
            return True
        return True


class HandTracker:
    """Run the supported MediaPipe video task with measured frame timestamps."""

    def __init__(self):
        import mediapipe as mp
        from types import SimpleNamespace
        self.mp, self.namespace = mp, SimpleNamespace
        self.last_timestamp = -1
        if hasattr(mp, 'solutions'):
            self.legacy = True
            self.detector = mp.solutions.hands.Hands(static_image_mode=False, max_num_hands=2,
                model_complexity=0, min_detection_confidence=.55, min_tracking_confidence=.55)
        else:
            self.legacy = False
            configured = os.environ.get('STUDIO_HAND_MODEL')
            if configured:
                options = mp.tasks.BaseOptions(model_asset_path=configured)
            elif globals().get('HAND_MODEL_B64'):
                import base64, gzip
                options = mp.tasks.BaseOptions(model_asset_buffer=gzip.decompress(base64.b64decode(HAND_MODEL_B64)))
            else:
                model = Path(__file__).resolve().parent / 'models/hand_landmarker.task'
                if not model.is_file():
                    raise FileNotFoundError('Hand tracking model is unavailable')
                options = mp.tasks.BaseOptions(model_asset_path=str(model))
            self.detector = mp.tasks.vision.HandLandmarker.create_from_options(
                mp.tasks.vision.HandLandmarkerOptions(base_options=options,
                    running_mode=mp.tasks.vision.RunningMode.VIDEO, num_hands=2,
                    min_hand_detection_confidence=.55, min_tracking_confidence=.55))

    def process(self, rgb):
        if self.legacy:
            return self.detector.process(rgb)
        timestamp = max(self.last_timestamp + 1, int(time.monotonic() * 1000))
        self.last_timestamp = timestamp
        image = self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=rgb)
        result = self.detector.detect_for_video(image, timestamp)
        return self.namespace(multi_hand_landmarks=[self.namespace(landmark=hand) for hand in result.hand_landmarks])

    def close(self):
        self.detector.close()


def _camera_worker(source, backend, outbox, stop_event, width, height, target_fps):
    """Own capture and inference in a process that can always be stopped."""
    capture = None
    hands = None
    picamera = None
    dropped = 0
    try:
        import cv2
        cv2.setNumThreads(1)
        _latest_put(outbox, {"state": "initialising", "progress": "Opening camera"})
        if backend == "picamera2":
            from picamera2 import Picamera2
            picamera = Picamera2(int(source))
            config = picamera.create_video_configuration(
                main={"size": (width, height), "format": "RGB888"},
                controls={"FrameRate": target_fps}, buffer_count=3)
            picamera.configure(config)
            picamera.start()
        else:
            capture = cv2.VideoCapture(source)
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            capture.set(cv2.CAP_PROP_FPS, target_fps)
            capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            if not capture.isOpened():
                raise RuntimeError("Camera is absent or access was denied")
        tracking_error = None
        _latest_put(outbox, {"state": "initialising", "progress": "Loading hand tracking"})
        try:
            hands = HandTracker()
        except Exception as exc:
            tracking_error = "Hand tracking unavailable: " + _message(exc)
        estimator = TrackingEstimator()
        previous = None
        fps = None
        failures = 0
        next_frame = time.monotonic()
        while not stop_event.is_set():
            if picamera is not None:
                frame = picamera.capture_array("main")
                ok = frame is not None
            else:
                ok, frame = capture.read()
            now = time.monotonic()
            wall_time = time.time()
            if not ok:
                dropped += 1
                failures += 1
                if failures >= 5:
                    raise RuntimeError("Camera stopped returning frames")
                stop_event.wait(0.1)
                continue
            failures = 0
            position = None
            landmarks = None
            pinch = None
            hand_count = 0
            if hands is not None:
                try:
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    rgb.flags.writeable = False
                    result = hands.process(rgb)
                    detected = result.multi_hand_landmarks or []
                    hand_count = len(detected)
                    if detected:
                        landmarks = [[p.x, p.y, p.z] for p in detected[0].landmark]
                        palm = [landmarks[i] for i in (0, 5, 9, 13, 17)]
                        position = [sum(p[i] for p in palm) / len(palm) for i in range(3)]
                        pinch = math.hypot(landmarks[4][0] - landmarks[8][0],
                                           landmarks[4][1] - landmarks[8][1])
                except Exception as exc:
                    tracking_error = "Hand tracking failed: " + _message(exc)
                    hands.close()
                    hands = None
            tracking = estimator.update(position, now, wall_time)
            tracking.update({"landmarks": landmarks, "pinch": pinch,
                             "hand_count": hand_count,
                             "state": "offline" if hands is None else "tracking" if position else "searching",
                             "error": tracking_error})
            if previous is not None:
                current = 1.0 / max(0.001, now - previous)
                fps = current if fps is None else fps * 0.85 + current * 0.15
            previous = now
            encoded, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 65])
            packet = {"state": "connected", "progress": "Camera ready", "error": None,
                      "resolution": [frame.shape[1], frame.shape[0]],
                      "fps": round(fps, 1) if fps else None, "target_fps": target_fps,
                      "dropped_frames": dropped, "drop_measurement": "Capture failures and delivery queue overflow",
                      "last_frame": wall_time, "tracking": tracking,
                      "jpeg": jpeg.tobytes() if encoded else None}
            if _latest_put(outbox, packet):
                dropped += 1
            next_frame = max(next_frame + 1.0 / target_fps, now)
            stop_event.wait(max(0.0, next_frame - time.monotonic()))
    except Exception as exc:
        _latest_put(outbox, {"state": "offline", "error": _message(exc),
                            "progress": "Camera unavailable", "tracking": {"confidence": 0.0, "state": "offline"}})
    finally:
        if hands is not None:
            hands.close()
        if capture is not None:
            capture.release()
        if picamera is not None:
            try:
                picamera.stop()
            finally:
                picamera.close()


class CameraService:
    """Lazy capture with persisted intent and a bounded latest frame mailbox."""

    def __init__(self, state_dir=None, source=None):
        configured = os.environ.get("STUDIO_CAMERA_SOURCE", "0") if source is None else source
        self.source = int(configured) if str(configured).isdigit() else str(configured)
        self.backend = os.environ.get("STUDIO_CAMERA_BACKEND", "opencv")
        self.state_file = Path(state_dir) / "camera.json" if state_dir else None
        self._state_lock = threading.RLock()
        self._control_lock = threading.Lock()
        self._context = multiprocessing.get_context("spawn")
        self._process = None
        self._outbox = None
        self._stop_event = None
        self._collector = None
        self._collector_stop = threading.Event()
        self._jpeg = None
        self._state = {"enabled": False, "state": "disabled", "error": None,
                       "resolution": None, "fps": None, "dropped_frames": 0,
                       "last_frame": None, "backend": self.backend,
                       "tracking": {"confidence": 0.0, "state": "disabled"}}
        self.saved_enabled = False
        if self.state_file:
            try:
                self.saved_enabled = json.loads(self.state_file.read_text()).get("enabled") is True
            except (OSError, ValueError, AttributeError):
                self.saved_enabled = False

    def _persist(self, enabled):
        self.saved_enabled = enabled
        if self.state_file:
            try:
                self.state_file.parent.mkdir(parents=True, exist_ok=True)
                temporary = self.state_file.with_suffix(".tmp")
                temporary.write_text(json.dumps({"enabled": enabled}))
                temporary.replace(self.state_file)
            except OSError as exc:
                with self._state_lock:
                    self._state["settings_error"] = _message(exc)

    def _collect(self):
        while not self._collector_stop.is_set():
            try:
                packet = self._outbox.get(timeout=0.2)
            except queue.Empty:
                if self._process is not None and not self._process.is_alive():
                    with self._state_lock:
                        if self._state["state"] not in ("disabled", "offline"):
                            self._state.update(state="offline", error="Camera worker stopped")
                    return
                continue
            except (OSError, ValueError, EOFError):
                return
            jpeg = packet.pop("jpeg", None)
            with self._state_lock:
                if self._state["enabled"]:
                    self._state.update(packet)
                    if jpeg is not None:
                        self._jpeg = jpeg

    def _stop_worker(self):
        if self._stop_event is not None:
            self._stop_event.set()
        if self._process is not None:
            self._process.join(1.5)
            if self._process.is_alive():
                self._process.terminate()
                self._process.join(1.0)
            if self._process.is_alive():
                self._process.kill()
                self._process.join(1.0)
            if self._process.is_alive():
                raise RuntimeError("Camera process did not release its device")
        self._collector_stop.set()
        if self._collector is not None:
            self._collector.join(0.5)
        if self._outbox is not None:
            self._outbox.close()
            self._outbox.join_thread()
        self._process = None
        self._outbox = None
        self._collector = None
        self._stop_event = None

    def set_enabled(self, enabled):
        if not isinstance(enabled, bool):
            raise ValueError("Camera enabled must be a boolean")
        with self._control_lock:
            self._persist(enabled)
            if enabled and self._process is not None and self._process.is_alive():
                return self.snapshot()
            self._stop_worker()
            with self._state_lock:
                self._jpeg = None
                self._state.update(enabled=enabled, error=None, last_frame=None,
                                   resolution=None, fps=None, dropped_frames=0,
                                   state="initialising" if enabled else "disabled",
                                   tracking={"confidence": 0.0, "state": "initialising" if enabled else "disabled"})
            if enabled:
                self._outbox = self._context.Queue(maxsize=2)
                self._stop_event = self._context.Event()
                self._collector_stop.clear()
                self._process = self._context.Process(
                    target=_camera_worker,
                    args=(self.source, self.backend, self._outbox, self._stop_event, 640, 480, 15),
                    name="studio_camera", daemon=True)
                try:
                    self._process.start()
                except Exception as exc:
                    self._outbox.close()
                    self._outbox = None
                    self._process = None
                    with self._state_lock:
                        self._state.update(state="offline", error=_message(exc))
                    return self.snapshot()
                self._collector = threading.Thread(target=self._collect, name="camera_delivery", daemon=True)
                self._collector.start()
            return self.snapshot()

    def snapshot(self):
        with self._state_lock:
            result = copy.deepcopy(self._state)
        age = time.time() - result["last_frame"] if result["last_frame"] is not None else None
        result["frame_age_seconds"] = age
        if result["enabled"] and age is not None and age > 2:
            result["state"] = "stale"
            result["tracking"]["confidence"] = 0.0
        result["worker_alive"] = self._process is not None and self._process.is_alive()
        return result

    def jpeg(self):
        with self._state_lock:
            return self._jpeg

    def stop(self):
        with self._control_lock:
            self._stop_worker()
            with self._state_lock:
                self._jpeg = None
                self._state.update(enabled=False, state="disabled", fps=None,
                                   last_frame=None, tracking={"confidence": 0.0, "state": "disabled"})


def decode_throttled(value):
    flags = {0: "Undervoltage detected", 1: "Arm frequency capped",
             2: "Currently throttled", 3: "Soft temperature limit active",
             16: "Undervoltage has occurred", 17: "Arm frequency capping has occurred",
             18: "Throttling has occurred", 19: "Soft temperature limit has occurred"}
    return {"raw": value, "current": [text for bit, text in flags.items() if bit < 16 and value & (1 << bit)],
            "history": [text for bit, text in flags.items() if bit >= 16 and value & (1 << bit)],
            "undervoltage": bool(value & 1), "thermal_limit": bool(value & 8)}


def lan_address():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as connection:
            connection.connect(("192.0.2.1", 80))
            return connection.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return None


class TelemetryService:
    """Read real host data every five seconds and cache slower inventories."""

    def __init__(self, version, camera=None, calibration_provider=None, interval=5.0):
        self.version = version
        self.camera = camera
        self.calibration_provider = calibration_provider
        self.interval = max(2.0, float(interval))
        self._lock = threading.Lock()
        self._lifecycle_lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None
        self._cpu_previous = {}
        self._psutil = None
        self._inventory = {}
        self._inventory_at = 0.0
        self._smart = []
        self._smart_at = 0.0
        self._state = {"state": "initialising", "last_rx": None, "build_version": version,
                       "telemetry_source": "Waiting for first host sample", "telemetry_error": None}

    def start(self):
        with self._lifecycle_lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop.clear()
            self._thread = threading.Thread(target=self._worker, name="host_telemetry", daemon=True)
            self._thread.start()

    def stop(self):
        with self._lifecycle_lock:
            self._stop.set()
            if self._thread is not None:
                self._thread.join(8.0)
            if self._thread is not None and not self._thread.is_alive():
                self._thread = None

    def snapshot(self):
        with self._lock:
            result = copy.deepcopy(self._state)
        result["age_seconds"] = time.time() - result["last_rx"] if result["last_rx"] else None
        if result["age_seconds"] is not None and result["age_seconds"] > self.interval * 3:
            result["state"] = "stale"
        if self.camera:
            result["camera"] = self.camera.snapshot()
        if self.calibration_provider:
            try:
                result["calibrations"] = self.calibration_provider()
            except Exception as exc:
                result["calibration_error"] = _message(exc)
        return result

    def _worker(self):
        try:
            import psutil
            self._psutil = psutil
        except ImportError:
            self._psutil = None
        while not self._stop.is_set():
            before = time.monotonic()
            try:
                result = self.collect()
                with self._lock:
                    self._state = result
            except Exception as exc:
                with self._lock:
                    self._state.update(state="error", telemetry_error=_message(exc))
            self._stop.wait(max(0.1, self.interval - (time.monotonic() - before)))

    def _cpu(self):
        raw = _read("/proc/stat", "")
        percentages = {}
        for line in raw.splitlines():
            words = line.split()
            if not words or not re.fullmatch(r"cpu\d*", words[0]):
                continue
            values = [int(v) for v in words[1:9]]
            total = sum(values)
            idle = values[3] + values[4]
            previous = self._cpu_previous.get(words[0])
            percentages[words[0]] = (round(100 * (1 - (idle - previous[1]) / (total - previous[0])), 1)
                                      if previous and total > previous[0] else None)
            self._cpu_previous[words[0]] = (total, idle)
        if percentages:
            return percentages.get("cpu"), [percentages[k] for k in sorted(percentages, key=lambda k: int(k[3:] or -1)) if k != "cpu"]
        if self._psutil:
            values = self._psutil.cpu_percent(interval=None, percpu=True)
            if not self._cpu_previous:
                self._cpu_previous["primed"] = True
                return None, [None for _ in values]
            return round(sum(values) / len(values), 1) if values else None, values
        return None, []

    def _inventory_snapshot(self):
        usb = []
        for device in sorted(Path("/sys/bus/usb/devices").glob("*")):
            vendor = _read(device / "idVendor")
            product_id = _read(device / "idProduct")
            if vendor and product_id:
                usb.append({"path": str(device), "vendor_id": vendor, "product_id": product_id,
                            "manufacturer": _read(device / "manufacturer"),
                            "product": _read(device / "product"), "serial": _read(device / "serial")})
        ports = []
        try:
            from serial.tools import list_ports
            ports = [{"device": port.device, "description": _message(port.description),
                      "manufacturer": port.manufacturer, "serial": port.serial_number,
                      "vendor_id": port.vid, "product_id": port.pid} for port in list_ports.comports()]
        except ImportError:
            for pattern in ("ttyACM*", "ttyUSB*", "cu.usb*"):
                ports.extend({"device": str(p), "description": "Serial port"} for p in Path("/dev").glob(pattern))
        camera_devices = [{"device": "/dev/" + p.name, "name": _read(p / "name")}
                          for p in Path("/sys/class/video4linux").glob("video*")]
        try:
            from .audition import detect_alsa_capture, detect_rtl_sdr
            audio_devices, audio_error = detect_alsa_capture()
            rtl_present, rtl_error = detect_rtl_sdr()
        except Exception as exc:  # pragma: no cover
            audio_devices, audio_error, rtl_present, rtl_error = [], _message(exc), False, _message(exc)
        return {"usb_devices": usb, "serial_ports": ports, "camera_devices": camera_devices,
                "audio_capture_devices": audio_devices, "audio_capture_note": audio_error,
                "rtl_sdr_presence": "detected" if rtl_present else "not identified", "rtl_sdr_note": rtl_error,
                "camera_inventory_note": "Video nodes can include codecs and image processors; camera capture is verified only when the device opens",
                "tinysa_presence": "detected" if any("tinysa" in str(p).lower() for p in ports + usb)
                else "not identified", "inventory_timestamp": time.time()}

    def _network(self):
        rows = []
        if self._psutil:
            stats = self._psutil.net_if_stats()
            for name, addresses in self._psutil.net_if_addrs().items():
                info = stats.get(name)
                rows.append({"name": name, "addresses": [a.address for a in addresses if a.family in (socket.AF_INET, socket.AF_INET6)],
                             "link_state": "up" if info and info.isup else "down",
                             "speed_mbps": info.speed if info and info.speed >= 0 else None,
                             "kind": "wireless" if Path("/sys/class/net", name, "wireless").exists() else "network"})
            return rows
        addresses = {}
        if shutil.which("ip"):
            output, code = _run(["ip", "-j", "address", "show"])
            if code == 0:
                try:
                    addresses = {row["ifname"]: [a["local"] for a in row.get("addr_info", [])] for row in json.loads(output)}
                except (ValueError, KeyError, TypeError):
                    addresses = {}
        for p in Path("/sys/class/net").glob("*"):
            rows.append({"name": p.name, "addresses": addresses.get(p.name, []),
                         "link_state": _read(p / "operstate", "unavailable"),
                         "kind": "wireless" if (p / "wireless").exists() else "network"})
        return rows

    def _storage(self):
        rows = []
        for p in sorted(Path("/sys/block").glob("*")):
            if p.name.startswith(("loop", "ram", "zram", "dm")):
                continue
            stats = (_read(p / "stat", "") or "").split()
            row = {"device": "/dev/" + p.name, "model": _read(p / "device/model"),
                   "written_bytes_since_boot": int(stats[6]) * 512 if len(stats) > 6 else None,
                   "write_scope": "Host block writes since boot", "health": "unavailable",
                   "emmc_life_time": _read(p / "device/life_time"),
                   "emmc_pre_eol": _read(p / "device/pre_eol_info")}
            rows.append(row)
        if not rows and self._psutil:
            try:
                counters = self._psutil.disk_io_counters(perdisk=True) or {}
                rows = [{"device": name, "written_bytes_since_boot": v.write_bytes,
                         "write_scope": "Host block writes since boot", "health": "unavailable"} for name, v in counters.items()]
            except Exception:
                rows = []
        return rows

    def _smart_snapshot(self, disks):
        smartctl = shutil.which("smartctl")
        if not smartctl:
            return []
        values = []
        for disk in disks[:4]:
            if self._stop.is_set():
                break
            device = disk["device"]
            if not str(device).startswith("/dev/"):
                continue
            output, code = _run([smartctl, "-a", "-j", device], timeout=1.0)
            try:
                result = json.loads(output)
            except (ValueError, TypeError):
                values.append({"device": device, "state": "unavailable"})
                continue
            status = result.get("smart_status", {}).get("passed")
            nvme = result.get("nvme_smart_health_information_log", {})
            values.append({"device": device, "state": "available" if status is not None else "unavailable",
                           "passed": status, "power_on_hours": result.get("power_on_time", {}).get("hours"),
                           "temperature_c": result.get("temperature", {}).get("current"),
                           "percentage_used": nvme.get("percentage_used"),
                           "lifetime_written_bytes": nvme["data_units_written"] * 512000 if "data_units_written" in nvme else None,
                           "command_status": code})
        return values

    def collect(self):
        now = time.time()
        model = _read("/proc/device-tree/model") or _read("/sys/firmware/devicetree/base/model") or platform.machine()
        raspberry_pi = "raspberry pi" in model.lower()
        cpu, cores = self._cpu()
        ps = self._psutil
        memory = {}
        for line in (_read("/proc/meminfo", "") or "").splitlines():
            fields = line.replace(":", " ").split()
            if len(fields) >= 2 and fields[1].isdigit():
                memory[fields[0]] = int(fields[1]) * 1024
        if memory:
            total = memory.get("MemTotal")
            available = memory.get("MemAvailable", memory.get("MemFree"))
            swap_total = memory.get("SwapTotal")
            swap_free = memory.get("SwapFree")
        elif ps:
            vm, swap = ps.virtual_memory(), ps.swap_memory()
            total, available, swap_total, swap_free = vm.total, vm.available, swap.total, swap.free
        else:
            total = available = swap_total = swap_free = None
        uptime_raw = _read("/proc/uptime")
        uptime = float(uptime_raw.split()[0]) if uptime_raw else max(0, now - ps.boot_time()) if ps else None
        frequencies = []
        for p in sorted(Path("/sys/devices/system/cpu").glob("cpu[0-9]*"), key=lambda p: int(p.name[3:])):
            raw = _read(p / "cpufreq/scaling_cur_freq")
            if raw:
                frequencies.append({"core": p.name, "mhz": float(raw) / 1000})
        if not frequencies and ps:
            try:
                frequencies = [{"core": "cpu" + str(i), "mhz": f.current} for i, f in enumerate(ps.cpu_freq(percpu=True) or [])]
            except Exception:
                frequencies = []
        temperature = None
        temperature_source = "unavailable"
        throttle = None
        power = []
        vcgencmd = shutil.which("vcgencmd") if raspberry_pi else None
        if vcgencmd:
            temp_raw, code = _run([vcgencmd, "measure_temp"])
            match = re.search(r"temp=([0-9.]+)", temp_raw)
            if code == 0 and match:
                temperature = float(match.group(1))
                temperature_source = "vcgencmd"
            throttled_raw, code = _run([vcgencmd, "get_throttled"])
            match = re.search(r"0x[0-9a-fA-F]+", throttled_raw)
            if code == 0 and match:
                throttle = decode_throttled(int(match.group(0), 16))
            if "raspberry pi 5" in model.lower():
                pmic_raw, code = _run([vcgencmd, "pmic_read_adc"])
                if code == 0:
                    for name, value, unit in re.findall(r"(\w+)\s+(?:\w+\([^)]*\)=)?([0-9.]+)([VA])", pmic_raw):
                        power.append({"name": name, "value": float(value), "unit": unit, "source": "PMIC ADC"})
        if temperature is None:
            for p in Path("/sys/class/thermal").glob("thermal_zone*"):
                kind = (_read(p / "type", "") or "").lower()
                raw = _read(p / "temp")
                if raw and any(s in kind for s in ("cpu", "soc", "bcm", "package")):
                    try:
                        temperature = float(raw) / 1000
                        temperature_source = "sysfs"
                        break
                    except ValueError:
                        continue
        for p in Path("/sys/class/power_supply").glob("*"):
            power.append({"name": p.name, "online": _read(p / "online"), "status": _read(p / "status"),
                          "voltage_uv": _read(p / "voltage_now"), "current_ua": _read(p / "current_now"),
                          "source": "sysfs"})
        disk = shutil.disk_usage("/")
        storage = self._storage()
        if time.monotonic() - self._inventory_at >= 30 or not self._inventory:
            self._inventory = self._inventory_snapshot()
            self._inventory_at = time.monotonic()
        if time.monotonic() - self._smart_at >= 60 or not self._smart_at:
            self._smart = self._smart_snapshot(storage)
            self._smart_at = time.monotonic()
        used = total - available if total is not None and available is not None else None
        os_release = _read("/etc/os-release", "")
        match = re.search(r'^PRETTY_NAME="?([^"\n]+)', os_release, re.MULTILINE)
        cpu_info = _read("/proc/cpuinfo", "")
        cpu_match = re.search(r"^(?:Model|model name|Hardware)\s*:\s*(.+)", cpu_info, re.MULTILINE)
        try:
            load = list(os.getloadavg())
        except (AttributeError, OSError):
            load = [None, None, None]
        process_rss = None
        if ps:
            try:
                process_rss = ps.Process().memory_info().rss
            except Exception:
                process_rss = None
        minutes = int(uptime or 0) // 60
        result = {"state": "connected", "last_rx": now, "build_version": self.version,
                  "host_model": model, "raspberry_pi": raspberry_pi,
                  "host_kind": "host computer" if raspberry_pi else "Development host",
                  "cpu_model": cpu_match.group(1) if cpu_match else platform.processor() or platform.machine(),
                  "os": match.group(1) if match else platform.system(), "kernel": platform.release(),
                  "hostname": socket.gethostname(), "mdns_hostname": socket.gethostname().split(".")[0] + ".local",
                  "lan_address": lan_address(), "wifi_ip": lan_address(), "interfaces": self._network(),
                  "cpu_usage": cpu, "cpu_per_core_pct": cores, "cpu_frequency": frequencies,
                  "cpu_temp": temperature, "temperature_available": temperature is not None,
                  "temperature_source": temperature_source, "temperature_uncertainty": "Manufacturer accuracy unavailable",
                  "throttling": throttle, "power_supplies": power,
                  "power_status": "exposed" if power or throttle is not None else "unavailable",
                  "ram_total_bytes": total, "ram_available_bytes": available,
                  "ram_used_mb": round(used / 1048576) if used is not None else None,
                  "ram_total_mb": round(total / 1048576) if total is not None else None,
                  "ram_pct": round(used / total * 100, 1) if total and used is not None else None,
                  "swap_total_bytes": swap_total, "swap_free_bytes": swap_free,
                  "swap_used_bytes": swap_total - swap_free if swap_total is not None and swap_free is not None else None,
                  "disk_total_bytes": disk.total, "disk_free_bytes": disk.free,
                  "disk_used_gb": round(disk.used / 1073741824, 1), "disk_total_gb": round(disk.total / 1073741824, 1),
                  "disk_pct": round(disk.used / disk.total * 100, 1), "storage": storage,
                  "storage_health": self._smart, "storage_health_timestamp": now - (time.monotonic() - self._smart_at),
                  "uptime_seconds": uptime, "uptime_str": f"{minutes // 60}h {minutes % 60}m" if uptime is not None else "unavailable",
                  "boot_time": now - uptime if uptime is not None else None,
                  "load_1": load[0], "load_5": load[1], "load_15": load[2],
                  "py_mem_mb": round(process_rss / 1048576, 1) if process_rss else None,
                  "process_id": os.getpid(), "thread_count": threading.active_count(),
                  "telemetry_source": "procfs and sysfs" if Path("/proc").exists() else "psutil" if ps else "Standard host APIs",
                  "telemetry_error": None, "poll_interval_seconds": self.interval,
                  "units": {"cpu_usage": "%", "cpu_temp": "°C", "cpu_frequency": "MHz", "uptime_seconds": "s"},
                  "uncertainty": "Host counters as reported by operating system; sensor accuracy is not calibrated"}
        result.update(copy.deepcopy(self._inventory))
        return result
