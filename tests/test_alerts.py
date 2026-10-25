"""S1-17: alert_change raises one event per crossing, in the direction asked."""
import pathlib
import random
import unittest

from mtdi.engine import Engine
from mtdi.project import ManifestError, load, normalise

ROOT = pathlib.Path(__file__).resolve().parent.parent


def project(**channel):
    spec = {"id": "level", "label": "Tank level", "keys": ["L"], "unit": "cm", "noise_floor": 0.1,
            "alert_change": 2.0, **channel}
    return normalise({"project": {"id": "a"}, "sources": [{"id": "s", "adapter": "http"}], "channels": [spec]})


class Alerts(unittest.TestCase):
    def setUp(self):
        self.clock = [0.0]
        self.rng = random.Random(3)

    def engine(self, **channel):
        engine = Engine(project(**channel), clock=lambda: self.clock[0])
        self.feed(engine, 12, 10.0)                       # learn the baseline
        return engine

    def feed(self, engine, seconds, value, data_source="HARDWARE"):
        for _ in range(int(seconds * 10)):
            self.clock[0] += 0.1
            engine.ingest_values("s", {"L": value + self.rng.gauss(0, 0.02)}, data_source)

    def alerts(self, engine):
        return [e["message"] for e in engine.snapshot()["events"] if e["kind"] == "alert"]

    def test_one_event_per_crossing_and_it_re_arms_below_half(self):
        engine = self.engine()
        self.assertEqual(self.alerts(engine), [])
        self.feed(engine, 1, 13.0)                        # +3 cm: past 2 cm
        self.assertEqual(len(self.alerts(engine)), 1)
        self.assertTrue(engine.snapshot()["channels"]["level"]["alert"])
        self.feed(engine, 1, 13.0)                        # still past it: no repeat
        self.feed(engine, 1, 11.5)                        # +1.5: under 2, not yet under half
        self.feed(engine, 1, 13.0)
        self.assertEqual(len(self.alerts(engine)), 1)
        self.feed(engine, 1, 10.5)                        # +0.5: under half, re-armed
        self.assertFalse(engine.snapshot()["channels"]["level"]["alert"])
        self.feed(engine, 1, 13.0)
        self.assertEqual(len(self.alerts(engine)), 2)
        self.assertRegex(self.alerts(engine)[0], r"^Tank level: (2\.9\d*|3(\.0\d*)?) cm above its baseline \(alerts at 2 cm\)$")

    def test_direction_down_ignores_a_rise(self):
        engine = self.engine(alert_direction="down")
        self.feed(engine, 1, 14.0)
        self.assertEqual(self.alerts(engine), [])
        self.feed(engine, 1, 10.0)
        self.feed(engine, 1, 7.0)
        self.assertEqual(len(self.alerts(engine)), 1)
        self.assertRegex(self.alerts(engine)[0], r": (2\.9\d*|3(\.0\d*)?) cm below its baseline")

    def test_a_new_baseline_clears_the_alert_and_the_next_crossing_is_reported(self):
        engine = self.engine()
        self.feed(engine, 1, 13.0)
        self.assertTrue(engine.snapshot()["channels"]["level"]["alert"])
        engine.learn("level")                             # 13 is the new normal
        self.assertFalse(engine.snapshot()["channels"]["level"]["alert"])
        self.feed(engine, 12, 13.0)                       # settles on the new level
        self.feed(engine, 1, 16.0)                        # +3 against the new baseline
        self.assertEqual(len(self.alerts(engine)), 2)

    def test_nothing_alerts_while_the_baseline_is_still_settling(self):
        engine = Engine(project(), clock=lambda: self.clock[0])
        self.feed(engine, 1, 10.0)
        self.feed(engine, 1, 20.0)
        self.assertEqual(self.alerts(engine), [])

    def test_a_simulated_alert_says_so(self):
        engine = Engine(project(), clock=lambda: self.clock[0])
        self.feed(engine, 12, 10.0, "SIMULATED")
        self.feed(engine, 1, 13.0, "SIMULATED")
        self.assertTrue(self.alerts(engine)[0].endswith("(SIMULATED)"))

    def test_bad_settings_name_the_problem(self):
        vector = {"keys": ["X", "Y"], "kind": "vector"}
        for channel, needle in (({"alert_change": 0}, "alert_change must be a finite number > 0"),
                                ({"alert_change": "big"}, "alert_change must be a finite number > 0"),
                                ({"alert_change": float("inf")}, "alert_change must be a finite number > 0"),
                                ({"alert_change": float("nan")}, "alert_change must be a finite number > 0"),
                                ({"alert_direction": "sideways"}, "alert_direction must be"),
                                (dict(vector, alert_direction="down"), "only a scalar channel has a sign")):
            with self.assertRaisesRegex(ManifestError, needle):
                project(**channel)

    def test_third_eye_alerts_when_something_comes_closer_not_when_it_moves_away(self):
        third_eye = load(ROOT / "projects" / "third-eye")
        engine = Engine(third_eye, clock=lambda: self.clock[0])

        def feed(seconds, left):
            for i in range(int(seconds * 13)):
                self.clock[0] += 1 / 13
                engine.ingest_line("eye", f"LEFT_CM={left + self.rng.gauss(0, 0.2):.1f},RIGHT_CM=150.0,BUZZ=0,_SEQ={i}")
        feed(30, 150)
        feed(2, 260)                                      # the left side opens up
        self.assertEqual(self.alerts(engine), [])
        feed(2, 150)
        feed(2, 40)                                       # something comes in on the left
        self.assertEqual(len(self.alerts(engine)), 1)
        self.assertIn("Left distance", self.alerts(engine)[0])


if __name__ == "__main__":
    unittest.main()
