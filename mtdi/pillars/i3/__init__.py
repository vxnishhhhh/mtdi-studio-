"""Pillar 03 · I³ — the interface framework extracted from Inductra Vaion.

Induction · Interference · Intelligence. I³ is everything you see: the startup
intro, the glass header, the scroll openings, the orbits, the pillars, the
document pages and the NVTRA dock. A product supplies a content pack; I³ supplies
the interface.

    from mtdi.pillars.i3 import create_app, load
    app = create_app(load("mtdi/pillars/i3/examples/placeholder.json"))
    app.run(port=8050)
"""
from .app import create_app
from .content import load, validate

__all__ = ["create_app", "load", "validate"]
__version__ = "0.1.0"
