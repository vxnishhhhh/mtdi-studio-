"""Deploy a project's static studio to Vercel.

Builds the project's studio as static pages (the real engine replayed on SIMULATED
data, see mtdi/site.py), uploads each file once by its SHA-1, then creates a
production deployment. The Vercel project is created by the first deployment with
the name you choose.
"""
import hashlib
import pathlib
import re
import tempfile

from . import IntegrationError, http, token

API = "https://api.vercel.com"
NAME = re.compile(r"^[a-z0-9]([a-z0-9\-]{0,98}[a-z0-9])?$")


def _team():
    import os
    team = os.environ.get("VERCEL_TEAM_ID", "").strip()
    return f"?teamId={team}" if team else ""


def deploy(project, name, dry_run=False, seconds=90):
    if not NAME.match(name or ""):
        raise IntegrationError("Vercel project names use lowercase letters, digits and dashes (max 100)")
    from ..site import build_project_site
    with tempfile.TemporaryDirectory() as tmp:
        out = build_project_site(project, pathlib.Path(tmp) / "site", seconds=seconds)
        files = []
        for f in sorted(p for p in out.rglob("*") if p.is_file()):
            data = f.read_bytes()
            files.append({"file": f.relative_to(out).as_posix(), "sha": hashlib.sha1(data).hexdigest(),
                          "size": len(data), "_data": data})
        body = {"name": name, "target": "production", "files": [{k: f[k] for k in ("file", "sha", "size")} for f in files],
                "projectSettings": {"framework": None, "buildCommand": None, "outputDirectory": None}}
        if dry_run:
            return {"dry_run": True, "files": len(files), "bytes": sum(f["size"] for f in files),
                    "request": {k: v for k, v in body.items() if k != "files"}}
        tok = token("VERCEL_TOKEN")
        for f in files:
            http("POST", f"{API}/v2/files{_team()}", tok, raw=f["_data"],
                 headers={"Content-Type": "application/octet-stream", "x-vercel-digest": f["sha"],
                          "Content-Length": str(f["size"])})
        result = http("POST", f"{API}/v13/deployments{_team()}&skipAutoDetectionConfirmation=1" if _team()
                      else f"{API}/v13/deployments?skipAutoDetectionConfirmation=1", tok, body)
    url = result.get("url")
    return {"url": f"https://{url}" if url and not url.startswith("http") else url, "id": result.get("id"),
            "state": result.get("readyState"), "project": name, "files": len(files)}
