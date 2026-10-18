"""Configuration, secrets, HTTPS tunnel, logging, SQLite archive and CSV session logging."""
#!/usr/bin/env python3

"""MTDI Studio host computer instrument.

This is the intentionally self-contained distribution requested for field use.  It
imports without starting hardware, never generates measurements unless ``--demo`` is
explicitly selected, owns every worker through one lifecycle, and archives full
TinySA sweeps to SQLite.

v2.6.1 — one active HTTPS link for first and repeated terminal launches.
"""

from flask import Flask, Response, request
import dash
from dash import html, dcc
from dash.dependencies import Input, Output, State, ALL
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go
from collections import deque
import argparse
import base64
import functools
import gzip
import hashlib
import shutil
import hmac
import ipaddress
import logging
from logging.handlers import RotatingFileHandler
import platform
import queue
import re
import secrets
import signal
import sqlite3
import statistics
import subprocess
from pathlib import Path
import threading, time, math, socket, os, json, urllib.request, urllib.error, urllib.parse

APP_VERSION = "v239"  # overridden by run.py from studio/__init__.py
LOG = logging.getLogger('studio')
STOP_EVENT = threading.Event()
ARCHIVE_STOP_EVENT = threading.Event()
RUNTIME = {
    "demo": False,
    "session_tag": "studio",
    "host": os.environ.get("STUDIO_HOST", "0.0.0.0"),
    "port": int(os.environ.get("STUDIO_PORT", "8050")),
    "access_token": None,
    "public_tunnel": False,
}

# Embedded, simplified Natural Earth 110m land outlines. Keeping the globe data in
# this distribution makes the UI independent of the launch directory, network, and
# whether an external assets folder was copied to the host computer.
_NATURAL_EARTH_LAND_GZIP_B64 = (
    "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"
)


def _env_enabled(name, default=True):
    raw = os.environ.get(name)
    return default if raw is None else raw.lower() in {"1", "true", "yes"}


