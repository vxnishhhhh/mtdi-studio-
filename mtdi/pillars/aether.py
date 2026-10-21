"""Pillar 04 · Aether — purpose, persistence and authorship.

Aether is a non-functional designation: it never enters the signal path and no
score depends on it. It holds why a project exists, who built it and what it
went through, taken from the "aether" block of project.json, so that every
project integrated into MTDI carries its reason with it.
"""


def record(project):
    meta = project["project"]
    aether = project.get("aether", {})
    return {
        "name": meta.get("name"),
        "author": meta.get("author"),
        "purpose": aether.get("purpose") or meta.get("description", ""),
        "story": aether.get("story", []),
        "authorship": aether.get("authorship", []),
        "milestones": aether.get("milestones", []),
        "quote": aether.get("quote"),
        "functional": False,
    }


# ── comment conventions (docs/AETHER.md) ────────────────────────────────────
# Four tags, each written as the tag, a colon, then the text, in any line comment (#, //, %):
#   GUIDE         how to extend this, written for the next person or AI
#   CONTEXT       why it is like this (the decision, not the code)
#   AETHER        the human layer: a joke, a note, a story. Never brain rot.
#   HOURS-WASTED  <hours> - what ate them. Summed by `python -m mtdi aether`.
import io  # noqa: E402
import os  # noqa: E402
import pathlib  # noqa: E402
import re  # noqa: E402
import tokenize  # noqa: E402

TAGS = ("GUIDE", "CONTEXT", "AETHER", "HOURS-WASTED")
_BODY = re.compile(r"^\s*(GUIDE|CONTEXT|AETHER|HOURS-WASTED):\s*(.*)$")
_HOURS = re.compile(r"^(\d+(?:\.\d+)?)\s*(?:h|hours?)?\s*[-–—:]\s*(.+)$")
_SKIP = {".git", "node_modules", "vendor", "public", "__pycache__", ".venv", "build", "dist"}
# Line-comment marker per file type. Python is read with its own tokenizer instead (docstrings, f-strings).
_MARKER = {".sh": "#", ".yml": "#", ".yaml": "#", ".m": "%",
           **dict.fromkeys((".js", ".mjs", ".ts", ".c", ".h", ".cpp", ".hpp", ".ino", ".java"), "//")}


def _python_comments(text):
    for tok in tokenize.generate_tokens(io.StringIO(text).readline):
        if tok.type == tokenize.COMMENT:
            yield tok.start[0], tok.string[1:]


def _line_comments(text, marker):
    """Line comments outside '...', "..." and (for //) /* ... */ blocks, which may span lines.
    Block comments are deliberately not tag carriers."""
    block = False
    for n, line in enumerate(text.splitlines(), 1):
        quote, i = None, 0
        while i < len(line):
            c = line[i]
            if block:
                if line.startswith("*/", i):
                    block, i = False, i + 1
            elif quote:
                if c == "\\":
                    i += 1
                elif c == quote:
                    quote = None
            elif c in "'\"":
                quote = c
            elif marker == "//" and line.startswith("/*", i):
                block, i = True, i + 1
            elif line.startswith(marker, i):
                yield n, line[i + len(marker):]
                break
            i += 1


def _files(root):
    for here, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in _SKIP)   # pruned before descending
        for name in sorted(files):
            path = pathlib.Path(here) / name
            if path.suffix == ".py" or path.suffix in _MARKER:
                yield path


def scan(root="."):
    """Every tagged comment under root: {"tags": {TAG: [..]}, "hours": total, "malformed": [..]}."""
    root = pathlib.Path(root)
    if not root.is_dir():
        raise FileNotFoundError(f"{root} is not a folder")
    found = {t: [] for t in TAGS}
    malformed = []
    for path in _files(root):
        try:
            text = path.read_text(encoding="utf-8")
            comments = list(_python_comments(text) if path.suffix == ".py" else _line_comments(text, _MARKER[path.suffix]))
        except (OSError, UnicodeDecodeError, tokenize.TokenError, SyntaxError):
            continue
        for n, body in comments:
            m = _BODY.match(body)
            if not m:
                continue
            tag, text = m.group(1), m.group(2).strip()
            where = f"{path.relative_to(root).as_posix()}:{n}"
            entry = {"where": where, "text": text}
            if tag == "HOURS-WASTED":
                h = _HOURS.match(text)
                if not h:
                    malformed.append(entry)
                    continue
                entry = {"where": where, "hours": float(h.group(1)), "text": h.group(2).strip()}
            found[tag].append(entry)
    hours = sum(e["hours"] for e in found["HOURS-WASTED"])
    return {"tags": found, "hours": hours, "malformed": malformed}


def render(result, top=10):
    t = result["tags"]
    out = [f"Aether · {len(t['GUIDE'])} guides · {len(t['CONTEXT'])} context notes · {len(t['AETHER'])} aether notes",
           f"Hours wasted, as confessed in comments: {result['hours']:g}"]
    for e in sorted(t["HOURS-WASTED"], key=lambda e: -e["hours"])[:top]:
        out.append(f"  {e['hours']:>5g} h  {e['text']}  ({e['where']})")
    for e in result["malformed"]:
        out.append(f"  ?  unreadable HOURS-WASTED at {e['where']}: write it as HOURS-WASTED, colon, '2 - what happened'")
    return "\n".join(out)
