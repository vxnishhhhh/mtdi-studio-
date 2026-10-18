"""Build MTDI's static website from the repository: `python -m mtdi site build`.

Everything on the site comes from the repository itself:

    /                     the MTDI home, drawn by I³ (pillar 03)
    /pillars              the five pillars round the core, with the signal path
    /demo/<project>/...   every example project's full studio, replaying the real MTDI
                          engine run on SIMULATED data at build time
    /docs/<page>          README, AI playbook, integration guide, manifest, protocol, ...
    /articles/<slug>      docs/articles/*.md
    /llms.txt             for AI assistants

Standard library only, so it builds anywhere Python 3.9+ exists, including Vercel.
`build_project_site` builds the same demo for a single project (used by `mtdi publish`).
"""
import copy
import json
import pathlib
import re
import shutil

from . import __version__
from .adapters.simulator import Signal, channels_of, rate_of
from .engine import Engine
from .markdown import render as md
from .pillars import PILLARS
from .pillars.i3 import static
from .project import load
from .studio import views

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPO = "https://github.com/vxnishhhhh/mtdi-studio"
ASSETS = ROOT / "mtdi" / "pillars" / "i3" / "assets"
SITE_ASSETS = ROOT / "site" / "assets"
DEMOS = ["inductra-vaion", "host-health", "auth-watch", "network-watch", "ultrasonic-room"]
DOCS = [  # (slug, source, title)
    ("overview", "README.md", "Overview"),
    ("ai", "docs/AI.md", "Use MTDI from any AI"),
    ("integrating", "INTEGRATING.md", "Integrating a project"),
    ("manifest", "docs/MANIFEST.md", "Manifest reference"),
    ("protocol", "firmware/PROTOCOL.md", "Line protocol"),
    ("i3", "mtdi/pillars/i3/README.md", "I³ interface"),
    ("matlab", "matlab/README.md", "MATLAB toolbox"),
    ("agents", "AGENTS.md", "Rules for AI agents"),
    ("changelog", "CHANGELOG.md", "Changelog"),
]
MERMAID = ('<script type="module">import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.esm.min.mjs";'
           'mermaid.initialize({startOnLoad:true,theme:"dark",themeVariables:{primaryColor:"#101827",primaryTextColor:"#e8eeff",'
           'lineColor:"#00e5ff",primaryBorderColor:"#2979ff",fontFamily:"DM Mono, monospace"}});</script>')


# ════ replay: the real engine, simulated inputs, a virtual clock ══════════════
def fast_replay(project, seconds=90):
    """Run the engine on SIMULATED data for `seconds` of virtual time, one state per second.

    States are delta-encoded: each holds only the bound values that changed, plus every
    channel's deviation (the browser rebuilds the live traces from those)."""
    clock = [0.0]
    engine = Engine(project, clock=lambda: clock[0])
    feeds = []
    for src in project["sources"]:
        chans = channels_of(project, src["id"])
        if chans:
            feeds.append([src["id"], Signal(chans, seed=7), 1.0 / rate_of(src, chans), 0.0])
            engine.set_source_state(src["id"], "connected", "SIMULATED · replay")
    # Warm up silently for one learning window, so the replay shows a learned environment
    # (a project that learns over five minutes would otherwise only ever show "learning").
    warm = int(min(project["environment"]["window"] * 1.2 + 5, 600))
    states, previous = [], {}
    for second in range(1, warm + seconds + 1):
        for feed in feeds:
            sid, signal, dt, t = feed
            while t < second:
                clock[0] = t
                engine.ingest_values(sid, signal.values(t), "SIMULATED")
                t += dt
            feed[3] = t
        clock[0] = float(second)
        if second <= warm:
            continue
        packet = engine.snapshot()
        flat = {k: v for k, v in views.flatten(packet).items() if not k.endswith(".spark")}
        delta = {k: v for k, v in flat.items() if previous.get(k) != v}
        previous = flat
        states.append({"v": delta, "d": {cid: round(c["environment"].get("deviation") or 0.0, 6)
                                         for cid, c in packet["channels"].items()},
                       "q": [packet["fusion"]["condition"], packet["fusion"]["interpretation"],
                             round(packet["fusion"]["score"], 1)]})
    return {"project": project["project"]["id"], "seconds": seconds, "data_source": "SIMULATED",
            "note": "The MTDI engine run on simulated inputs at build time, replayed in the browser.",
            "states": states}


