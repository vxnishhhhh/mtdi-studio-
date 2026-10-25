"""Data fed into the studio names its sender and says SIMULATED; it never wears the studio's own sensor labels."""
import copy
import json
import os
import pathlib
import sys
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("STUDIO_HTTPS_PORT", "0")


def text(component):
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


class StudioStatus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from run import NAMESPACE
        cls.ns = NAMESPACE

    def setUp(self):
        # feed_ch1/feed_ch2 write the studio's shared channel state; put it back afterwards.
        saved = {k: copy.deepcopy(dict(self.ns[k])) for k in ("ch1_data", "ch2f_data")}

        def restore():
            for k, v in saved.items():
                self.ns[k].clear()
                self.ns[k].update(v)
        self.addCleanup(restore)

    def status(self, callback):
        return text(list(self.ns[callback](0, None)))

    def test_fed_channel_1_names_the_sender_and_its_unit(self):
        self.ns["feed_ch1"]([150.0], unit="cm", source="MTDI:third-eye")
        shown = self.status("update_numbers")
        self.assertIn("SOURCE ONLINE · MTDI:third-eye", shown)
        self.assertNotIn("0x2C", shown)
        self.assertIn(" cm", shown)

    def test_simulated_channel_1_says_so(self):
        self.ns["feed_ch1"]([150.0], unit="cm", source="SIMULATED MTDI:third-eye")
        self.assertIn("SIMULATED DATA · SIMULATED MTDI:third-eye", self.status("update_numbers"))

    def test_fed_channel_2_renders_without_crashing_and_names_the_sender(self):
        """update_ch2f_numbers raised UnboundLocalError for every non-Uno source with data (fixed here)."""
        for _ in range(3):
            self.ns["feed_ch2"](40.0, unit="%", source="SIMULATED MTDI:host-health")
        shown = self.status("update_ch2f_numbers")
        self.assertNotIn("0x48", shown)
        if "ONLINE" in shown or "SIMULATED DATA" in shown:     # past its settling phase
            self.assertIn("MTDI:host-health", shown)


class BridgeMarksSimulated(unittest.TestCase):
    def engine(self):
        from mtdi.engine import Engine
        from mtdi.project import normalise
        return Engine(normalise({"project": {"id": "s"}, "sources": [{"id": "s", "adapter": "http"}],
                                 "channels": [{"id": "a", "keys": ["A"], "unit": "cm", "noise_floor": 0.1}]}))

    def test_simulated_samples_carry_simulated_in_their_source(self):
        from mtdi.bridge import StudioBridge
        engine = self.engine()
        engine.ingest_values("s", {"A": 1.0}, "SIMULATED")
        calls = []
        bridge = StudioBridge(engine, {"feed_ch1": lambda v, **kw: calls.append(kw)})
        bridge.push(bridge.collect())
        self.assertEqual(calls[0]["source"], "SIMULATED MTDI:s")

    def test_real_samples_keep_the_plain_source_over_http(self):
        from mtdi.bridge import StudioBridge
        engine = self.engine()
        engine.ingest_values("s", {"A": 1.0}, "HARDWARE")
        sent = {}

        class Response:
            def read(self): return b'{"ok": true}'
            def __enter__(self): return self
            def __exit__(self, *a): return False

        def fake_open(request, timeout=None):
            sent.update(json.loads(request.data))
            return Response()
        bridge = StudioBridge(engine, "http://127.0.0.1:9")
        with mock.patch("urllib.request.urlopen", fake_open):
            bridge.push(bridge.collect())
        self.assertEqual(sent["source"], "MTDI:s")


if __name__ == "__main__":
    unittest.main()
