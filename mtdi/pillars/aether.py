"""Pillar 04 · Aether — purpose, persistence and authorship.

Aether is a non-functional designation: it never enters the signal path and no
score depends on it. It holds why a project exists, who built it and what it
went through, taken from the "aether" block of project.json, so that every
project integrated into MTDI carries its reason with it.
"""


def record(project):
    meta = project["project"]
    aether = project.get("aether", {})
    return {
        "name": meta.get("name"),
        "author": meta.get("author"),
        "purpose": aether.get("purpose") or meta.get("description", ""),
        "story": aether.get("story", []),
        "authorship": aether.get("authorship", []),
        "milestones": aether.get("milestones", []),
        "quote": aether.get("quote"),
        "functional": False,
    }
