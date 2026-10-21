"""S1-04: each Intelligence Profile loads its modules and refuses an under-capable target."""
import copy
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mtdi import profiles  # noqa: E402
from mtdi.capabilities import load_targets  # noqa: E402
from mtdi.project import ManifestError, normalise  # noqa: E402

MANIFEST = {"project": {"id": "p"}, "sources": [{"id": "s", "adapter": "system"}],
            "channels": [{"id": "c", "keys": ["CPU_PCT"]}]}


class Profiles(unittest.TestCase):
    targets = load_targets()

    def _check(self, name, big, small):
        mods = profiles.activate(name, self.targets[big])
        self.assertEqual(set(mods), set(profiles.PROFILES[name]["modules"]))
        for core in profiles.CORE:
            self.assertIn(core, mods)
        with self.assertRaises(profiles.ProfileError):
            profiles.activate(name, self.targets[small])

    def test_edge(self):
        self._check("edge", "raspberry-pi-4", "arduino-uno")

    def test_scientific(self):
        self._check("scientific", "mac-m5", "esp32")

    def test_vision(self):
        self._check("vision", "mac-m5", "esp32")

    def test_autonomous(self):
        self._check("autonomous", "raspberry-pi-5", "cloud-function")

    def test_hybrid(self):
        self._check("hybrid", "desktop", "browser")

    def test_research(self):
        self._check("research", "raspberry-pi-5", "cloud-function")

    def test_edge_is_smaller_than_research(self):
        self.assertLess(len(profiles.PROFILES["edge"]["modules"]), len(profiles.PROFILES["research"]["modules"]))
        self.assertNotIn("mtdi.llm", profiles.PROFILES["edge"]["modules"])

    def test_edge_runner_never_imports_the_bot(self):
        import subprocess
        code = ("import sys, json; sys.path.insert(0, '.'); from mtdi.project import normalise; "
                "from mtdi.runtime import Runner; m = json.load(open('projects/host-health/project.json')); "
                "m['profile'] = 'edge'; p = normalise(m); p['_dir'] = 'projects/host-health'; "
                "r = Runner(p, start=False); r.ask('status?'); print('mtdi.bot' in sys.modules)")
        out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(out.stdout.strip(), "False", out.stderr)

    def test_manifest_field(self):
        self.assertEqual(normalise(MANIFEST)["profile"], "hybrid")
        m = copy.deepcopy(MANIFEST)
        m["profile"] = "research"
        self.assertEqual(normalise(m)["profile"], "research")
        m["profile"] = ["research"]
        with self.assertRaises(ManifestError):
            normalise(m)
        m["profile"] = "telepathy"
        with self.assertRaises(ManifestError):
            normalise(m)


if __name__ == "__main__":
    unittest.main()
