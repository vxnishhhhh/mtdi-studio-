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

    def test_fuse_survives_tiny_and_huge_variances(self):
        v, var = fusion.fuse([(10.0, 1e-320), (20.0, 1e-320)])
        self.assertEqual((v, var), (15.0, 5e-321))
        v, var = fusion.fuse([(1.0, 5e-324), (1.0, 5e-324)])
        self.assertEqual((v, var), (1.0, 5e-324))
        fusion.fuse([(v, var)])                          # the result is itself a valid input
        v, var = fusion.fuse([(10.0, 1e300), (20.0, 1e-300)])
        self.assertAlmostEqual(v, 20.0)
        self.assertGreater(var, 0)

    def test_fuse_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            fusion.fuse([])
        with self.assertRaises(ValueError):
            fusion.fuse([(1.0, 0.0)])
        with self.assertRaises(ValueError):
            fusion.fuse([(float("nan"), 1.0)])
        with self.assertRaises(ValueError):
            fusion.Kalman1D().update(1.0, r=float("inf"))

    def test_plane_fit_is_scale_independent_and_rejects_collinear(self):
        raw = [i * 1e-6 for i in range(10)]
        temp = [20 + (i % 3) * 1e-6 for i in range(10)]
        ref = [2.0 * r + 0.5 * (t - 25.0) + 1.0 for r, t in zip(raw, temp)]
        cal = fusion.Calibration.fit(raw, ref, temperature=temp)
        self.assertAlmostEqual(cal.gain, 2.0, places=6)
        with self.assertRaises(ValueError):
            fusion.Calibration.fit([1, 2, 3, 4], [2, 4, 6, 8], temperature=[2, 4, 6, 8])

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


