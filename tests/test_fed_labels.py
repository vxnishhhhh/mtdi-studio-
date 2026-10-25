"""Data fed into the studio names its sender and says SIMULATED; it never wears the studio's own sensor labels."""
import ast
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

    def test_only_a_leading_simulated_marks_the_data_simulated(self):
        self.ns["feed_ch1"]([150.0], unit="cm", source="MTDI:SIMULATED-annealing-rig")
        shown = self.status("update_numbers")
        self.assertIn("SOURCE ONLINE · MTDI:SIMULATED-annealing-rig", shown)
        self.assertNotIn("SIMULATED DATA", shown)
        is_simulated = self.ns["_simulated_label"]
        self.assertEqual([is_simulated(x) for x in ("SIMULATED", "SIMULATED MTDI:x", "MTDI:SIMULATED", None)],
                         [True, True, False, False])

    def test_fed_channel_2_renders_without_crashing_and_names_the_sender(self):
        """update_ch2f_numbers raised UnboundLocalError for every non-Uno source with data (fixed here)."""
        for _ in range(3):
            self.ns["feed_ch2"](40.0, unit="%", source="SIMULATED MTDI:host-health")
        shown = self.status("update_ch2f_numbers")
        self.assertNotIn("0x48", shown)
        if "ONLINE" in shown or "SIMULATED DATA" in shown:     # past its settling phase
            self.assertIn("MTDI:host-health", shown)

    def test_a_feed_after_the_uno_drops_the_uno_status_and_axes(self):
        """The Uno writer leaves data_source and per-axis values behind; a fed reading must clear them."""
        self.ns["ch2f_data"].update(data_source="ARDUINO_UNO_USB", provisional_adc=True, triaxial=True,
                                    ex_vu=1.5, ey_vu=2.5, ez_vu=3.5, e_magnitude_vu=4.5, axes_live=3,
                                    axis_clipped={"x": True, "y": False, "z": False}, sample_rate=10.0)
        for _ in range(3):
            self.ns["feed_ch2"](40.0, unit="%", source="MTDI:host-health")
        e = self.ns["ch2f_data"]
        self.assertIsNone(e["data_source"])
        self.assertEqual((e["ex_vu"], e["e_magnitude_vu"], e["axes_live"], e["axis_clipped"]), (None, None, 0, {}))
        shown = self.status("update_ch2f_numbers")
        self.assertNotIn("UNO", shown)
        self.assertNotIn("1.500", shown)


class NativeWritersClearFedLabels(unittest.TestCase):
    """After a feed, the studio's own sensors must not keep showing the fed sender's name and unit."""

    def test_every_native_channel_1_and_2_update_clears_fed_source(self):
        tree = ast.parse((ROOT / "studio" / "acquisition.py").read_text(encoding="utf-8"))
        found = 0
        for node in ast.walk(tree):
            if not isinstance(node, ast.With):
                continue
            lock = ast.unparse(node.items[0].context_expr)
            if lock not in ("ns['c1_lock']", "ns['ch2f_lock']"):
                continue
            for call in ast.walk(node):
                if not (isinstance(call, ast.Call) and getattr(call.func, "attr", "") == "update"):
                    continue
                keys = {k.arg: ast.unparse(k.value) for k in call.keywords}
                if "last_rx" not in keys or keys.get("fed_source") == "str(source)":
                    continue                              # not a reading, or the feed itself
                found += 1
                self.assertEqual(keys.get("fed_source"), "None", f"line {call.lineno}: native reading keeps fed_source")
                if lock == "ns['c1_lock']":
                    self.assertEqual(keys.get("fed_unit"), "None", f"line {call.lineno}: native reading keeps fed_unit")
        self.assertEqual(found, 4, "two native channel 1 writers and two channel 2 writers (Uno, ADS1115)")


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
        self.assertEqual([s["source"] for s in sent["samples"]], ["MTDI:s"])

    def mixed(self):
        from mtdi.engine import Engine
        from mtdi.project import normalise
        engine = Engine(normalise({"project": {"id": "s"},
                                   "sources": [{"id": "hw", "adapter": "http"}, {"id": "sim", "adapter": "http"}],
                                   "channels": [{"id": "a", "keys": ["A"], "source": "hw", "noise_floor": 0.1},
                                                {"id": "b", "keys": ["B"], "source": "sim", "noise_floor": 0.1}]}))
        engine.ingest_values("hw", {"A": 1.0}, "HARDWARE")
        engine.ingest_values("sim", {"B": 2.0}, "SIMULATED")
        return engine

    def test_mixed_samples_go_over_http_with_a_label_each(self):
        """The ingest route applies a sample's label to every slot in it, so real and simulated slots
        travel as separate samples: one request, one label per sample."""
        from mtdi.bridge import StudioBridge
        engine = self.mixed()
        sent = []

        class Response:
            def read(self): return b'{"ok": true}'
            def __enter__(self): return self
            def __exit__(self, *a): return False

        def fake_open(request, timeout=None):
            sent.append(json.loads(request.data))
            return Response()
        bridge = StudioBridge(engine, "http://127.0.0.1:9")
        with mock.patch("urllib.request.urlopen", fake_open):
            self.assertEqual(bridge.push(bridge.collect()), 2)
        self.assertEqual(len(sent), 1)
        by_source = {s["source"]: set(s) - {"source", "unit"} for s in sent[0]["samples"]}
        self.assertEqual(by_source, {"MTDI:s": {"ch1"}, "SIMULATED MTDI:s": {"ch2"}})

    def test_a_failed_push_is_sent_again_on_the_next_tick(self):
        """collect() used to mark a sample seen before it was delivered, so a failed request lost it."""
        from mtdi.bridge import StudioBridge
        engine = self.mixed()
        sent = []

        class Response:
            def read(self): return b'{"ok": true}'
            def __enter__(self): return self
            def __exit__(self, *a): return False

        def down(request, timeout=None):
            raise OSError("studio restarting")

        def up(request, timeout=None):
            sent.append(json.loads(request.data))
            return Response()
        bridge = StudioBridge(engine, "http://127.0.0.1:9")
        with mock.patch("urllib.request.urlopen", down):
            self.assertEqual(bridge.tick(), 0)                 # tick() reports the failure, never raises
        with mock.patch("urllib.request.urlopen", up):
            bridge.tick()                                       # no new readings since: the same two go out
            bridge.tick()                                       # delivered once, never again
        self.assertEqual(len(sent), 1)
        self.assertEqual(sorted(k for s in sent[0]["samples"] for k in s if k.startswith("ch")), ["ch1", "ch2"])

    def test_a_failed_in_process_feed_is_retried_and_delivered_slots_are_not(self):
        from mtdi.bridge import StudioBridge
        engine = self.mixed()
        calls, broken = [], [True]

        def feed_ch2(v, **kw):
            if broken[0]:
                raise RuntimeError("channel 2 busy")
            calls.append("ch2")
        bridge = StudioBridge(engine, {"feed_ch1": lambda v, **kw: calls.append("ch1"), "feed_ch2": feed_ch2})
        bridge.tick()
        broken[0] = False
        bridge.tick()
        self.assertEqual(calls, ["ch1", "ch2"])                 # ch1 once, ch2 on the retry


if __name__ == "__main__":
    unittest.main()
