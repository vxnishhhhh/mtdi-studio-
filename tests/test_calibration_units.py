"""Calibration units (S1-06 slice 12): a project feed calibrates in its own unit; the studio's own
sources keep their physical units; anything else is refused."""
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from studio.analysis import AnalysisEngine  # noqa: E402


def engine_fed(channel, unit):
    engine = AnalysisEngine(pathlib.Path(tempfile.mkdtemp()) / "calibration.json")
    for t in range(5):
        engine.ingest(channel, 10.0, timestamp=t, unit=unit, vector=[10, 0, 0] if channel == "ch1" else None,
                      metadata={"monotonic": t})
    return engine


class CalibrationUnits(unittest.TestCase):
    def test_a_project_feed_keeps_its_own_unit(self):
        self.assertEqual(engine_fed("ch1", "cm").calibrate("ch1", [1, 2], [2, 4], 0.1)["unit"], "cm")

    def test_the_studio_magnetometer_calibrates_in_microtesla(self):
        self.assertEqual(engine_fed("ch1", "µT").calibrate("ch1", [1, 2], [2, 4], 0.1)["unit"], "µT")

    def test_the_studio_probe_still_calibrates_to_volts_per_metre(self):
        self.assertEqual(engine_fed("ch2", "mV RMS relative").calibrate("ch2", [1, 2], [2, 4], 0.1)["unit"], "V/m")

    def test_an_unrelated_unit_is_refused(self):
        with self.assertRaises(ValueError):
            engine_fed("ch1", "cm").calibrate("ch1", [1, 2], [2, 4], 0.1, unit="kg")


if __name__ == "__main__":
    unittest.main()
