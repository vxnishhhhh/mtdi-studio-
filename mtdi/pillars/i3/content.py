"""Content packs: the only thing a product writes to get an I³ interface.

A content pack is one JSON file (or the same structure as a Python dict). The
framework never hardcodes product text: every title, label, description and page
comes from here, so Inductra, MTDI Studio and AstroTech are three packs on one
framework. ``content/placeholder.json`` documents every field by example.

Inline markup inside any text field:
    [[term]]   renders as a highlighted technical term (the cyan mono span)
"""
import json
import pathlib
import re

from dash import html

PAGE_TYPES = {"home", "framework", "document", "module", "settings"}
_HIGHLIGHT = re.compile(r"\[\[(.+?)\]\]")


def load(path):
    """Read a content pack from disk and validate the parts the layout relies on."""
    data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    validate(data)
    return data


def validate(data):
    """Fail at startup, with the offending field named, instead of mid-render."""
    for key in ("brand", "pages"):
        if key not in data:
            raise ValueError(f"content pack is missing '{key}'")
    paths = set()
    for index, page in enumerate(data["pages"]):
        where = f"pages[{index}]"
        if page.get("type") not in PAGE_TYPES:
            raise ValueError(f"{where}.type must be one of {sorted(PAGE_TYPES)}")
        path = page.get("path", "")
        if not path.startswith("/"):
            raise ValueError(f"{where}.path must start with '/'")
        if path in paths:
            raise ValueError(f"{where}.path '{path}' is used twice")
        paths.add(path)
    if "/" not in paths:
        raise ValueError("content pack needs a page at path '/'")
    return data


def rich(text):
    """Turn a content string into Dash children, honouring [[term]] highlights."""
    if text is None:
        return None
    parts = _HIGHLIGHT.split(str(text))
    # split() alternates plain text and captured terms: even indexes are plain.
    return [part if i % 2 == 0 else html.Span(part, className="i3-hi")
            for i, part in enumerate(parts) if part]


def nav_pages(data):
    """Pages that appear in the header, in content order."""
    return [p for p in data["pages"] if p.get("nav", True)]
