"""I³ components as Dash layouts.

Every builder takes plain content (dicts from a content pack) and returns markup
carrying the i3-* classes and data-i3-* attributes that ``assets/i3.js`` animates.
Nothing in this module knows what the product measures.
"""
import json

from dash import dcc, html

from .content import nav_pages, rich

# Accent colours for cards that do not name their own; the Inductra module palette.
ACCENTS = ["#67cbd5", "#718ee8", "#72b99c", "#9a91bd", "#d4a26a", "#d77a8a"]


def _acc(item, index):
    return item.get("accent") or ACCENTS[index % len(ACCENTS)]


def _bound(value, bind):
    """A value that live state can overwrite later through data-i3-bind."""
    attrs = {"data-i3-bind": bind} if bind else {}
    return html.Span("—" if value is None else value, **attrs)


# ════ SHELL ═════════════════════════════════════════════════════════════════
def header(content):
    brand = content["brand"]
    pages = nav_pages(content)
    buttons = []
    for index, page in enumerate(pages):
        if index:
            buttons.append(html.Div(className="i3-nav-sep"))
        # dcc.Link accepts no data-* attributes, so the marked element sits inside it.
        buttons.append(dcc.Link(html.Span([html.Span(className="i3-nav-dot"), page.get("label", page["path"])],
                                          className="i3-nav-btn", **{"data-i3-path": page["path"]}),
                                href=page["path"], className="i3-nav-link"))
    pills = [html.Span([html.Span(className=f"i3-dot {p.get('state', 'off')}"),
                        p.get("label", ""), html.B(_bound(p.get("value"), p.get("bind")))],
                       className="i3-pill")
             for p in content.get("status", [])]
    return html.Header([
        dcc.Link(html.Span(brand.get("name", ""), className="i3-brand"), href="/", className="i3-brand-link"),
        html.Nav(html.Div(buttons, className="i3-nav"), className="i3-nav-wrap"),
        html.Div(pills, className="i3-pills"),
    ], className="i3-header")


def intro(content):
    """The startup takeover. Plays once per document load, then removes itself."""
    data = content.get("intro")
    if not data:
        return None
    brand = content["brand"]
    grid = data.get("grid", [])
    return html.Section([
        html.Div([
            html.Canvas(id="i3-intro-shader"),
            html.Div(data.get("eyebrow", "I³   Induction · Interference · Intelligence"), className="i3-intro-eyebrow"),
            html.Div(data.get("title_top", ""), className="i3-intro-title i3-intro-top"),
            html.Div(data.get("title_bottom", ""), className="i3-intro-title i3-intro-bottom"),
            html.Article([
                html.Div(data.get("kicker", "Project overview"), className="i3-intro-kicker"),
                html.H1(data.get("card_title", brand.get("name", "")), className="i3-intro-card-title"),
                html.P(rich(data.get("description")), className="i3-intro-desc"),
                html.Div(data.get("grid_label", ""), className="i3-intro-grid-label") if grid else None,
                html.Div([html.Div([html.B(g.get("name", "")), html.Span(g.get("role", ""))], className="i3-intro-item")
                          for g in grid], className="i3-intro-grid") if grid else None,
                html.Div(["by ", html.Strong(brand.get("author", ""))], className="i3-intro-credit")
                if brand.get("author") else None,
            ], className="i3-intro-card"),
            html.Button("Skip", className="i3-btn-ghost i3-intro-skip", type="button", **{"data-i3-intro-skip": "1"}),
        ], className="i3-intro-stage"),
    ], id="i3-intro", **{"aria-label": f"{brand.get('name', '')} introduction"})


def dock(content):
    """The NVTRA island: collapsed pill, expands into a question box."""
    data = content.get("dock")
    if not data:
        return None
    chip = data.get("chip")
    return html.Div([
        html.Div([
            html.Canvas(className="i3-dock-orb", **{"data-i3-sphere": "1.4"}),
            html.Div([html.Div(data.get("name", "NVTRA"), className="i3-dock-name"),
                      html.Div(data.get("hint", ""), className="i3-dock-hint")], className="i3-dock-head"),
            html.Span([html.Span(className=f"i3-dot {chip.get('state', 'off')}"), chip.get("label", ""),
                       html.B(_bound(chip.get("value"), chip.get("bind")))], className="i3-dock-chip") if chip else None,
        ], className="i3-dock-top"),
        html.Div([
            html.Div([html.P(data.get("greeting", ""))] if data.get("greeting") else [], className="i3-dock-log"),
            # i3.js builds the form here, so the input is never a React-controlled field.
            html.Div(className="i3-dock-form", **{"data-i3-placeholder": data.get("placeholder", "Ask")}),
        ], className="i3-dock-body"),
    ], id="i3-dock", className="is-collapsed", role="complementary", **{"aria-label": data.get("name", "NVTRA")})


# ════ CONTENT BLOCKS ════════════════════════════════════════════════════════
def blocks(items):
    """Render a list of content blocks. Unknown block kinds fail loudly."""
    return [block(b, i) for i, b in enumerate(items or [])]


