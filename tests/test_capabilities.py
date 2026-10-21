"""S1-03: capability records for every reference target and the runtime-selection rules."""
import json
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mtdi import capabilities as cap  # noqa: E402

# What a person would expect, written out by hand, so a rule change has to change this too.
EXPECTED = {
    ("arduino-uno", "edge"): "line-protocol",
    ("esp32", "edge"): "edge",
    ("esp32", "research"): "edge",
    ("raspberry-pi-4", "edge"): "full",
    ("raspberry-pi-5", "research"): "full",
    ("raspberry-pi-5", "autonomous"): "full",
    ("mac-m5", "vision"): "full",
    ("desktop", "hybrid"): "full",
    ("cloud-function", "edge"): "full",
    ("cloud-function", "research"): "remote",
    ("browser", "hybrid"): "remote",
}


class Capabilities(unittest.TestCase):
    def setUp(self):
        self.targets = cap.load_targets()

    def test_every_reference_target_is_valid(self):
        self.assertEqual(set(self.targets), {"arduino-uno", "esp32", "raspberry-pi-4", "raspberry-pi-5",
                                             "mac-m5", "desktop", "cloud-function", "browser"})
        for t in self.targets.values():
            self.assertIn(t["class"], cap.CLASSES)

    def test_selection_rules(self):
        for (tid, profile), runtime in EXPECTED.items():
            got, why = cap.select_runtime(self.targets[tid], profile)
            self.assertEqual(got, runtime, f"{tid}/{profile}: {why}")
            self.assertTrue(why)

    def test_every_pair_has_a_runtime_and_a_reason(self):
        for tid, row in cap.matrix().items():
            for profile, (runtime, why) in row.items():
                self.assertIn(runtime, cap.RUNTIMES, (tid, profile))
                self.assertGreater(len(why), 10, (tid, profile))

    def test_small_python_host_goes_remote(self):
        tiny = dict(self.targets["desktop"], memory_mb=512)
        self.assertEqual(cap.select_runtime(tiny, "vision")[0], "remote")
        self.assertEqual(cap.select_runtime(tiny, "edge")[0], "full")

    def test_unknown_profile_and_bad_record_are_rejected(self):
        with self.assertRaises(ValueError):
            cap.select_runtime(self.targets["desktop"], "telepathy")
        with self.assertRaises(ValueError):
            cap.validate({"id": "x"})

    def test_host_detection_and_cli(self):
        host = cap.detect_host()
        self.assertIn("python", host["languages"])
        self.assertGreater(host["memory_mb"], 0)
        out = subprocess.run([sys.executable, "-m", "mtdi", "capabilities", "--json"], cwd=ROOT,
                             capture_output=True, text=True, timeout=120)
        self.assertEqual(out.returncode, 0, out.stderr)
        data = json.loads(out.stdout)
        self.assertIn("host", data["selection"])
        desc = json.loads(subprocess.run([sys.executable, "-m", "mtdi", "describe"], cwd=ROOT,
                                         capture_output=True, text=True, timeout=120).stdout)
        self.assertEqual(sorted(desc["capabilities"]["targets"]), sorted(self.targets))


if __name__ == "__main__":
    unittest.main()
