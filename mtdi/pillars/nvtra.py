"""Pillar 02 · NVTRA — the intelligence that explains what the other pillars found.

NVTRA turns the MTDI packet into plain language. It never sees hardware: it reads
only the packet, so it works for any project. Two layers:

1. Interpretation rules. Universal rules cover what every project shares
   (offline, settling, ambient, one channel dominant, several channels active).
   A project adds its own domain rules in project.json, for example
   "channel a SNR >= 6 and channel b SNR < 3 means a local source near a":

       {"when": {"a": ">=6", "b": "<3"},
        "condition": "Channel a dominant", "text": "..."}

   Each key in "when" is a channel id compared on its signal-to-noise ratio
   (the channel must be live for the rule to match), or "active_at_least": N.

2. Answers. answer() gives a grounded, rule-based reply from the packet. A
   language model can replace it (Studio(ask=...)), but whatever answers must be
   given the packet, never asked to guess.
"""
import operator
import re

OPS = {">=": operator.ge, ">": operator.gt, "<=": operator.le, "<": operator.lt, "==": operator.eq}
_TEST = re.compile(r"^\s*(>=|<=|==|>|<)\s*(-?\d+(\.\d+)?)\s*$")


def _matches(rule, snrs, live):
    for key, test in rule["when"].items():
        if key == "active_at_least":
            if sum(1 for c in live if snrs[c] >= 3) < int(test):
                return False
            continue
        m = _TEST.match(str(test))
        if not m or key not in live:
            return False
        if not OPS[m.group(1)](snrs[key], float(m.group(2))):
            return False
    return True


def interpret(project, channels):
    """channels: {id: {"label", "evidence", "environment", "unit"}} -> interpretation dict."""
    live = [cid for cid, c in channels.items() if c["evidence"]["state"] == "connected"]
    snrs = {cid: (c["environment"].get("snr") or 0.0) if cid in live else 0.0 for cid, c in channels.items()}
    evidence = [f"{channels[c]['label']}: deviation {channels[c]['environment'].get('deviation', 0):.3g} "
                f"{channels[c]['unit']}, signal to ambient noise {snrs[c]:.1f}, "
                f"{channels[c]['environment'].get('transient', {}).get('state', '—')}" for c in live]
    rule_id = None
    if not live:
        condition = "Sensors offline"
        text = "No live measurement is available. Connect the configured sources to begin."
    elif any(channels[c]["environment"].get("settling", True) for c in live):
        condition = "Baseline settling"
        text = "The ambient reference is still forming. Wait for the baseline before interpreting deviations."
    else:
        chosen = next((r for r in project["nvtra"]["rules"] if _matches(r, snrs, live)), None)
        if chosen:
            condition, text, rule_id = chosen["condition"], chosen.get("text", ""), chosen.get("id", chosen["condition"])
        else:
            strong = [c for c in live if snrs[c] >= 6]
            active = [c for c in live if snrs[c] >= 3]
            if len(active) >= 2:
                condition = "Mixed activity"
                text = ("Several channels changed relative to their ambient baselines. A common source is possible "
                        "when the event timing agrees.")
            elif len(strong) == 1:
                label = channels[strong[0]]["label"]
                condition = f"{label} dominant"
                text = f"{label} changed clearly while the other live channels stayed near their ambient level."
            elif not active:
                condition = "Ambient conditions"
                text = "Available channels show no clear change beyond their measured ambient variation."
            else:
                condition = "Channel activity detected"
                text = "At least one channel changed. More live channels are needed to say more."
    warnings = []
    for cid, c in channels.items():
        ev, env = c["evidence"], c["environment"]
        if ev["state"] != "connected" and not c.get("optional"):
            warnings.append(f"{c['label']}: {ev['state']}")
        if ev["clipped"]:
            warnings.append(f"{c['label']}: clipping, the value is a lower bound")
        if env.get("stale"):
            warnings.append(f"{c['label']}: baseline stale by {env['stale_offset']:.3g} {c['unit']}; re-learn or wait")
    simulated = any(channels[c]["evidence"]["data_source"] == "SIMULATED" for c in live)
    if simulated:
        condition = "SIMULATED · " + condition
        text = "SIMULATED DATA. " + text
    return {"condition": condition, "interpretation": text, "evidence": evidence,
            "warnings": warnings, "rule": rule_id, "simulated": simulated}


def answer(question, packet):
    """A grounded reply built only from the packet. No guessing, no invented values."""
    q = (question or "").lower()
    fusion = packet["fusion"]
    chans = packet["channels"]
    lines = []
    if any(w in q for w in ("score", "mtdi", "trust", "confidence")):
        lines.append(f"MTDI is {fusion['score']:.1f} % with {fusion['completeness']:.0f} % of channels live. "
                     "It is an evidence-quality score, not a probability.")
        worst = sorted(((c["score"], cid) for cid, c in chans.items()))[:1]
        if worst:
            s, cid = worst[0]
            lines.append(f"The weakest channel is {chans[cid]['label']} at {s:.1f} %.")
    for cid, c in chans.items():
        if c["label"].lower() in q or cid.lower() in q:
            ev, env = c["evidence"], c["environment"]
            lines.append(f"{c['label']} is {ev['state']}, deviation {env.get('deviation', 0):.3g} {c['unit']}, "
                         f"SNR {env.get('snr', 0):.1f}, {env.get('transient', {}).get('state', '—')}.")
    if not lines:
        lines.append(f"{fusion['condition']}. {fusion['interpretation']}")
    if fusion["warnings"]:
        lines.append("Warnings: " + "; ".join(fusion["warnings"][:3]) + ".")
    return " ".join(lines)
