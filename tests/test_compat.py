"""S1-05: the Compatibility Laboratory keeps compiled, ran and tested-on-hardware apart."""
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("compat_lab", ROOT / "tools" / "compat" / "lab.py")
lab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab)


def compile_json(flash, ram, ok=True, flash_max=32256, ram_max=2048):
    return {"success": ok, "compiler_err": "" if ok else "error: 'tone' was not declared",
            "builder_result": {"executable_sections_size": [{"name": "text", "size": flash, "max_size": flash_max},
                                                            {"name": "data", "size": ram, "max_size": ram_max}]}}


class Firmware(unittest.TestCase):
    def test_every_repository_sketch_is_found_and_builds_from_a_folder_of_its_name(self):
        found = lab.sketches()
        self.assertIn(pathlib.Path("projects/third-eye/firmware/third_eye/third_eye.ino"), found)
        for rel in found:
            self.assertEqual((ROOT / rel).parent.name, rel.stem, f"{rel}: the Arduino IDE needs folder == sketch name")

    def test_a_sketch_outside_its_own_folder_is_copied_and_says_so(self):
        with tempfile.TemporaryDirectory() as d:
            loose = pathlib.Path(d, "firmware", "probe.ino")
            loose.parent.mkdir()
            loose.write_text("void setup(){} void loop(){}")
            folder, note = lab.sketch_dir(loose, pathlib.Path(d, "scratch"))
            self.assertEqual(folder.name, "probe")
            self.assertTrue((folder / "probe.ino").exists())
            self.assertIn("folder of its own name", note)
            self.assertEqual(lab.sketch_dir(folder / "probe.ino", d), (folder, None))

    def test_sizes_and_verdicts(self):
        self.assertEqual(lab.sizes(compile_json(5712, 257)), {"flash": [5712, 32256], "ram": [257, 2048]})
        self.assertEqual(lab.judge(True, {"flash": [5712, 32256], "ram": [257, 2048]}), "ok")
        self.assertEqual(lab.judge(True, {"flash": [5712, 32256], "ram": [1600, 2048]}), "warn")   # >= 75 % RAM
        self.assertEqual(lab.judge(True, {"flash": [30000, 32256], "ram": [257, 2048]}), "warn")   # >= 90 % flash
        self.assertEqual(lab.judge(True, {"flash": [33000, 32256]}), "too-big")
        self.assertEqual(lab.judge(False, {}), "failed")

    def test_build_records_each_sketch_and_the_compiler_error(self):
        calls = []

        def fake(cmd, **kw):
            calls.append(cmd)
            if cmd[1] == "version":
                return subprocess.CompletedProcess(cmd, 0, "arduino-cli Version: test", "")
            ok = "third_eye" not in cmd[-3] and "third_eye" not in cmd[-1]
            return subprocess.CompletedProcess(cmd, 0 if ok else 1, json.dumps(compile_json(2000, 200, ok)), "")
        result = lab.build_firmware("esp32", run=fake)
        self.assertEqual(result["evidence"], "compiled")
        statuses = {r["sketch"]: r["status"] for r in result["sketches"]}
        self.assertEqual(statuses["projects/third-eye/firmware/third_eye/third_eye.ino"], "failed")
        failed = next(r for r in result["sketches"] if r["status"] == "failed")
        self.assertIn("'tone' was not declared", failed["error"])
        compiles = [c for c in calls if c[1] == "compile"]
        self.assertTrue(all("--additional-urls" in c and lab.ESP32_INDEX in c for c in compiles))


VERBOSE = """test_cpp (test_sdks.SDKs.test_cpp) ... ok
test_matlab_in_octave (test_sdks.SDKs.test_matlab_in_octave) ... skipped 'octave not installed'
test_buzzer (test_third_eye.ThirdEye.test_buzzer)
A 0/1 state at its bounds is normal. ... ok
test_broken (test_x.X.test_broken) ... FAIL

----------------------------------------------------------------------
Ran 4 tests in 1.2s

FAILED (failures=1, skipped=1)
"""


class CoreSuite(unittest.TestCase):
    def test_unittest_output_is_read_test_by_test(self):
        parsed = lab.parse_unittest(VERBOSE)
        self.assertEqual(parsed["ran"], 4)
        self.assertFalse(parsed["ok"])
        self.assertEqual(parsed["tests"]["test_third_eye.ThirdEye.test_buzzer"], "ok")   # docstring on its own line
        self.assertEqual(parsed["tests"]["test_x.X.test_broken"], "FAIL")
        self.assertEqual(parsed["skipped"], {"test_sdks.SDKs.test_matlab_in_octave": "octave not installed"})

    def test_a_failing_run_keeps_the_tracebacks(self):
        text = VERBOSE.replace("\n----", "\n======================================================================\n"
                               "FAIL: test_broken (test_x.X.test_broken)\nAssertionError: 1 != 2\n----", 1)
        self.assertTrue(lab.failure_text(text).startswith("======"))
        self.assertIn("AssertionError: 1 != 2", lab.failure_text(text))
        self.assertEqual(lab.failure_text("boom" * 5000)[-4:], "boom")       # no tracebacks: the tail

    def test_named_checks_exist_in_the_suite(self):
        for check, test_id in lab.CHECKS.items():
            module, cls, name = test_id.split(".")
            text = (ROOT / "tests" / f"{module}.py").read_text(encoding="utf-8")
            self.assertIn(f"class {cls}(", text, check)
            self.assertIn(f"def {name}(", text, check)


