"""Generate the studio's I³ content pack from a project, and flatten packets for it.

Nothing here is written per project: the pages, the signal path, the pillar
contents and every live binding are derived from project.json, so a newly
integrated project gets a complete interface the moment its manifest loads.
"""
from ..pillars import PILLARS

GOOD, FAIR = 75.0, 50.0


# ════ live state: packet -> {bind key: value | {value, state}} ═══════════════
def _n(v, unit=""):
    if v is None:
        return "—"
    if isinstance(v, list):
        return " · ".join(_n(x) for x in v) + (f" {unit}" if unit else "")
    a = abs(v)
    text = f"{v:.3e}" if a >= 1e6 else f"{v:.0f}" if a >= 1000 else f"{v:.4g}"
    return f"{text} {unit}".strip()


def _grade(score):
    return "ok" if score >= GOOD else "warn" if score >= FAIR else "high"


STATE_DOT = {"connected": "ok", "receiving": "ok", "stale": "high", "offline": "high", "waiting": "off",
             "idle": "off", "finished": "warn"}


def flatten(packet):
    f = packet["fusion"]
    out = {
        "mtdi.score": {"value": f"{f['score']:.1f} %", "state": _grade(f["score"])},
        "mtdi.completeness": f"{f['completeness']:.0f} %",
        "mtdi.condition": f["condition"],
        "mtdi.interpretation": f["interpretation"],
        "mtdi.evidence": " | ".join(f["evidence"]) or "No live channel.",
        "mtdi.warnings": " | ".join(f["warnings"]) or "None.",
        "mtdi.correlation": " | ".join(f"{a} ↔ {b}: {m['coefficient']:+.2f}" for m in f["correlation"]
                                       for a, b in [m["channels"]]) or "Needs two channels with history.",
        "env.names": ", ".join(packet["environments"]) or "None saved yet.",
        "events.last": packet["events"][-1]["message"] if packet["events"] else "No actions yet.",
    }
    for cid, c in packet["channels"].items():
        ev, env, unit = c["evidence"], c["environment"], c["unit"]
        p = f"ch.{cid}."
        if env.get("pinned"):
            base_state = "comparing to saved environment"
        elif env.get("frozen"):
            base_state = "locked"
        elif env.get("settling"):
            base_state = "learning"
        else:
            base_state = "tracking ambient"
        out.update({
            p + "value": _n(c["magnitude"], unit),
            p + "vector": _n(c["value"], unit) if c["kind"] == "vector" else _n(c["value"], unit),
            p + "deviation": _n(env.get("deviation"), unit),
            p + "snr": _n(env.get("snr")),
            p + "score": {"value": f"{c['score']:.1f} %", "state": _grade(c["score"])},
            p + "state": {"value": ev["state"], "state": STATE_DOT.get(ev["state"], "off")},
            p + "age": "—" if ev["age"] is None else f"{ev['age']:.1f} s",
            p + "rate": (f"{ev['rate']:.3g} Hz" + (f" of {ev['expected_rate']:g}" if ev["expected_rate"] else "")),
            p + "timing": f"{ev['timing'] * 100:.0f} %",
            p + "clip": f"{ev['clip_share'] * 100:.0f} %" + (" · clipping now" if ev["clipped"] else ""),
            p + "lod": _n(ev.get("lod"), unit),
            p + "loq": _n(ev.get("loq"), unit),
            p + "samples": str(ev["samples"]),
            p + "source": ev["data_source"],
            p + "baseline": _n(env.get("baseline"), unit),
            p + "baseline_state": base_state + (" · STALE" if env.get("stale") else ""),
            p + "noise": _n(env.get("noise"), unit),
            p + "transient": env.get("transient", {}).get("state", "—"),
            p + "agreement": "—" if env.get("agreement") is None else f"{env['agreement'] * 100:.0f} %",
            p + "spark": c["spark"],
        })
        for factor, value in c["terms"].items():
            out[p + "term." + factor] = f"{value:.0f} %"
    for sid, s in packet["sources"].items():
        p = f"src.{sid}."
        out[p + "state"] = {"value": s["state"], "state": STATE_DOT.get(s["state"], "off")}
        out[p + "message"] = s["message"] or "—"
        out[p + "lines"] = f"{s['lines']} lines · {s['rejected']} rejected"
    return out


