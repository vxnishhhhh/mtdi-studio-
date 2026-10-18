"""Serve the studio locally the way Vercel runs it (WSGI app, serverless mode).

    python tools/serve.py 8062            # http://127.0.0.1:8062
"""
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
os.environ.setdefault("STUDIO_SERVERLESS", "1")
os.environ.setdefault("HOME", tempfile.mkdtemp(prefix="mtdi-home-"))
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

import app  # noqa: E402
from werkzeug.serving import run_simple  # noqa: E402

run_simple("127.0.0.1", int(sys.argv[1]) if len(sys.argv) > 1 else 8062, app.app, threaded=True)
