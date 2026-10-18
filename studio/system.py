"""Host telemetry, archive loop, demo reader, instrument lifecycle and the application lock."""
from ._shared import inherit
inherit(globals(), 'common', 'sensors', 'intelligence')

def _host_hardware_model():
    """Return the kernel's real board model where Linux device-tree exposes it."""
    for candidate in (
        Path("/proc/device-tree/model"),
        Path("/sys/firmware/devicetree/base/model"),
    ):
        try:
            value = candidate.read_bytes().replace(b"\x00", b"").decode("utf-8").strip()
            if value:
                return value
        except (OSError, UnicodeError):
            continue
    try:
        uname = os.uname()
        return f"{uname.sysname} {uname.machine}"
    except (AttributeError, OSError):
        return os.sys.platform


def _linux_cpu_temperature():
    """Read the real SoC temperature without manufacturing a fallback value."""
    candidates = []
    thermal_root = Path("/sys/class/thermal")
    try:
        for zone in thermal_root.glob("thermal_zone*"):
            try:
                kind = (zone / "type").read_text(encoding="utf-8").strip().lower()
                raw = float((zone / "temp").read_text(encoding="utf-8").strip())
                value = raw / 1000.0 if raw > 1000 else raw
                priority = 0 if any(x in kind for x in ("cpu", "soc", "bcm", "package")) else 1
                if -20 <= value <= 150:
                    candidates.append((priority, value))
            except (OSError, ValueError):
                continue
    except OSError:
        pass
    if candidates:
        return round(sorted(candidates)[0][1], 1), "sysfs"
    try:
        result = subprocess.run(
            ["vcgencmd", "measure_temp"], capture_output=True, text=True,
            timeout=2, check=False,
        )
        match = re.search(r"(-?\d+(?:\.\d+)?)", result.stdout)
        if result.returncode == 0 and match:
            return round(float(match.group(1)), 1), "vcgencmd"
    except (OSError, subprocess.SubprocessError, ValueError):
        pass
    return 0.0, "unavailable"


_proc_cpu_sample = [None]


def _proc_cpu_percent():
    fields = Path("/proc/stat").read_text(encoding="utf-8").splitlines()[0].split()[1:]
    values = [int(value) for value in fields]
    total = sum(values)
    idle = values[3] + (values[4] if len(values) > 4 else 0)
    previous = _proc_cpu_sample[0]
    _proc_cpu_sample[0] = (total, idle)
    if not previous or total <= previous[0]:
        return 0.0
    return round(100.0 * (1.0 - (idle - previous[1]) / (total - previous[0])), 1)


def _proc_memory():
    values = {}
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        name, raw = line.split(":", 1)
        values[name] = int(raw.strip().split()[0]) * 1024
    total = values["MemTotal"]
    available = values.get("MemAvailable", values.get("MemFree", 0))
    used = max(0, total - available)
    return used, total, round(100.0 * used / total, 1)


def _system_snapshot():
    """Collect one real host snapshot via psutil or Linux /proc and sysfs."""
    import shutil
    source = "psutil" if psutil is not None else "linux-procfs"
    if psutil is not None:
        cpu = round(psutil.cpu_percent(interval=None), 1)
        mem = psutil.virtual_memory()
        mem_used, mem_total, mem_pct = mem.used, mem.total, round(mem.percent, 1)
        disk = psutil.disk_usage("/")
        disk_used, disk_total, disk_pct = disk.used, disk.total, round(disk.percent, 1)
        boot_time = psutil.boot_time()
        try:
            load = psutil.getloadavg()
        except Exception:
            load = os.getloadavg()
        proc_mem = psutil.Process().memory_info().rss
    else:
        cpu = _proc_cpu_percent()
        mem_used, mem_total, mem_pct = _proc_memory()
        disk = shutil.disk_usage("/")
        disk_used, disk_total = disk.used, disk.total
        disk_pct = round(100.0 * disk_used / disk_total, 1)
        uptime = float(Path("/proc/uptime").read_text(encoding="utf-8").split()[0])
        boot_time = time.time() - uptime
        load = os.getloadavg()
        pages = int(Path("/proc/self/statm").read_text(encoding="utf-8").split()[1])
        proc_mem = pages * os.sysconf("SC_PAGE_SIZE")
    temp, temp_source = _linux_cpu_temperature()
    host_model = _host_hardware_model()
    up = max(0, int(time.time() - boot_time))
    days, remain = divmod(up, 86400)
    hours, remain = divmod(remain, 3600)
    minutes, seconds = divmod(remain, 60)
    uptime_str = (
        f"{days}d {hours}h {minutes}m" if days else
        f"{hours}h {minutes}m {seconds}s" if hours else f"{minutes}m {seconds}s"
    )
    return {
        "cpu_temp": temp, "temperature_available": temp_source != "unavailable",
        "cpu_usage": cpu, "ram_used_mb": round(mem_used / (1024**2)),
        "ram_total_mb": round(mem_total / (1024**2)), "ram_pct": mem_pct,
        "disk_used_gb": round(disk_used / (1024**3), 1),
        "disk_total_gb": round(disk_total / (1024**3), 1), "disk_pct": disk_pct,
        "uptime_str": uptime_str, "load_1": round(load[0], 2),
        "load_5": round(load[1], 2), "load_15": round(load[2], 2),
        "wifi_ip": _local_ip(), "py_mem_mb": round(proc_mem / (1024**2), 1),
        "telemetry_source": f"{source} + {temp_source}", "telemetry_error": None,
        "host_model": host_model,
        "raspberry_pi": "raspberry pi" in host_model.lower(),
        "last_rx": time.time(),
    }


