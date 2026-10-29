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
import math
import pathlib
import re
import shutil

from .protocol import KEY  # a calibration's temperature_key must be one the protocol can carry

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


CALIBRATION_FIELDS = {"gain", "offset", "temp_coeff", "temp_ref", "temperature_key",
                      "residual_sd", "method", "n", "file"}   # "file": set by load(), not by hand


FUSED_FIELDS = {"id", "label", "unit", "inputs", "method", "sd"}
SD_RANGE = (1e-12, 1e12)   # squared, still a normal float: no zero or infinite variance reaches fuse()


class ManifestError(ValueError):
    pass


def load(path):
    """Load a project from its folder or its project.json."""
    path = pathlib.Path(path)
    bundled = pathlib.Path(__file__).resolve().parent.parent / path
    if not path.exists() and not path.is_absolute() and bundled.exists():
        path = bundled                       # "projects/host-health" works from any folder
    file = path / "project.json" if path.is_dir() else path
    if not file.exists():
        raise ManifestError(f"no project.json at {file}")
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except ValueError as error:
        raise ManifestError(f"{file}: invalid JSON ({error})") from error
    # A channel's "calibration" may name a file saved by mtdi.fusion.Calibration.save,
    # relative to the project folder; it is read here so normalise() only sees dicts.
    channels = data.get("channels") if isinstance(data, dict) else None
    for ch in channels if isinstance(channels, list) else []:
        cal = ch.get("calibration") if isinstance(ch, dict) else None
        if isinstance(cal, str):
            folder = file.parent.resolve()
            cal_file = (folder / cal).resolve()
            # CONTEXT: only files inside the project folder. A manifest must not be able to read elsewhere.
            if not cal_file.is_relative_to(folder):
                raise ManifestError(f"channel '{ch.get('id')}': calibration file {cal} is outside the project folder")
            try:
                loaded = json.loads(cal_file.read_text(encoding="utf-8"))
            except (OSError, ValueError) as error:
                raise ManifestError(f"channel '{ch.get('id')}': calibration file {cal}: {error}") from error
            if not isinstance(loaded, dict):
                raise ManifestError(f"channel '{ch.get('id')}': calibration file {cal} must hold a JSON object")
            ch["calibration"] = dict(loaded, file=cal)
    project = normalise(data)
    project["_dir"] = str(file.parent.resolve())
    return project


def normalise(data):
    """Validate a manifest and fill every default, naming the field that is wrong."""
    data = copy.deepcopy(data)
    _require(isinstance(data, dict), "manifest must be a JSON object")
    meta = data.setdefault("project", {})
    _require(isinstance(meta, dict), "project must be an object")
    _require(isinstance(meta.get("id"), str) and meta["id"], "project.id is required")
    meta.setdefault("name", meta["id"])
    data.setdefault("mtdi", MTDI_VERSION)
    from .profiles import DEFAULT, PROFILES  # Intelligence Profile (ADR 0006); late import avoids a cycle
    data.setdefault("profile", DEFAULT)
    _require(isinstance(data["profile"], str) and data["profile"] in PROFILES, f"profile must be one of {', '.join(PROFILES)}")

    sources = data.get("sources") or []
    _require(isinstance(sources, list) and sources, "at least one entry in sources is required")
    source_ids = set()
    for i, src in enumerate(sources):
        where = f"sources[{i}]"
        _require(isinstance(src, dict), f"{where} must be an object")
        _require(isinstance(src.get("id"), str) and src["id"], f"{where}.id is required")
        _require(src["id"] not in source_ids, f"{where}.id '{src['id']}' is used twice")
        _require(isinstance(src.get("adapter"), str) and src["adapter"] in ADAPTERS, f"{where}.adapter must be one of {sorted(ADAPTERS)}")
        source_ids.add(src["id"])

    channels = data.get("channels") or []
    _require(isinstance(channels, list) and channels, "at least one entry in channels is required")
    channel_ids = set()
    for i, ch in enumerate(channels):
        _channel(ch, f"channels[{i}]", sources[0]["id"], source_ids)
        _require(ch["id"] not in channel_ids, f"channels[{i}].id '{ch['id']}' is used twice")
        channel_ids.add(ch["id"])
    by_id = {ch["id"]: ch for ch in channels}
    _fused(data, by_id)

    data.setdefault("hardware", [])
    data.setdefault("environment", {})
    _require(isinstance(data["environment"], dict), "environment must be an object")
    env = data["environment"]
    env.setdefault("window", 10.0)
    env.setdefault("auto_relock_after", None)
    data.setdefault("weights", {})
    data.setdefault("nvtra", {})
    _require(isinstance(data["nvtra"], dict), "nvtra must be an object")
    data["nvtra"].setdefault("rules", [])
    _require(isinstance(data["nvtra"]["rules"], list), "nvtra.rules must be a list")
    for i, rule in enumerate(data["nvtra"]["rules"]):
        _require(isinstance(rule, dict), f"nvtra.rules[{i}] must be an object")
        _require(isinstance(rule.get("when"), dict) and rule["when"], f"nvtra.rules[{i}].when is required")
        for key in rule["when"]:
            _require(key in channel_ids or key in ("active_at_least",),
                     f"nvtra.rules[{i}].when names unknown channel '{key}'")
        _require(rule.get("condition"), f"nvtra.rules[{i}].condition is required")
        direction = rule.get("direction", {})
        _require(isinstance(direction, dict), f"nvtra.rules[{i}].direction must be an object")
        for key, way in direction.items():
            _require(key in by_id, f"nvtra.rules[{i}].direction names unknown channel '{key}'")
            _require(way in ("up", "down"), f"nvtra.rules[{i}].direction.{key} must be \"up\" or \"down\"")
            _require(by_id[key]["kind"] == "scalar",
                     f"nvtra.rules[{i}].direction.{key}: only a scalar channel has a sign (a vector's deviation is a length)")
    data.setdefault("aether", {})
    data.setdefault("interface", {})
    _require(isinstance(data["interface"], dict), "interface must be an object of studio word keys to text")
    return data


