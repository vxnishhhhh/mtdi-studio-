"""MTDI probe: TCP connect latency to one target, one protocol line per interval.

    RTT_MS=12.84,FAIL_PCT=0

FAIL_PCT is the share of the last 20 attempts that failed. A failed attempt prints
no RTT (never a stand-in value). Configure with MTDI_TARGET=host:port and
MTDI_INTERVAL=seconds. Standard library only, so it runs on any Pi.
"""
import collections
import os
import socket
import sys
import time

host, _, port = os.environ.get("MTDI_TARGET", "1.1.1.1:443").rpartition(":")
interval = float(os.environ.get("MTDI_INTERVAL", "1"))
recent = collections.deque(maxlen=20)
while True:
    start = time.perf_counter()
    try:
        with socket.create_connection((host, int(port)), timeout=2):
            rtt = (time.perf_counter() - start) * 1000
        recent.append(True)
        line = f"RTT_MS={rtt:.3f},FAIL_PCT={100 * recent.count(False) / len(recent):.1f}"
    except OSError:
        recent.append(False)
        line = f"FAIL_PCT={100 * recent.count(False) / len(recent):.1f}"
    print(line, flush=True)
    time.sleep(max(0.0, interval - (time.perf_counter() - start)))
