"""Project manifests: how a piece of hardware, firmware or software joins MTDI.

A project is a folder under projects/ with a project.json. The manifest names
the sources (where lines arrive), the channels (which keys form which
measurement, in which unit) and anything the pillars should know. A channel can
be a physical sensor, a software metric, a network measurement or a security
counter: MTDI's pillars never hardcode one. Everything specific lives here.

Field reference: docs/MANIFEST.md. Template: projects/_template/project.json.
"""
import copy
import json
import pathlib
import re

MTDI_VERSION = "5.0"
ADAPTERS = {"serial", "tcp", "http", "replay", "simulator", "python", "process", "system"}
KINDS = {"scalar", "vector"}
TRANSFORMS = {"none", "ac_rms"}
# A channel's domain is an open word. These are the ones the docs and interface know;
# any other lowercase word is accepted, so a new field never needs a code change.
KNOWN_DOMAINS = {"ultrasonic", "radio", "acoustic", "optical", "thermal", "motion", "power",
                 "inertial", "pressure", "chemical", "compute", "network",
                 "security", "software", "energy", "environmental", "biomedical", "generic"}
_DOMAIN = re.compile(r"^[a-z][a-z0-9_\-]{0,31}$")


class ManifestError(ValueError):
    pass


def load(path):
    """Load a project from its folder or its project.json."""
    path = pathlib.Path(path)
    file = path / "project.json" if path.is_dir() else path
    if not file.exists():
        raise ManifestError(f"no project.json at {file}")
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except ValueError as error:
        raise ManifestError(f"{file}: invalid JSON ({error})") from error
    project = normalise(data)
    project["_dir"] = str(file.parent.resolve())
    return project


def normalise(data):
    """Validate a manifest and fill every default, naming the field that is wrong."""
    data = copy.deepcopy(data)
    _require(isinstance(data, dict), "manifest must be a JSON object")
    meta = data.setdefault("project", {})
    _require(isinstance(meta.get("id"), str) and meta["id"], "project.id is required")
    meta.setdefault("name", meta["id"])
    data.setdefault("mtdi", MTDI_VERSION)
    from .profiles import DEFAULT, PROFILES  # Intelligence Profile (ADR 0006); late import avoids a cycle
    data.setdefault("profile", DEFAULT)
    _require(data["profile"] in PROFILES, f"profile must be one of {', '.join(PROFILES)}")

    sources = data.get("sources") or []
    _require(isinstance(sources, list) and sources, "at least one entry in sources is required")
    source_ids = set()
    for i, src in enumerate(sources):
        where = f"sources[{i}]"
        _require(isinstance(src.get("id"), str) and src["id"], f"{where}.id is required")
        _require(src["id"] not in source_ids, f"{where}.id '{src['id']}' is used twice")
        _require(src.get("adapter") in ADAPTERS, f"{where}.adapter must be one of {sorted(ADAPTERS)}")
        source_ids.add(src["id"])

    channels = data.get("channels") or []
    _require(isinstance(channels, list) and channels, "at least one entry in channels is required")
    channel_ids = set()
    for i, ch in enumerate(channels):
        _channel(ch, f"channels[{i}]", sources[0]["id"], source_ids)
        _require(ch["id"] not in channel_ids, f"channels[{i}].id '{ch['id']}' is used twice")
        channel_ids.add(ch["id"])

    data.setdefault("hardware", [])
    data.setdefault("environment", {})
    env = data["environment"]
    env.setdefault("window", 10.0)
    env.setdefault("auto_relock_after", None)
    data.setdefault("weights", {})
    data.setdefault("nvtra", {})
    data["nvtra"].setdefault("rules", [])
    for i, rule in enumerate(data["nvtra"]["rules"]):
        _require(isinstance(rule.get("when"), dict) and rule["when"], f"nvtra.rules[{i}].when is required")
        for key in rule["when"]:
            _require(key in channel_ids or key in ("active_at_least",),
                     f"nvtra.rules[{i}].when names unknown channel '{key}'")
        _require(rule.get("condition"), f"nvtra.rules[{i}].condition is required")
    data.setdefault("aether", {})
    data.setdefault("interface", {})
    return data


def _channel(ch, where, default_source, source_ids):
    _require(isinstance(ch.get("id"), str) and ch["id"], f"{where}.id is required")
    ch.setdefault("label", ch["id"])
    # A channel may arrive from one source or from several interchangeable ones
    # (for example a board on USB, or the same board through a TCP bridge).
    src = ch.setdefault("source", default_source)
    ch["sources"] = src if isinstance(src, list) else [src]
    for sid in ch["sources"]:
        _require(sid in source_ids, f"{where}.source '{sid}' is not a declared source")
    # "domain" is the field; "physical" (MTDI 5.0 early manifests) is accepted as an alias.
    ch["domain"] = ch.get("domain") or ch.get("physical") or "generic"
    _require(isinstance(ch["domain"], str) and _DOMAIN.match(ch["domain"]),
             f"{where}.domain must be one lowercase word (e.g. {', '.join(sorted(KNOWN_DOMAINS)[:6])}, …)")
    ch["physical"] = ch["domain"]
    keys = ch.get("keys")
    _require(isinstance(keys, list) and keys and all(isinstance(k, str) for k in keys), f"{where}.keys must list protocol keys")
    ch.setdefault("kind", "vector" if len(keys) > 1 else "scalar")
    _require(ch["kind"] in KINDS, f"{where}.kind must be scalar or vector")
    _require(ch["kind"] == "vector" or len(keys) == 1, f"{where}: a scalar channel takes exactly one key")
    ch.setdefault("axes", [k.lower() for k in keys])
    _require(len(ch["axes"]) == len(keys), f"{where}.axes must match keys")
    ch.setdefault("unit", "")
    scale = ch.setdefault("scale", 1.0)
    if isinstance(scale, list):
        _require(len(scale) == len(keys), f"{where}.scale list must match keys")
    offset = ch.setdefault("offset", 0.0)
    if isinstance(offset, list):
        _require(len(offset) == len(keys), f"{where}.offset list must match keys")
    rng = ch.get("raw_range")
    if rng is not None:
        _require(isinstance(rng, list) and len(rng) == 2 and rng[0] < rng[1], f"{where}.raw_range must be [low, high]")
    ch.setdefault("transform", "none")
    _require(ch["transform"] in TRANSFORMS, f"{where}.transform must be one of {sorted(TRANSFORMS)}")
    ch.setdefault("window", 25)
    floor = ch.setdefault("noise_floor", 0.01)
    _require(isinstance(floor, (int, float)) and floor > 0, f"{where}.noise_floor must be > 0")
    ch.setdefault("noise_budget", floor * 10)
    rate = ch.get("expected_rate")
    _require(rate is None or rate > 0, f"{where}.expected_rate must be > 0")
    ch.setdefault("stale_after", max(2.0, 5.0 / rate) if rate else 4.0)
    ch.setdefault("alert_change", floor * 20)
    ch.setdefault("optional", False)


def _require(ok, message):
    if not ok:
        raise ManifestError(message)


def scale_of(ch, i):
    s = ch["scale"]
    return s[i] if isinstance(s, list) else s


def offset_of(ch, i):
    o = ch["offset"]
    return o[i] if isinstance(o, list) else o
