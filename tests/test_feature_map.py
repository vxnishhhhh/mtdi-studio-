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

    def test_offline_mode_never_probes_the_local_ai_url(self):
        from unittest import mock
        from run import NAMESPACE
        offline = NAMESPACE["instrument_offline"]
        NAMESPACE["instrument_offline"] = lambda: True
        try:
            with mock.patch("urllib.request.urlopen") as urlopen:
                rows = self.client.get("/api/system-check").get_json()["doctor"]
        finally:
            NAMESPACE["instrument_offline"] = offline
        self.assertEqual([c for c in urlopen.call_args_list if "/api/tags" in str(c)], [])
        self.assertIn("disk", {row["name"] for row in rows})       # the run went past the local-AI check
        self.assertEqual([r for r in rows if r["name"] == "local AI"],
                         [{"name": "local AI", "status": "skipped", "detail": "offline mode: not probed"}])

    def test_a_key_saved_in_settings_counts_as_set_up_and_is_never_sent(self):
        from run import NAMESPACE
        saved = NAMESPACE["_elevenlabs_key"]
        NAMESPACE["_elevenlabs_key"] = lambda: "sk-secret-value-123456"
        try:
            reply = self.client.get("/api/system-check")
        finally:
            NAMESPACE["_elevenlabs_key"] = saved
        rows = {r["id"]: r["status"] for r in reply.get_json()["integrations"]}
        self.assertEqual(rows["elevenlabs"], "configured")
        self.assertNotIn("sk-secret-value-123456", reply.get_data(as_text=True))

    def test_a_key_saved_in_settings_is_what_nvtra_uses_when_no_local_model(self):
        from unittest import mock
        from run import NAMESPACE
        from mtdi import doctor
        saved, offline = NAMESPACE["_active_ai_credential"], NAMESPACE["instrument_offline"]
        NAMESPACE["_active_ai_credential"] = lambda: ("sk-another-secret-987654", "gemini")
        NAMESPACE["instrument_offline"] = lambda: False
        try:
            with mock.patch.object(doctor, "run", return_value=[("local AI", "warn", "no local model")]):
                reply = self.client.get("/api/system-check")
        finally:
            NAMESPACE["_active_ai_credential"], NAMESPACE["instrument_offline"] = saved, offline
        row = next(r for r in reply.get_json()["doctor"] if r["name"] == "local AI")
        self.assertEqual((row["status"], row["detail"]), ("ok", "no local model; NVTRA uses the gemini key saved in Settings"))
        self.assertNotIn("sk-another-secret-987654", reply.get_data(as_text=True))

    def test_every_bundled_project_checks_from_settings(self):
        from run import NAMESPACE
        page = json.dumps(NAMESPACE["PAGES"]["/settings"]().to_plotly_json(), default=lambda o: o.to_plotly_json())
        self.assertIn("PROJECT CHECK", page)
        self.assertIn("data-i3-project-check", page)
        names = self.client.get("/api/project-check").get_json()["projects"]
        self.assertIn("host-health", names)
        self.assertNotIn("_template", names)
        for name in names:
            data = self.client.get("/api/project-check", query_string={"id": name}).get_json()
            self.assertTrue(data["ok"], name)
            self.assertEqual(data["id"], name)
            self.assertTrue(data["channels"] and data["sources"], name)

    def test_project_check_reads_only_listed_folders(self):
        for wanted in ("../run", "_template", "/etc/passwd", "host-health/../third-eye"):
            self.assertEqual(self.client.get("/api/project-check", query_string={"id": wanted}).status_code, 404, wanted)

    def test_a_bad_manifest_is_reported_not_raised(self):
        import tempfile
        from unittest import mock
        good = json.loads((ROOT / "projects" / "host-health" / "project.json").read_text(encoding="utf-8"))
        broken = {"sources": [None]}, {"project": None}, {"channels": [None]}, {"nvtra": None}, {"nvtra": {"rules": [None]}}
        for change in broken:
            with tempfile.TemporaryDirectory() as tmp:
                folder = pathlib.Path(tmp) / "projects"
                (folder / "broken").mkdir(parents=True)
                (folder / "broken" / "project.json").write_text(json.dumps({**good, **change}), encoding="utf-8")
                with mock.patch("studio.ui.bundled_projects", return_value=["broken"]), \
                     mock.patch("mtdi.project.__file__", str(pathlib.Path(tmp) / "mtdi" / "project.py")):
                    reply = self.client.get("/api/project-check", query_string={"id": "broken"})
            self.assertEqual(reply.status_code, 200, change)
            data = reply.get_json()
            self.assertFalse(data["ok"], change)
            self.assertIn("must be an object", data["error"], change)

    def test_the_line_tester_matches_the_protocol(self):
        ok = self.client.post("/api/parse-line", json={"line": "CH1=512,CH2=498,_T=1200"}).get_json()
        self.assertEqual(ok, {"ok": True, "values": {"CH1": 512.0, "CH2": 498.0, "_T": 1200.0}})
        for line in ("CH1=512,CH2", '{"A": ' + "9" * 400 + "}"):   # the second overflows a float
            reply = self.client.post("/api/parse-line", json={"line": line})
            self.assertEqual(reply.status_code, 200, line)
            self.assertFalse(reply.get_json()["ok"], line)
            self.assertTrue(reply.get_json()["error"], line)
        for body in ({}, {"line": 5}, {"line": "A=1," * 2000}, [], ["CH1=1"], 7, "CH1=1"):
            self.assertEqual(self.client.post("/api/parse-line", json=body).status_code, 400, body)

    def test_mtdi_check_prints_the_same_summary(self):
        import subprocess, sys
        out = subprocess.run([sys.executable, "-m", "mtdi", "check", "projects/host-health"], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout
        data = self.client.get("/api/project-check", query_string={"id": "host-health"}).get_json()
        self.assertIn(f"{data['name']} ({data['id']})", out)
        for ch in data["channels"]:
            self.assertIn(ch["id"], out)
        self.assertTrue(out.rstrip().endswith("OK"))

if __name__ == "__main__":
    unittest.main()