def _keychain_value(account):
    """Read a studio secret from macOS Keychain without exposing it in source."""
    if os.sys.platform != "darwin":
        return ""
    try:
        result = subprocess.run(
            ["/usr/bin/security", "find-generic-password", "-a", account,
             "-s", "MTDI Studio Notion", "-w"],
            capture_output=True, text=True, timeout=4, check=False,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def _keychain_store(account, value):
    if os.sys.platform != "darwin" or not value:
        return False
    try:
        result = subprocess.run(
            ["/usr/bin/security", "add-generic-password", "-U", "-a", account,
             "-s", "MTDI Studio Notion", "-w", value],
            capture_output=True, text=True, timeout=4, check=False,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _notion_setting(name):
    """Environment variables work on host computer; macOS uses its secure Keychain."""
    return os.environ.get(name, "").strip() or _keychain_value(name)


def _cloud_cipher_secret():
    secret = os.environ.get("STUDIO_CLOUD_CIPHER_SECRET", "").strip()
    if secret:
        return secret
    secret = _keychain_value("STUDIO_CLOUD_CIPHER_SECRET")
    if not secret and os.sys.platform == "darwin":
        secret = secrets.token_urlsafe(48)
        if not _keychain_store("STUDIO_CLOUD_CIPHER_SECRET", secret):
            return ""
    if not secret and os.sys.platform != "darwin":
        secret_path = Path(os.environ.get(
            "STUDIO_CLOUD_CIPHER_FILE",
            str(Path.home() / ".config/mtdi-studio/cloud_cipher.key"),
        )).expanduser()
        try:
            if secret_path.exists():
                secret = secret_path.read_text(encoding="utf-8").strip()
            else:
                secret = secrets.token_urlsafe(48)
                secret_path.parent.mkdir(parents=True, exist_ok=True)
                secret_path.write_text(secret, encoding="utf-8")
                secret_path.chmod(0o600)
        except OSError:
            return ""
    return secret


def _persistent_access_token():
    """Return one stable LAN-link token without exposing it in source control."""
    configured = os.environ.get("STUDIO_ACCESS_TOKEN", "").strip()
    if configured:
        return configured
    token_path = Path(os.environ.get(
        "STUDIO_ACCESS_TOKEN_FILE",
        str(Path.home() / ".config/mtdi-studio/access_token"),
    )).expanduser()
    try:
        if token_path.exists():
            token = token_path.read_text(encoding="utf-8").strip()
            if token:
                return token
        token = secrets.token_urlsafe(32)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(token, encoding="utf-8")
        token_path.chmod(0o600)
        return token
    except OSError:
        LOG.exception("Could not persist the LAN access token")
        return secrets.token_urlsafe(32)


def _print_access_link(url):
    """Print only the clickable address and its compact terminal QR code."""
    print(url, flush=True)
    try:
        try:
            import qrcode
        except ImportError:
            # Install into the exact interpreter running the dashboard. --user is
            # invalid inside many virtual environments, which was why the previous
            # best-effort install could finish without making the QR appear.
            result = subprocess.run(
                [os.sys.executable, "-m", "pip", "install", "qrcode>=7.4,<9"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=60, check=False,
            )
            if result.returncode:
                result = subprocess.run(
                    [os.sys.executable, "-m", "pip", "install", "--user", "qrcode>=7.4,<9"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    timeout=60, check=False,
                )
            if result.returncode:
                # host computer OS Bookworm marks /usr/bin/python3 as externally
                # managed. A user-site install with this explicit override leaves
                # Debian's system packages untouched and works without sudo.
                result = subprocess.run(
                    [os.sys.executable, "-m", "pip", "install", "--user",
                     "--break-system-packages", "qrcode>=7.4,<9"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    timeout=60, check=False,
                )
            import importlib
            importlib.invalidate_caches()
            import qrcode
        code = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=1,
            border=1,
        )
        code.add_data(url)
        code.make(fit=True)
        print()
        code.print_ascii(out=os.sys.stdout, tty=False, invert=True)
        os.sys.stdout.flush()
    except Exception as exc:
        LOG.exception("Terminal QR generation failed")
        print(
            f"QR unavailable: {os.sys.executable} -m pip install --user "
            "--break-system-packages qrcode",
            flush=True,
        )


def _dashboard_url(host, port):
    """Return the same simple address for both first and repeated launches."""
    if host in {"127.0.0.1", "::1", "localhost"}:
        return f"http://localhost:{port}"
    return os.environ.get(
        "STUDIO_PUBLIC_URL", f"http://pi.local:{port}"
    ).strip().rstrip("/")


def _cloudflared_download_url():
    """Return Cloudflare's official latest binary for this portable host."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    arch = "arm64" if machine in {"aarch64", "arm64"} else (
        "amd64" if machine in {"x86_64", "amd64"} else ""
    )
    if system not in {"linux", "darwin"} or not arch:
        raise RuntimeError(f"automatic HTTPS is unsupported on {system}/{machine}")
    return (
        "https://github.com/cloudflare/cloudflared/releases/latest/download/"
        f"cloudflared-{system}-{arch}"
    )


def _ensure_cloudflared():
    """Find or securely download the HTTPS tunnel client into the user cache."""
    import shutil
    existing = shutil.which("cloudflared")
    if existing:
        return existing
    user_binary = Path.home() / ".local" / "bin" / "cloudflared"
    if user_binary.exists() and user_binary.stat().st_size > 5_000_000:
        return str(user_binary)
    suffix = ".exe" if platform.system().lower() == "windows" else ""
    binary = Path.home() / ".cache" / "mtdi-studio" / f"cloudflared{suffix}"
    try:
        if binary.exists() and binary.stat().st_size > 5_000_000:
            subprocess.run([str(binary), "--version"], timeout=8, check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return str(binary)
    except (OSError, subprocess.SubprocessError):
        pass
    binary.parent.mkdir(parents=True, exist_ok=True)
    temporary = binary.with_suffix(binary.suffix + ".download")
    request_obj = urllib.request.Request(
        _cloudflared_download_url(),
        headers={"User-Agent": f"MTDI-Studio/{APP_VERSION}"},
    )
    with urllib.request.urlopen(request_obj, timeout=45) as response, temporary.open("wb") as output:
        while True:
            block = response.read(1024 * 1024)
            if not block:
                break
            output.write(block)
    if temporary.stat().st_size < 5_000_000:
        temporary.unlink(missing_ok=True)
        raise RuntimeError("downloaded HTTPS tunnel client is unexpectedly small")
    temporary.chmod(0o700)
    temporary.replace(binary)
    subprocess.run([str(binary), "--version"], timeout=8, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return str(binary)


def _start_portable_https_tunnel(port):
    """Launch a free browser-trusted HTTPS tunnel and return (process, URL)."""
    binary = _ensure_cloudflared()
    process = subprocess.Popen(
        [binary, "tunnel", "--no-autoupdate", "--protocol", "http2",
         "--url", f"http://127.0.0.1:{port}"],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace", bufsize=1,
    )
    deadline = time.monotonic() + 75
    address = ""
    try:
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError("HTTPS tunnel stopped before publishing an address")
            line = process.stderr.readline()
            match = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line or "")
            if match:
                address = match.group(0)
                break
        if not address:
            raise RuntimeError("timed out while requesting a public HTTPS address")
        threading.Thread(
            target=lambda: deque(process.stderr, maxlen=0),
            name="https-tunnel-log-drain", daemon=True,
        ).start()
        return process, address
    except Exception:
        process.terminate()
        raise


def _existing_public_https_url():
    """Recover the newest tunnel link so repeat launches print one useful URL."""
    stored = Path.home() / ".config" / "mtdi-studio" / "public_url"
    try:
        value = stored.read_text(encoding="utf-8").strip()
        if value.startswith("https://"):
            return value
    except OSError:
        pass
    # Compatibility with the persistent service installed on the original Pi.
    try:
        text = (Path.home() / "studio-tunnel.log").read_text(
            encoding="utf-8", errors="replace"
        )[-200_000:]
        matches = re.findall(r"https://[a-z0-9-]+\.trycloudflare\.com", text)
        if matches:
            return matches[-1]
    except OSError:
        pass
    return ""


def _cloud_encrypt(text):
    """Authenticated PRF stream encryption; its master secret never enters Notion."""
    master = _cloud_cipher_secret().encode("utf-8")
    if not master:
        return ""
    nonce = secrets.token_bytes(24)
    enc_key = hmac.new(master, b"studio-cloud-encryption", hashlib.sha256).digest()
    mac_key = hmac.new(master, b"studio-cloud-authentication", hashlib.sha256).digest()
    raw = text.encode("utf-8")
    stream = bytearray()
    counter = 0
    while len(stream) < len(raw):
        stream.extend(hmac.new(
            enc_key, nonce + counter.to_bytes(8, "big"), hashlib.sha256
        ).digest())
        counter += 1
    ciphertext = bytes(a ^ b for a, b in zip(raw, stream))
    body = b"IVC1" + nonce + ciphertext
    tag = hmac.new(mac_key, body, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(body + tag).decode("ascii")


def _cloud_decrypt(encoded):
    """Authenticate and decrypt a Notion credential record."""
    master = _cloud_cipher_secret().encode("utf-8")
    if not master or not encoded:
        return ""
    try:
        packed = base64.urlsafe_b64decode(encoded.encode("ascii"))
        if len(packed) < 4 + 24 + 32 or packed[:4] != b"IVC1":
            return ""
        body, supplied_tag = packed[:-32], packed[-32:]
        mac_key = hmac.new(
            master, b"studio-cloud-authentication", hashlib.sha256
        ).digest()
        expected = hmac.new(mac_key, body, hashlib.sha256).digest()
        if not hmac.compare_digest(supplied_tag, expected):
            return ""
        nonce, ciphertext = body[4:28], body[28:]
        enc_key = hmac.new(
            master, b"studio-cloud-encryption", hashlib.sha256
        ).digest()
        stream = bytearray()
        counter = 0
        while len(stream) < len(ciphertext):
            stream.extend(hmac.new(
                enc_key, nonce + counter.to_bytes(8, "big"), hashlib.sha256
            ).digest())
            counter += 1
        return bytes(a ^ b for a, b in zip(ciphertext, stream)).decode("utf-8")
    except (ValueError, UnicodeError):
        return ""


def _configure_logging(level="INFO", log_path=None, console=False):
    """Write diagnostics to a rotating file; terminal logging is explicit."""
    numeric = getattr(logging, str(level).upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(numeric)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    for handler in list(root.handlers):
        if getattr(handler, "_studio_console", False) and not console:
            root.removeHandler(handler)
            handler.close()
    if console and not any(
        getattr(h, "_studio_console", False) for h in root.handlers
    ):
        console_handler = logging.StreamHandler()
        console_handler._studio_console = True
        console_handler.setFormatter(formatter)
        root.addHandler(console_handler)
    if log_path and not any(
        getattr(h, "_studio_file", False) for h in root.handlers
    ):
        path = Path(log_path).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.parent.chmod(0o700)
        except OSError:
            pass
        file_handler = RotatingFileHandler(
            path, maxBytes=5_000_000, backupCount=3, encoding="utf-8"
        )
        try:
            path.chmod(0o600)
        except OSError:
            pass
        file_handler._studio_file = True
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)


class ArchiveStore:
    """Single-writer SQLite archive; acquisition workers only enqueue short records."""

    def __init__(self, path):
        self.path = Path(path).expanduser()
        self.items = queue.Queue(maxsize=1000)
        self.last_write = None
        self.last_error = None
        self.session_id = None

    def put(self, kind, payload):
        try:
            self.items.put_nowait((kind, payload))
        except queue.Full:
            self.last_error = "archive queue full; newest record was not stored"
            LOG.error(self.last_error)

    def _open(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(self.path, timeout=15)
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA foreign_keys=ON")
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions(
              id INTEGER PRIMARY KEY, started_at REAL NOT NULL, ended_at REAL,
              source_tag TEXT NOT NULL, app_version TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS rf_sweeps(
              id INTEGER PRIMARY KEY, session_id INTEGER NOT NULL, started_at REAL NOT NULL,
              completed_at REAL NOT NULL, duration_s REAL NOT NULL, profile TEXT NOT NULL,
              start_hz INTEGER NOT NULL, stop_hz INTEGER NOT NULL, requested_points INTEGER NOT NULL,
              returned_points INTEGER NOT NULL, repeat_count INTEGER NOT NULL, bin_width_hz REAL NOT NULL,
              frequencies_json TEXT NOT NULL, levels_json TEXT NOT NULL, peaks_json TEXT NOT NULL,
              warnings_json TEXT NOT NULL, trusted INTEGER NOT NULL, firmware TEXT,
              device_port TEXT, transport TEXT NOT NULL, raw_response TEXT,
              FOREIGN KEY(session_id) REFERENCES sessions(id)
            );
            CREATE INDEX IF NOT EXISTS idx_rf_sweeps_time ON rf_sweeps(started_at);
            CREATE TABLE IF NOT EXISTS magnetometer_samples(
              id INTEGER PRIMARY KEY, session_id INTEGER NOT NULL, captured_at REAL NOT NULL,
              x_ut REAL NOT NULL, y_ut REAL NOT NULL, z_ut REAL NOT NULL, magnitude_ut REAL NOT NULL,
              trusted INTEGER NOT NULL, warning TEXT,
              FOREIGN KEY(session_id) REFERENCES sessions(id)
            );
            CREATE INDEX IF NOT EXISTS idx_mag_time ON magnetometer_samples(captured_at);
            CREATE TABLE IF NOT EXISTS efield_samples(
              id INTEGER PRIMARY KEY, session_id INTEGER NOT NULL, captured_at REAL NOT NULL,
              rms_mv REAL NOT NULL, peak_activity_mv REAL NOT NULL, baseline_mv REAL NOT NULL,
              relative_ratio REAL NOT NULL, relative_index REAL NOT NULL, gain REAL NOT NULL,
              clipped INTEGER NOT NULL, trusted INTEGER NOT NULL, warning TEXT,
              FOREIGN KEY(session_id) REFERENCES sessions(id)
            );
            CREATE INDEX IF NOT EXISTS idx_efield_time ON efield_samples(captured_at);
            CREATE TABLE IF NOT EXISTS wifi_discoveries(
              id INTEGER PRIMARY KEY, session_id INTEGER NOT NULL, captured_at REAL NOT NULL,
              scan_mode TEXT NOT NULL, interface TEXT, records_json TEXT NOT NULL,
              FOREIGN KEY(session_id) REFERENCES sessions(id)
            );
            CREATE TABLE IF NOT EXISTS bluetooth_discoveries(
              id INTEGER PRIMARY KEY, session_id INTEGER NOT NULL, captured_at REAL NOT NULL,
              scan_mode TEXT NOT NULL, adapter TEXT, records_json TEXT NOT NULL,
              FOREIGN KEY(session_id) REFERENCES sessions(id)
            );
            CREATE TABLE IF NOT EXISTS system_health(
              id INTEGER PRIMARY KEY, session_id INTEGER NOT NULL, captured_at REAL NOT NULL,
              payload_json TEXT NOT NULL,
              FOREIGN KEY(session_id) REFERENCES sessions(id)
            );
            CREATE TABLE IF NOT EXISTS events(
              id INTEGER PRIMARY KEY, session_id INTEGER, captured_at REAL NOT NULL,
              severity TEXT NOT NULL, source TEXT NOT NULL, message TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS calibration_profiles(
              id INTEGER PRIMARY KEY, sensor TEXT NOT NULL, created_at REAL NOT NULL,
              active INTEGER NOT NULL DEFAULT 0, payload_json TEXT NOT NULL
            );
            """
        )
        row = con.execute(
            "INSERT INTO sessions(started_at, source_tag, app_version) VALUES(?,?,?)",
            (time.time(), RUNTIME["session_tag"], APP_VERSION),
        )
        self.session_id = row.lastrowid
        con.commit()
        return con

    def _write(self, con, kind, p):
        sid = self.session_id
        if kind == "rf":
            con.execute(
                """INSERT INTO rf_sweeps(
                session_id,started_at,completed_at,duration_s,profile,start_hz,stop_hz,
                requested_points,returned_points,repeat_count,bin_width_hz,frequencies_json,
                levels_json,peaks_json,warnings_json,trusted,firmware,device_port,transport,
                raw_response) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    sid, p["started_at"], p["completed_at"], p["duration_s"],
                    p["profile"], p["start_hz"], p["stop_hz"], p["requested_points"],
                    len(p["frequencies"]), p["repeat"], p["bin_width_hz"],
                    json.dumps(p["frequencies"], separators=(",", ":")),
                    json.dumps(p["levels"], separators=(",", ":")),
                    json.dumps(p["peaks"], separators=(",", ":")),
                    json.dumps(p["warnings"], separators=(",", ":")), int(p["trusted"]),
                    p.get("firmware"), p.get("port"), p.get("transport", "serial-text-scan"),
                    p.get("raw_response"),
                ),
            )
        elif kind == "mag":
            con.execute(
                """INSERT INTO magnetometer_samples(
                session_id,captured_at,x_ut,y_ut,z_ut,magnitude_ut,trusted,warning)
                VALUES(?,?,?,?,?,?,?,?)""",
                (sid, p["t"], p["x"], p["y"], p["z"], p["mag"], int(p["trusted"]), p.get("warning")),
            )
        elif kind == "efield":
            con.execute(
                """INSERT INTO efield_samples(
                session_id,captured_at,rms_mv,peak_activity_mv,baseline_mv,relative_ratio,
                relative_index,gain,clipped,trusted,warning) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (sid, p["t"], p["rms_mv"], p["peak_mv"], p["baseline_mv"], p["ratio"],
                 p["rel_index"], p["gain"], int(p["clipped"]), int(p["trusted"]), p.get("warning")),
            )
        elif kind == "wifi":
            con.execute(
                "INSERT INTO wifi_discoveries(session_id,captured_at,scan_mode,interface,records_json) VALUES(?,?,?,?,?)",
                (sid, p["t"], p["mode"], p.get("iface"), json.dumps(p["records"], separators=(",", ":"))),
            )
        elif kind == "bluetooth":
            con.execute(
                "INSERT INTO bluetooth_discoveries(session_id,captured_at,scan_mode,adapter,records_json) VALUES(?,?,?,?,?)",
                (sid, p["t"], p["mode"], p.get("adapter"), json.dumps(p["records"], separators=(",", ":"))),
            )
        elif kind == "system":
            con.execute(
                "INSERT INTO system_health(session_id,captured_at,payload_json) VALUES(?,?,?)",
                (sid, p["t"], json.dumps(p["payload"], separators=(",", ":"))),
            )
        elif kind == "event":
            con.execute(
                "INSERT INTO events(session_id,captured_at,severity,source,message) VALUES(?,?,?,?,?)",
                (sid, p.get("t", time.time()), p["severity"], p["source"], p["message"]),
            )
        elif kind == "calibration":
            con.execute(
                "INSERT INTO calibration_profiles(sensor,created_at,active,payload_json) VALUES(?,?,?,?)",
                (
                    p["sensor"], p.get("t", time.time()), int(p.get("active", True)),
                    json.dumps(p["payload"], separators=(",", ":")),
                ),
            )
        else:
            raise ValueError(f"unknown archive record kind: {kind}")

    def history(self, minutes=10.0, points=240):
        """Read-only, downsampled view of the archive for the last `minutes`.

        Opens its own connection (WAL lets readers run beside the writer). Rows are bucketed
        into `points` time slots and each bucket reports the mean plus min/max so short
        spikes survive the downsampling. Nothing is synthesised: an empty archive returns
        empty lists.
        """
        minutes = max(0.1, min(float(minutes), 24 * 60.0))
        points = max(10, min(int(points), 2000))
        since = time.time() - minutes * 60.0
        out = {"since": since, "minutes": minutes, "points": points,
               "magnetometer": [], "efield": [], "rf": [], "events": []}
        if not self.path.exists():
            return out
        width = minutes * 60.0 / points
        try:
            con = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True, timeout=5)
        except sqlite3.Error as exc:
            out["error"] = str(exc)
            return out
        try:
            bucket = f"CAST((captured_at - {since!r}) / {width!r} AS INTEGER)"
            for row in con.execute(
                    f"SELECT MIN(captured_at), AVG(magnitude_ut), MIN(magnitude_ut), MAX(magnitude_ut), "
                    f"AVG(x_ut), AVG(y_ut), AVG(z_ut), COUNT(*), MIN(trusted) FROM magnetometer_samples "
                    f"WHERE captured_at >= ? GROUP BY {bucket} ORDER BY 1", (since,)):
                out["magnetometer"].append({"t": row[0], "magnitude_ut": row[1], "min_ut": row[2], "max_ut": row[3],
                                            "x_ut": row[4], "y_ut": row[5], "z_ut": row[6], "n": row[7],
                                            "trusted": bool(row[8])})
            for row in con.execute(
                    f"SELECT MIN(captured_at), AVG(rms_mv), MIN(rms_mv), MAX(rms_mv), AVG(baseline_mv), "
                    f"AVG(relative_index), COUNT(*), MAX(clipped), MIN(trusted) FROM efield_samples "
                    f"WHERE captured_at >= ? GROUP BY {bucket} ORDER BY 1", (since,)):
                out["efield"].append({"t": row[0], "rms_mv": row[1], "min_mv": row[2], "max_mv": row[3],
                                      "baseline_mv": row[4], "relative_index": row[5], "n": row[6],
                                      "clipped": bool(row[7]), "trusted": bool(row[8])})
            for row in con.execute(
                    "SELECT completed_at, start_hz, stop_hz, peaks_json, levels_json, trusted FROM rf_sweeps "
                    "WHERE completed_at >= ? ORDER BY completed_at DESC LIMIT ?", (since, points)):
                try:
                    peaks = json.loads(row[3] or "[]")[:3]
                    levels = json.loads(row[4] or "[]")
                except ValueError:
                    peaks, levels = [], []
                floor = sorted(levels)[len(levels) // 4] if levels else None
                out["rf"].append({"t": row[0], "start_hz": row[1], "stop_hz": row[2], "floor_dbm": floor,
                                  "peak_dbm": max(levels) if levels else None, "peaks": peaks, "trusted": bool(row[5])})
            out["rf"].reverse()
            for row in con.execute(
                    "SELECT captured_at, severity, source, message FROM events WHERE captured_at >= ? "
                    "ORDER BY captured_at DESC LIMIT 200", (since,)):
                out["events"].append({"t": row[0], "severity": row[1], "source": row[2], "message": row[3]})
            out["events"].reverse()
        except sqlite3.Error as exc:
            out["error"] = str(exc)
        finally:
            con.close()
        return out

    # ── retention ─────────────────────────────────────────────────────────────
    # OFF by default. The archive is the author's measured data and deleting any of
    # it is his decision, not the instrument's, so nothing is removed unless
    # STUDIO_RETENTION_DAYS is set to a positive number.
    #
    # Why it exists: measured on this host on 23 Sep 2026, the archive was 10.85 GB
    # on a 29 GB card with 7.0 GB free, over a 46.1 day span - about 235 MB a day,
    # so roughly 30 days from filling the card. The service does not survive a full
    # card. The bulk is not the four channel tables; it is `raw_samples`, at 15.1
    # million rows, one JSON document per magnetometer sample, each one repeating
    # the whole calibration profile and warning string - measured at 416 B average
    # over a 20,000-row sample, so 6.31 GB of JSON text out of a 10.92 GB file.
    # That table is not in the PDF's table list, so it grew entirely unseen.
    #
    # Only the high-rate sample tables are pruned. Sessions, events and calibration
    # profiles are small and are the provenance record, so they are never touched.
    RETENTION_TABLES = (("raw_samples", "captured_at"),
                        ("magnetometer_samples", "captured_at"),
                        ("efield_samples", "captured_at"),
                        ("system_health", "captured_at"))
    RETENTION_INTERVAL = 900.0     # seconds between prune passes
    # Stop recording before the card fills rather than after. A full filesystem
    # does not merely lose the next row: SQLite can fail mid-transaction and
    # leave the database unusable, which loses everything already captured. The
    # archive was 17.4 million rows on a card at 78% when this was written, with
    # retention off by the operator's choice, so the instrument has to be able to
    # protect the record it already holds.
    #
    # Paused is a state the instrument reports, never one it hides: the channels
    # keep measuring and displaying, and only the writing to disk stops.
    DISK_FLOOR_MB = float(os.environ.get("STUDIO_ARCHIVE_FLOOR_MB", "600"))
    DISK_RESUME_MB = DISK_FLOOR_MB * 1.5   # hysteresis, so it cannot flap
    DISK_CHECK_INTERVAL = 30.0
    RETENTION_BATCH = 20000        # rows per statement, so the writer is never blocked long

    def retention_days(self):
        try:
            return max(0.0, float(os.environ.get("STUDIO_RETENTION_DAYS", "0") or 0))
        except ValueError:
            return 0.0

    def prune(self, con, days=None):
        """Delete sample rows older than `days`. Returns {table: rows_deleted}."""
        days = self.retention_days() if days is None else float(days)
        removed = {}
        if days <= 0:
            return removed
        cutoff = time.time() - days * 86400.0
        for table, column in self.RETENTION_TABLES:
            total = 0
            while True:
                # Bounded deletes: one unbounded DELETE over 15 million rows would
                # hold the write lock long enough to fill the acquisition queue and
                # drop live samples, which is exactly what must not happen.
                cursor = con.execute(
                    f"DELETE FROM {table} WHERE id IN "
                    f"(SELECT id FROM {table} WHERE {column} < ? LIMIT ?)",
                    (cutoff, self.RETENTION_BATCH))
                con.commit()
                if not cursor.rowcount:
                    break
                total += cursor.rowcount
                if ARCHIVE_STOP_EVENT.is_set():
                    break
            if total:
                removed[table] = total
        if removed:
            LOG.warning("Archive retention removed %s (older than %.1f days). "
                        "Space is reclaimed on the next VACUUM.",
                        ", ".join(f"{v:,} from {k}" for k, v in removed.items()), days)
        return removed

    def free_mb(self):
        try:
            return shutil.disk_usage(self.path.parent).free / (1024 * 1024)
        except Exception:
            return None            # unknown is not low: never pause on a bad read

    def worker(self):
        con = None
        next_prune = time.monotonic() + 60.0
        next_disk = 0.0
        self.paused_for_disk = False
        try:
            con = self._open()
            while not ARCHIVE_STOP_EVENT.is_set() or not self.items.empty():
                if self.retention_days() and time.monotonic() >= next_prune:
                    next_prune = time.monotonic() + self.RETENTION_INTERVAL
                    try:
                        self.prune(con)
                    except Exception:
                        LOG.exception("Archive retention pass failed")
                if time.monotonic() >= next_disk:
                    next_disk = time.monotonic() + self.DISK_CHECK_INTERVAL
                    free = self.free_mb()
                    if free is not None:
                        if not self.paused_for_disk and free < self.DISK_FLOOR_MB:
                            self.paused_for_disk = True
                            self.last_error = ("Archive paused: %.0f MB free, below the %.0f MB floor. "
                                               "Measurement continues; recording to disk has stopped so a "
                                               "full card cannot corrupt the archive."
                                               % (free, self.DISK_FLOOR_MB))
                            LOG.warning(self.last_error)
                        elif self.paused_for_disk and free >= self.DISK_RESUME_MB:
                            self.paused_for_disk = False
                            self.last_error = None
                            LOG.warning("Archive resumed: %.0f MB free.", free)
                try:
                    kind, payload = self.items.get(timeout=0.5)
                except queue.Empty:
                    continue
                if self.paused_for_disk:
                    continue       # drained so the queue cannot back up behind the pause
                try:
                    self._write(con, kind, payload)
                    con.commit()
                    self.last_write = time.time()
                    self.last_error = None
                except Exception as exc:
                    con.rollback()
                    self.last_error = str(exc)
                    LOG.exception("Archive write failed for %s", kind)
                finally:
                    self.items.task_done()
        except Exception as exc:
            self.last_error = str(exc)
            LOG.exception("Archive worker failed")
        finally:
            if con is not None:
                try:
                    if self.session_id is not None:
                        con.execute(
                            "UPDATE sessions SET ended_at=? WHERE id=?",
                            (time.time(), self.session_id),
                        )
                        con.commit()
                    con.close()
                except Exception:
                    LOG.exception("Archive shutdown failed")


ARCHIVE = ArchiveStore(
    os.environ.get(
        "STUDIO_DB", str(Path.home() / ".local/share/mtdi-studio/archive.sqlite3")
    )
)

CSV_STOP_EVENT = threading.Event()


class SessionCSVLogger:
    """Per-session raw sample log in CSV, for offline analysis and reporting.

    WHY THIS EXISTS, AND HOW IT DIFFERS FROM ``ArchiveStore``
    --------------------------------------------------------
    ``ArchiveStore`` persists to SQLite, but its magnetometer and E-field rows are
    written by ``archive_loop()``, which snapshots the *current* value once every
    3 seconds (see the ``STOP_EVENT.wait(3)`` at the end of that loop). The
    magnetometer read loop runs at roughly 20 Hz, so approximately 59 of every 60
    magnetometer samples were never persisted anywhere. Any results table or graph
    built from the SQLite archive is therefore a 0.33 Hz decimation of the signal,
    not the signal itself.

    This logger is called directly from each acquisition loop, so it records every
    sample the hardware actually produced, at the rate it produced them.

    FORMAT
    ------
    One file per session, ISO-8601 timestamp on every row, plus a commented
    metadata header carrying the fields needed to caption a figure: start time,
    location label, source label, distance in cm, and operator notes.

    Rows are long-format: one ``channel`` column ("mag", "efield", "rf") and a
    superset of columns, with unused columns left empty. This keeps a single file
    per session (as required) while remaining directly loadable:

        import pandas as pd
        df = pd.read_csv(path, comment="#", parse_dates=["iso_time"])
        mag = df[df.channel == "mag"].dropna(axis=1, how="all")

    An RF row is one completed sweep, summarised (peak, floor, span). The full
    per-bin arrays are large and stay in SQLite; ``export_rf_csv_bytes()`` already
    flattens those to one row per frequency bin when needed.

    Writes go through a queue and a single writer thread so that a slow SD card
    can never stall the I2C or serial acquisition loops.
    """

    # `data_source` is deliberately a per-ROW column, not only a header field.
    # Comment headers get stripped by spreadsheet imports and lost when sessions
    # are concatenated; a simulated row must stay identifiable as simulated no
    # matter how the file is later handled.
    COLUMNS = [
        "iso_time", "unix_time", "channel", "data_source",
        # magnetometer
        "mag_x_ut", "mag_y_ut", "mag_z_ut", "mag_total_ut",
        "mag_raw_x_ut", "mag_raw_y_ut", "mag_raw_z_ut",
        "mag_calibrated", "mag_trusted",
        # e-field
        "ef_rms_mv", "ef_peak_mv", "ef_baseline_mv",
        "ef_field_v_m", "ef_peak_v_m", "ef_baseline_v_m", "ef_ratio",
        "ef_rel_index_pct", "ef_gain", "ef_utilisation_pct",
        "ef_clipped", "ef_calibrated", "ef_trusted",
        # spectrum
        "rf_start_hz", "rf_stop_hz", "rf_points", "rf_sweep_s",
        "rf_peak_hz", "rf_peak_dbm", "rf_floor_dbm", "rf_trusted",
        "note",
    ]

    def __init__(self, directory=None, enabled=False, metadata=None):
        self.enabled = enabled
        self.directory = Path(directory or os.environ.get(
            "STUDIO_CSV_DIR", str(Path.home() / "studio-sessions")
        )).expanduser()
        self.metadata = dict(metadata or {})
        self.items = queue.Queue(maxsize=20000)
        self.path = None
        self.rows_written = 0
        self.dropped = 0
        self.last_error = None

    # ── producer side: called from the acquisition loops ──
    def _put(self, row):
        if not self.enabled:
            return
        row["data_source"] = "SIMULATED" if RUNTIME["demo"] else "hardware"
        try:
            self.items.put_nowait(row)
        except queue.Full:
            # Never block an acquisition loop. Count the loss so it is reportable
            # rather than silent — a dropped sample must not look like a real gap.
            self.dropped += 1
            if self.dropped in (1, 100, 1000) or self.dropped % 10000 == 0:
                LOG.error("CSV logger queue full; %d sample(s) dropped", self.dropped)

    def log_mag(self, t, x, y, z, total, raw, calibrated, trusted, note=None):
        self._put({
            "unix_time": t, "channel": "mag",
            "mag_x_ut": x, "mag_y_ut": y, "mag_z_ut": z, "mag_total_ut": total,
            "mag_raw_x_ut": raw[0], "mag_raw_y_ut": raw[1], "mag_raw_z_ut": raw[2],
            "mag_calibrated": int(bool(calibrated)), "mag_trusted": int(bool(trusted)),
            "note": note,
        })

    def log_efield(self, t, rms_mv, peak_mv, baseline_mv, ratio, rel_index,
                   gain, utilisation, clipped, calibrated, trusted, note=None):
        self._put({
            "unix_time": t, "channel": "efield",
            "ef_rms_mv": rms_mv, "ef_peak_mv": peak_mv, "ef_baseline_mv": baseline_mv,
            "ef_field_v_m": _ef_v_per_m(rms_mv),
            "ef_peak_v_m": _ef_v_per_m(peak_mv),
            "ef_baseline_v_m": _ef_v_per_m(baseline_mv),
            "ef_ratio": ratio, "ef_rel_index_pct": rel_index, "ef_gain": gain,
            "ef_utilisation_pct": utilisation, "ef_clipped": int(bool(clipped)),
            "ef_calibrated": int(bool(calibrated)), "ef_trusted": int(bool(trusted)),
            "note": note,
        })

    def log_rf(self, t, start_hz, stop_hz, points, sweep_s,
               peak_hz, peak_dbm, floor_dbm, trusted, note=None):
        self._put({
            "unix_time": t, "channel": "rf",
            "rf_start_hz": start_hz, "rf_stop_hz": stop_hz, "rf_points": points,
            "rf_sweep_s": sweep_s, "rf_peak_hz": peak_hz, "rf_peak_dbm": peak_dbm,
            "rf_floor_dbm": floor_dbm, "rf_trusted": int(bool(trusted)),
            "note": note,
        })

    # ── consumer side ──
    def _header_lines(self):
        md = self.metadata
        started = md.get("started_unix", time.time())
        def fmt(v):
            return "" if v is None else str(v)
        return [
            "# MTDI Studio raw session log",
            f"# app_version: {APP_VERSION}",
            f"# session_start_iso: {self._iso(started)}",
            f"# session_start_unix: {started:.6f}",
            f"# data_source: {md.get('data_source', RUNTIME['session_tag'])}",
            f"# location_label: {fmt(md.get('location'))}",
            f"# source_label: {fmt(md.get('source_label'))}",
            f"# distance_cm: {fmt(md.get('distance_cm'))}",
            f"# operator_notes: {fmt(md.get('operator_notes'))}",
            f"# magnetometer_lsb_per_ut: {LSB_PER_UT}",
            f"# magnetometer_calibration_file: "
            f"{fmt(os.environ.get('STUDIO_MAG_CALIBRATION') or None)}",
            f"# efield_samples_per_block: {SAMPLES_PER_BLOCK}",
            f"# efield_adc_sps: {ADS_DATA_RATE}",
            f"# efield_probe_scale_v_per_m_per_input_v: {EF_V_PER_M_PER_VOLT}",
            f"# efield_units: *_mv columns preserve ADC input voltage; *_v_m columns "
            f"use the configured probe scale. 1 V/m = 1 N/C. ef_rel_index_pct is "
            f"relative to the learned session baseline",
            f"# rf_units: unit as returned by the TinySA text scan, no conversion applied",
            "# one row per sample; empty columns are not applicable to that channel",
        ]

    @staticmethod
    def _iso(t):
        return (time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(t))
                + f".{int((t % 1) * 1e6):06d}Z")

    def _open(self):
        import csv as _csv
        self.directory.mkdir(parents=True, exist_ok=True)
        started = self.metadata.get("started_unix", time.time())
        stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime(started))
        label = re.sub(r"[^A-Za-z0-9_-]+", "-",
                       str(self.metadata.get("location") or "session")).strip("-") or "session"
        self.path = self.directory / f"studio_{stamp}_{label}.csv"
        handle = self.path.open("w", encoding="utf-8", newline="")
        for line in self._header_lines():
            handle.write(line + "\n")
        writer = _csv.DictWriter(handle, fieldnames=self.COLUMNS, extrasaction="ignore")
        writer.writeheader()
        handle.flush()
        return handle, writer

    def worker(self):
        if not self.enabled:
            return
        handle = writer = None
        last_flush = time.monotonic()
        try:
            handle, writer = self._open()
            LOG.info("CSV session log: %s", self.path)
            while not CSV_STOP_EVENT.is_set() or not self.items.empty():
                try:
                    row = self.items.get(timeout=0.5)
                except queue.Empty:
                    if handle and time.monotonic() - last_flush > 2.0:
                        handle.flush(); last_flush = time.monotonic()
                    continue
                try:
                    row["iso_time"] = self._iso(row["unix_time"])
                    row["unix_time"] = f"{row['unix_time']:.6f}"
                    writer.writerow(row)
                    self.rows_written += 1
                    # Flush on a time budget, not per row: an SD card cannot take
                    # an fsync at 20 Hz, but an hour of data must not be lost to a
                    # power cut either.
                    if time.monotonic() - last_flush > 2.0:
                        handle.flush(); last_flush = time.monotonic()
                except Exception as exc:
                    self.last_error = str(exc)
                    LOG.exception("CSV row write failed")
                finally:
                    self.items.task_done()
        except Exception as exc:
            self.last_error = str(exc)
            LOG.exception("CSV logger failed")
        finally:
            if handle is not None:
                try:
                    handle.flush(); handle.close()
                    LOG.info("CSV session log closed: %s (%d rows, %d dropped)",
                             self.path, self.rows_written, self.dropped)
                except Exception:
                    LOG.exception("CSV logger close failed")


CSV_LOG = SessionCSVLogger()


def export_archive_json_bytes():
    """Export the fixed archive schema; no caller-controlled table or path is used."""
    if not ARCHIVE.path.exists():
        return json.dumps({"error":"archive database does not exist"}, indent=2).encode()
    con = sqlite3.connect(ARCHIVE.path, timeout=15)
    con.row_factory = sqlite3.Row
    try:
        output = {"app_version":APP_VERSION, "exported_at":time.time(), "tables":{}}
        tables = (
            "sessions", "rf_sweeps", "magnetometer_samples", "efield_samples",
            "wifi_discoveries", "bluetooth_discoveries", "system_health",
            "events", "calibration_profiles", "raw_samples",
        )
        for table in tables:
            if not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone():
                continue
            rows = []
            for row in con.execute(f"SELECT * FROM {table}"):
                record = dict(row)
                for key, value in list(record.items()):
                    if key.endswith("_json") and isinstance(value, str):
                        try:
                            record[key[:-5]] = json.loads(value)
                            del record[key]
                        except json.JSONDecodeError:
                            record[key] = value
                rows.append(record)
            output["tables"][table] = rows
        return json.dumps(output, indent=2, sort_keys=True).encode("utf-8")
    finally:
        con.close()


def export_rf_csv_bytes():
    """Flatten archived RF sweeps to one frequency/level row per returned bin."""
    import csv
    import io
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow([
        "sweep_id", "session_id", "completed_at", "profile", "trusted",
        "frequency_hz", "level_dbm",
    ])
    if ARCHIVE.path.exists():
        con = sqlite3.connect(ARCHIVE.path, timeout=15)
        try:
            for row in con.execute(
                "SELECT id,session_id,completed_at,profile,trusted,frequencies_json,levels_json "
                "FROM rf_sweeps ORDER BY id"
            ):
                frequencies = json.loads(row[5])
                levels = json.loads(row[6])
                for frequency, level in zip(frequencies, levels):
                    writer.writerow([row[0], row[1], row[2], row[3], row[4], frequency, level])
        finally:
            con.close()
    return stream.getvalue().encode("utf-8")

try:
    import psutil
except Exception:
    psutil = None

