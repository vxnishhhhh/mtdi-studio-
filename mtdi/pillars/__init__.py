"""The five MTDI pillars.

    00  validation   Validation Chamber          Evidence   is each channel present, fresh, on time, in range
    01  environment  Environmental Intelligence  Baselines  learn, lock and compare the real environment
    02  nvtra        NVTRA                       Health     explain what the pillars found, in plain language
    03  i3           I³                          Meaning    the interface everything is seen through
    04  aether       Aether                      Reason     purpose and authorship (non-functional)

The MTDI core (mtdi/core.py) fuses 00 and 01 into one score; 02 and 03 present
it; 04 carries why the project exists.
"""
PILLARS = [
    {"id": "validation", "num": "00", "title": "Validation Chamber", "role": "Evidence",
     "desc": "Presence, freshness, timing, range and detection limits for every channel.", "accent": "#2979ff"},
    {"id": "environment", "num": "01", "title": "Environmental Intelligence", "role": "Baselines",
     "desc": "Learn, lock and compare the real environment each channel sits in.", "accent": "#00e676"},
    {"id": "nvtra", "num": "02", "title": "NVTRA", "role": "Health",
     "desc": "The intelligence that explains what the pillars found.", "accent": "#ffd166"},
    {"id": "i3", "num": "03", "title": "I³", "role": "Meaning",
     "desc": "Induction, interference and intelligence made visible.", "accent": "#b388ff"},
    {"id": "aether", "num": "04", "title": "Aether", "role": "Reason",
     "desc": "Purpose, persistence and authorship behind the build.", "accent": "#ff5252"},
]