class CalibratedChannel(unittest.TestCase):
    def manifest(self, cal):
        return {"project": {"id": "cal"}, "sources": [{"id": "s", "adapter": "http"}],
                "channels": [{"id": "co", "keys": ["CO"], "noise_floor": 0.1, "calibration": cal}]}

    def test_engine_applies_calibration_with_temperature(self):
        from mtdi.engine import Engine
        from mtdi.project import normalise
        cal = {"gain": 2.0, "offset": 1.0, "temp_coeff": 0.5, "temp_ref": 20.0, "temperature_key": "T",
               "method": "least-squares+temperature", "n": 40, "residual_sd": 0.3}
        engine = Engine(normalise(self.manifest(cal)))
        engine.ingest_values("s", {"CO": 3.0, "T": 24.0})
        ch = engine.snapshot()["channels"]["co"]
        self.assertAlmostEqual(ch["value"], 2.0 * 3.0 + 1.0 + 0.5 * 4.0)
        self.assertEqual(ch["raw"], [3.0])
        self.assertEqual(ch["calibration"]["method"], "least-squares+temperature")
        engine.ingest_values("s", {"CO": 3.0})             # temperature missing: no compensation
        self.assertAlmostEqual(engine.snapshot()["channels"]["co"]["value"], 7.0)

    def test_manifest_loads_a_saved_calibration_file(self):
        from mtdi.project import load
        with tempfile.TemporaryDirectory() as d:
            fusion.Calibration.two_point(0, 0, 10, 50).save(pathlib.Path(d) / "co.cal.json")
            m = self.manifest("co.cal.json")
            (pathlib.Path(d) / "project.json").write_text(__import__("json").dumps(m), encoding="utf-8")
            project = load(d)
        cal = project["channels"][0]["calibration"]
        self.assertEqual((cal["gain"], cal["method"], cal["file"]), (5.0, "two-point", "co.cal.json"))

    def test_saved_temperature_fit_loads_and_compensates(self):
        from mtdi.engine import Engine
        from mtdi.project import load
        rng = random.Random(3)
        raw = [rng.uniform(0, 10) for _ in range(30)]
        temp = [rng.uniform(15, 35) for _ in range(30)]
        truth = [2 * r + 1 + 0.3 * (t - 25) for r, t in zip(raw, temp)]
        cal = fusion.Calibration.fit(raw, truth, temperature=temp, temperature_key="T")
        with tempfile.TemporaryDirectory() as d:
            cal.save(pathlib.Path(d) / "co.cal.json")
            (pathlib.Path(d) / "project.json").write_text(__import__("json").dumps(self.manifest("co.cal.json")),
                                                         encoding="utf-8")
            engine = Engine(load(d))
        engine.ingest_values("s", {"CO": 4.0, "T": 35.0})
        self.assertAlmostEqual(engine.snapshot()["channels"]["co"]["value"], 2 * 4 + 1 + 0.3 * 10, places=6)

    def test_bad_calibration_is_named(self):
        from mtdi.project import ManifestError, load, normalise
        for cal, needle in [([1, 2], "object or a file path"), ({"gain": "2"}, "gain must be a finite number"),
                            ({"gain": True}, "gain must be a finite number"),
                            ({"temp_coeff": 0.1}, "no temperature_key"),
                            ({"gian": 2.0}, "unknown field.*gian"), ({"n": "x"}, "n must be a whole number"),
                            ({"residual_sd": -1}, "residual_sd"), ({"method": 3}, "method must be text"),
                            ({"gain": float("nan")}, "gain must be a finite number"),
                            ({"offset": float("inf")}, "offset must be a finite number"),
                            ({"temp_coeff": 0.1, "temperature_key": "room temp"}, "must be a protocol key")]:
            with self.assertRaisesRegex(ManifestError, needle):
                normalise(self.manifest(cal))
        vec = self.manifest({"gain": 2})
        vec["channels"][0]["keys"] = ["X", "Y"]
        with self.assertRaisesRegex(ManifestError, "scalar channels only"):
            normalise(vec)
        with tempfile.TemporaryDirectory() as d:
            (pathlib.Path(d) / "project.json").write_text(__import__("json").dumps(self.manifest("missing.json")),
                                                         encoding="utf-8")
            with self.assertRaisesRegex(ManifestError, "missing.json"):
                load(d)
            for path, body, needle in [("../outside.json", None, "outside the project folder"),
                                       ("null.json", "null", "must hold a JSON object")]:
                if body is not None:
                    (pathlib.Path(d) / path).write_text(body, encoding="utf-8")
                (pathlib.Path(d) / "project.json").write_text(__import__("json").dumps(self.manifest(path)),
                                                             encoding="utf-8")
                with self.assertRaisesRegex(ManifestError, needle):
                    load(d)