def sys_loop():
    if psutil is not None:
        psutil.cpu_percent(interval=None)
    else:
        try:
            _proc_cpu_percent()
        except Exception:
            LOG.exception("Could not initialise /proc CPU telemetry")
    while not STOP_EVENT.is_set():
        try:
            snapshot = _system_snapshot()
            with sys_lock:
                try:
                    db_size = ARCHIVE.path.stat().st_size / (1024**2)
                except OSError:
                    db_size = 0.0
                snapshot.update({"db_size_mb":round(db_size,2),"worker_count":LIFECYCLE.active_count,
                    "thread_count":threading.active_count(),"archive_queue":ARCHIVE.items.qsize(),
                    "last_db_write":ARCHIVE.last_write})
                sys_data.update(snapshot)
                snapshot = dict(sys_data)
            ARCHIVE.put("system", {"t":time.time(), "payload":snapshot})
        except Exception as e:
            LOG.exception("System monitor failed: %s", e)
            with sys_lock:
                sys_data["telemetry_error"] = str(e)[:160]
        STOP_EVENT.wait(1.0)

def archive_loop():
    """Snapshot live signals into one stored area (every 3s while the sensor is healthy)."""
    while not STOP_EVENT.is_set():
        try:
            with mag_lock:
                err = magnetic_data["error"]; last = magnetic_data["last_rx"]
                m = magnetic_data["magnitude"]; x = magnetic_data["x"]; y = magnetic_data["y"]; z = magnetic_data["z"]
                # Only a chip fault makes a magnetic sample untrusted. Being uncalibrated
                # is recorded as a note so the archive still reflects usable data.
                mag_fault = magnetic_data["chip_warning"]
                mag_note = magnetic_data["warning"]
            if err is None and last is not None and (time.time() - last) < 5:
                with archive_lock:
                    signal_archive.append({"t":time.time(), "mag":m, "x":x, "y":y, "z":z})
                    session_stats["count"] += 1
                    session_stats["sum"] += m
                    session_stats["min"] = min(session_stats["min"], m)
                    session_stats["max"] = max(session_stats["max"], m)
                ARCHIVE.put("mag", {
                    "t":time.time(), "mag":m, "x":x, "y":y, "z":z,
                    "trusted":mag_fault is None,
                    "warning":mag_note,
                })
            with efield_lock:
                ed = {
                    "t":time.time(), "rms_mv":efield_data["rms_mv"],
                    "peak_mv":efield_data["peak_mv"],
                    "baseline_mv":efield_data["baseline_mv"],
                    "ratio":efield_data["ratio"], "rel_index":efield_data["rel_index"],
                    "gain":efield_data["gain"], "clipped":efield_data["clipped"],
                    "trusted":(
                        efield_data["error"] is None and efield_data["calibrated"]
                        and not efield_data["clipped"] and not efield_data["warning"]
                    ),
                    "warning":efield_data["warning"] or efield_data["error"],
                }
                ef_fresh = efield_data["last_rx"] and time.time() - efield_data["last_rx"] < 5
            if ef_fresh:
                ARCHIVE.put("efield", ed)
        except Exception:
            LOG.exception("Signal archive snapshot failed")
        STOP_EVENT.wait(3)


