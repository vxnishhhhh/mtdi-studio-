"""WSGI entry point (Vercel, gunicorn, any WSGI host).

Vercel's Python runtime looks for a module-level ``app`` here. A serverless host has
a read-only code directory and no long-running process, so state moves to /tmp and
the local HTTPS listener is switched off (the host already serves HTTPS).

Run locally with ``python run.py`` instead; it serves the same app on port 8050.
"""
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if os.environ.get("VERCEL") or os.environ.get("STUDIO_SERVERLESS"):
    os.environ["STUDIO_SERVERLESS"] = "1"
    home = pathlib.Path(tempfile.gettempdir()) / "mtdi-studio"
    home.mkdir(parents=True, exist_ok=True)
    os.environ["HOME"] = str(home)
    os.environ.setdefault("STUDIO_STATE_DIR", str(home / "state"))
    os.environ.setdefault("STUDIO_HTTPS_PORT", "0")
    os.environ.setdefault("STUDIO_FORCE_HTTPS", "0")
    os.environ.setdefault("STUDIO_RESTORE_CLOUD", "0")

from run import NAMESPACE  # noqa: E402  builds the whole app

NAMESPACE["LIFECYCLE"].start()
app = NAMESPACE["server"]