# ════ content pack ═══════════════════════════════════════════════════════════
def content_pack(project, simulated):
    meta, ui = project["project"], project.get("interface", {})
    name = meta.get("name", meta["id"])
    words = name.upper().split()
    top, bottom = (words[0], " ".join(words[1:])) if len(words) > 1 else (name.upper(), "MTDI")
    channels = project["channels"]
    hw = project.get("hardware", [])
    intro = ui.get("intro", {})
    return {
        "brand": {"name": name, "author": meta.get("author"), "credit": meta.get("author")},
        "notice": "SIMULATED DATA · SOFTWARE SIMULATOR" if simulated else None,
        "force_home_on_load": ui.get("force_home_on_load", False),
        "intro": {
            "eyebrow": "MTDI 5.0   ·   I³   Induction · Interference · Intelligence",
            "title_top": intro.get("title_top", top), "title_bottom": intro.get("title_bottom", bottom),
            "kicker": "Project overview", "card_title": name,
            "description": meta.get("description", ""),
            "grid_label": "Hardware" if hw else "Channels",
            "grid": [{"name": h.get("name", ""), "role": h.get("role", "")} for h in hw[:6]] or
                    [{"name": c["label"].upper(), "role": c["unit"] or c["domain"]} for c in channels[:6]],
        },
        "status": [{"label": "MTDI", "bind": "mtdi.score", "state": "off"},
                   {"label": "LIVE", "bind": "mtdi.completeness", "state": "ok"}],
        "dock": {"name": "NVTRA", "hint": "Press N or click to ask about this project",
                 "placeholder": "Ask NVTRA: score, a channel name, what is happening…",
                 "chip": {"label": "MTDI", "bind": "mtdi.score", "state": "off"}},
        "pages": [_home(project, name), _channels(project), _framework(project), _environment(project),
                  _validation(project), _settings(project)],
    }


def _hero(project, title, tag_em, tag, description):
    return {"title": title, "tag_em": tag_em, "tag": tag, "description": description,
            "spec": [{"k": h.get("name", ""), "v": h.get("role", "")} for h in project.get("hardware", [])[:7]]}


def _home(project, name):
    meta, ui = project["project"], project.get("interface", {})
    page = {"path": "/", "type": "home", "label": "Home",
            "hero": _hero(project, name, "MTDI 5.0", "   —   " + (meta.get("tagline") or meta.get("domain", "").upper()),
                          meta.get("description", "")),
            "modules": {
                "title": "MTDI Studio",
                "line": "Every pillar of [[MTDI 5.0]], working on this project's own channels.",
                "core": "MTDI", "core_sub": "5.0",
                "items": [
                    {"num": "01", "key": "CHANNELS", "role": "live", "title": "Channels", "href": "/channels", "accent": "#67cbd5",
                     "desc": f"{len(project['channels'])} channels from {len(project['sources'])} sources.",
                     "live": {"bind": "mtdi.completeness", "label": "LIVE"}},
                    {"num": "02", "key": "MTDI", "role": "framework", "title": "MTDI Framework", "href": "/mtdi", "accent": "#72b99c",
                     "desc": "Five pillars round one diagnostic core.", "live": {"bind": "mtdi.score", "label": "SCORE"}},
                    {"num": "03", "key": "ENVIRONMENT", "role": "pillar 01", "title": "Environmental Intelligence",
                     "href": "/environment", "accent": "#00e676", "desc": "Learn, lock and compare the real environment.",
                     "live": {"bind": "env.names", "label": "SAVED"}},
                    {"num": "04", "key": "VALIDATION", "role": "pillar 00", "title": "Validation Chamber", "href": "/validation",
                     "accent": "#2979ff", "desc": "Presence, freshness, timing and detection limits.",
                     "live": {"bind": "mtdi.condition", "label": ""}},
                ],
            }}
    if ui.get("globe"):
        page["modules"]["globe"] = ui["globe"]
    if ui.get("home_opening"):
        page["opening"] = ui["home_opening"]
    return page