def demo_reader():
    """Deterministic software-only source. It runs only after explicit ``--demo``."""
    tick = 0
    last_rf = 0.0
    while not STOP_EVENT.is_set():
        now = time.time()
        phase = tick * 0.075
        x = 21.0 + 1.8 * math.sin(phase)
        y = -6.5 + 1.2 * math.cos(phase * 0.8)
        z = 38.0 + 0.9 * math.sin(phase * 0.4)
        magnitude = math.sqrt(x*x + y*y + z*z)
        with mag_lock:
            magnetic_data.update({
                "x":x, "y":y, "z":z, "magnitude":magnitude,
                "min_mag":min(magnetic_data["min_mag"], magnitude),
                "max_mag":max(magnetic_data["max_mag"], magnitude),
                "raw_x":x, "raw_y":y, "raw_z":z,
                "error":None, "warning":None, "chip_warning":None,
                "calibration_warning":None, "calibrated":True,
                "calibration_metadata":{"source":"software simulator"},
                "chip_id":0x80, "last_rx":now,
            })
            magnetic_data["history"].append(magnitude)
            magnetic_data["xyz_history"].append((x, y, z))
        # The simulator logs too, so the CSV pipeline can be exercised without
        # hardware. Every row it writes carries data_source="SIMULATED" and an
        # explicit note, so it can never be mistaken for a measurement.
        CSV_LOG.log_mag(now, x, y, z, magnitude, (x, y, z), True, False,
                        note="SIMULATED — software simulator, not a measurement")

        rms = 0.8 + 0.25 * (1.0 + math.sin(phase * 1.7))
        ratio = rms / 0.8
        rel = max(0.0, min(100.0, (ratio - 1.0) / 9.0 * 100.0))
        demo_field = _ef_v_per_m(rms)
        with efield_lock:
            efield_data.update({
                "rms_mv":rms, "mean_mv":0.0, "peak_mv":rms * 1.7,
                "field_v_m":demo_field, "peak_v_m":_ef_v_per_m(rms * 1.7),
                "baseline_v_m":_ef_v_per_m(0.8),
                "baseline_mv":0.8, "rel_index":rel, "ratio":ratio,
                "level":"LOW", "gain":16, "min_code":-120, "max_code":125,
                "utilisation":0.4, "clipped":False, "status":"SIMULATED",
                "error":None, "warning":None, "last_rx":now, "calibrated":True,
            })
            efield_data["history"].append(demo_field)
            efield_data["rel_history"].append(rel)
        CSV_LOG.log_efield(now, rms, rms * 1.7, 0.8, ratio, rel, 16, 0.4,
                           False, True, False,
                           note="SIMULATED — software simulator, not a measurement")

        with tinysa_cmd_lock:
            rf_paused = tinysa_cmd["paused"]
        if rf_paused:
            with spectrum_lock:
                spectrum_data["status"] = "SIMULATED DATA · paused by operator"
        if not rf_paused and now - last_rf >= 1.0:
            with spectrum_lock:
                start_hz = spectrum_data["span_start"]
                stop_hz = spectrum_data["span_stop"]
                points = spectrum_data["points"]
                preset = spectrum_data["preset"]
            freqs = [
                start_hz + i * (stop_hz - start_hz) / max(points - 1, 1)
                for i in range(points)
            ]
            levels = []
            for i, frequency in enumerate(freqs):
                base = -103.0 + 1.2 * math.sin(i * 0.31 + phase)
                fm_peak = 34.0 * math.exp(
                    -((frequency - 98_500_000.0) /
                      max((stop_hz-start_hz)/80.0, 250_000.0))**2
                )
                ism_peak = 26.0 * math.exp(
                    -((frequency - 2_437_000_000.0) /
                      max((stop_hz-start_hz)/70.0, 1_000_000.0))**2
                )
                levels.append(base + fm_peak + ism_peak)
            floor = statistics.median(levels)
            peaks = _tsa_peaks(freqs, levels, floor)
            peak_i = max(range(points), key=lambda i: levels[i])
            bin_width = (stop_hz-start_hz) / max(points-1, 1)
            with spectrum_lock:
                old_hold = spectrum_data["maxhold"]
                max_hold = (
                    [max(old, new) for old, new in zip(old_hold, levels)]
                    if len(old_hold) == points else list(levels)
                )
                spectrum_data.update({
                    "freqs":list(freqs), "levels":list(levels),
                    "maxhold":max_hold, "peaks":peaks, "floor":floor,
                    "peak_level":levels[peak_i], "peak_freq":freqs[peak_i],
                    "sweep_s":0.01, "sweeps":spectrum_data["sweeps"]+1,
                    "device":"Software simulator",
                    "device_info":"Deterministic seeded UI source",
                    "help_summary":"simulated scan", "port":"SIMULATED",
                    "leveloffset":"not applicable", "level_sane":True,
                    "trusted":True, "warnings":[],
                    "level_note":"simulated estimated floor", "present":True,
                    "status":"SIMULATED DATA", "error":None, "last_rx":now,
                })
                spectrum_data["waterfall"].append(list(levels))
                spectrum_data["waterfall_times"].append(now)
                spectrum_data["peak_history"].append(levels[peak_i])
            CSV_LOG.log_rf(now, start_hz, stop_hz, points, 0.01,
                           freqs[peak_i], levels[peak_i], floor, False,
                           note="SIMULATED — software simulator, not a measurement")
            ARCHIVE.put("rf", {
                "started_at":now, "completed_at":now+0.01, "duration_s":0.01,
                "profile":preset, "start_hz":start_hz, "stop_hz":stop_hz,
                "requested_points":points, "repeat":3, "bin_width_hz":bin_width,
                "frequencies":freqs, "levels":levels, "peaks":peaks,
                "warnings":["software simulator"], "trusted":True,
                "firmware":"software simulator", "port":"SIMULATED",
                "transport":"deterministic-software-simulator", "raw_response":None,
            })
            with wifi_lock:
                wifi_data.update({
                    "networks":[{
                        "ssid":"SIMULATED-AP", "bssid":"02:00:00:00:00:01",
                        "chan":"6", "mhz":2437, "band":"2.4 GHz", "signal":72,
                        "dbm":-64.0, "sec":"WPA2", "rate":"simulated", "active":False,
                    }],
                    "iface":"SIMULATED", "backend":"Software simulator",
                    "connected":None, "scan_mode":"simulated discovery",
                    "paused":False, "error":None, "last_rx":now,
                    "scans":wifi_data["scans"]+1,
                })
            with bt_lock:
                bt_data.update({
                    "devices":[{
                        "addr":"02:00:00:00:00:02", "name":"SIMULATED-BLE",
                        "rssi":-61, "vendor":"Software simulator",
                        "services":1, "tx":-4, "kind":"BLE",
                    }],
                    "adapter":"SIMULATED", "backend":"Software simulator",
                    "scan_mode":"simulated discovery", "paused":False,
                    "error":None, "last_rx":now, "scans":bt_data["scans"]+1,
                })
            last_rf = now
        tick += 1
        STOP_EVENT.wait(0.1)


