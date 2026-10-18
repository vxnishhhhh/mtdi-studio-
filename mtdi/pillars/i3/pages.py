"""Page builders, one per page type a content pack can declare.

    home       scroll opening, hero, module orbit round a globe
    framework  signal-path opening, landing hero, pillar orbit (the MTDI pattern)
    document   numbered sections with a contents strip (the Sixth Sense pattern)
    module     hero plus free content blocks (an instrument page skeleton)
    settings   interface preferences
"""
from dash import dcc, html

from . import components as c
from .content import rich


def home(page, content):
    modules = page.get("modules")
    return html.Div([
        c.scrub_opening(page.get("opening"), "field"),
        c.hero(page.get("hero")),
        html.Div([
            c.section_head(modules.get("title", "MODULES"), modules.get("line"),
                           [{"label": f"{m.get('num', f'{i + 1:02d}')} · {m.get('key', m.get('title', ''))}",
                             "accent": c._acc(m, i)} for i, m in enumerate(modules.get("items", []))]),
            c.module_orbit(modules),
        ], className="i3-pad") if modules else None,
        html.Div(c.blocks(page.get("blocks")), className="i3-pad") if page.get("blocks") else None,
    ])


def framework(page, content):
    name = page.get("name", page.get("label", "FRAMEWORK"))
    landing = page.get("landing", {})
    return html.Div([
        c.scrub_opening(page.get("opening"), "flow"),
        html.Div([
            html.Div([
                html.Div(landing.get("kicker", ""), className="i3-fw-kicker"),
                html.H1(landing.get("title", ""), className="i3-fw-title"),
                html.Div(rich(landing.get("copy")), className="i3-fw-copy"),
                html.Div([html.Span(m) for m in landing.get("meta", [])], className="i3-fw-meta")
                if landing.get("meta") else None,
            ], className="i3-fw-hero"),
            c.pillar_orbit(page, name),
            html.Div(c.blocks(page.get("blocks")), className="i3-doc") if page.get("blocks") else None,
        ], className="i3-pad i3-fw-landing"),
    ])


def document(page, content):
    sections = [dict(s) for s in page.get("sections", [])]   # never mutate the shared pack
    for i, s in enumerate(sections):
        s.setdefault("id", f"sec-{i + 1}")
        s.setdefault("kind", "section")
        s.setdefault("kicker", f"{i + 1:02d}")
    return html.Div([
        c.scrub_opening(page.get("opening"), "field"),
        html.Div([
            html.Div([
                html.Div(page.get("kicker", ""), className="i3-fw-kicker"),
                html.H1(page.get("title", ""), className="i3-fw-title"),
                html.Div(rich(page.get("copy")), className="i3-fw-copy"),
            ], className="i3-doc-head"),
            html.Nav([html.A(f"{s['kicker']} · {s.get('title', '')}", href=f"#{s['id']}") for s in sections],
                     className="i3-doc-toc") if page.get("toc", True) else None,
            *c.blocks(sections),
        ], className="i3-pad i3-doc"),
    ])


def module(page, content):
    return html.Div([
        c.scrub_opening(page.get("opening"), "field"),
        c.hero(page.get("hero")),
        html.Div(c.blocks(page.get("blocks")), className="i3-pad"),
    ])


def settings(page, content):
    rows = [html.Div([
        html.Div([html.B("Animations"),
                  html.Span("Background shader, openings and orbits. Off also honours the system reduce-motion setting.")],
                 className="i3-set-lab"),
        html.Div([html.Button("On", value="on", type="button"), html.Button("Off", value="off", type="button")],
                 className="i3-seg", **{"data-i3-setting": "anim"}),
    ], className="i3-set-row")]
    for extra in page.get("rows", []):
        rows.append(html.Div([html.Div([html.B(extra.get("title", "")), html.Span(extra.get("text", ""))],
                                       className="i3-set-lab"),
                              html.Span(extra.get("value", ""), className="i3-pill")], className="i3-set-row"))
    return html.Div([
        html.Div([
            html.Div(page.get("kicker", "INTERFACE"), className="i3-fw-kicker"),
            html.H1(page.get("title", "Settings"), className="i3-fw-title"),
            html.Div(rich(page.get("copy")), className="i3-fw-copy"),
            html.Div(rows, className="i3-set-card"),
            *c.blocks(page.get("blocks")),
            dcc.Link(html.Button("← HOME", className="i3-btn-ghost", type="button"), href="/", className="i3-back"),
        ], className="i3-set"),
    ], className="i3-pad")


BUILDERS = {"home": home, "framework": framework, "document": document, "module": module, "settings": settings}


def build(page, content):
    return BUILDERS[page["type"]](page, content)
