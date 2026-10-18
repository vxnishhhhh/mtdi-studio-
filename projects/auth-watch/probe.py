"""MTDI probe: authentication events from a log, counted per window.

    FAILED_AUTH=3,ACCEPTED_AUTH=1,WINDOW_S=10

Follows the log like `tail -F` (new lines only) and prints one line per window,
including windows with zero events: an observed zero is a real measurement.
Configure with MTDI_LOG (default /var/log/auth.log) and MTDI_WINDOW (seconds).
Patterns cover OpenSSH, sudo and PAM. Read-only; needs permission to read the log.
"""
import os
import re
import sys
import time

path = os.environ.get("MTDI_LOG", "/var/log/auth.log")
window = float(os.environ.get("MTDI_WINDOW", "10"))
FAILED = re.compile(r"Failed password|authentication failure|Invalid user|Failed publickey|incorrect password attempts")
ACCEPTED = re.compile(r"Accepted (password|publickey|keyboard-interactive)|session opened for user")

try:
    log = open(path, "r", errors="replace")
except OSError as error:
    sys.exit(f"cannot read {path}: {error.strerror}")
log.seek(0, os.SEEK_END)
inode = os.fstat(log.fileno()).st_ino
while True:
    failed = accepted = 0
    end = time.monotonic() + window
    while time.monotonic() < end:
        line = log.readline()
        if line:
            failed += bool(FAILED.search(line))
            accepted += bool(ACCEPTED.search(line))
            continue
        time.sleep(0.2)
        try:
            if os.stat(path).st_ino != inode:          # log rotated: reopen from the start
                log = open(path, "r", errors="replace")
                inode = os.fstat(log.fileno()).st_ino
        except OSError:
            pass
    print(f"FAILED_AUTH={failed},ACCEPTED_AUTH={accepted},WINDOW_S={window:g}", flush=True)
