"""NVTRA's agents (S1-12, owner brief: "agents that actually work and do whatever, create graphs").

Four agents, each added because something was missing (the owner's rule: no agent for the sake
of it). Every agent returns plain data plus the sources it used, so NVTRA can explain where an
answer came from and the Validation Chamber can check it.

    researcher  goes online: scholarly papers (Crossref), preprints (arXiv), encyclopaedia
                (Wikipedia). Free, keyless APIs only. Results are references, never facts NVTRA
                may state as measured.
    analyst     statistics and features of a channel's recent values (mtdi.ml.features)
    grapher     a Plotly figure (JSON) for any series, ready for the studio or a report
    validator   checks that every number in a draft answer exists in the live data, so NVTRA
                cannot slip in an invented reading

How to add one: write a function that takes plain inputs and returns {"result", "sources"},
register it in AGENTS, and give it a test. (Aether: please do not add an agent that writes
other agents. We have seen that film. Hours wasted: 0, and we would like to keep it that way.)
"""
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from .ml.features import window_features

UA = {"User-Agent": "MTDI-NVTRA/5.0 (+https://github.com/vxnishhhhh/mtdi-studio-)"}
CROSSREF = "https://api.crossref.org/works"
ARXIV = "https://export.arxiv.org/api/query"
WIKIPEDIA = "https://en.wikipedia.org/w/api.php"


def _get(url, timeout=20):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


# ── researcher ──────────────────────────────────────────────────────────────
def research(query, limit=5, sources=("crossref", "arxiv", "wikipedia"), base=None):
    """Search free scholarly sources. Each hit: title, authors, year, url, source. Never raises
    for one failing source: its error is reported in "errors" and the others still answer."""
    base = base or {}
    query = str(query).strip()[:300]
    if not query:
        raise ValueError("research() needs a query")
    hits, errors = [], {}
    if "crossref" in sources:
        try:
            q = urllib.parse.urlencode({"query": query, "rows": limit,
                                        "select": "title,author,issued,DOI,URL,container-title"})
            for item in json.loads(_get(f"{base.get('crossref', CROSSREF)}?{q}"))["message"]["items"]:
                year = (((item.get("issued") or {}).get("date-parts") or [[None]])[0] or [None])[0]
                hits.append({"source": "crossref", "title": (item.get("title") or ["?"])[0],
                             "authors": [f"{a.get('family', '')}, {a.get('given', '')}".strip(", ")
                                         for a in item.get("author", [])][:6],
                             "year": year, "venue": (item.get("container-title") or [""])[0],
                             "url": item.get("URL") or (f"https://doi.org/{item['DOI']}" if item.get("DOI") else "")})
        except Exception as exc:
            errors["crossref"] = f"{type(exc).__name__}: {exc}"
    if "arxiv" in sources:
        try:
            words = [w for w in re.findall(r"[\w-]+", query)][:8]  # every word must match, or arXiv ORs them
            q = urllib.parse.urlencode({"search_query": " AND ".join(f"all:{w}" for w in words), "max_results": limit})
            ns = {"a": "http://www.w3.org/2005/Atom"}
            for entry in ET.fromstring(_get(f"{base.get('arxiv', ARXIV)}?{q}")).findall("a:entry", ns):
                hits.append({"source": "arxiv", "title": " ".join((entry.findtext("a:title", "", ns)).split()),
                             "authors": [a.findtext("a:name", "", ns) for a in entry.findall("a:author", ns)][:6],
                             "year": (entry.findtext("a:published", "", ns) or "")[:4] or None, "venue": "arXiv",
                             "url": entry.findtext("a:id", "", ns)})
        except Exception as exc:
            errors["arxiv"] = f"{type(exc).__name__}: {exc}"
    if "wikipedia" in sources:
        try:
            q = urllib.parse.urlencode({"action": "query", "list": "search", "srsearch": query,
                                        "srlimit": limit, "format": "json"})
            for item in json.loads(_get(f"{base.get('wikipedia', WIKIPEDIA)}?{q}"))["query"]["search"]:
                hits.append({"source": "wikipedia", "title": item["title"], "authors": ["Wikipedia contributors"],
                             "year": (item.get("timestamp") or "")[:4] or None, "venue": "Wikipedia",
                             "url": "https://en.wikipedia.org/wiki/" + urllib.parse.quote(item["title"].replace(" ", "_")),
                             "snippet": re.sub(r"<[^>]+>", "", item.get("snippet", ""))})
        except Exception as exc:
            errors["wikipedia"] = f"{type(exc).__name__}: {exc}"
    return {"result": hits, "sources": sorted({h["source"] for h in hits}), "errors": errors,
            "note": "references to read, not measurements"}


# ── analyst ─────────────────────────────────────────────────────────────────
def analyse(values, label="series"):
    vals = [float(v) for v in values if v is not None]
    if len(vals) < 2:
        raise ValueError("analyse() needs at least two values")
    return {"result": {"label": label, "n": len(vals), **window_features(vals)}, "sources": [label]}


# ── grapher ─────────────────────────────────────────────────────────────────
def graph(series, title="", y_label="", x=None):
    """A Plotly figure dict. series: {name: [values]}; x: shared x values (default: index)."""
    if not series:
        raise ValueError("graph() needs at least one series")
    traces = []
    for name, values in series.items():
        ys = [float(v) for v in values]
        traces.append({"type": "scatter", "mode": "lines", "name": str(name), "y": ys,
                       "x": list(x) if x is not None else list(range(len(ys))),
                       "line": {"width": 2}})
    layout = {"title": {"text": title}, "yaxis": {"title": {"text": y_label}},
              "paper_bgcolor": "#000000", "plot_bgcolor": "#000000", "font": {"color": "#E3B945"}}
    return {"result": {"data": traces, "layout": layout}, "sources": list(series)}


# ── validator ───────────────────────────────────────────────────────────────
NUMBER = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?(?:e-?\d+)?")


def validate(text, packet, tolerance=0.01):
    """Every number in `text` must match a number in `packet` (relative tolerance), except
    small counting words like 1-10 used as ordinals. Returns the unsupported numbers."""
    known = [float(n) for n in NUMBER.findall(json.dumps(packet, default=str))]
    unsupported = []
    for token in NUMBER.findall(text):
        value = float(token)
        if value.is_integer() and 0 <= value <= 10:
            continue
        if not any(abs(value - k) <= tolerance * max(1.0, abs(k)) for k in known):
            unsupported.append(token)
    return {"result": {"ok": not unsupported, "unsupported": unsupported}, "sources": ["live packet"]}


AGENTS = {"researcher": research, "analyst": analyse, "grapher": graph, "validator": validate}
