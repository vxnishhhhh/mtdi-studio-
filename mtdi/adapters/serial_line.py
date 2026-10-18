"""Serial (USB / UART) source.

    {"id": "uno", "adapter": "serial", "port": "auto", "baud": 115200}

port may also be a URL (socket://host:port, rfc2217://host:port) for network serial
bridges. port "auto" picks the first board whose USB vendor id is a known microcontroller
(Arduino, CH340, CP210x, FTDI, Pico boards, Espressif), so changing
/dev/ttyACM* or /dev/cu.usbmodem* names never need a manifest edit.
Requires pyserial (pip install pyserial).
"""
from . import Adapter

KNOWN_VIDS = {0x2341, 0x2A03, 0x1A86, 0x10C4, 0x0403, 0x2E8A, 0x303A, 0x239A}


def find_port(spec):
    from serial.tools import list_ports
    wanted = spec.get("vid")
    for port in list_ports.comports():
        if port.vid is None:
            continue
        if (wanted and port.vid == int(str(wanted), 0)) or (not wanted and port.vid in KNOWN_VIDS):
            return port.device
    return None


class SerialAdapter(Adapter):
    def run(self):
        try:
            import serial
        except ImportError as error:
            raise RuntimeError("pyserial is not installed (pip install pyserial)") from error
        port = self.spec.get("port", "auto")
        if port == "auto":
            port = find_port(self.spec)
            if not port:
                self.engine.set_source_state(self.id, "waiting", "no microcontroller found on USB")
                self.stop_event.wait(2.0)
                return
        baud = int(self.spec.get("baud", 115200))
        # serial_for_url takes plain ports and URLs alike: /dev/ttyACM0, COM3,
        # socket://host:port (ser2net, ESP-Link), rfc2217://host:port.
        with serial.serial_for_url(port, baudrate=baud, timeout=1.0) as link:
            self.engine.set_source_state(self.id, "connected", f"{port} @ {baud}")
            while not self.stop_event.is_set():
                raw = link.readline()
                if raw:
                    self.line(raw)