def _channel_section(c):
    p = f"ch.{c['id']}."
    unit = f" ({c['unit']})" if c["unit"] else ""
    return {"kind": "section", "kicker": f"{c['domain']} · {c['kind']} · {', '.join(c['keys'])}",
            "title": c["label"], "accent": c.get("accent"),
            "blocks": [
                {"kind": "metrics", "items": [
                    {"label": "Value" + unit, "bind": p + "value"},
                    {"label": "Deviation from baseline", "bind": p + "deviation"},
                    {"label": "Signal to ambient noise", "bind": p + "snr"},
                    {"label": "MTDI channel score", "bind": p + "score"},
                    {"label": "State", "bind": p + "state"},
                ]},
                {"kind": "spark", "label": "Deviation from baseline · last ~12 s", "bind": p + "spark",
                 "value_bind": p + "transient"},
            ]}


def _channels(project):
    return {"path": "/channels", "type": "module", "label": "Channels",
            "hero": _hero(project, "Channels", "LIVE", "   —   EVERY MEASURED CHANNEL",
                          "Each channel is a set of protocol keys mapped to one measurement. Values are shown "
                          "after the manifest's [[scale]] and [[offset]]; deviation is measured against the channel's "
                          "own learned baseline."),
            "blocks": [_channel_section(c) for c in project["channels"]]}


def _flow(project):
    """The signal path, derived from the project's channels."""
    chans = project["channels"]
    shown = chans[:4] if len(chans) <= 4 else chans[:3]
    xs = {1: [0.5], 2: [0.3, 0.7], 3: [0.18, 0.5, 0.82], 4: [0.14, 0.38, 0.62, 0.86]}
    n = len(shown) + (1 if len(chans) > 4 else 0)
    nodes = [{"x": xs[n][i], "y": 0.22, "w": 0.22, "title": c["label"], "copy": f"{c['domain']} · {c['unit'] or 'units'}"}
             for i, c in enumerate(shown)]
    if len(chans) > 4:
        nodes.append({"x": xs[n][-1], "y": 0.22, "w": 0.22, "title": f"+{len(chans) - 3} channels", "copy": "see Channels"})
    base = len(nodes)
    nodes += [
        {"x": 0.31, "y": 0.44, "w": 0.35, "title": "Validation Chamber", "copy": "Presence · freshness · timing · range"},
        {"x": 0.69, "y": 0.44, "w": 0.35, "title": "Environmental Intelligence", "copy": "Learn · lock · compare"},
        {"x": 0.50, "y": 0.64, "w": 0.48, "title": "MTDI Core", "copy": "Eight weighted factors per channel", "core": True},
        {"x": 0.29, "y": 0.83, "w": 0.35, "title": "I³ Interface", "copy": "Live graphs · vectors · confidence"},
        {"x": 0.71, "y": 0.83, "w": 0.35, "title": "NVTRA", "copy": "Plain language · reasoning context"},
    ]
    # Left channels feed Validation, right channels feed Environment, the middle one feeds both.
    mid = (base - 1) / 2
    links = []
    for i in range(base):
        if i <= mid:
            links.append([i, base])
        if i >= mid:
            links.append([i, base + 1])
    links += [[base, base + 2], [base + 1, base + 2], [base + 2, base + 3], [base + 2, base + 4]]
    return {"kind": "flow", "title": "MTDI SIGNAL PATH",
            "tagline": "Scroll to trace each channel into the MTDI core.",
            "nodes": nodes, "links": links,
            "footnote": "Aether is a non-functional designation and does not appear in the signal path."}


def _validation_blocks(project):
    blocks = []
    for c in project["channels"]:
        p = f"ch.{c['id']}."
        blocks.append({"kind": "section", "kicker": "Evidence", "title": c["label"], "accent": "#2979ff", "blocks": [
            {"kind": "metrics", "items": [
                {"label": "State", "bind": p + "state"}, {"label": "Sample age", "bind": p + "age"},
                {"label": "Achieved rate", "bind": p + "rate"}, {"label": "Timing regularity", "bind": p + "timing"},
                {"label": "Clipped samples", "bind": p + "clip"}, {"label": "Data source", "bind": p + "source"},
                {"label": "LOD · 3σ", "bind": p + "lod"}, {"label": "LOQ · 10σ", "bind": p + "loq"},
                {"label": "Samples", "bind": p + "samples"},
            ]}]})
    blocks.append({"kind": "section", "kicker": "Sources", "title": "Where the lines come from", "accent": "#2979ff",
                   "blocks": [{"kind": "metrics", "items": [
                       {"label": f"{s['id']} · {s['adapter']}", "bind": f"src.{s['id']}.state",
                        "note": ""} for s in project["sources"]]},
                       {"kind": "metrics", "items": [
                           {"label": f"{s['id']} detail", "bind": f"src.{s['id']}.message"} for s in project["sources"]]},
                       {"kind": "metrics", "items": [
                           {"label": f"{s['id']} traffic", "bind": f"src.{s['id']}.lines"} for s in project["sources"]]}]})
    return blocks


