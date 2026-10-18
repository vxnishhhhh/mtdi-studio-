"""Aggregate of the split application modules, in load order.

Importing this module loads every section (common, sensors, intelligence, system,
tokens, theme, browser, webapp, reports, charts, pages, routing) and unifies their
namespaces, so ``vars(app)`` behaves like the original single file.
"""
from ._shared import ORDER, unify
from . import common, sensors, intelligence, system, tokens, theme, browser, webapp, reports, charts, pages, routing  # noqa: F401

globals().update(unify())