class InstrumentLifecycle:
    """Own all long-running workers and guarantee at-most-once startup."""

    def __init__(self):
        self._lock = threading.Lock()
        self._threads = {}
        self._started = False

    @property
    def active_count(self):
        with self._lock:
            return sum(thread.is_alive() for thread in self._threads.values())

    def start(self):
        with self._lock:
            if self._started:
                return
            STOP_EVENT.clear()
            ARCHIVE_STOP_EVENT.clear()
            CSV_STOP_EVENT.clear()
            workers = [
                ("archive-db", ARCHIVE.worker),
                ("system", sys_loop),
                ("archive-signals", archive_loop),
                ("mtdi", mtdi_loop),
            ]
            if CSV_LOG.enabled:
                workers.append(("csv-log", CSV_LOG.worker))
            # No hardware readers and no simulator: every page shows what it has, as is.
            for name, target in workers:
                # A serverless host freezes the process between requests; daemon workers
                # never hold it open.
                thread = threading.Thread(
                    target=target, name=f"studio-{name}",
                    daemon=bool(os.environ.get("STUDIO_SERVERLESS")),
                )
                thread.start()
                self._threads[name] = thread
                LOG.info("Started worker: %s", name)
            self._started = True

    def stop(self, join_timeout=15.0):
        with self._lock:
            if not self._started:
                return
            STOP_EVENT.set()
            threads = list(self._threads.items())
        deadline = time.monotonic() + join_timeout
        # Sinks (archive writer, CSV writer) must outlive the producers so queued
        # samples are flushed rather than discarded at shutdown.
        sinks = {"archive-db", "csv-log"}
        producers = [(name, thread) for name, thread in threads if name not in sinks]
        archive_threads = [(name, thread) for name, thread in threads if name in sinks]
        for name, thread in producers:
            remaining = max(0.0, deadline - time.monotonic())
            thread.join(remaining)
            if thread.is_alive():
                LOG.error("Worker did not stop before deadline: %s", name)
        ARCHIVE_STOP_EVENT.set()
        CSV_STOP_EVENT.set()
        for name, thread in archive_threads:
            remaining = max(0.0, deadline - time.monotonic())
            thread.join(remaining)
            if thread.is_alive():
                LOG.error("Worker did not stop before deadline: %s", name)
        with self._lock:
            self._threads.clear()
            self._started = False
        LOG.info("Instrument lifecycle stopped")


LIFECYCLE = InstrumentLifecycle()


class ApplicationLock:
    """Prevent accidental multi-process ownership of I²C and serial hardware."""

    def __init__(self, path=None):
        self.path = Path(path or os.environ.get(
            "STUDIO_LOCK_FILE", "/tmp/mtdi-studio.lock"
        ))
        self.handle = None

    def acquire(self):
        try:
            import fcntl
            self.handle = self.path.open("a+", encoding="utf-8")
            fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.handle.seek(0)
            self.handle.truncate()
            self.handle.write(str(os.getpid()))
            self.handle.flush()
        except BlockingIOError as exc:
            raise RuntimeError(
                f"another studio process owns {self.path}"
            ) from exc

    def close(self):
        if self.handle is not None:
            try:
                import fcntl
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
                self.handle.close()
            finally:
                self.handle = None