def block(b, index=0):
    kind = b.get("kind", "text")
    style = {"--acc": b["accent"]} if b.get("accent") else None
    if kind == "section":
        return html.Section([
            html.Div(b.get("kicker", ""), className="i3-sec-kicker") if b.get("kicker") else None,
            html.H2(b.get("title", ""), className="i3-sec-title") if b.get("title") else None,
            *[html.P(rich(p), className="i3-copy") for p in _as_list(b.get("copy"))],
            *blocks(b.get("blocks")),
        ], className="i3-sec", style=style, **_id(b))
    if kind == "text":
        return html.Div([html.P(rich(p), className="i3-copy") for p in _as_list(b.get("copy"))], className="i3-block")
    if kind == "cards":
        cards = []
        for i, item in enumerate(b.get("items", [])):
            body = [html.Div(item.get("num", f"{i + 1:02d}"), className="i3-card-num"),
                    html.Div(item.get("title", ""), className="i3-card-head"),
                    html.Div(rich(item.get("desc")), className="i3-card-desc")]
            attrs = {"className": "i3-card", "style": {"--acc": _acc(item, i)}}
            cards.append(dcc.Link(body, href=item["href"], **attrs) if item.get("href") else html.Div(body, **attrs))
        return html.Div(cards, className="i3-grid", style={"--cols": str(b.get("cols", 4))})
    if kind == "metrics":
        return html.Div([
            html.Div([html.Div(m.get("label", ""), className="i3-metric-k"),
                      html.Div(_bound(m.get("value"), m.get("bind")), className="i3-metric-v"),
                      html.Div(m.get("note", ""), className="i3-metric-n") if m.get("note") else None],
                     className="i3-metric", style={"--acc": _acc(m, i)})
            for i, m in enumerate(b.get("items", []))], className="i3-metrics")
    if kind == "slot":
        # A reserved region a product fills with its own live component (a chart,
        # a 3D view, a table). The label says what belongs there.
        return html.Div([html.B(b.get("label", "Live component")), b.get("note", "")],
                        className="i3-slot", style={"--h": f"{b.get('height', 260)}px"}, **_id(b))
    if kind == "spark":
        # A live trace: the bound key carries a list of numbers (newest last).
        acc = {"--acc": b["accent"]} if b.get("accent") else {}
        return html.Div([
            html.Div([html.Span(b.get("label", "")), html.B(_bound(b.get("value"), b.get("value_bind")))],
                     className="i3-spark-head"),
            html.Canvas(**{"data-i3-spark": b["bind"], "aria-label": b.get("label", "live trace")}),
        ], className="i3-spark", style={"--h": f"{b.get('height', 90)}px", **acc})
    if kind == "live":
        # A sentence that follows live state (e.g. NVTRA's interpretation).
        return html.Div([html.Div(b.get("label", ""), className="i3-metric-k") if b.get("label") else None,
                         html.P(_bound(b.get("value"), b.get("bind")), className="i3-copy i3-live")],
                        className="i3-block", style=style)
    if kind == "actions":
        # Buttons that POST {action, args} to the host's action handler.
        buttons = [html.Button(a.get("label", a["action"]), type="button", className="i3-btn-ghost i3-action",
                               **{"data-i3-action": json.dumps({k: a[k] for k in ("action", "args", "prompt", "confirm")
                                                                if k in a})})
                   for a in b.get("items", [])]
        return html.Div([html.Div(buttons, className="i3-actions-row"),
                         html.Div(className="i3-action-out", **{"aria-live": "polite"})], className="i3-actions")
    if kind == "list":
        return html.Ul([html.Li(rich(x)) for x in b.get("items", [])], className="i3-list", style=style)
    if kind == "quote":
        return html.Blockquote(rich(b.get("text")), className="i3-quote", style=style)
    raise ValueError(f"unknown block kind '{kind}' (section, text, cards, metrics, slot, spark, live, actions, list, quote)")


def _id(b):
    """Dash rejects id=None, so an id is only passed when the content names one."""
    return {"id": b["id"]} if b.get("id") else {}