def _fused(data, by_id):
    """"fused": several channels measuring the same quantity -> one estimate with an uncertainty."""
    fused = data.setdefault("fused", [])
    _require(isinstance(fused, list), "fused must be a list")
    seen = set(by_id)
    for i, f in enumerate(fused):
        where = f"fused[{i}]"
        _require(isinstance(f, dict), f"{where} must be an object")
        unknown = sorted(set(f) - FUSED_FIELDS)
        _require(not unknown, f"{where} has unknown field(s) {', '.join(unknown)}; allowed: {', '.join(sorted(FUSED_FIELDS))}")
        _require(isinstance(f.get("id"), str) and f["id"], f"{where}.id is required")
        _require(f["id"] not in seen, f"{where}.id '{f['id']}' is already a channel or fused id")
        seen.add(f["id"])
        inputs = f.get("inputs")
        _require(isinstance(inputs, list) and all(isinstance(c, str) for c in inputs), f"{where}.inputs must list channel ids")
        _require(len(inputs) >= 2 and len(set(inputs)) == len(inputs),
                 f"{where}.inputs must list at least two different channel ids")
        for cid in inputs:
            _require(cid in by_id, f"{where}.inputs names unknown channel '{cid}'")
            _require(by_id[cid]["kind"] == "scalar", f"{where}.inputs: '{cid}' is not a scalar channel")
        units = {by_id[cid]["unit"] for cid in inputs}
        _require(len(units) == 1, f"{where}.inputs mix units ({', '.join(sorted(map(repr, units)))}); "
                                  "fuse only readings of the same quantity in the same unit")
        f.setdefault("label", f["id"])
        f["unit"] = units.pop()
        f.setdefault("method", "inverse-variance")
        _require(f["method"] == "inverse-variance", f"{where}.method must be inverse-variance")
        sd = f.setdefault("sd", {})
        _require(isinstance(sd, dict) and all(k in inputs for k in sd), f"{where}.sd may only name its inputs")
        for k, v in sd.items():
            _require(_finite(v) and SD_RANGE[0] <= v <= SD_RANGE[1],
                     f"{where}.sd.{k} must be a number from {SD_RANGE[0]:g} to {SD_RANGE[1]:g}")


