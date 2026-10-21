"""Run one MTDI project: engine, adapters, recorder, NVTRA and the machine API.

    from mtdi.runtime import Runner
    runner = Runner("projects/host-health")          # starts its adapters
    packet = runner.engine.snapshot()
    runner.ask("is anything unusual?")
    runner.stop()

Embedding without adapters (your program supplies the values):

    runner = Runner("projects/my-project", start=False)
    runner.engine.ingest_values("my-source", {"TEMP_C": 21.4})

The same runner serves a JSON API on its own (``headless_app``) or adds its routes to
the studio's server (``register``), so the interface and the API share one engine.
"""
import pathlib

from .adapters import build
from .adapters.replay import Recorder
from .engine import Engine
from .pillars import nvtra
from .project import load


class Runner:
    def __init__(self, project, simulate=False, record=None, ask=None, start=True):
        self.project = load(project) if isinstance(project, (str, pathlib.Path)) else project
        self.simulate_all = simulate
        self.simulate = simulate or any(s["adapter"] == "simulator" for s in self.project["sources"])
        # Load exactly the Intelligence Profile's modules (ADR 0006). The host check is
        # reported by `mtdi check`, not enforced here, so a laptop can still run a big profile.
        from .profiles import activate
        self.modules = activate(self.project["profile"])
        self.engine = Engine(self.project)
        if record:
            self.engine.recorders.append(Recorder(record))
        self.adapters = [build(self.engine, s, simulate) for s in self.project["sources"]]
        self._ask = ask
        if start:
            for adapter in self.adapters:
                adapter.start()

    # ── NVTRA ────────────────────────────────────────────────────────────────
    def ask(self, question):
        """Answer from the live packet. A custom handler, then a language model when a key
        is configured, then the built-in rule engine, which always works offline."""
        packet = self.engine.snapshot()
        if self._ask:
            return self._ask(question, packet)
        if "mtdi.bot" not in self.modules:  # e.g. the edge profile: stay inside what it loaded
            return nvtra.answer(question, packet)
        from .bot import Bot
        return Bot(self).reply(question)["text"]

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

    # ── machine API ──────────────────────────────────────────────────────────
    def register(self, server, prefix="/mtdi"):
        """Add /mtdi/packet, /mtdi/ingest, /mtdi/action and /mtdi/ask to a Flask server."""
        from flask import jsonify, request
        http_sources = {s["id"]: s for s in self.project["sources"] if s["adapter"] == "http"}

        @server.get(prefix + "/packet", endpoint="mtdi_packet")
        def _packet():
            return jsonify(self.engine.snapshot())

        @server.post(prefix + "/ingest", endpoint="mtdi_ingest")
        def _ingest():
            """{"source": id, "line": "..."} | {"source": id, "lines": [...]} | {"source": id, "values": {...}}.
            Only sources declared with adapter "http" accept posts."""
            body = request.get_json(silent=True) or {}
            sid = body.get("source")
            if sid not in http_sources:
                return jsonify({"ok": False, "message": "source is not an http source in this project"}), 400
            if self.simulate_all:
                return jsonify({"ok": False, "message": "running --simulate; restart without it to ingest"}), 409
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

        @server.post(prefix + "/action", endpoint="mtdi_action")
        def _action():
            body = request.get_json(silent=True) or {}
            try:
                return jsonify({"ok": True, "message": self.action(str(body.get("action", "")), body.get("args") or {})})
            except (ValueError, KeyError, OSError) as error:
                return jsonify({"ok": False, "message": str(error)}), 400

        @server.post(prefix + "/ask", endpoint="mtdi_ask")
        def _ask():
            body = request.get_json(silent=True) or {}
            return jsonify({"answer": self.ask(str(body.get("question", ""))[:2000])})

        return server

    def headless_app(self):
        from flask import Flask, jsonify
        server = Flask("mtdi")

        @server.get("/")
        def _index():
            meta = self.project["project"]
            return jsonify({"mtdi": self.project.get("mtdi"), "project": meta.get("name"), "headless": True,
                            "endpoints": ["/mtdi/packet", "/mtdi/ingest", "/mtdi/action", "/mtdi/ask"]})
        return self.register(server)

    def stop(self):
        for adapter in self.adapters:
            adapter.stop()


def answer_offline(question, packet):
    """The rule-based answer NVTRA gives with no model configured."""
    return nvtra.answer(question, packet)
