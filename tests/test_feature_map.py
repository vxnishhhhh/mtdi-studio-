"""P-01: every mtdi CLI command and studio API route is listed in studio/features.json with where
the owner uses it in the studio, why it stays hidden, or what is still missing."""
import json
import os
import pathlib
import re
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("STUDIO_HTTPS_PORT", "0")
FEATURES = json.loads((ROOT / "studio" / "features.json").read_text(encoding="utf-8"))


def cli_commands():
    out = subprocess.run([sys.executable, "-m", "mtdi", "-h"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return set(re.search(r"\{([a-z,]+)\}", out).group(1).split(","))


class FeatureMap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from run import NAMESPACE
        cls.client = NAMESPACE["server"].test_client()
        cls.routes = {r.rule for r in NAMESPACE["server"].url_map.iter_rules() if r.rule.startswith("/api/")}
        cls.source = "".join(p.read_text(encoding="utf-8") for p in (ROOT / "studio").glob("*.py"))

    def test_every_cli_command_is_listed(self):
        self.assertEqual(set(FEATURES["cli"]), cli_commands())

    def test_every_api_route_is_listed(self):
        self.assertEqual(set(FEATURES["routes"]), self.routes)

    def test_each_entry_says_studio_hidden_or_missing(self):
        for group in ("cli", "routes"):
            for name, entry in FEATURES[group].items():
                self.assertEqual(len(entry), 1, name)
                kind, words = next(iter(entry.items()))
                self.assertIn(kind, ("studio", "hidden", "missing"), name)
                self.assertTrue(words.strip(), name)

    def test_each_studio_entry_names_a_real_control(self):
        for group in ("cli", "routes"):
            for name, entry in FEATURES[group].items():
                if "studio" in entry:
                    self.assertIn(entry["studio"], self.source, f"{name}: no '{entry['studio']}' in the studio")

    def test_the_system_check_runs_from_settings(self):
        from run import NAMESPACE
        page = json.dumps(NAMESPACE["PAGES"]["/settings"]().to_plotly_json(), default=lambda o: o.to_plotly_json())
        reply = self.client.get("/api/system-check")
        self.assertEqual(reply.status_code, 200)
        data = reply.get_json()
        self.assertTrue(data["doctor"] and data["targets"] and data["integrations"] and data["modules"])
        self.assertTrue({"python", "engine"} <= {row["name"] for row in data["doctor"]})
        self.assertIn("arduino-uno", {row["target"] for row in data["targets"]})
        self.assertIn("fetch('/api/system-check'", self.client.get("/").get_data(as_text=True))
        self.assertIn("SYSTEM CHECK", page)
        self.assertIn("data-i3-system-check", page)


if __name__ == "__main__":
    unittest.main()
