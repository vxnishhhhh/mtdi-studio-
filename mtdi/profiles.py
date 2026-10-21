"""Intelligence Profiles (S1-04, ADR 0006).

A project declares `"profile"` in its manifest (default `hybrid`). The profile decides which
framework modules load and the smallest machine that may host it, so a sensor project on a
Pi stays small and a research project gets its ML and data stack. Profiles only ever ADD
modules on top of the core every project needs; they never fork the framework.

    edge        sensors, actuators, light firmware
    scientific  maths, MATLAB, experiments, recordings
    vision      computer vision and relational reasoning (features, classifiers)
    autonomous  agents and language models
    hybrid      hardware + firmware + cloud + AI together (the default)
    research    datasets, ML experiments, reproducibility

Vision has no camera pipeline in mtdi/ yet (hand vision lives in the browser); the profile
loads what exists today and grows as modules land. Being honest beats being impressive.
(Aether: "grows as modules land" is engineer for "TODO, but with dignity".)
"""
import importlib

from .capabilities import PROFILE_MIN_MB, select_runtime

CORE = ["mtdi.protocol", "mtdi.project", "mtdi.engine", "mtdi.adapters", "mtdi.core",
        "mtdi.pillars.validation", "mtdi.pillars.environment", "mtdi.pillars.nvtra", "mtdi.pillars.aether"]
ML = ["mtdi.ml.anomaly", "mtdi.ml.features", "mtdi.ml.monitor", "mtdi.ml.forecast",
      "mtdi.ml.classify", "mtdi.ml.cluster"]

PROFILES = {
    "edge": {"for": "sensors, actuators, lightweight firmware",
             "modules": CORE + ["mtdi.ml.anomaly"]},
    "scientific": {"for": "MATLAB, experiments, numerical analysis",
                   "modules": CORE + ML + ["mtdi.analysis", "mtdi.adapters.replay", "mtdi.integrations.matlab"]},
    "vision": {"for": "computer vision, relational reasoning",
               "modules": CORE + ["mtdi.ml.features", "mtdi.ml.classify", "mtdi.ml.cluster"]},
    "autonomous": {"for": "engineering agents, project creation",
                   "modules": CORE + ["mtdi.llm", "mtdi.bot", "mtdi.voice", "mtdi.create"]},
    "hybrid": {"for": "hardware + firmware + cloud + AI together",
               "modules": CORE + ML + ["mtdi.analysis", "mtdi.llm", "mtdi.bot", "mtdi.bridge", "mtdi.storage"]},
    "research": {"for": "datasets, ML experiments, reproducibility",
                 "modules": CORE + ML + ["mtdi.analysis", "mtdi.adapters.replay", "mtdi.storage", "mtdi.capabilities", "mtdi.registry"]},
}
DEFAULT = "hybrid"


class ProfileError(RuntimeError):
    pass


def get(name):
    if name not in PROFILES:
        raise ProfileError(f"unknown profile {name!r}; one of {', '.join(PROFILES)}")
    return PROFILES[name]


def qualifies(name, target):
    """(ok, runtime, reason): can `target` host this profile's Python runtime itself?"""
    get(name)
    runtime, why = select_runtime(target, name)
    return runtime == "full", runtime, why


def activate(name, target=None):
    """Import exactly the profile's modules; refuse an under-capable host. Returns {module: module}."""
    profile = get(name)
    if target is not None:
        ok, runtime, why = qualifies(name, target)
        if not ok:
            raise ProfileError(f"{target.get('name', target['id'])} cannot host the {name} profile "
                               f"({PROFILE_MIN_MB[name]} MB estimate): {why}. Use runtime '{runtime}'.")
    return {m: importlib.import_module(m) for m in profile["modules"]}
