"""S1-11: fusion and calibration behave as the maths says they must.

The inputs here are constructed test vectors with known answers (exact lines, fixed noise
seeds). They test the algorithms; they are not sensor data and are never shown as such.
"""
import math
import pathlib
import random
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mtdi import fusion  # noqa: E402
from mtdi.pillars import COMPUTATIONAL_MODULES  # noqa: E402


class Fusion(unittest.TestCase):
    def test_inverse_variance_is_never_worse_than_best_sensor(self):
        value, var = fusion.fuse([(10.0, 4.0), (12.0, 1.0)])
        self.assertAlmostEqual(value, (10 / 4 + 12 / 1) / (1 / 4 + 1), places=12)
        self.assertAlmostEqual(var, 0.8, places=12)
        self.assertLess(var, 1.0)

    def test_fuse_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            fusion.fuse([])
        with self.assertRaises(ValueError):
            fusion.fuse([(1.0, 0.0)])

    def test_kalman_converges_and_shrinks_uncertainty(self):
        rng = random.Random(7)
        kf = fusion.Kalman1D(q=0.0, r=0.25)
        for _ in range(400):
            x, p = kf.update(5.0 + rng.gauss(0, 0.5))
        self.assertAlmostEqual(x, 5.0, delta=0.1)
        self.assertLess(p, 0.25 / 100)

    def test_kalman_two_sensors_beat_one(self):
        rng = random.Random(3)
        one, two = fusion.Kalman1D(q=0, r=1), fusion.Kalman1D(q=0, r=1)
        for _ in range(50):
            one.update(1 + rng.gauss(0, 1), r=1)
            two.update(1 + rng.gauss(0, 1), r=1)
            two.update(1 + rng.gauss(0, 0.5), r=0.25)
        self.assertLess(two.p, one.p)

    def test_complementary_removes_rate_drift(self):
        cf = fusion.Complementary(alpha=0.95)
        for _ in range(2000):
            angle = cf.update(rate=0.1, absolute=30.0, dt=0.01)  # a gyro biased by 0.1 deg/s
        self.assertAlmostEqual(angle, 30.0, delta=0.05)

    def test_two_point_and_least_squares(self):
        cal = fusion.Calibration.two_point(100, 0.0, 900, 50.0)
        self.assertAlmostEqual(cal.apply(500), 25.0)
        raw = [i * 10.0 for i in range(20)]
        ref = [0.5 * r - 3.0 for r in raw]
        fit = fusion.Calibration.fit(raw, ref)
        self.assertAlmostEqual(fit.gain, 0.5, places=9)
        self.assertAlmostEqual(fit.offset, -3.0, places=9)
        self.assertAlmostEqual(fit.residual_sd, 0.0, places=9)

    def test_temperature_compensation_recovers_coefficient(self):
        rng = random.Random(11)
        raw, temp, ref = [], [], []
        for _ in range(200):
            r, t = rng.uniform(0, 100), rng.uniform(10, 40)
            raw.append(r)
            temp.append(t)
            ref.append(1.2 * r + 4.0 - 0.3 * (t - 25.0))
        cal = fusion.Calibration.fit(raw, ref, temperature=temp)
        self.assertAlmostEqual(cal.gain, 1.2, places=6)
        self.assertAlmostEqual(cal.temp_coeff, -0.3, places=6)
        self.assertAlmostEqual(cal.offset, 4.0, places=6)

    def test_save_load_and_limits(self):
        cal = fusion.Calibration(gain=2, offset=1, method="test")
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "cal.json"
            cal.save(path)
            self.assertEqual(fusion.Calibration.load(path).to_dict(), cal.to_dict())
        lim = fusion.detection_limits(0.04)
        self.assertAlmostEqual(lim["lod"], 0.6)
        self.assertAlmostEqual(lim["loq"], 2.0)

    def test_registered_in_computational_core(self):
        self.assertIn("mtdi.fusion", [m for mods in COMPUTATIONAL_MODULES.values() for m in mods])


if __name__ == "__main__":
    unittest.main()
