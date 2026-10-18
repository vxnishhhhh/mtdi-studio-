#!/usr/bin/env python3
"""Forward the Inductra Uno's measured serial lines to a Pi TCP receiver."""
import argparse
import os
import socket
import time
import serial
from serial.tools import list_ports


UNO_IDS = {(0x2341, 0x0043), (0x2A03, 0x0043)}
DEFAULT_PI_HOSTS = ("pi.local", "inductra.local", "192.168.0.232")


def find_uno(explicit=None):
    if explicit:
        return explicit
    for port in list_ports.comports():
        if (port.vid, port.pid) in UNO_IDS or "arduino uno" in str(port.description or "").lower():
            return port.device
    raise serial.SerialException("Arduino Uno not detected")


def connect_pi(host, port):
    configured = [host] if host else [item.strip() for item in
        os.environ.get("INDUCTRA_PI_HOSTS", ",".join(DEFAULT_PI_HOSTS)).split(",") if item.strip()]
    errors = []
    for candidate in configured:
        try:
            return socket.create_connection((candidate, port), timeout=3)
        except OSError as exc:
            errors.append(f"{candidate}: {exc}")
    raise OSError("Pi unavailable (" + "; ".join(errors) + ")")


def run(device, baud, host, port):
    while True:
        try:
            selected = find_uno(device)
            with serial.Serial(selected, baud, timeout=1) as uno:
                uno.reset_input_buffer()
                with connect_pi(host, port) as target:
                    target.settimeout(None)
                    while True:
                        line = uno.readline()
                        if line:
                            target.sendall(line)
        except (OSError, serial.SerialException) as exc:
            print(f"bridge reconnecting: {exc}", flush=True)
            time.sleep(2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", help="optional serial path; omitted discovers the Uno by USB identity")
    parser.add_argument("--host", help="optional fixed Pi host; automatic fallbacks are used when omitted")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--baud", type=int, default=115200)
    args = parser.parse_args()
    run(args.device, args.baud, args.host, args.port)


if __name__ == "__main__":
    main()