def _prefix_pack(content, prefix):
    pack = copy.deepcopy(content)

    def fix(href):
        if prefix.strip("/") == "" or not href.startswith("/"):
            return href
        return (prefix.rstrip("/") + href).rstrip("/") or "/"
    for page in pack["pages"]:
        page["path"] = fix(page["path"])
        for item in page.get("modules", {}).get("items", []):
            item["href"] = fix(item.get("href", "/"))
    return pack


def _write(out, url_path, html):
    target = out / url_path.strip("/") / "index.html" if url_path.strip("/") else out / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding="utf-8")


def _demo(project, out, prefix, base, seconds):
    """Write a project's whole studio as static pages under `prefix`, with its replay."""
    pack = _prefix_pack(views.content_pack(project, True), prefix)
    pack["notice"] = "SIMULATED DATA · REPLAY OF THE MTDI ENGINE · RUN THE STUDIO FOR LIVE DATA"
    replay = fast_replay(project, seconds)
    (out / prefix.strip("/")).mkdir(parents=True, exist_ok=True)
    (out / prefix.strip("/") / "replay.json").write_text(json.dumps(replay, separators=(",", ":")), encoding="utf-8")
    script = f'<script src="{base}assets/replay.js" data-replay="{prefix.rstrip("/")}/replay.json"></script>'
    for i, page in enumerate(pack["pages"]):
        _write(out, page["path"], static.page(pack, page, base=base, body_extra=script, intro=(i == 0),
                                              title=f"{pack['brand']['name']} · {page.get('label', '')} · MTDI 5.0",
                                              description=project["project"].get("description", "").replace("[[", "").replace("]]", "")))
    return pack


def _assets(out):
    dest = out / "assets"
    dest.mkdir(parents=True, exist_ok=True)
    for f in ("i3.css", "i3.js", "land.json"):
        shutil.copy2(ASSETS / f, dest / f)
    for f in SITE_ASSETS.iterdir():
        if f.is_file():
            shutil.copy2(f, dest / f.name)
    if (ROOT / "docs" / "assets").exists():
        shutil.copytree(ROOT / "docs" / "assets", dest / "docs", dirs_exist_ok=True)


