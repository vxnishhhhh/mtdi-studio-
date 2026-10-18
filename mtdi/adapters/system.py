"""The computer MTDI runs on, as a source: real telemetry with no hardware to wire.

    {"id": "host", "adapter": "system", "interval": 1.0}

Keys it emits (map the ones you want to channels):

    CPU_PCT   MEM_PCT   SWAP_PCT   LOAD1   DISK_PCT   PROCS
    NET_RX_KBS   NET_TX_KBS   TEMP_C (when the board exposes a thermal sensor)

On Linux (Raspberry Pi included) it reads /proc and /sys with the standard library
only. Elsewhere it uses psutil when installed. A key the platform cannot measure
is simply not sent, never estimated.
"""
import os
import pathlib
import shutil
import time

from . import Adapter


class _Proc:
    """Linux /proc reader keeping the previous counters for rates."""

    def __init__(self):
        self.cpu = None
        self.net = None

    def read(self, disk_path):
        out = {}
        with open("/proc/stat") as f:
            parts = [float(x) for x in f.readline().split()[1:]]
        idle, total = parts[3] + (parts[4] if len(parts) > 4 else 0), sum(parts)
        if self.cpu:
            d_total, d_idle = total - self.cpu[1], idle - self.cpu[0]
            if d_total > 0:
                out["CPU_PCT"] = round(100.0 * (1 - d_idle / d_total), 2)
        self.cpu = (idle, total)
        mem = {}
        with open("/proc/meminfo") as f:
            for line in f:
                key, _, rest = line.partition(":")
                mem[key] = float(rest.split()[0])
        if mem.get("MemTotal"):
            avail = mem.get("MemAvailable", mem.get("MemFree", 0))
            out["MEM_PCT"] = round(100.0 * (1 - avail / mem["MemTotal"]), 2)
        if mem.get("SwapTotal"):
            out["SWAP_PCT"] = round(100.0 * (1 - mem.get("SwapFree", 0) / mem["SwapTotal"]), 2)
        out["LOAD1"] = round(os.getloadavg()[0], 3)
        out["PROCS"] = float(sum(1 for p in os.listdir("/proc") if p.isdigit()))
        rx = tx = 0.0
        with open("/proc/net/dev") as f:
            for line in list(f)[2:]:
                name, _, data = line.partition(":")
                if name.strip() == "lo":
                    continue
                fields = data.split()
                rx, tx = rx + float(fields[0]), tx + float(fields[8])
        now = time.monotonic()
        if self.net:
            dt = now - self.net[0]
            if dt > 0:
                out["NET_RX_KBS"] = round((rx - self.net[1]) / dt / 1024, 3)
                out["NET_TX_KBS"] = round((tx - self.net[2]) / dt / 1024, 3)
        self.net = (now, rx, tx)
        zone = pathlib.Path("/sys/class/thermal/thermal_zone0/temp")
        if zone.exists():
            try:
                out["TEMP_C"] = round(float(zone.read_text().strip()) / 1000.0, 2)
            except ValueError:
                pass
        usage = shutil.disk_usage(disk_path)
        out["DISK_PCT"] = round(100.0 * usage.used / usage.total, 2)
        return out


class _Psutil:
    def __init__(self, psutil):
        self.ps = psutil
        self.net = None
        psutil.cpu_percent(None)

    def read(self, disk_path):
        ps = self.ps
        out = {"CPU_PCT": ps.cpu_percent(None), "MEM_PCT": ps.virtual_memory().percent,
               "DISK_PCT": ps.disk_usage(disk_path).percent, "PROCS": float(len(ps.pids()))}
        swap = ps.swap_memory()
        if swap.total:
            out["SWAP_PCT"] = swap.percent
        try:
            out["LOAD1"] = round(os.getloadavg()[0], 3)
        except (AttributeError, OSError):
            pass
        io, now = ps.net_io_counters(), time.monotonic()
        if self.net:
            dt = now - self.net[0]
            if dt > 0:
                out["NET_RX_KBS"] = round((io.bytes_recv - self.net[1]) / dt / 1024, 3)
                out["NET_TX_KBS"] = round((io.bytes_sent - self.net[2]) / dt / 1024, 3)
        self.net = (now, io.bytes_recv, io.bytes_sent)
        temps = getattr(ps, "sensors_temperatures", lambda: {})() or {}
        for entries in temps.values():
            if entries:
                out["TEMP_C"] = entries[0].current
                break
        return out


def reader():
    if os.path.exists("/proc/stat") and os.path.exists("/proc/meminfo"):
        return _Proc()
    try:
        import psutil
    except ImportError as error:
        raise RuntimeError("system source needs Linux /proc or psutil (pip install psutil)") from error
    return _Psutil(psutil)


class SystemAdapter(Adapter):
    data_source = "SOFTWARE"

    def run(self):
        source = reader()
        interval = max(0.2, float(self.spec.get("interval", 1.0)))
        disk = self.spec.get("disk", "/")
        self.engine.set_source_state(self.id, "connected", f"host telemetry every {interval:g} s")
        next_t = time.monotonic()
        while not self.stop_event.is_set():
            values = source.read(disk)
            if values:
                self.engine.ingest_values(self.id, values, self.data_source)
            next_t += interval
            self.stop_event.wait(max(0.0, next_t - time.monotonic()))