def result(kind, **fields):
    return {"kind": kind, "where": "test machine", "when": "2026-10-25", "commit": "abc1234", **fields}


UNO = result("firmware", board="arduino-uno", fqbn="arduino:avr:uno", evidence="compiled",
             sketches=[{"sketch": "a/a.ino", "status": "ok", "flash": [5712, 32256], "ram": [257, 2048]}])
CORE = result("core", target="linux-x64", evidence="ran", python="3.12", ran=213, ok=True, failed=[],
              skipped={}, checks={"cpp-sdk-matches-python": "ok", "octave-matches-python": "ok"})
RUNTIMES = {"arduino-uno": {"edge": ("line-protocol", "2 KB RAM")}}


class Report(unittest.TestCase):
    def test_nothing_is_tested_on_hardware_without_a_record(self):
        text = lab.report([UNO, CORE], [], RUNTIMES)
        rows = [line for line in text.splitlines() if line.startswith("| Arduino") or line.startswith("| ESP32")
                or line.startswith("| Raspberry") or line.startswith("| Desktop") or line.startswith("| Cloud")
                or line.startswith("| Software")]
        self.assertEqual(len(rows), 6)
        self.assertTrue(all(row.endswith("| none recorded |") for row in rows), rows)
        self.assertIn("| Arduino-class (AVR) | 1/1 sketches build for `arduino:avr:uno`", text)
        self.assertIn("C++ SDK detectors match Python on the host: linux-x64 ok", text)
        self.assertIn("ESP32 + edge processing | not built yet", text)

    def test_a_hardware_record_shows_on_its_own_target_only(self):
        record = {"target": "arduino-uno", "check": "Third Eye prints protocol lines", "result": "passed",
                  "date": "2026-11-01", "by": "owner"}
        rows = {r[0]: r[3] for r in lab.target_rows([UNO], [record])}
        self.assertEqual(rows["Arduino-class (AVR)"], "Third Eye prints protocol lines: passed (2026-11-01, owner)")
        self.assertEqual({k for k, v in rows.items() if v != "none recorded"}, {"Arduino-class (AVR)"})

    def test_a_hardware_record_must_say_who_and_when(self):
        with tempfile.TemporaryDirectory() as d:
            pathlib.Path(d, "pi.json").write_text(json.dumps({"target": "raspberry-pi-5", "check": "doctor",
                                                              "result": "passed", "date": "2026-11-01"}))
            with self.assertRaisesRegex(ValueError, "pi.json: a hardware record needs by"):
                lab.hardware_records(d)

    def test_a_hardware_record_for_an_unknown_target_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            pathlib.Path(d, "x.json").write_text(json.dumps({"target": "raspbery-pi-5", "check": "doctor",
                                                             "result": "passed", "date": "2026-11-01", "by": "owner"}))
            with self.assertRaisesRegex(ValueError, "unknown target 'raspbery-pi-5'"):
                lab.hardware_records(d)

    def test_every_row_target_is_a_capability_record(self):
        sys.path.insert(0, str(ROOT))
        from mtdi.capabilities import load_targets
        ids = set(load_targets())
        for row, targets in lab.ROW_TARGETS.items():
            self.assertLessEqual(set(targets), ids, row)

    def test_failures_are_reported_as_failures(self):
        bad = dict(CORE, ok=False, failed=["test_x.X.test_broken"])
        serverless = result("serverless", target="cloud", evidence="ran", ok=False,
                            checks={"page": True, "ingest with the token": False})
        text = lab.report([bad, serverless], [], RUNTIMES)
        self.assertIn("FAILED: test_broken", text)
        self.assertIn("serverless studio: FAILED: ingest with the token", text)
        self.assertIn("- FAILED: ingest with the token", text)

    def test_the_committed_report_matches_the_committed_results(self):
        res = subprocess.run([sys.executable, str(ROOT / "tools" / "compat" / "lab.py"), "report", "--check"],
                             capture_output=True, text=True, timeout=120)
        self.assertEqual(res.returncode, 0, res.stderr)

    def test_committed_results_claim_no_hardware(self):
        for path in (ROOT / "docs" / "results" / "compat").glob("*.json"):
            self.assertIn(json.loads(path.read_text())["evidence"], ("compiled", "emulated", "ran"), path.name)


if __name__ == "__main__":
    unittest.main()
