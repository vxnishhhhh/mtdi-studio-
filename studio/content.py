"""Studio words (S1-06): the words the studio shows come from one content file.

    studio/content/default.json      the defaults: today's placeholders, word for word
    MTDI_CONTENT=/path/words.json    override any of them for this studio
    a project's "interface" block    `mtdi run` applies it before the studio is built

T("nav.home") returns the word for a key. An unknown key raises KeyError, so a typo fails
the tests instead of putting a blank on screen. An override may only set keys that exist in
the defaults, and only to non-empty strings; anything else is a ContentError naming the key.
Later overrides win: defaults < MTDI_CONTENT < the project's interface block.
GUIDE: a new word: add its key and today's text to default.json, then build it with T(key).
"""
import json
import os
import pathlib

DEFAULT_PATH = pathlib.Path(__file__).with_name("content") / "default.json"
_state = {"defaults": None, "env": None, "project": {}}


class ContentError(ValueError):
    pass


def defaults():
    if _state["defaults"] is None:
        _state["defaults"] = json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))
    return _state["defaults"]


def validate(words, source):
    """Return words if every key is known and every value a non-empty string."""
    if not isinstance(words, dict):
        raise ContentError(f"{source}: must be an object of key -> words")
    known = defaults()
    unknown = sorted(k for k in words if k not in known)
    if unknown:
        raise ContentError(f"{source}: unknown key(s) {', '.join(unknown)} "
                           f"(see studio/content/default.json for the keys)")
    bad = sorted(k for k, v in words.items() if not isinstance(v, str) or not v.strip())
    if bad:
        raise ContentError(f"{source}: {', '.join(bad)} must be non-empty text")
    return dict(words)


def _from_env():
    if _state["env"] is None:
        path = os.environ.get("MTDI_CONTENT", "").strip()
        words = {}
        if path:
            try:
                words = json.loads(pathlib.Path(path).expanduser().read_text(encoding="utf-8"))
            except (OSError, ValueError) as error:
                raise ContentError(f"MTDI_CONTENT={path}: {error}") from error
            words = validate(words, f"MTDI_CONTENT={path}")
        _state["env"] = words
    return _state["env"]


def use(words, source="interface"):
    """Apply a project's interface block. Call before the studio layout is built."""
    _state["project"] = validate({} if words is None else words, source)


def reset():
    """Forget overrides and re-read MTDI_CONTENT on next use (tests, reloads)."""
    _state["env"] = None
    _state["project"] = {}


def T(key):
    if key not in defaults():
        raise KeyError(f"unknown studio word '{key}' (add it to studio/content/default.json)")
    return _state["project"].get(key) or _from_env().get(key) or defaults()[key]


def words():
    """Every key with the word it resolves to now (for tools and the docs)."""
    return {key: T(key) for key in defaults()}
