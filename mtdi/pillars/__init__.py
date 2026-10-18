"""The five MTDI pillars and the Aether layer (ADR 0001).

    00  validation     Validation Chamber          Evidence     is each channel present, fresh, on time, in range
    01  environment    Environmental Intelligence  Baselines    learn, lock and compare the real environment
    02  computational  Computational Core          Computation  ML, mathematics, simulation, agents, integrations
    03  nvtra          NVTRA                       Explanation  explain what the pillars found, in plain language
    04  i3             I³                          Interface    the interface everything is seen through

    ··  aether         Aether                      Soul         the layer across every pillar: terminal, Easter
                                                                eggs, purpose and authorship; shown, never scored

The MTDI core (mtdi/core.py) fuses 00 and 01 into one score; 02 computes on it; 03 and
04 present it; Aether carries why the project exists.
"""
PILLARS = [
    {"id": "validation", "num": "00", "title": "Validation Chamber", "role": "Evidence",
     "desc": "Presence, freshness, timing, range and detection limits for every channel.", "accent": "#2979ff"},
    {"id": "environment", "num": "01", "title": "Environmental Intelligence", "role": "Baselines",
     "desc": "Learn, lock and compare the real environment each channel sits in.", "accent": "#00e676"},
    {"id": "computational", "num": "02", "title": "Computational Core", "role": "Computation",
     "desc": "Machine learning, mathematics, simulation, agents and every integration.", "accent": "#00e5ff"},
    {"id": "nvtra", "num": "03", "title": "NVTRA", "role": "Explanation",
     "desc": "The intelligence that explains what the pillars found.", "accent": "#ffd166"},
    {"id": "i3", "num": "04", "title": "I³", "role": "Interface",
     "desc": "Induction, interference and intelligence made visible.", "accent": "#b388ff"},
]

AETHER = {"id": "aether", "num": "··", "title": "Aether", "role": "Soul",
          "desc": "The layer across every pillar: the terminal, the Easter eggs, purpose and authorship. "
                  "Shown, never scored.", "accent": "#ff5252"}

# The Computational Core's modules, by area. Each entry names the Python module that
# implements it; the registry (mtdi.registry) checks every one imports.
COMPUTATIONAL_MODULES = {
    "machine learning": ["mtdi.ml.anomaly", "mtdi.ml.classify", "mtdi.ml.cluster", "mtdi.ml.forecast",
                         "mtdi.ml.features", "mtdi.ml.monitor"],
    "language models": ["mtdi.llm"],
    "voice": ["mtdi.voice"],
    "intelligence": ["mtdi.bot"],
    "storage": ["mtdi.storage"],
    "integrations": ["mtdi.integrations.github", "mtdi.integrations.vercel", "mtdi.integrations.notion",
                     "mtdi.integrations.matlab"],
}
