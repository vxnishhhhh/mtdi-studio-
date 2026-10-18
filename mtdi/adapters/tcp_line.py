"""TCP line stream source.

    {"id": "bridge", "adapter": "tcp", "listen": "0.0.0.0:8765"}     accept senders
    {"id": "node",   "adapter": "tcp", "connect": "192.168.1.20:9000"} dial a sender

Listen mode suits a serial-to-network bridge on another machine: it forwards raw
serial lines, which is exactly the MTDI protocol.
"""
import socket

from . import Adapter


def _addr(text):
    host, _, port = text.rpartition(":")
    return host or "0.0.0.0", int(port)


class TcpAdapter(Adapter):
    def run(self):
        if self.spec.get("connect"):
            with socket.create_connection(_addr(self.spec["connect"]), timeout=5) as conn:
                self.engine.set_source_state(self.id, "connected", f"connected to {self.spec['connect']}")
                self._read(conn)
            return
        host, port = _addr(self.spec.get("listen", "0.0.0.0:8765"))
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((host, port))
            server.listen(1)
            server.settimeout(1.0)
            self.engine.set_source_state(self.id, "waiting", f"listening on {host}:{port}")
            while not self.stop_event.is_set():
                try:
                    conn, peer = server.accept()
                except socket.timeout:
                    continue
                with conn:
                    self.engine.set_source_state(self.id, "connected", f"sender {peer[0]}")
                    self._read(conn)
                self.engine.set_source_state(self.id, "waiting", f"sender left; listening on {host}:{port}")

    def _read(self, conn):
        conn.settimeout(1.0)
        buffer = b""
        while not self.stop_event.is_set():
            try:
                chunk = conn.recv(4096)
            except socket.timeout:
                continue
            if not chunk:
                return
            buffer += chunk
            if len(buffer) > 65536:          # a sender that never ends a line is not speaking MTDI
                buffer = b""
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                if line.strip():
                    self.line(line)
