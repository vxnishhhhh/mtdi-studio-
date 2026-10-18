"""Create a project's page in Notion.

Needs an internal integration token (NOTION_TOKEN) and the id of a page the
integration has been shared with (NOTION_PARENT_PAGE_ID). The new page holds the
project's description, its channels and pillars, and links to its repository and
deployment.
"""
import os
import re

from . import IntegrationError, http, token

API = "https://api.notion.com/v1/pages"
VERSION = "2022-06-28"


def _text(content):
    return [{"type": "text", "text": {"content": content[:1900]}}]


def _block(kind, content):
    return {"object": "block", "type": kind, kind: {"rich_text": _text(content)}}


def page_body(project, parent, links=None):
    meta = project["project"]
    plain = lambda s: re.sub(r"\[\[|\]\]", "", s or "")
    children = [_block("callout", f"MTDI {project.get('mtdi', '5.0')} project · {meta.get('domain', 'generic')}"),
                _block("paragraph", plain(meta.get("description", ""))),
                _block("heading_2", "Channels")]
    for ch in project["channels"]:
        children.append(_block("bulleted_list_item",
                               f"{ch['label']} — {ch['domain']}, keys {', '.join(ch['keys'])}"
                               + (f", unit {ch['unit']}" if ch["unit"] else "") + f", source {'/'.join(ch['sources'])}"))
    children.append(_block("heading_2", "Pillars"))
    for p in ("00 Validation Chamber", "01 Environmental Intelligence", "02 NVTRA", "03 I³", "04 Aether"):
        children.append(_block("to_do", p))
    for label, url in (links or {}).items():
        if url:
            children.append({"object": "block", "type": "bookmark", "bookmark": {"url": url, "caption": _text(label)}})
    return {"parent": {"page_id": parent},
            "properties": {"title": {"title": _text(meta.get("name", meta["id"]))}},
            "children": children[:100]}


def create(project, links=None, parent=None, dry_run=False):
    parent = (parent or os.environ.get("NOTION_PARENT_PAGE_ID", "")).replace("-", "").strip()
    if not dry_run and not re.fullmatch(r"[0-9a-fA-F]{32}", parent):
        raise IntegrationError("NOTION_PARENT_PAGE_ID must be the 32-character id of a page shared with your integration")
    body = page_body(project, parent or "<parent page id>", links)
    if dry_run:
        return {"dry_run": True, "request": body}
    result = http("POST", API, token("NOTION_TOKEN"), body, headers={"Notion-Version": VERSION})
    return {"url": result.get("url"), "id": result.get("id")}