ENV_ACTIONS = {"kind": "actions", "items": [
    {"label": "Re-learn all", "action": "learn"},
    {"label": "Lock all", "action": "lock"},
    {"label": "Unlock all", "action": "unlock"},
    {"label": "Save as environment…", "action": "save", "prompt": "Name this environment (e.g. bedroom, lab bench)"},
    {"label": "Compare with saved…", "action": "compare", "prompt": "Which saved environment? (see the list below)"},
]}


def _environment_blocks(project):
    blocks = [{"kind": "section", "kicker": "Pillar 01", "title": "Learn · lock · compare", "accent": "#00e676",
               "copy": ["Each channel learns its reference from the real environment it sits in. Lock the reference and "
                        "every change after that is measured against it; it never drifts toward a new signal on its own.",
                        "Save a learned environment under a name and compare against it later. Simulated data is refused: "
                        "a saved environment is evidence."],
               "blocks": [ENV_ACTIONS,
                          {"kind": "metrics", "items": [{"label": "Saved environments", "bind": "env.names"},
                                                         {"label": "Last action", "bind": "events.last"}]}]}]
    for c in project["channels"]:
        p = f"ch.{c['id']}."
        items = [{"label": "Baseline", "bind": p + "baseline"}, {"label": "Baseline state", "bind": p + "baseline_state"},
                 {"label": "Ambient noise σ", "bind": p + "noise"}, {"label": "Deviation", "bind": p + "deviation"},
                 {"label": "Signal to noise", "bind": p + "snr"}, {"label": "Transient", "bind": p + "transient"}]
        if c["kind"] == "vector":
            items.append({"label": "Axial consensus", "bind": p + "agreement"})
        blocks.append({"kind": "section", "kicker": f"{c['domain']} environment", "title": c["label"], "accent": "#00e676",
                       "blocks": [{"kind": "metrics", "items": items},
                                  {"kind": "spark", "label": "Deviation from baseline", "bind": p + "spark",
                                   "value_bind": p + "baseline_state", "accent": "#00e676"}]})
    return blocks


def _nvtra_blocks(project):
    rules = project["nvtra"]["rules"]
    return [{"kind": "section", "kicker": "Pillar 02", "title": "What the pillars found", "accent": "#ffd166", "blocks": [
        {"kind": "live", "label": "Condition", "bind": "mtdi.condition"},
        {"kind": "live", "label": "Interpretation", "bind": "mtdi.interpretation"},
        {"kind": "live", "label": "Evidence", "bind": "mtdi.evidence"},
        {"kind": "live", "label": "Warnings", "bind": "mtdi.warnings"},
        {"kind": "live", "label": "Cross-channel correlation", "bind": "mtdi.correlation"},
        {"kind": "list", "items": [f"[[{r['condition']}]] when " + ", ".join(f"{k} {v}" for k, v in r["when"].items())
                                   for r in rules] or ["This project defines no domain rules yet; universal rules apply."]},
    ]}]


def _core_blocks(project):
    from ..core import FACTOR_LABELS
    blocks = [{"kind": "section", "kicker": "MTDI core", "title": "A score that can be taken apart", "accent": "#00e5ff",
               "copy": "Eight named factors per channel, weighted, averaged over every declared channel. An offline channel "
                       "scores zero. It is an evidence-quality score, [[not a calibrated probability]].",
               "blocks": [{"kind": "metrics", "items": [
                   {"label": "MTDI", "bind": "mtdi.score"}, {"label": "Channels live", "bind": "mtdi.completeness"}]}]}]
    for c in project["channels"]:
        blocks[0]["blocks"].append({"kind": "metrics", "items": [
            {"label": f"{c['label']} · {FACTOR_LABELS[k]}", "bind": f"ch.{c['id']}.term.{k}"} for k in FACTOR_LABELS]})
    return blocks