class CalibrationDrift(unittest.TestCase):
    def runner(self, residual_sd=0.5, clock=None):
        from mtdi.project import normalise
        from mtdi.runtime import Runner
        m = normalise({"project": {"id": "d"}, "sources": [{"id": "s", "adapter": "http"}],
                       "channels": [{"id": "co", "label": "CO", "unit": "ppm", "keys": ["CO"], "noise_floor": 0.1,
                                     "calibration": {"gain": 1.0, "offset": 0.0, "residual_sd": residual_sd}},
                                    {"id": "raw", "keys": ["R"], "noise_floor": 0.1}]})
        r = Runner(m, start=False)
        if clock:
            r.engine.clock = clock
        r.engine.ingest_values("s", {"CO": 10.0, "R": 1.0})
        return r

    def test_stale_or_simulated_readings_are_not_checked(self):
        t = [0.0]
        r = self.runner(clock=lambda: t[0])
        t[0] = 100.0
        with self.assertRaisesRegex(ValueError, "check it while it is live"):
            r.action("check", {"channel": "co", "reference": 10})
        r.engine.ingest_values("s", {"CO": 10.0, "R": 1.0}, data_source="SIMULATED")
        with self.assertRaisesRegex(ValueError, "SIMULATED"):
            r.action("check", {"channel": "co", "reference": 10})

    def test_clipped_reading_and_missing_residual(self):
        from mtdi.project import ManifestError, normalise
        from mtdi.runtime import Runner
        base = {"project": {"id": "d"}, "sources": [{"id": "s", "adapter": "http"}],
                "channels": [{"id": "co", "keys": ["CO"], "noise_floor": 0.1, "raw_range": [0, 1023],
                              "calibration": {"gain": 1.0}}]}
        r = Runner(normalise(base), start=False)
        r.engine.ingest_values("s", {"CO": 10.0})
        self.assertIn("cannot be judged", r.action("check", {"channel": "co", "reference": 10}))
        r.engine.ingest_values("s", {"CO": 1023.0})
        with self.assertRaisesRegex(ValueError, "clipping"):
            r.action("check", {"channel": "co", "reference": 10})
        with self.assertRaisesRegex(ValueError, "within"):
            r.action("check", {"channel": "co", "reference": 1e300})
        base["channels"][0]["calibration"] = {"residual_sd": 1e308}
        with self.assertRaisesRegex(ManifestError, "residual_sd must be a number from 0 to"):
            normalise(base)

    def test_summary(self):
        self.assertIsNone(fusion.drift_summary([], 0.5)["drift"])
        self.assertIsNone(fusion.drift_summary([0.1, 0.2], 0.5)["drift"])        # too few checks
        self.assertFalse(fusion.drift_summary([0.1, -0.2, 0.3], 0.5)["drift"])
        self.assertTrue(fusion.drift_summary([2.0, 2.1, 1.9], 0.5)["drift"])
        self.assertIsNone(fusion.drift_summary([5, 5, 5], None)["drift"])        # no promise to break
        self.assertAlmostEqual(fusion.drift_summary([1.0, 3.0], 1.0)["bias"], 2.0)
        self.assertTrue(fusion.drift_summary([0.1, 0.1, 0.1], 0.0)["drift"])     # exact fit: any error is drift
        big = fusion.drift_summary([1e200, 1e200, 1e200], 0.5)
        self.assertTrue(math.isfinite(big["rms"]) and big["drift"])
        self.assertTrue(math.isfinite(fusion.drift_summary([1e308] * 3, 0.5)["bias"]))

    def test_checks_flag_drift_into_snapshot_and_warnings(self):
        r = self.runner()
        msg = r.action("check", {"channel": "co", "reference": 10.2})
        self.assertIn("need 2 more", msg)
        r.action("check", {"channel": "co", "reference": 12.0})
        msg = r.action("check", {"channel": "co", "reference": 12.1})
        self.assertIn("DRIFT", msg)
        packet = r.engine.snapshot()
        self.assertTrue(packet["channels"]["co"]["calibration"]["checks"]["drift"])
        self.assertTrue(any("calibration drift" in w for w in packet["fusion"]["warnings"]))

    def test_bad_checks_are_refused(self):
        r = self.runner()
        for args, err in [({"channel": "raw", "reference": 1}, ValueError), ({"channel": "nope", "reference": 1}, KeyError),
                          ({"channel": "co", "reference": "x"}, ValueError), ({"channel": "co", "reference": None}, ValueError), ({"channel": "co", "reference": True}, ValueError),
                          ({"channel": "co", "reference": float("nan")}, ValueError), ({"reference": 1}, ValueError)]:
            with self.assertRaises(err):
                r.action("check", args)

