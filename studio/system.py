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
        "single_board": " pi " in f" {host_model.lower()} ",
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
            with c1_lock:
                err = ch1_data["error"]; last = ch1_data["last_rx"]
                m = ch1_data["magnitude"]; x = ch1_data["x"]; y = ch1_data["y"]; z = ch1_data["z"]
                # Only a chip fault makes a ch1 sample untrusted. Being uncalibrated
                # is recorded as a note so the archive still reflects usable data.
                c1_fault = ch1_data["chip_warning"]
                c1_note = ch1_data["warning"]
            if err is None and last is not None and (time.time() - last) < 5:
                with archive_lock:
                    signal_archive.append({"t":time.time(), "c1":m, "x":x, "y":y, "z":z})
                    session_stats["count"] += 1
                    session_stats["sum"] += m
                    session_stats["min"] = min(session_stats["min"], m)
                    session_stats["max"] = max(session_stats["max"], m)
                ARCHIVE.put("c1", {
                    "t":time.time(), "c1":m, "x":x, "y":y, "z":z,
                    "trusted":c1_fault is None,
                    "warning":c1_note,
                })
            with ch2f_lock:
                ed = {
                    "t":time.time(), "rms_mv":ch2f_data["rms_mv"],
                    "peak_mv":ch2f_data["peak_mv"],
                    "baseline_mv":ch2f_data["baseline_mv"],
                    "ratio":ch2f_data["ratio"], "rel_index":ch2f_data["rel_index"],
                    "gain":ch2f_data["gain"], "clipped":ch2f_data["clipped"],
                    "trusted":(
                        ch2f_data["error"] is None and ch2f_data["calibrated"]
                        and not ch2f_data["clipped"] and not ch2f_data["warning"]
                    ),
                    "warning":ch2f_data["warning"] or ch2f_data["error"],
                }
                c2_fresh = ch2f_data["last_rx"] and time.time() - ch2f_data["last_rx"] < 5
            if c2_fresh:
                ARCHIVE.put("ch2f", ed)
        except Exception:
            LOG.exception("Signal archive snapshot failed")
        STOP_EVENT.wait(3)


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

