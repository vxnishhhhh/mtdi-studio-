"""tools/pi/measure.py: the engine and render paths run (the subprocess import timing is left to the real run)."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools" / "pi"))
import measure  # noqa: E402


class Measure(unittest.TestCase):
    def test_engine_and_render(self):
        e = measure.engine_throughput(4, 50)
        self.assertEqual(e["channels"], 4)
        self.assertGreater(e["packets_per_s"], 0)
        report = measure.render({"date": "2026-10-21", "machine": measure.machine(),
                                 "profiles": {"edge": {"import_s": 0.1, "peak_mb": 20}, "x": {"error": "boom"}},
                                 "engine": [e], "llm": {"model": "m", "measured": False, "why": "no server"}})
        self.assertIn("| edge | 0.10 | 20 |", report)
        self.assertIn("error: boom", report)
        self.assertIn("not measured (no server)", report)