# ════ the official site ═══════════════════════════════════════════════════════
def site_pack():
    nav = [{"path": "/", "label": "Home", "type": "home"}, {"path": "/pillars", "label": "Pillars", "type": "framework"},
           {"path": "/demo", "label": "Demo", "type": "module"}, {"path": "/docs/overview", "label": "Docs", "type": "module"},
           {"path": "/docs/ai", "label": "Use with AI", "type": "module"}, {"path": "/articles", "label": "Articles", "type": "module"}]
    home = {
        "path": "/", "type": "home", "label": "Home",
        "opening": {"kind": "field", "title": "A reading means nothing until you know whether to believe it.",
                    "tagline": "MTDI turns anything that produces numbers — sensors, firmware, software, networks, security logs — "
                               "into channels, learns their normal environment, proves each one can be trusted, and explains what "
                               "it sees. Small enough for a Raspberry Pi."},
        "hero": {"title": "MTDI 5.0", "tag_em": "MICROPROCESSING TECHNOLOGICAL DIAGNOSTIC INTELLIGENCE",
                 "tag": "   —   STUDIO",
                 "description": "Five pillars over any channel: the [[Validation Chamber]] proves each one is present, fresh and in "
                                "range; [[Environmental Intelligence]] learns, locks and compares its real environment; "
                                "[[NVTRA]] explains what is happening; [[I³]] draws it; [[Aether]] carries why it exists. "
                                "One [[project.json]] per project, [[pure Python]], hardware, firmware or software.",
                 "spec": [{"k": "VERSION", "v": __version__}, {"k": "PILLARS", "v": "5 · one core"},
                          {"k": "SCORE", "v": "8 weighted factors"}, {"k": "ADAPTERS", "v": "8"},
                          {"k": "RUNS ON", "v": "Raspberry Pi and up"}, {"k": "ENGINE", "v": "Python standard library"}]},
        "modules": {"title": "MTDI Studio", "line": "Everything here is generated from the [[repository]] itself.",
                    "core": "MTDI", "core_sub": __version__,
                    "items": [
                        {"num": "01", "key": "DEMO", "role": "live", "title": "Live demo", "href": "/demo", "accent": "#67cbd5",
                         "desc": "Five example projects, the real engine, simulated inputs.", "live": {"value": "5", "label": "PROJECTS"}},
                        {"num": "02", "key": "PILLARS", "role": "framework", "title": "The pillars", "href": "/pillars", "accent": "#72b99c",
                         "desc": "Validation, environment, NVTRA, I³, Aether, one core.", "live": {"value": "5", "label": "PILLARS"}},
                        {"num": "03", "key": "AI", "role": "playbook", "title": "Use with any AI", "href": "/docs/ai", "accent": "#b388ff",
                         "desc": "Paste the repository link; the playbook does the rest.", "live": {"value": "docs/AI.md", "label": ""}},
                        {"num": "04", "key": "DOCS", "role": "reference", "title": "Documentation", "href": "/docs/overview", "accent": "#718ee8",
                         "desc": "Integration guide, manifest, protocol, MATLAB.", "live": {"value": f"{len(DOCS)}", "label": "PAGES"}},
                    ]},
    }
    pillars_blocks = {
        "validation": "Before anything is interpreted, every channel proves it is present, fresh, on time and inside its declared range. "
                      "Detection limits come from its own measured noise: [[LOD = 3σ]], [[LOQ = 10σ]].",
        "environment": "Each channel learns its baseline from the real environment with a time-windowed median that refuses excursions. "
                       "Lock it, save it under a name, compare against it later. Simulated data can never be saved as an environment.",
        "nvtra": "Universal rules (offline, settling, ambient, one channel dominant, mixed activity) plus each project's own domain rules, "
                 "written as data. Every explanation says what a pattern suggests and what else could cause it.",
        "i3": "Induction, interference, intelligence. The interface every pillar is seen through, generated from the manifest; this "
              "website is drawn by it.",
        "aether": "Purpose, persistence and authorship. A non-functional designation: shown, never scored, never in the signal path.",
    }
    framework = {
        "path": "/pillars", "type": "framework", "label": "Pillars", "name": "MTDI",
        "opening": {"kind": "flow", "title": "MTDI SIGNAL PATH", "tagline": "Scroll to trace any input into the MTDI core.",
                    "nodes": [{"x": .18, "y": .22, "w": .25, "title": "Hardware", "copy": "Sensors · boards · instruments"},
                              {"x": .50, "y": .22, "w": .25, "title": "Firmware", "copy": "KEY=value protocol lines"},
                              {"x": .82, "y": .22, "w": .25, "title": "Software", "copy": "Probes · programs · the host"},
                              {"x": .31, "y": .44, "w": .35, "title": "Validation Chamber", "copy": "Presence · freshness · timing · range"},
                              {"x": .69, "y": .44, "w": .35, "title": "Environmental Intelligence", "copy": "Learn · lock · compare"},
                              {"x": .50, "y": .64, "w": .48, "title": "MTDI Core", "copy": "Eight weighted factors per channel", "core": True},
                              {"x": .29, "y": .83, "w": .35, "title": "I³ Interface", "copy": "Live graphs · vectors · confidence"},
                              {"x": .71, "y": .83, "w": .35, "title": "NVTRA", "copy": "Plain language · reasoning context"}],
                    "links": [[0, 3], [1, 3], [1, 4], [2, 4], [3, 5], [4, 5], [5, 6], [5, 7]],
                    "footnote": "Aether is a non-functional designation and does not appear in the signal path."},
        "landing": {"kicker": "MICROPROCESSING TECHNOLOGICAL DIAGNOSTIC INTELLIGENCE · 5.0",
                    "title": "Five pillars, one core.",
                    "copy": "Every MTDI project, whatever it measures, runs on the same five pillars. Select one to enter it.",
                    "meta": ["5 PILLARS", "8 WEIGHTED FACTORS", "8 ADAPTERS", "ANY DOMAIN"]},
        "caption": {"title": "FIVE PILLARS · ONE CORE", "text": "Select a pillar to expand it."},
        "core": {"label": "MTDI", "sub": "5.0 core", "sphere": True},
        "pillars": [dict(p, blocks=[{"kind": "section", "kicker": f"Pillar {p['num']} · {p['role']}", "title": p["title"],
                                     "accent": p["accent"], "copy": pillars_blocks[p["id"]],
                                     "blocks": [{"kind": "cards", "cols": 2, "items": [
                                         {"num": "→", "title": "Read the article", "desc": "How it works, in depth.",
                                          "href": {"environment": "/articles/02-environmental-intelligence"}.get(p["id"], "/articles/01-introducing-mtdi-5")},
                                         {"num": "→", "title": "See it live", "desc": "In the demo projects.", "href": "/demo"}]}]}])
                    for p in PILLARS],
    }
    return {"brand": {"name": "MTDI Studio", "credit": "MTDI 5.0"},
            "intro": {"eyebrow": "MICROPROCESSING · TECHNOLOGICAL · DIAGNOSTIC · INTELLIGENCE",
                      "title_top": "MTDI", "title_bottom": "5.0", "kicker": "MTDI Studio", "card_title": "MTDI 5.0",
                      "description": "One framework for anything that produces numbers: sensors, firmware, software, networks and "
                                     "security. Five pillars, one score you can take apart, small enough for a Raspberry Pi.",
                      "grid_label": "Pillars",
                      "grid": [{"name": p["title"].upper(), "role": p["role"]} for p in PILLARS] + [{"name": "MTDI CORE", "role": "8 factors"}]},
            "dock": {"name": "NVTRA", "hint": "Ask about MTDI", "placeholder": "Ask: what is MTDI? how do I start?",
                     "greeting": "I am NVTRA. On this website I answer from MTDI's documentation; in the studio I answer from live data."},
            "pages": nav, "_home": home, "_framework": framework}


