"""S1-02: the integrations registry is complete, honest and wired into the CLI."""
import json
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mtdi import registry  # noqa: E402

SEED = {"github", "vercel", "notion", "matlab", "anthropic", "openai", "gemini", "groq", "xai",
        "elevenlabs", "s3", "coderabbit", "codex", "platformio", "kicad", "ollama"}


class Registry(unittest.TestCase):
    def test_schema_and_seed(self):
        records = registry.load_integrations()
        self.assertTrue(SEED <= {r["id"] for r in records}, SEED - {r["id"] for r in records})
        for r in records:
            self.assertIsInstance(r["env"], list, r["id"])
            self.assertIsInstance(r["risks"], list, r["id"])
            self.assertTrue(r["purpose"] and r["cost"] and r["fallback"], r["id"])

    def test_missing_field_is_rejected(self):
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({"integrations": [{"id": "x"}]}, f)
        with self.assertRaises(ValueError):
            registry.load_integrations(f.name)

    def test_status_is_derived_from_env(self):
        rec = {"env": ["SOME_KEY"]}
        self.assertEqual(registry.status(rec, {}), "not set up")
        self.assertEqual(registry.status(rec, {"SOME_KEY": "x"}), "configured")
        self.assertEqual(registry.status({"env": []}, {}), "available")
        both = {"env": ["A", "B"]}
        self.assertEqual(registry.status(both, {"A": "1"}), "not set up")
        self.assertEqual(registry.status(both, {"A": "1", "B": "2"}), "configured")

    def test_wrong_types_are_rejected(self):
        import tempfile
        rec = dict(registry.load_integrations()[0], env="GITHUB_TOKEN")
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({"integrations": [rec]}, f)
        with self.assertRaises(ValueError):
            registry.load_integrations(f.name)

    def test_missing_file_is_empty(self):
        self.assertEqual(registry.load_integrations(ROOT / "no-such-file.json"), [])

    def test_every_module_imports(self):
        bad = [r for r in registry.check_modules() if not r[2]]
        self.assertEqual(bad, [])

    def test_paid_services_are_flagged(self):
        # Owner rule: nothing paid is on by default; every paid record says so in its cost.
        for r in registry.load_integrations():
            if registry.paid(r):
                self.assertIn("not enabled", r["cost"], r["id"])

    def test_cli_and_describe(self):
        out = subprocess.run([sys.executable, "-m", "mtdi", "registry", "--json"], cwd=ROOT,
                             capture_output=True, text=True, timeout=120)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("huggingface", {r["id"] for r in json.loads(out.stdout)["integrations"]})
        desc = subprocess.run([sys.executable, "-m", "mtdi", "describe"], cwd=ROOT,
                              capture_output=True, text=True, timeout=120)
        reg = json.loads(desc.stdout)["registry"]
        self.assertIn("modules", reg)
        self.assertTrue(all("status" in r and "paid" in r for r in reg["integrations"]))


if __name__ == "__main__":
    unittest.main()