def _channel(ch, where, default_source, source_ids):
    _require(isinstance(ch, dict), f"{where} must be an object")
    _require(isinstance(ch.get("id"), str) and ch["id"], f"{where}.id is required")
    ch.setdefault("label", ch["id"])
    # A channel may arrive from one source or from several interchangeable ones
    # (for example a board on USB, or the same board through a TCP bridge).
    src = ch.setdefault("source", default_source)
    ch["sources"] = src if isinstance(src, list) else [src]
    for sid in ch["sources"]:
        _require(isinstance(sid, str) and sid in source_ids, f"{where}.source '{sid}' is not a declared source")
    # "domain" is the field; "physical" (MTDI 5.0 early manifests) is accepted as an alias.
    ch["domain"] = ch.get("domain") or ch.get("physical") or "generic"
    _require(isinstance(ch["domain"], str) and _DOMAIN.match(ch["domain"]),
             f"{where}.domain must be one lowercase word (e.g. {', '.join(sorted(KNOWN_DOMAINS)[:6])}, …)")
    ch["physical"] = ch["domain"]
    keys = ch.get("keys")
    _require(isinstance(keys, list) and keys and all(isinstance(k, str) for k in keys), f"{where}.keys must list protocol keys")
    ch.setdefault("kind", "vector" if len(keys) > 1 else "scalar")
    _require(isinstance(ch["kind"], str) and ch["kind"] in KINDS, f"{where}.kind must be scalar or vector")
    _require(ch["kind"] == "vector" or len(keys) == 1, f"{where}: a scalar channel takes exactly one key")
    ch.setdefault("axes", [k.lower() for k in keys])
    _require(isinstance(ch["axes"], list) and len(ch["axes"]) == len(keys), f"{where}.axes must match keys")
    ch.setdefault("unit", "")
    _require(isinstance(ch["unit"], str), f"{where}.unit must be text")
    scale = ch.setdefault("scale", 1.0)
    if isinstance(scale, list):
        _require(len(scale) == len(keys), f"{where}.scale list must match keys")
    offset = ch.setdefault("offset", 0.0)
    if isinstance(offset, list):
        _require(len(offset) == len(keys), f"{where}.offset list must match keys")
    rng = ch.get("raw_range")
    if rng is not None:
        _require(isinstance(rng, list) and len(rng) == 2 and all(_finite(v) for v in rng) and rng[0] < rng[1], f"{where}.raw_range must be [low, high]")
    ch.setdefault("transform", "none")
    _require(isinstance(ch["transform"], str) and ch["transform"] in TRANSFORMS, f"{where}.transform must be one of {sorted(TRANSFORMS)}")
    ch.setdefault("window", 25)
    floor = ch.setdefault("noise_floor", 0.01)
    _require(_finite(floor) and floor > 0, f"{where}.noise_floor must be > 0")
    ch.setdefault("noise_budget", floor * 10)
    rate = ch.get("expected_rate")
    _require(rate is None or (_finite(rate) and rate > 0), f"{where}.expected_rate must be > 0")
    ch.setdefault("stale_after", max(2.0, 5.0 / rate) if rate else 4.0)
    alert = ch.setdefault("alert_change", floor * 20)
    _require(_finite(alert) and alert > 0, f"{where}.alert_change must be a finite number > 0")
    way = ch.setdefault("alert_direction", "both")
    _require(way in ("both", "up", "down"), f"{where}.alert_direction must be \"both\", \"up\" or \"down\"")
    _require(way == "both" or ch["kind"] == "scalar",
             f"{where}.alert_direction: only a scalar channel has a sign (a vector's change is a length)")
    ch.setdefault("optional", False)
    cal = ch.get("calibration")
    if cal is not None:
        _require(isinstance(cal, dict), f"{where}.calibration must be an object or a file path")
        unknown = sorted(set(cal) - CALIBRATION_FIELDS)
        _require(not unknown, f"{where}.calibration has unknown field(s) {', '.join(unknown)}; "
                              f"allowed: {', '.join(sorted(CALIBRATION_FIELDS))}")
        _require(ch["kind"] == "scalar", f"{where}.calibration applies to scalar channels only")
        for field in ("gain", "offset", "temp_coeff", "temp_ref"):
            _require(_finite(cal.get(field, 0)), f"{where}.calibration.{field} must be a finite number")
        sd = cal.get("residual_sd")
        _require(sd is None or (_finite(sd) and 0 <= sd <= SD_RANGE[1]),
                 f"{where}.calibration.residual_sd must be a number from 0 to {SD_RANGE[1]:g}, or null")
        _require(isinstance(cal.get("n", 0), int) and not isinstance(cal.get("n", 0), bool) and cal.get("n", 0) >= 0,
                 f"{where}.calibration.n must be a whole number >= 0")
        _require(isinstance(cal.get("method", ""), str), f"{where}.calibration.method must be text")
        tkey = cal.get("temperature_key")
        _require(tkey is None or (isinstance(tkey, str) and KEY.match(tkey)),
                 f"{where}.calibration.temperature_key must be a protocol key (letters, digits, _ . -)")
        _require(not cal.get("temp_coeff") or tkey, f"{where}.calibration has temp_coeff but no temperature_key")


