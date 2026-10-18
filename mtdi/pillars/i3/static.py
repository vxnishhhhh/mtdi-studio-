"""Render I³ to static HTML: the same components, no server.

The Dash components that I³ builds are plain trees (type, namespace, props,
children), so they can be written straight to HTML. A static site therefore uses
the very same header, intro, orbits, pillars and blocks as the running studio,
with assets/i3.js bringing them to life in the browser. Live values are pushed
with window.I3.set(key, value) instead of polled from a server.
"""
import html as _html
import json
import re

from . import components as c
from . import pages as page_builders

VOID = {"input", "br", "hr", "img", "meta", "link"}
SKIP = {"Location", "Store", "Interval", "Download"}
_CAMEL = re.compile(r"(?<!^)(?=[A-Z])")
ATTR = {"className": "class", "tabIndex": "tabindex", "htmlFor": "for", "autoComplete": "autocomplete"}


def render(node):
    if node is None or node is False:
        return ""
    if isinstance(node, (list, tuple)):
        return "".join(render(n) for n in node)
    if isinstance(node, (str, int, float)):
        return _html.escape(str(node))
    kind = type(node).__name__
    if kind in SKIP:
        return ""
    tag = "a" if kind == "Link" else kind.lower()
    attrs = []
    # Sorted: Dash keeps data-*/aria-* props in hash order, and builds must be reproducible.
    for key, value in sorted(node.to_plotly_json()["props"].items()):
        if key in ("children", "n_clicks", "n_clicks_timestamp", "disable_n_clicks", "refresh") or value is None:
            continue
        if key == "style":
            value = ";".join(f"{k if k.startswith('--') else _CAMEL.sub('-', k).lower()}:{v}" for k, v in value.items())
        if value is True:
            attrs.append(ATTR.get(key, key))
            continue
        if value is False:
            continue
        attrs.append(f'{ATTR.get(key, key)}="{_html.escape(str(value), quote=True)}"')
    open_tag = f"<{tag}{(' ' + ' '.join(attrs)) if attrs else ''}>"
    if tag in VOID:
        return open_tag
    return open_tag + render(getattr(node, "children", None)) + f"</{tag}>"


def document(content, body_html, title=None, config=None, base="/", head_extra="", body_extra="",
             intro=False, description=""):
    """A complete page: header, optional intro, dock, and body inside #i3-page."""
    cfg = {"landUrl": f"{base}assets/land.json", "statePollMs": 1000}
    cfg.update(config or {})
    brand = content["brand"]
    notice = content.get("notice")
    parts = [render(c.header(content)),
             f'<div class="i3-notice">{_html.escape(notice)}</div>' if notice else "",
             f'<div class="i3-credit">{_html.escape(brand["credit"])}</div>' if brand.get("credit") else "",
             render(c.intro(content)) if intro else "",
             render(c.dock(content)),
             f'<div id="i3-shell"><main id="i3-page">{body_html}</main></div>']
    title = title or brand.get("name", "I³")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_html.escape(title)}</title>
<meta name="description" content="{_html.escape(description, quote=True)}">
<meta property="og:title" content="{_html.escape(title, quote=True)}">
<meta property="og:description" content="{_html.escape(description, quote=True)}">
<meta property="og:image" content="{base}assets/og.png">
<meta name="theme-color" content="#07090f">
<link rel="icon" href="{base}assets/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Inter:wght@300;400;500;600&display=swap">
<link rel="stylesheet" href="{base}assets/i3.css">
<link rel="stylesheet" href="{base}assets/site.css">
<script>window.I3_CONFIG={json.dumps(cfg)};</script>
{head_extra}
</head>
<body>
{''.join(parts)}
<script src="{base}assets/i3.js"></script>
{body_extra}
</body>
</html>
"""


def page(content, page_spec, **kw):
    """Render one content-pack page (home, framework, document, module, settings)."""
    return document(content, render(page_builders.build(page_spec, content)), **kw)