def _framework(project):
    pillar_blocks = {
        "validation": _validation_blocks(project),
        "environment": _environment_blocks(project),
        "nvtra": _nvtra_blocks(project),
        "i3": [{"kind": "section", "kicker": "Pillar 03", "title": "I³ Philosophy", "accent": "#b388ff",
                "copy": "I³ is the interface every pillar is seen through: induction as the origin, interference as the "
                        "target, intelligence as the meaning layer. This page is drawn by it.",
                "blocks": [{"kind": "cards", "cols": 3, "items": [
                    {"num": "I¹", "title": "Induction", "desc": "Taking the world in: the channels and their sources.", "accent": "#00e5ff"},
                    {"num": "I²", "title": "Interference", "desc": "What disturbs it, separated from what is ambient.", "accent": "#2979ff"},
                    {"num": "I³", "title": "Intelligence", "desc": "Readings that keep their health and trust attached.", "accent": "#b388ff"}]}]}],
        "aether": _aether_blocks(project),
    }
    return {"path": "/mtdi", "type": "framework", "label": "MTDI", "name": "MTDI",
            "opening": _flow(project),
            "landing": {"kicker": "MICROPROCESSING TECHNOLOGICAL DIAGNOSTIC INTELLIGENCE · 5.0",
                        "title": "The system’s self-awareness.",
                        "copy": "MTDI separates connection, freshness, stability, completeness and trust. Five pillars "
                                "surround one diagnostic core; select one to enter it.",
                        "meta": ["5 PILLARS", "8 WEIGHTED FACTORS", f"{len(project['channels'])} CHANNELS",
                                 f"{len(project['sources'])} SOURCES"]},
            "caption": {"title": "FIVE PILLARS · ONE CORE", "text": "Select a pillar to expand it."},
            "core": {"label": "MTDI", "sub": "5.0 core", "sphere": True},
            "pillars": [dict(p, blocks=pillar_blocks[p["id"]]) for p in PILLARS],
            "blocks": _core_blocks(project)}


def _aether_blocks(project):
    a = project.get("aether", {})
    meta = project["project"]
    copy = [a.get("purpose") or meta.get("description") or "This project has not written its purpose yet."]
    copy += a.get("story", [])
    blocks = [{"kind": "list", "items": a["authorship"]}] if a.get("authorship") else []
    if a.get("quote"):
        blocks.append({"kind": "quote", "text": a["quote"]})
    return [{"kind": "section", "kicker": "Pillar 04 · non-functional", "title": "Aether", "accent": "#ff5252",
             "copy": copy, "blocks": blocks}]


def _environment(project):
    return {"path": "/environment", "type": "module", "label": "Environment",
            "hero": {"title": "Environmental Intelligence", "tag_em": "PILLAR 01", "tag": "   —   BASELINES",
                     "description": "The real environment, learned per channel: [[magnetic]], [[electric]], [[ultrasonic]] "
                                    "or anything else that emits numbers. Learn it, lock it, save it, and compare against it."},
            "blocks": _environment_blocks(project)}


def _validation(project):
    return {"path": "/validation", "type": "module", "label": "Validation",
            "hero": {"title": "Validation Chamber", "tag_em": "PILLAR 00", "tag": "   —   EVIDENCE",
                     "description": "Before anything is interpreted, every channel proves it is present, fresh, on time and "
                                    "inside its range. Detection limits come from its own measured noise: [[LOD = 3σ]], "
                                    "[[LOQ = 10σ]]."},
            "blocks": _validation_blocks(project)}


def _settings(project):
    return {"path": "/settings", "type": "settings", "label": "Settings", "title": "Settings",
            "copy": "Interface preferences.",
            "rows": [{"title": "MTDI", "text": "Framework version of this studio.", "value": project.get("mtdi", "5.0")},
                     {"title": "Project", "text": "Loaded manifest.", "value": project["project"]["id"]}]}