def _as_list(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


# ════ PAGE PIECES ═══════════════════════════════════════════════════════════
def scrub_opening(data, default_kind="field"):
    """The scroll-locked opening at the top of a page (drawn by the browser)."""
    if not data:
        return None
    kind = data.get("kind", default_kind)
    attrs = {"data-i3-scrub": kind, "data-i3-title": data.get("title", ""),
             "data-i3-tagline": data.get("tagline", "")}
    if kind == "flow":
        attrs["data-i3-flow"] = json.dumps({"nodes": data.get("nodes", []), "links": data.get("links", []),
                                            "footnote": data.get("footnote", "")})
    return html.Div(className="i3-scrub", **attrs)


def hero(data):
    if not data:
        return None
    return html.Div([
        html.Div([
            html.Div(data.get("title", ""), className="i3-hero-title"),
            html.Div([html.Em(data.get("tag_em", "")), data.get("tag", "")], className="i3-hero-tag")
            if data.get("tag") or data.get("tag_em") else None,
        ], className="i3-hero-titles"),
        html.Div(rich(data.get("description")), className="i3-hero-sub"),
        html.Div([html.Div([html.Div(s.get("k", ""), className="k"), html.Div(s.get("v", ""), className="v")])
                  for s in data.get("spec", [])], className="i3-spec") if data.get("spec") else None,
    ], className="i3-hero")


def section_head(title, line=None, key=None):
    return html.Div([
        html.Div(title, className="i3-section-title"),
        html.Div(rich(line), className="i3-section-line") if line else None,
        html.Div([html.Span([html.I(style={"--acc": k.get("accent", "#7f92ad")}), k.get("label", "")]) for k in key],
                 className="i3-key") if key else None,
    ], className="i3-section-head")


def module_orbit(data):
    """Home: module cards revolving round the globe; each card is a link."""
    modules = data.get("items", [])
    globe = data.get("globe")
    cards = []
    for i, m in enumerate(modules):
        live = m.get("live")
        cards.append(dcc.Link(html.Div([
            html.Div([html.Span(m.get("num", f"{i + 1:02d}"), className="i3-card-index"),
                      html.Span(m.get("role", ""), className="i3-card-role")], className="i3-card-top"),
            html.Div(m.get("title", ""), className="i3-card-title"),
            html.Div(rich(m.get("desc")), className="i3-card-short"),
            html.Div([_bound(live.get("value"), live.get("bind")), html.Small(live.get("label", ""))],
                     className="i3-card-live") if live else None,
            html.Span(m.get("enter", "ENTER MODULE  →"), className="i3-card-enter"),
        ], className="i3-card-summary"), href=m.get("href", "/"), className="i3-orbit-card",
            style={"--acc": _acc(m, i)}, title=f"Open {m.get('title', '')}"))
    if globe is not None:
        core = html.Div([
            html.Canvas(**{"data-i3-globe": "1", "data-i3-nodes": json.dumps(globe.get("nodes", [])),
                           "data-i3-links": json.dumps(globe.get("links", [])),
                           "title": globe.get("hint", "Drag to rotate · Select a node · Double-click reverses spin"),
                           "aria-label": globe.get("label", "Interactive globe")}),
            html.Div([html.B(), html.Span()], className="i3-globe-note", hidden=True, **{"aria-live": "polite"}),
        ], className="i3-orbit-core has-globe")
    else:
        core = html.Div([html.B(data.get("core", "I³")), html.Span(data.get("core_sub", ""))], className="i3-orbit-core")
    return html.Div([html.Div(className="i3-orbit-ring"), core, *cards],
                    className="i3-orbit", **{"data-i3-orbit": "links"})


def pillar_orbit(data, framework_name):
    """Framework: pillar cards round a core; each opens in place to full screen."""
    core = data.get("core", {})
    cards = []
    for i, p in enumerate(data.get("pillars", [])):
        num = p.get("num", f"{i:02d}")
        cards.append(html.Article([
            html.Div([
                html.Div([html.Span(num, className="i3-card-index"),
                          html.Span(p.get("role", ""), className="i3-card-role")], className="i3-card-top"),
                html.Div(p.get("title", ""), className="i3-card-title"),
                html.Div(rich(p.get("desc")), className="i3-card-short"),
                html.Span(p.get("enter", "OPEN PILLAR  →"), className="i3-card-enter"),
            ], className="i3-card-summary"),
            html.Div([
                html.Div([html.Button("←  BACK TO ORBIT", className="i3-pillar-close", type="button",
                                      **{"aria-label": f"Close {p.get('title', '')}"}),
                          html.Span(f"{framework_name} / PILLAR {num}", className="i3-pillar-id")],
                         className="i3-pillar-nav"),
                html.Div(blocks(p.get("blocks")), className="i3-pillar-body"),
            ], className="i3-pillar-detail"),
        ], className="i3-orbit-card", tabIndex=0, role="button", style={"--acc": _acc(p, i)},
           **{"aria-label": f"Open {p.get('title', '')}"}))
    if core.get("sphere", True):
        core_el = html.Div([html.Canvas(**{"data-i3-sphere": "0.6"}),
                            html.Div([html.B(core.get("label", framework_name)),
                                      html.Span(core.get("sub", ""))], className="i3-orbit-core-label")],
                           className="i3-orbit-core has-canvas")
    else:
        core_el = html.Div([html.B(core.get("label", framework_name)), html.Span(core.get("sub", ""))],
                           className="i3-orbit-core")
    caption = data.get("caption")
    return html.Div([
        html.Div([html.B(caption.get("title", "")), html.Span(caption.get("text", ""))], className="i3-orbit-caption")
        if caption else None,
        html.Div(className="i3-orbit-ring"), core_el, *cards,
    ], className="i3-orbit", **{"data-i3-orbit": "pillars"})