def _finite(value):
    # json.loads accepts NaN and Infinity; a calibration built from them turns every reading into NaN.
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:   # a JSON integer too large for a float
        return False


def _require(ok, message):
    if not ok:
        raise ManifestError(message)


def scale_of(ch, i):
    s = ch["scale"]
    return s[i] if isinstance(s, list) else s


def offset_of(ch, i):
    o = ch["offset"]
    return o[i] if isinstance(o, list) else o


PROJECT_ID = re.compile(r"[a-z0-9][a-z0-9\-]{1,47}")


def new_project(pid, name=None, folder=None):
    """`mtdi new`: copy projects/_template to projects/<pid> and name it. Returns the new folder.

    Raises ValueError with the reason when the id or name is unusable or the folder exists."""
    folder = pathlib.Path(folder) if folder else pathlib.Path(__file__).resolve().parent.parent / "projects"
    if not isinstance(pid, str) or not PROJECT_ID.fullmatch(pid):
        raise ValueError("project id: lowercase letters, digits and dashes")
    if name is not None and (not isinstance(name, str) or len(name) > 80
                             or any(ord(c) < 32 or ord(c) == 127 for c in name)):
        raise ValueError("project name: text of at most 80 characters, on one line")
    name = (name or "").strip() or pid.replace("-", " ").title()
    target = folder / pid
    try:
        exists = target.exists()
    except OSError as error:   # e.g. no permission to look in projects/
        raise ValueError(f"could not check {target}: {error.strerror or error}") from None
    if exists:
        raise ValueError(f"{target} already exists")
    try:
        shutil.copytree(folder / "_template", target)
    except FileExistsError:   # made between the check and the copy: someone else's folder, leave it
        raise ValueError(f"{target} already exists") from None
    except OSError as error:
        shutil.rmtree(target, ignore_errors=True)
        raise ValueError(f"could not write {target}: {error.strerror or error}") from None
    try:
        manifest = target / "project.json"
        data = json.loads(manifest.read_text(encoding="utf-8"))
        data["project"]["id"] = pid
        data["project"]["name"] = name
        manifest.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        load(target)
    except OSError as error:
        shutil.rmtree(target, ignore_errors=True)
        raise ValueError(f"could not write {target}: {error.strerror or error}") from None
    except BaseException:
        shutil.rmtree(target, ignore_errors=True)   # never leave half a project behind
        raise
    return target


def summary(project, target=None):
    """What `mtdi check` reports about a loaded project, as data (the CLI and the studio both show it)."""
    from .capabilities import detect_host
    from .profiles import qualifies
    meta = project["project"]
    target = target or detect_host()
    ok, runtime, why = qualifies(project["profile"], target)
    return {
        "id": meta["id"], "name": meta["name"], "mtdi": project["mtdi"],
        "sources": [{"id": s["id"], "adapter": s["adapter"],
                     "detail": {k: v for k, v in s.items() if k not in ("id", "adapter")}} for s in project["sources"]],
        "channels": [{k: c[k] for k in ("id", "kind", "domain", "keys", "unit", "sources", "noise_floor", "transform", "window")}
                     for c in project["channels"]],
        "interface_words": len(project["interface"] or {}),
        "profile": project["profile"], "target": target["id"], "runtime": runtime, "qualifies": ok, "why": why,
        "nvtra_rules": len(project["nvtra"]["rules"]),
        "environments": len(list((pathlib.Path(project["_dir"]) / "environments").glob("*.json"))),
    }