class FusedChannels(unittest.TestCase):
    def manifest(self, fused, units=("ppm", "ppm")):
        return {"project": {"id": "f"}, "sources": [{"id": "s", "adapter": "http"}],
                "channels": [{"id": "a", "keys": ["A"], "unit": units[0], "noise_floor": 0.1},
                             {"id": "b", "keys": ["B"], "unit": units[1], "noise_floor": 0.1},
                             {"id": "v", "keys": ["X", "Y"], "noise_floor": 0.1}],
                "fused": fused}

    def test_snapshot_fuses_connected_inputs_by_inverse_variance(self):
        from mtdi.engine import Engine
        from mtdi.project import normalise
        clock = [0.0]
        engine = Engine(normalise(self.manifest([{"id": "co", "inputs": ["a", "b"], "sd": {"a": 1.0, "b": 2.0}}])),
                        clock=lambda: clock[0])
        engine.ingest_values("s", {"A": 10.0, "B": 20.0, "X": 0, "Y": 0})
        f = engine.snapshot()["fused"]["co"]
        value, variance = fusion.fuse([(10.0, 1.0), (20.0, 4.0)])
        self.assertAlmostEqual(f["value"], value)
        self.assertAlmostEqual(f["sd"], math.sqrt(variance))
        self.assertLess(f["sd"], 1.0)                          # better than the best single sensor
        self.assertEqual(f["unit"], "ppm")
        self.assertEqual([i["basis"] for i in f["inputs"]], ["manifest", "manifest"])
        clock[0] = 100.0                                       # every input goes stale
        stale = engine.snapshot()["fused"]["co"]
        self.assertEqual((stale["value"], stale["inputs"], stale["of"]), (None, [], 2))

    def test_extreme_residual_falls_back_instead_of_breaking_the_snapshot(self):
        from mtdi.engine import Engine
        from mtdi.project import normalise
        m = self.manifest([{"id": "co", "inputs": ["a", "b"]}])
        m["channels"][0]["calibration"] = {"residual_sd": 1e-200}
        engine = Engine(normalise(m))
        engine.ingest_values("s", {"A": 10.0, "B": 20.0, "X": 0, "Y": 0})
        f = engine.snapshot()["fused"]["co"]
        self.assertEqual(f["inputs"][0]["basis"], "noise floor")
        self.assertTrue(math.isfinite(f["value"]))

    def test_bad_fused_entries_are_named(self):
        from mtdi.project import ManifestError, normalise
        for fused, needle, units in [
                ([{"id": "co", "inputs": ["a"]}], "at least two", ("ppm", "ppm")),
                ([{"id": "co", "inputs": ["a", "zz"]}], "unknown channel 'zz'", ("ppm", "ppm")),
                ([{"id": "co", "inputs": ["a", "v"]}], "not a scalar", ("ppm", "ppm")),
                ([{"id": "co", "inputs": ["a", "b"]}], "mix units", ("ppm", "mg/m3")),
                ([{"id": "a", "inputs": ["a", "b"]}], "already a channel", ("ppm", "ppm")),
                ([{"id": "co", "inputs": ["a", "b"], "sd": {"a": 0}}], "sd.a must be a number from", ("ppm", "ppm")),
                ([{"id": "co", "inputs": ["a", "b"], "sd": {"a": 1e-200}}], "sd.a must be a number from", ("ppm", "ppm")),
                ([{"id": "co", "inputs": ["a", "b"], "sd": {"a": float("inf")}}], "sd.a must be", ("ppm", "ppm")),
                ([{"id": "co", "inputs": ["a", "b"], "sds": {"a": 1}}], "unknown field.*sds", ("ppm", "ppm")),
                ([{"id": "co", "inputs": ["a", []]}], "must list channel ids", ("ppm", "ppm")),
                ([{"id": "co", "inputs": ["a", "b"], "method": "kalman"}], "inverse-variance", ("ppm", "ppm"))]:
            with self.assertRaisesRegex(ManifestError, needle):
                normalise(self.manifest(fused, units))


