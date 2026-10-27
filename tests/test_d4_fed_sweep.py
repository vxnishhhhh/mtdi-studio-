"""D4 and a fed channel 3 sweep (S1-06 slice 8, CodeRabbit on #71).

The D4 sweep analysis was written for the radio: hertz and dBm. A project's sweep has its own x
unit and its own level unit, so its positions keep their decimals, decibel arithmetic runs only on
decibels, and a floor change is stated only between two sweeps of the same kind."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
class FedSweep(unittest.TestCase):
    def sweep(self, x_unit, xs=None):
        xs = xs or [100.0e6 + i * 0.25e6 for i in range(24)]
        levels = [-80.0] * 24
        levels[8] = -30.0
        return {"freqs": xs, "levels": levels, "trusted": x_unit is None, "status": "s", "x_unit": x_unit}

    def test_the_radio_sweep_is_analysed_in_whole_hertz(self):
        from studio.d4live import ch3_packet
        r = ch3_packet(self.sweep(None), 10.0)
        self.assertNotIn("error", r)
        self.assertEqual(r["primary_peak_hz"], 102.0e6)
        self.assertIsNone(r["x_unit"])

    def test_a_fed_sweep_in_db_keeps_fractional_positions(self):
        from studio.d4live import ch3_packet
        xs = [0.5 + i * 0.25 for i in range(24)]
        r = ch3_packet(self.sweep("mm", xs), 10.0, level_unit="dB")
        self.assertEqual(r["primary_peak_hz"], 2.5)
        self.assertEqual(r["x_unit"], "mm")
        self.assertTrue(all(p["hz"] % 0.25 == 0 for p in r["peaks"]))

    def test_a_fed_sweep_not_in_db_is_not_put_through_decibel_arithmetic(self):
        from studio.d4live import ch3_packet
        r = ch3_packet(self.sweep("mm", [float(i) for i in range(24)]), 10.0, level_unit="kPa")
        self.assertIn("decibels", r["error"])
        self.assertNotIn("noise_floor_dbm", r)
        self.assertEqual((r["x_unit"], r["status"]), ("mm", "s"))

    def test_a_floor_change_is_only_stated_between_like_sweeps(self):
        from studio import d4
        radio = d4.fingerprint([], [], -80.0, 1.0e8, 0)
        fed = d4.fingerprint([], [], -60.0, 2.5, 0, ch3_x_unit="mm")
        self.assertEqual(fed["ch3_peak_hz"], 2.5)
        self.assertEqual(d4.compare_fingerprints(radio, d4.fingerprint([], [], -70.0, 1.0e8, 0))["ch3_floor_db"], 10.0)
        self.assertIsNone(d4.compare_fingerprints(radio, fed)["ch3_floor_db"])
        self.assertIsNone(d4.compare_fingerprints(radio, d4.fingerprint([], [], None, None, 0))["ch3_floor_db"])
        dbfs = d4.fingerprint([], [], -50.0, 2.5, 0, ch3_x_unit="mm", ch3_level_unit="dBFS")
        dbm = d4.fingerprint([], [], -40.0, 2.5, 0, ch3_x_unit="mm", ch3_level_unit="dBm")
        self.assertIsNone(d4.compare_fingerprints(dbfs, dbm)["ch3_floor_db"])      # same axis, other level unit
        self.assertEqual(d4.compare_fingerprints(dbm, dict(dbm, ch3_floor_dbm=-35.0))["ch3_floor_db"], 5.0)

    def test_a_fed_peak_is_not_a_frequency_feature(self):
        from studio import d4
        from studio.d4live import ch3_packet
        fed = ch3_packet(self.sweep("mm", [0.5 + i * 0.25 for i in range(24)]), 10.0, level_unit="dB")
        radio = ch3_packet(self.sweep(None), 10.0)
        self.assertEqual(fed["level_unit"], "dB")
        self.assertIsNone(d4.feature_vector({"ch3": fed})[9])
        self.assertEqual(d4.feature_vector({"ch3": radio})[9], 0.102)
