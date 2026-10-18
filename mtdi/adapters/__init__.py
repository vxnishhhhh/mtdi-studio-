"""Adapters: how lines reach MTDI from any hardware, firmware or software.

    serial     a microcontroller on USB / UART (Arduino, ESP32, Pico, STM32, ...)
    tcp        a network line stream; listen (a bridge connects in) or connect
    http       any program POSTs to /mtdi/ingest (no thread needed)
    replay     a recorded session file played back in real time
    simulator  declared-simulated data from the manifest; always labelled SIMULATED
    python     any Python generator you write: "package.module:function"
    process    any program in any language; its stdout lines are the protocol
    system     the host computer itself (CPU, memory, temperature, disk, network)

Every adapter does one thing: deliver protocol lines or {KEY: value} dicts to
Engine.ingest_line / ingest_values with an honest data_source label. None of them
interpret data.
"""
import importlib
import threading
import time


class Adapter:
    data_source = "HARDWARE"

    def __init__(self, engine, spec):
        self.engine = engine
        self.spec = spec
        self.id = spec["id"]
        self.stop_event = threading.Event()
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self._guarded, name=f"mtdi-{self.id}", daemon=True)
        self.thread.start()
        return self

    def stop(self):
        self.stop_event.set()

    def _guarded(self):
        """Run forever; on any failure report it and retry, never take the studio down."""
        delay = 1.0
        while not self.stop_event.is_set():
            try:
                self.run()
                delay = 1.0
            except Exception as error:   # noqa: BLE001 — a source failing must never stop the others
                self.engine.set_source_state(self.id, "offline", f"{type(error).__name__}: {error}")
                self.stop_event.wait(delay)
                delay = min(delay * 2, 10.0)
            else:
                if not self.stop_event.is_set():
                    self.stop_event.wait(1.0)

    def run(self):
        raise NotImplementedError

    def line(self, text):
        self.engine.ingest_line(self.id, text, self.data_source)


class HttpAdapter(Adapter):
    """Passive: the studio's /mtdi/ingest endpoint feeds this source."""

    def start(self):
        self.engine.set_source_state(self.id, "waiting", "POST lines or values to /mtdi/ingest")
        return self


def build(engine, spec, simulate=False):
    from .serial_line import SerialAdapter
    from .tcp_line import TcpAdapter
    from .replay import ReplayAdapter
    from .simulator import SimulatorAdapter
    from .process import ProcessAdapter
    from .system import SystemAdapter
    if simulate or spec["adapter"] == "simulator":
        return SimulatorAdapter(engine, spec)
    kinds = {"serial": SerialAdapter, "tcp": TcpAdapter, "http": HttpAdapter,
             "replay": ReplayAdapter, "python": PythonAdapter, "process": ProcessAdapter,
             "system": SystemAdapter}
    return kinds[spec["adapter"]](engine, spec)


class PythonAdapter(Adapter):
    """Calls a generator you write. It yields protocol lines or {KEY: value} dicts.

        {"id": "imu", "adapter": "python", "callable": "my_pkg.sensors:read_imu",
         "data_source": "HARDWARE", "options": {...}}
    """

    def run(self):
        target = self.spec.get("callable", "")
        module_name, _, func_name = target.partition(":")
        func = getattr(importlib.import_module(module_name), func_name)
        self.data_source = self.spec.get("data_source", "SOFTWARE")
        self.engine.set_source_state(self.id, "receiving", target)
        for item in func(**self.spec.get("options", {})):
            if self.stop_event.is_set():
                return
            if isinstance(item, dict):
                self.engine.ingest_values(self.id, item, self.data_source)
            else:
                self.line(item)


def sleep_until(stop_event, deadline):
    remaining = deadline - time.monotonic()
    if remaining > 0:
        stop_event.wait(remaining)