SITE_FAQ = [
    (("what", "mtdi"), "MTDI (Microprocessing Technological Diagnostic Intelligence) turns anything that produces numbers into channels and runs five pillars over them: Validation Chamber, Environmental Intelligence, NVTRA, I³ and Aether. Start at /docs/overview."),
    (("start", "install", "run"), "pip install -r requirements.txt, then python -m mtdi run projects/host-health for real data from your own computer, or add --simulate to any project."),
    (("ai", "chatgpt", "claude", "agent"), "Paste the repository link into any AI and ask it to follow docs/AI.md. The playbook is at /docs/ai."),
    (("pi", "raspberry", "small"), "The engine is pure Python standard library; see /articles/06-mtdi-on-a-raspberry-pi, including headless mode."),
    (("environment", "baseline"), "Environmental Intelligence learns each channel's normal level, locks it, saves it under a name and compares against it. See /articles/02-environmental-intelligence."),
    (("score", "confidence", "factor"), "The MTDI score is eight weighted, named factors per channel: a heuristic evidence-quality score, not a probability. See /articles/03-a-score-you-can-take-apart."),
    (("security", "cyber", "network", "software"), "MTDI works beyond sensors: see /articles/05-beyond-sensors and the auth-watch, network-watch and host-health projects."),
    (("matlab",), "matlab/+mtdi is an independent implementation; mtdi.verify checks it agrees with Python. See /docs/matlab."),
]


def _site_ask_script():
    faq = json.dumps([[list(k), a] for k, a in SITE_FAQ])
    return ("<script>(function(){var F=" + faq + ";window.I3=window.I3||{};I3.ask=function(q){q=(q||'').toLowerCase();"
            "for(var i=0;i<F.length;i++){if(F[i][0].some(function(w){return q.indexOf(w)>=0;}))return Promise.resolve(F[i][1]);}"
            "return Promise.resolve('On this website I can point you to the docs: try asking what MTDI is, how to start, "
            "how to use it with AI, or about the score. Run the studio for answers from live data.');};})();</script>")


def _link_mapper(source):
    """Rewrite links inside a Markdown file for the site."""
    pages = {src: f"/docs/{slug}" for slug, src, _ in DOCS}
    src_dir = pathlib.PurePosixPath(source).parent

    def link(url):
        if re.match(r"^(https?:|mailto:|#)", url):
            return url
        path, _, anchor = url.partition("#")
        resolved = str(pathlib.PurePosixPath(*[p for p in (src_dir / path).parts]))
        parts = []
        for part in resolved.split("/"):
            if part == "..":
                if parts:
                    parts.pop()
            elif part not in ("", "."):
                parts.append(part)
        resolved = "/".join(parts)
        if resolved in pages:
            target = pages[resolved]
        elif resolved.startswith("docs/articles/") and resolved.endswith(".md"):
            target = "/articles/" + pathlib.PurePosixPath(resolved).stem
        elif resolved.startswith("docs/assets/"):
            target = "/assets/docs/" + resolved[len("docs/assets/"):]
        else:
            target = f"{REPO}/blob/main/{resolved}"
        return target + (f"#{anchor}" if anchor else "")
    return link


def _md_page(pack, path, title, source_text, source_path, sidebar, description):
    body, toc = md(source_text, _link_mapper(source_path))
    toc_html = "".join(f'<a class="lvl{lvl}" href="#{a}">{t}</a>' for lvl, a, t in toc)
    html = (f'<div class="i3-pad site-doc"><aside class="site-side">{sidebar}'
            f'{("<div class=site-toc><b>On this page</b>" + toc_html + "</div>") if toc_html else ""}</aside>'
            f'<article class="i3-md">{body}<p class="site-edit"><a href="{REPO}/blob/main/{source_path}" target="_blank" '
            f'rel="noopener">View source on GitHub →</a></p></article></div>')
    extra = MERMAID if 'class="mermaid"' in body else ""
    return static.document(pack, html, title=f"{title} · MTDI 5.0", head_extra=extra, description=description,
                           body_extra=_site_ask_script())


