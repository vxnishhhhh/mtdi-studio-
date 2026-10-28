"""Calibration units (S1-06 slice 12): a project feed calibrates in its own unit; the studio's own
sources keep their physical units; anything else is refused."""
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from studio.analysis import AnalysisEngine  # noqa: E402


def feed(engine, channel, unit, fed, start=0, value=10.0):
    for t in range(start, start + 5):
        engine.ingest(channel, value, timestamp=t, unit=unit, vector=[value, 0, 0] if channel == "ch1" else None,
                      metadata={"monotonic": t, "fed": fed})
    return engine


def engine_fed(channel, unit, fed=False):
    return feed(AnalysisEngine(pathlib.Path(tempfile.mkdtemp()) / "calibration.json"), channel, unit, fed)


class CalibrationUnits(unittest.TestCase):
    def test_a_project_feed_keeps_its_own_unit(self):
        self.assertEqual(engine_fed("ch1", "cm", fed=True).calibrate("ch1", [1, 2], [2, 4], 0.1)["unit"], "cm")

    def test_the_studio_magnetometer_calibrates_in_microtesla(self):
        self.assertEqual(engine_fed("ch1", "µT").calibrate("ch1", [1, 2], [2, 4], 0.1)["unit"], "µT")

    def test_the_studio_probe_still_calibrates_to_volts_per_metre(self):
        self.assertEqual(engine_fed("ch2", "mV RMS relative").calibrate("ch2", [1, 2], [2, 4], 0.1)["unit"], "V/m")

    def test_the_uno_probe_is_not_a_project_feed(self):
        engine = engine_fed("ch2", "ADC counts RMS relative")
        self.assertEqual(engine.calibrate("ch2", [1, 2], [2, 4], 0.1)["unit"], "V/m")

    def test_a_feed_calibration_never_touches_the_magnetometer(self):
        engine = engine_fed("ch1", "cm", fed=True)
        engine.calibrate("ch1", [1, 2], [2, 4], 0.1)          # scale 2, in cm
        feed(engine, "ch1", "µT", False, start=10, value=7.0)  # the studio's own magnetometer comes back
        snap = engine.snapshot(now=15)["channels"]["ch1"]
        self.assertEqual(snap["unit"], "µT")

    def test_a_skipped_calibration_is_not_reported_as_applied(self):
        engine = engine_fed("ch1", "cm", fed=True)
        engine.calibrate("ch1", [1, 2], [2, 4], 0.1)
        feed(engine, "ch1", "µT", False, start=10, value=7.0)
        self.assertFalse(engine.snapshot(now=15)["channels"]["ch1"]["calibration"]["calibrated"])
        feed(engine, "ch1", "cm", True, start=20, value=7.0)
        self.assertTrue(engine.snapshot(now=25)["channels"]["ch1"]["calibration"]["calibrated"])

    def test_a_calibration_saved_before_any_sample_never_rescales_a_feed(self):
        engine = AnalysisEngine(pathlib.Path(tempfile.mkdtemp()) / "calibration.json")
        engine.calibrate("ch1", [1, 2], [2, 4], 0.1)          # no sample yet: made for the studio's own source
        feed(engine, "ch1", "cm", True, value=7.0)
        snap = engine.snapshot(now=5)["channels"]["ch1"]
        self.assertEqual(snap["unit"], "cm")
        self.assertFalse(snap["calibration"]["calibrated"])

    def test_a_new_input_unit_starts_a_fresh_baseline(self):
        engine = engine_fed("ch1", "cm", fed=True)
        self.assertTrue(engine.histories["ch1"])
        engine.ingest("ch1", 7.0, timestamp=10, unit="µT", vector=[7.0, 0, 0], metadata={"monotonic": 10})
        self.assertEqual(len(engine.histories["ch1"]), 1)   # only the first sample in the new unit

    def test_an_unrelated_unit_is_refused(self):
        with self.assertRaises(ValueError):
            engine_fed("ch1", "cm", fed=True).calibrate("ch1", [1, 2], [2, 4], 0.1, unit="kg")


if __name__ == "__main__":
    unittest.main()
