"""MTDI Studio: one project, every pillar, one running interface.

    from mtdi.studio import Studio
    studio = Studio("projects/inductra-vaion")
    studio.run(port=8050)

Embedding in another program instead of using adapters:

    studio = Studio("projects/my-project", start_adapters=False)
    studio.engine.ingest_values("my-source", {"DIST_CM": 41.7})
    packet = studio.engine.snapshot()
"""
import pathlib

from flask import jsonify, request

from ..adapters import build
from ..adapters.replay import Recorder
from ..engine import Engine
from ..pillars import nvtra
from ..pillars.i3 import create_app
from ..project import load
from . import views


class Studio:
    def __init__(self, project, simulate=False, record=None, ask=None, start_adapters=True):
        self.project = load(project) if isinstance(project, (str, pathlib.Path)) else project
        self.simulate_all = simulate
        self.simulate = simulate or any(s["adapter"] == "simulator" for s in self.project["sources"])
        self.engine = Engine(self.project)
        if record:
            self.engine.recorders.append(Recorder(record))
        self.adapters = [build(self.engine, s, simulate) for s in self.project["sources"]]
        self._ask = ask
        self.app = create_app(views.content_pack(self.project, self.simulate),
                              state_provider=self.state, ask_handler=self.ask,
                              action_handler=self.action, state_poll_ms=1000)
        self._routes(self.app.server)
        if start_adapters:
            for adapter in self.adapters:
                adapter.start()

    # ── I³ hooks ─────────────────────────────────────────────────────────────
    def state(self):
        return views.flatten(self.engine.snapshot())

    def ask(self, question, path):
        packet = self.engine.snapshot()
        if self._ask:
            return self._ask(question, packet)
        return nvtra.answer(question, packet)

    def action(self, action, args):
        engine, channel = self.engine, args.get("channel")
        if action == "learn":
            engine.learn(channel)
            return "Re-learning the baseline from the current environment."
        if action == "lock":
            engine.lock_baseline(channel, True)
            return "Baseline locked. Every change is now measured against it."
        if action == "unlock":
            engine.lock_baseline(channel, False)
            return "Baseline unlocked; it follows the quiet level again."
        if action == "save":
            engine.save_environment(args.get("name", ""))
            return f"Saved environment '{args.get('name')}'."
        if action == "compare":
            name = args.get("name", "")
            if name not in engine.environments.names():
                raise ValueError(f"no saved environment called '{name}'")
            engine.load_environment(name)
            return f"Comparing live readings against '{name}'."
        raise ValueError(f"unknown action '{action}'")

    # ── machine endpoints ────────────────────────────────────────────────────
    def _routes(self, server):
        http_sources = {s["id"]: s for s in self.project["sources"] if s["adapter"] == "http"}

        @server.get("/mtdi/packet")
        def _packet():
            return jsonify(self.engine.snapshot())

        @server.post("/mtdi/ingest")
        def _ingest():
            """Body: {"source": id, "line": "..."} or {"source": id, "lines": [...]} or {"source": id, "values": {...}}.
            Only sources declared with adapter "http" accept posts."""
            body = request.get_json(silent=True) or {}
            sid = body.get("source")
            if sid not in http_sources:
                return jsonify({"ok": False, "message": "source is not an http source in this project"}), 400
            if self.simulate_all:
                # Mixing real posts into a simulated run would blur the data-source label.
                return jsonify({"ok": False, "message": "studio is running --simulate; restart without it to ingest"}), 409
            label = http_sources[sid].get("data_source", "HARDWARE")
            updated = 0
            for line in ([body["line"]] if "line" in body else body.get("lines", [])):
                updated += self.engine.ingest_line(sid, str(line), label)
            if isinstance(body.get("values"), dict):
                try:
                    updated += self.engine.ingest_values(sid, {k: float(v) for k, v in body["values"].items()}, label)
                except (TypeError, ValueError):
                    return jsonify({"ok": False, "message": "values must be numbers"}), 400
            return jsonify({"ok": True, "channels_updated": updated})

    def run(self, host="127.0.0.1", port=8050, debug=False):
        self.app.run(host=host, port=port, debug=debug, use_reloader=False)

    def stop(self):
        for adapter in self.adapters:
            adapter.stop()
