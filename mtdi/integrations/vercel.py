"""Deploy the studio (the live interface and API) to Vercel for one project.

Steps, all through the Vercel REST API with VERCEL_TOKEN (and VERCEL_TEAM_ID for a team):

1. create the Vercel project (framework: Flask) unless it already exists
2. store a fresh STUDIO_INGEST_TOKEN as an encrypted environment variable, so the
   deployed studio accepts data only from you
3. upload every file once by its SHA-1, then create a production deployment

Vercel runs the interface; your sources keep running where they are, and
``python -m mtdi run <project> --studio-url <url>`` streams them to it.
"""
import hashlib
import os
import pathlib
import re
import secrets

from . import IntegrationError, http, token

API = "https://api.vercel.com"
NAME = re.compile(r"^[a-z0-9]([a-z0-9\-]{0,98}[a-z0-9])?$")
ROOT = pathlib.Path(__file__).resolve().parents[2]
INCLUDE = ["app.py", "run.py", "requirements.txt", ".python-version", "vercel.json", "LICENSE",
           "studio/**/*", "mtdi/**/*", "public/**/*"]
SKIP = re.compile(r"(__pycache__|\.pyc$|\.gz$|\.tmp$|/models/)")


def _q(extra=""):
    team = os.environ.get("VERCEL_TEAM_ID", "").strip()
    parts = ([f"teamId={team}"] if team else []) + ([extra] if extra else [])
    return ("?" + "&".join(parts)) if parts else ""


def _files(project):
    seen = {}
    patterns = list(INCLUDE)
    folder = pathlib.Path(project.get("_dir") or "").resolve()
    if project.get("_dir") and ROOT in folder.parents:
        patterns.append(f"{folder.relative_to(ROOT).as_posix()}/**/*")
    for pattern in patterns:
        for path in sorted(ROOT.glob(pattern)):
            rel = path.relative_to(ROOT).as_posix()
            if path.is_file() and not SKIP.search(rel) and rel not in seen:
                data = path.read_bytes()
                seen[rel] = {"file": rel, "sha": hashlib.sha1(data).hexdigest(), "size": len(data), "_data": data}
    return list(seen.values())


def deploy(project, name, dry_run=False):
    if not NAME.match(name or ""):
        raise IntegrationError("Vercel project names use lowercase letters, digits and dashes (max 100)")
    files = _files(project)
    body = {"name": name, "target": "production", "project": name,
            "files": [{k: f[k] for k in ("file", "sha", "size")} for f in files],
            "projectSettings": {"framework": "flask"}}
    if dry_run:
        return {"dry_run": True, "files": len(files), "bytes": sum(f["size"] for f in files),
                "request": {k: v for k, v in body.items() if k != "files"}}
    tok = token("VERCEL_TOKEN")
    try:
        http("POST", f"{API}/v10/projects{_q()}", tok, {"name": name, "framework": "flask"})
    except IntegrationError as error:
        if "409" not in str(error) and "exist" not in str(error).lower():
            raise
    ingest_token = secrets.token_urlsafe(24)
    http("POST", f"{API}/v10/projects/{name}/env{_q('upsert=true')}", tok,
         {"key": "STUDIO_INGEST_TOKEN", "value": ingest_token, "type": "encrypted",
          "target": ["production", "preview"]})
    for f in files:
        http("POST", f"{API}/v2/files{_q()}", tok, raw=f["_data"],
             headers={"Content-Type": "application/octet-stream", "x-vercel-digest": f["sha"],
                      "Content-Length": str(f["size"])})
    result = http("POST", f"{API}/v13/deployments{_q('skipAutoDetectionConfirmation=1')}", tok, body)
    url = result.get("url")
    return {"url": f"https://{url}" if url and not url.startswith("http") else url, "id": result.get("id"),
            "state": result.get("readyState"), "project": name, "files": len(files),
            # shown once to the person who deployed; MTDI never writes it to disk
            "ingest_token": ingest_token}
