"""Create a GitHub repository for a project and push it.

Prefers an authenticated `gh` CLI (it keeps its own credentials). Otherwise uses
GITHUB_TOKEN through the REST API and pushes with an in-memory auth header, so the
token never lands in .git/config.
"""
import base64
import shutil
import subprocess

from . import IntegrationError, http, token

API = "https://api.github.com"


def _gh_ready():
    if not shutil.which("gh"):
        return False
    return subprocess.run(["gh", "auth", "status"], capture_output=True).returncode == 0


def _git(args, cwd, extra=()):
    result = subprocess.run(["git", *extra, *args], cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise IntegrationError(f"git {' '.join(args)}: {result.stderr.strip()[:300]}")
    return result.stdout.strip()


def ensure_commit(path, message="Start project on MTDI 5.0"):
    if subprocess.run(["git", "rev-parse", "--git-dir"], cwd=path, capture_output=True).returncode != 0:
        _git(["init", "-b", "main"], path)
    _git(["add", "-A"], path)
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=path).returncode != 0:
        _git(["-c", "user.name=MTDI Studio", "-c", "user.email=mtdi@localhost", "commit", "-m", message], path)


def create(path, name, description="", private=True, dry_run=False):
    request = {"name": name, "description": description[:350], "private": private, "auto_init": False}
    if dry_run:
        return {"dry_run": True, "via": "gh" if _gh_ready() else "api", "request": request}
    ensure_commit(path)
    if _gh_ready():
        flag = "--private" if private else "--public"
        result = subprocess.run(["gh", "repo", "create", name, flag, "--source", str(path), "--push",
                                 "--description", description[:350]], capture_output=True, text=True)
        if result.returncode != 0:
            raise IntegrationError(f"gh repo create: {result.stderr.strip()[:300]}")
        url = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else f"https://github.com/{name}"
        return {"url": url, "via": "gh"}
    tok = token("GITHUB_TOKEN")
    repo = http("POST", f"{API}/user/repos", tok, request)
    url = repo["clone_url"]
    basic = base64.b64encode(f"x-access-token:{tok}".encode()).decode()
    if subprocess.run(["git", "remote", "get-url", "origin"], cwd=path, capture_output=True).returncode != 0:
        _git(["remote", "add", "origin", url], path)
    _git(["push", "-u", "origin", "main"], path, extra=["-c", f"http.extraheader=AUTHORIZATION: basic {basic}"])
    return {"url": repo["html_url"], "full_name": repo["full_name"], "via": "api"}
