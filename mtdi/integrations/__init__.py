"""Integrations: create everything a new MTDI project needs around it.

    github   create the repository and push           GITHUB_TOKEN, or an authenticated `gh` CLI
    vercel   deploy the project's static studio        VERCEL_TOKEN (+ VERCEL_TEAM_ID for a team)
    notion   create the project's Notion page          NOTION_TOKEN + NOTION_PARENT_PAGE_ID
    matlab   open MATLAB Online with a starter script  your browser's MathWorks sign-in

Tokens are read from the environment only. They are never written to a file, a
manifest, a git remote or a log line. Every integration supports dry_run, which
returns the exact request it would send (with the token redacted).
"""
import json
import os
import urllib.error
import urllib.request


class IntegrationError(RuntimeError):
    pass


def token(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise IntegrationError(f"{name} is not set. Create a token and run:  export {name}=...")
    return value


def http(method, url, token_value=None, body=None, headers=None, raw=None, timeout=60):
    """Send a request and decode a JSON reply. Kept in one place so tests can replace it."""
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(url, data=data, method=method)
    if token_value:
        req.add_header("Authorization", f"Bearer {token_value}")
    if body is not None and raw is None:
        req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode() or "{}"
            return json.loads(text) if text.strip().startswith(("{", "[")) else {"text": text}
    except urllib.error.HTTPError as error:
        detail = error.read().decode(errors="replace")[:400]
        raise IntegrationError(f"{method} {url.split('?')[0]} failed: HTTP {error.code} {detail}") from error
    except urllib.error.URLError as error:
        raise IntegrationError(f"{method} {url.split('?')[0]} failed: {error.reason}") from error
