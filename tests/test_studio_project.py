"""The studio project panel reads the MTDI packet directly (S1-11 data path)."""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
class StudioProjectPanel(unittest.TestCase):
    """The studio's project panel renders the engine packet directly (S1-11 data path)."""

    def packet(self):
        from mtdi.engine import Engine
        from mtdi.project import normalise
        m = normalise({"project": {"id": "p"}, "sources": [{"id": "s", "adapter": "http"}],
                       "channels": [{"id": "a", "label": "Gas A", "keys": ["A"], "unit": "ppm", "noise_floor": 0.1,
                                     "calibration": {"gain": 2.0, "offset": 1.0, "residual_sd": 0.3, "method": "linear"}},
                                    {"id": "b", "label": "Gas B", "keys": ["B"], "unit": "ppm", "noise_floor": 0.1}],
                       "fused": [{"id": "co", "label": "CO", "inputs": ["a", "b"], "sd": {"b": 1.0}}]})
        engine = Engine(m, clock=lambda: 0.0)
        engine.ingest_values("s", {"A": 5.0, "B": 12.0})
        return engine.snapshot()

    def text(self, component):
        out = []
        def walk(c):
            if isinstance(c, str):
                out.append(c)
            elif isinstance(c, (list, tuple)):
                for x in c:
                    walk(x)
            elif hasattr(c, "children"):
                walk(c.children)
        walk(component)
        return " | ".join(out)

    def test_channels_calibration_and_fused_estimate_are_shown(self):

        sys.path.insert(0, str(ROOT))
        from run import NAMESPACE
        text = self.text(NAMESPACE["project_channels_view"](self.packet()))
        self.assertIn("Gas A", text)
        self.assertIn("11 ppm", text)                      # 2 * 5 + 1, the calibrated value
        self.assertIn("calibrated linear · ±0.3", text)
        self.assertIn("FUSED · CO", text)
        self.assertIn("2/2 inputs live", text)
        self.assertIn("a (calibration), b (manifest)", text)

    def test_no_project_is_an_honest_empty_state(self):

        sys.path.insert(0, str(ROOT))
        from run import NAMESPACE
        self.assertIn("No MTDI project is running", self.text(NAMESPACE["project_channels_view"](None)))

    def test_the_live_callback_reads_a_registered_project(self):
        import json
        import tempfile
        sys.path.insert(0, str(ROOT))
        from run import NAMESPACE
        from mtdi.runtime import Runner
        server = NAMESPACE["app"].server
        saved = server.config.pop("MTDI_RUNNER", None)
        with tempfile.TemporaryDirectory() as d:
            pathlib.Path(d, "project.json").write_text(json.dumps({
                "project": {"id": "live", "name": "Live"}, "sources": [{"id": "s", "adapter": "http"}],
                "channels": [{"id": "t", "label": "Temp", "keys": ["T"], "unit": "C", "noise_floor": 0.1}]}))
            runner = Runner(d)
            try:
                self.assertIn("No MTDI project", self.text(NAMESPACE["update_project_channels"](0)))
                server.config["MTDI_RUNNER"] = runner
                runner.engine.ingest_values("s", {"T": 21.5})
                self.assertIn("21.5 C", self.text(NAMESPACE["update_project_channels"](1)))
            finally:
                runner.stop()
                server.config.pop("MTDI_RUNNER", None)
                if saved is not None:
                    server.config["MTDI_RUNNER"] = saved


if __name__ == "__main__":
    unittest.main()