def _articles():
    out = []
    for f in sorted((ROOT / "docs" / "articles").glob("*.md")):
        text = f.read_text(encoding="utf-8")
        title = text.splitlines()[0].lstrip("# ").strip()
        para = next((l for l in text.split("\n\n")[2:] if l.strip() and not l.startswith(("#", "|", "*", "`"))), "")
        out.append((f.stem, title, re.sub(r"[*`\[\]]", "", para).replace("\n", " ")[:220], text, f"docs/articles/{f.name}"))
    return out


def build_site(out=None, seconds=90):
    out = pathlib.Path(out or ROOT / "site" / "dist")
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    _assets(out)
    pack = site_pack()
    desc = ("MTDI 5.0: five pillars for anything that produces numbers. Validation Chamber, Environmental Intelligence, "
            "NVTRA, I³ and Aether. Pure Python, runs on a Raspberry Pi.")
    ask = _site_ask_script()
    _write(out, "/", static.page(pack, pack["_home"], intro=True, title="MTDI Studio · MTDI 5.0", description=desc, body_extra=ask))
    _write(out, "/pillars", static.page(pack, pack["_framework"], title="The pillars · MTDI 5.0", description=desc, body_extra=ask))

    cards = []
    for pid in DEMOS:
        project = load(ROOT / "projects" / pid)
        _demo(project, out, f"/demo/{pid}", "/", seconds)
        meta = project["project"]
        cards.append({"num": meta.get("domain", "").upper(), "title": meta["name"], "href": f"/demo/{pid}",
                      "desc": re.sub(r"\[\[|\]\]", "", meta.get("description", ""))[:170]})
    demo_index = static.render(static.c.hero({"title": "Live demo", "tag_em": "SIMULATED", "tag": "   —   THE REAL ENGINE, REPLAYED",
                               "description": "Each project below is its complete MTDI studio. At build time the real MTDI engine ran on "
                                              "[[simulated]] inputs for 90 seconds; your browser replays what it produced. Every page says "
                                              "SIMULATED because it is. Run any of them live with [[python -m mtdi run projects/<id>]]."}))
    demo_index += '<div class="i3-pad">' + static.render(static.c.block({"kind": "cards", "cols": 3, "items": cards})) + "</div>"
    _write(out, "/demo", static.document(pack, demo_index, title="Live demo · MTDI 5.0", description=desc, body_extra=ask))

    sidebar = "<b>Documentation</b>" + "".join(f'<a href="/docs/{s}">{t}</a>' for s, _, t in DOCS)
    for slug, src, title in DOCS:
        _write(out, f"/docs/{slug}", _md_page(pack, f"/docs/{slug}", title, (ROOT / src).read_text(encoding="utf-8"), src, sidebar, desc))

    arts = _articles()
    art_side = "<b>Articles</b>" + "".join(f'<a href="/articles/{s}">{t}</a>' for s, t, *_ in arts)
    for slug, title, summary, text, src in arts:
        _write(out, f"/articles/{slug}", _md_page(pack, f"/articles/{slug}", title, text, src, art_side, summary))
    art_index = static.render(static.c.hero({"title": "Articles", "tag_em": "MTDI 5.0", "tag": "   —   HOW IT WORKS AND WHY",
                                             "description": "Written from the code, about what it actually does."}))
    art_index += '<div class="i3-pad">' + static.render(static.c.block(
        {"kind": "cards", "cols": 2, "items": [{"num": s[:2], "title": t, "desc": d, "href": f"/articles/{s}"} for s, t, d, *_ in arts]})) + "</div>"
    _write(out, "/articles", static.document(pack, art_index, title="Articles · MTDI 5.0", description=desc, body_extra=ask))

    shutil.copy2(ROOT / "llms.txt", out / "llms.txt")
    (out / "schema").mkdir()
    shutil.copy2(ROOT / "docs" / "schema" / "project.schema.json", out / "schema" / "project.schema.json")
    (out / "404.html").write_text(static.document(pack, static.render(static.c.hero(
        {"title": "404", "tag_em": "NOT FOUND", "tag": "", "description": "Nothing here. Try the [[home page]] or the docs."})),
        title="Not found · MTDI 5.0"), encoding="utf-8")
    return out


def build_project_site(project, out, seconds=90):
    """One project's studio as a static site at the root (what `mtdi publish vercel` deploys)."""
    project = load(project) if isinstance(project, (str, pathlib.Path)) else project
    out = pathlib.Path(out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    _assets(out)
    _demo(project, out, "/", "/", seconds)
    return out