class CalibrateCommand(unittest.TestCase):
    def run_cli(self, *args, cwd):
        import subprocess
        return subprocess.run([sys.executable, "-m", "mtdi", "calibrate", *args], cwd=cwd, capture_output=True,
                              text=True, env={**__import__("os").environ, "PYTHONPATH": str(ROOT)})

    def test_fit_save_and_load_in_a_manifest(self):
        import json
        from mtdi.engine import Engine
        from mtdi.project import load
        rng = random.Random(8)
        with tempfile.TemporaryDirectory() as d:
            d = pathlib.Path(d)
            rows = ["raw,reference,temperature"]
            for _ in range(30):
                r, t = rng.uniform(0, 10), rng.uniform(15, 35)
                rows.append(f"{r},{2 * r + 1 + 0.1 * (t - 25)},{t}")
            (d / "co.csv").write_text("\n".join(rows), encoding="utf-8")
            res = self.run_cli("co.csv", "--temperature-key", "T", cwd=d)
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertIn('"calibration": "co.cal.json"', res.stdout)
            self.assertIn("project folder", res.stdout)
            (d / "project.json").write_text(json.dumps({
                "project": {"id": "c"}, "sources": [{"id": "s", "adapter": "http"}],
                "channels": [{"id": "co", "keys": ["CO"], "noise_floor": 0.1, "calibration": "co.cal.json"}]}))
            engine = Engine(load(d))
        engine.ingest_values("s", {"CO": 4.0, "T": 35.0})
        self.assertAlmostEqual(engine.snapshot()["channels"]["co"]["value"], 2 * 4 + 1 + 0.1 * 10, places=6)

    def test_refuses_unclear_input(self):
        with tempfile.TemporaryDirectory() as d:
            d = pathlib.Path(d)
            (d / "t.csv").write_text("raw,reference,temperature\n1,2,20\n2,4,21\n3,6,25\n", encoding="utf-8")
            self.assertIn("--temperature-key", self.run_cli("t.csv", cwd=d).stderr)
            self.assertEqual(self.run_cli("t.csv", "--no-temperature", cwd=d).returncode, 0)
            (d / "bad.csv").write_text("x,y\n1,2\n", encoding="utf-8")
            self.assertIn("raw,reference", self.run_cli("bad.csv", cwd=d).stderr)
            (d / "few.csv").write_text("raw,reference\n1,2\n2,4\n", encoding="utf-8")
            self.assertIn("at least 3", self.run_cli("few.csv", cwd=d).stderr)
            (d / "nan.csv").write_text("raw,reference\n1,2\nx,4\n3,6\n", encoding="utf-8")
            self.assertNotEqual(self.run_cli("nan.csv", cwd=d).returncode, 0)
            self.assertIn("No such file", self.run_cli("missing.csv", cwd=d).stderr)
            (d / "t.cal.json").unlink()                  # written by the --no-temperature run above
            for bad in (["--temperature-key", "TEMP C"], ["--temperature-key", "T", "--temp-ref", "nan"]):
                res = self.run_cli("t.csv", *bad, cwd=d)
                self.assertIn("a manifest would reject it", res.stderr)
                self.assertFalse((d / "t.cal.json").exists())
            (d / "inf.csv").write_text("raw,reference\n1,2\n2,inf\n3,6\n", encoding="utf-8")
            self.assertNotEqual(self.run_cli("inf.csv", cwd=d).returncode, 0)
            self.assertFalse((d / "inf.cal.json").exists())


class WatchFrame(unittest.TestCase):
    def test_shows_calibrated_marker_and_fused_estimate(self):
        from mtdi.__main__ import watch_frame
        from mtdi.engine import Engine
        from mtdi.project import normalise
        m = normalise({"project": {"id": "w", "name": "Watch"}, "sources": [{"id": "s", "adapter": "http"}],
                       "channels": [{"id": "a", "label": "CO A", "keys": ["A"], "unit": "ppm", "noise_floor": 0.1,
                                     "calibration": {"gain": 2.0}},
                                    {"id": "b", "label": "CO B", "keys": ["B"], "unit": "ppm", "noise_floor": 0.1}],
                       "fused": [{"id": "co", "label": "CO fused", "inputs": ["a", "b"], "sd": {"a": 1, "b": 2}}]})
        e = Engine(m)
        e.ingest_values("s", {"A": 5.0, "B": 12.0})
        frame = watch_frame(e.snapshot())
        a_line = next(l for l in frame.splitlines() if l.startswith("CO A"))
        b_line = next(l for l in frame.splitlines() if l.startswith("CO B"))
        self.assertIn(" cal ", a_line)
        self.assertNotIn(" cal ", b_line)
        self.assertIn("CO fused", frame)
        self.assertIn("2/2 live", frame)
        self.assertIn("10.4 ± 0.89", frame)        # (10/1 + 12/4) / (1/1 + 1/4) = 10.4, sd sqrt(0.8)
