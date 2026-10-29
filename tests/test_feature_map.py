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

    def _projects_copy(self):
        import shutil
        import tempfile
        from unittest import mock
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        shutil.copytree(ROOT / "projects" / "_template", pathlib.Path(tmp.name) / "projects" / "_template")
        patch = mock.patch("mtdi.project.__file__", str(pathlib.Path(tmp.name) / "mtdi" / "project.py"))
        patch.start()
        self.addCleanup(patch.stop)
        from run import NAMESPACE
        local = mock.patch.dict(NAMESPACE["RUNTIME"], {"host": "127.0.0.1", "public_tunnel": False})
        local.start()   # the studio as run on this machine; the LAN case is tested on its own
        self.addCleanup(local.stop)
        return pathlib.Path(tmp.name) / "projects"

    def test_a_new_project_is_created_from_settings(self):
        from mtdi.project import load
        from run import NAMESPACE
        page = json.dumps(NAMESPACE["PAGES"]["/settings"]().to_plotly_json(), default=lambda o: o.to_plotly_json())
        self.assertIn("data-i3-new-create", page)
        folder = self._projects_copy()
        data = self.client.post("/api/project-new", json={"id": "bench-rig", "name": "Bench Rig"}).get_json()
        self.assertEqual(data, {"ok": True, "id": "bench-rig", "path": "projects/bench-rig/project.json"})
        made = load(folder / "bench-rig")
        self.assertEqual((made["project"]["id"], made["project"]["name"]), ("bench-rig", "Bench Rig"))
        again = self.client.post("/api/project-new", json={"id": "bench-rig"}).get_json()
        self.assertFalse(again["ok"])
        self.assertIn("already exists", again["error"])
        self.assertNotIn(str(folder), again["error"])   # the server's folders stay private
        named = self.client.post("/api/project-new", json={"id": "no-name"}).get_json()
        self.assertTrue(named["ok"])
        self.assertEqual(load(folder / "no-name")["project"]["name"], "No Name")

    def test_a_bad_new_project_is_refused_not_raised(self):
        folder = self._projects_copy()
        shapes = [None, [], {}, 7, -1, 0, 10**400, True, "", " ", [None], {"a": None}]
        bad_ids = shapes + ["x", "A-b", "../x", "x/../y", "-x", "a" * 49, "_template", "a b", "a\nb"]
        bad_names = [n for n in shapes if n is not None and n != "" and n != " "] + ["a" * 81, "a\nb", "a\x7fb"]
        for pid in bad_ids:
            reply = self.client.post("/api/project-new", json={"id": pid})
            self.assertEqual(reply.status_code, 200, pid)
            self.assertFalse(reply.get_json()["ok"], pid)
        for name in bad_names:
            reply = self.client.post("/api/project-new", json={"id": "ok-id", "name": name})
            self.assertEqual(reply.status_code, 200, name)
            self.assertFalse(reply.get_json()["ok"], name)
        for body in ("[]", '"x"', "7", "null", "{not json"):
            reply = self.client.post("/api/project-new", data=body, content_type="application/json")
            self.assertEqual(reply.status_code, 400, body)
        self.assertEqual(sorted(p.name for p in folder.iterdir()), ["_template"])   # nothing half-made

    def test_a_disk_error_is_reported_and_cleaned_up(self):
        import shutil
        from unittest import mock
        folder = self._projects_copy()
        real = shutil.copytree

        def half_copy(src, dst, **kw):
            real(src, dst, **kw)
            raise PermissionError(13, "Permission denied")
        with mock.patch("mtdi.project.shutil.copytree", half_copy):
            data = self.client.post("/api/project-new", json={"id": "no-disk"}).get_json()
        self.assertFalse(data["ok"])
        self.assertIn("could not write", data["error"])
        self.assertFalse((folder / "no-disk").exists())

        def windows_copy(src, dst, **kw):   # shutil.Error text carries repr()-escaped absolute paths
            raise shutil.Error([(r"C:\\srv\\projects\\_template\\a", r"C:\\srv\\projects\\x\\a", "denied")])
        with mock.patch("mtdi.project.shutil.copytree", windows_copy):
            data = self.client.post("/api/project-new", json={"id": "win-copy"}).get_json()
        self.assertTrue(data["error"].endswith(": the template could not be copied"), data["error"])
        self.assertNotIn("srv", data["error"])
        self.assertNotIn(str(folder), data["error"])
        (folder / "theirs").mkdir()
        (folder / "theirs" / "keep.txt").write_text("someone else's", encoding="utf-8")
        with mock.patch("pathlib.Path.stat", side_effect=FileNotFoundError(2, "gone")):   # made after the check: a race
            data = self.client.post("/api/project-new", json={"id": "theirs"}).get_json()
        self.assertIn("already exists", data["error"])
        self.assertTrue((folder / "theirs" / "keep.txt").exists())    # their folder is left alone
        with mock.patch("pathlib.Path.stat", side_effect=PermissionError(13, "Permission denied")):
            data = self.client.post("/api/project-new", json={"id": "no-look"}).get_json()
        self.assertFalse(data["ok"])
        self.assertIn("could not check", data["error"])

    def test_an_open_lan_studio_does_not_create_projects(self):
        from unittest import mock
        from run import NAMESPACE
        folder = self._projects_copy()
        runtime = NAMESPACE["RUNTIME"]
        clear = {k: "" for k in ("STUDIO_AUTH_USER", "STUDIO_AUTH_PASSWORD_HASH")}
        with mock.patch.dict(runtime, {"host": "0.0.0.0", "access_token": "", "public_tunnel": False}), \
             mock.patch.dict(os.environ, clear):
            reply = self.client.post("/api/project-new", json={"id": "lan-try"})
        self.assertEqual(reply.status_code, 403)
        self.assertIn("without a login", reply.get_json()["error"])
        self.assertFalse((folder / "lan-try").exists())
        token = "t" * 32
        with mock.patch.dict(runtime, {"host": "0.0.0.0", "access_token": token, "public_tunnel": False}), \
             mock.patch.dict(os.environ, clear):
            self.assertEqual(self.client.post("/api/project-new", json={"id": "lan-anon"}).status_code, 401)
            self.client.set_cookie("studio_access", token)
            try:
                data = self.client.post("/api/project-new", json={"id": "lan-ok"}).get_json()
            finally:
                self.client.delete_cookie("studio_access")
        self.assertTrue(data["ok"])
        self.assertFalse((folder / "lan-anon").exists())

    def test_the_https_listener_follows_local_only(self):
        from unittest import mock
        from run import NAMESPACE
        import studio.common as common
        runtime = common.INSTRUMENT_RUNTIME
        cases = [({"host": "127.0.0.1", "public_tunnel": False}, "127.0.0.1"),
                 ({"host": "::1", "public_tunnel": False}, "::1"),
                 ({"host": "127.0.0.1", "public_tunnel": True}, "0.0.0.0"),   # the tunnel hook logs everyone in
                 ({"host": "0.0.0.0", "public_tunnel": False}, "0.0.0.0")]
        for state, address in cases:
            with mock.patch.dict(NAMESPACE["RUNTIME"], state):
                self.assertEqual(runtime.https_bind_address(), address, state)

    def test_the_online_studio_does_not_create_projects(self):
        from unittest import mock
        folder = self._projects_copy()
        with mock.patch.dict(os.environ, {"STUDIO_SERVERLESS": "1"}):
            data = self.client.post("/api/project-new", json={"id": "cloud-try"}).get_json()
        self.assertFalse(data["ok"])
        self.assertIn("mtdi new", data["error"])
        self.assertFalse((folder / "cloud-try").exists())

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

    def test_a_csv_calibration_fits_from_settings(self):
        from run import NAMESPACE
        page = json.dumps(NAMESPACE["PAGES"]["/settings"]().to_plotly_json(), default=lambda o: o.to_plotly_json())
        self.assertIn("CSV CALIBRATION FIT", page)
        self.assertIn("data-i3-csv-fit", page)
        csv = "raw,reference\n100,10.1\n200,19.9\n300,30.2\n400,39.8\n"
        data = self.client.post("/api/calibration-fit", json={"csv": csv}).get_json()
        self.assertTrue(data["ok"], data)
        from mtdi.fusion import Calibration
        expected = Calibration.fit([100, 200, 300, 400], [10.1, 19.9, 30.2, 39.8]).to_dict()
        self.assertAlmostEqual(data["calibration"]["gain"], expected["gain"], places=12)
        self.assertAlmostEqual(data["calibration"]["offset"], expected["offset"], places=12)
        self.assertEqual(data["calibration"]["n"], 4)
        hot = "\ufeffraw,reference,temperature\n1,3,20\n2,5,25\n3,7.5,30\n4,9,22\n"
        data = self.client.post("/api/calibration-fit", json={"csv": hot, "temperature_key": "T"}).get_json()
        self.assertTrue(data["ok"], data)
        self.assertEqual(data["calibration"]["temperature_key"], "T")

    def test_a_short_row_names_its_physical_line(self):
        from mtdi.fusion import fit_csv
        with self.assertRaisesRegex(ValueError, r"line 5 has fewer"):
            fit_csv("raw,reference\n1,2\n\n2,4\n3\n")    # the blank line 3 still counts

    def test_a_bad_csv_is_reported_not_raised(self):
        # Every input a person can paste: the fit is refused with a reason, never a server error.
        good = "raw,reference\n1,2\n2,4\n3,6\n"
        bad_csv = ["", "x,y\n1,2\n", "raw,reference\n1,2\n2,4\n", "raw,reference\n1,2\nx,4\n3,6\n",
                   "raw,reference\n1,2\n2\n3,6\n", "raw,reference\n1,nan\n2,4\n3,6\n",
                   "raw,reference\n1,2\n2,inf\n3,6\n", "raw,reference\n1e400,2\n2,4\n3,6\n",
                   "raw,reference\n" + "9" * 400 + ",2\n2,4\n3,6\n", "raw,reference\n1,2\n1,4\n1,6\n",
                   "raw,reference,temperature\n1,2,20\n2,4,20\n3,6,20\n", "raw,reference\n\n\n",
                   "raw,raw,reference\n1,1,2\n2,2,4\n3,3,6\n", "\x00\x00", "raw,reference\n" + "1,2\n" * 100_001,
                   "raw,reference\n1,2,999\n2,4,999\n3,6,999\n", "raw,reference\n1,2\n2,4\n3," + "6" * 200_000 + "\n",
                   "raw,reference\n\"1\n2,4\n3,6\n", "raw,reference,temperature\n1,2,20\n2,4\n3,6,22\n",
                   "raw,reference,note\n1,2,a\n2,4,b\n3,60,\"x\n4,8,z\n", "raw,reference\n1,2\n2,4\n3,6,\"x\n"]
        for csv in bad_csv:
            reply = self.client.post("/api/calibration-fit", json={"csv": csv, "temperature_key": "T"})
            self.assertEqual(reply.status_code, 200, csv[:40])
            self.assertFalse(reply.get_json()["ok"], csv[:40])
            self.assertTrue(reply.get_json()["error"], csv[:40])
        for extra in ({"temperature_key": "TEMP C"}, {"temp_ref": "nan"}, {"temp_ref": "x"}, {"temp_ref": None},
                      {"temp_ref": 10 ** 400}, {"temp_ref": []}):
            hot = "raw,reference,temperature\n1,3,20\n2,5,25\n3,7.5,30\n4,9,22\n"
            reply = self.client.post("/api/calibration-fit", json={"csv": hot, "temperature_key": "T", **extra})
            self.assertEqual(reply.status_code, 200, extra)
            self.assertFalse(reply.get_json()["ok"], extra)
        for body in ({}, {"csv": 5}, {"csv": None}, [], "x", 7, {"csv": good, "temperature_key": 5},
                     {"csv": good, "temperature_key": ["T"]}, {"csv": "x" * 2_000_001}):
            self.assertEqual(self.client.post("/api/calibration-fit", json=body).status_code, 400, str(body)[:40])

if __name__ == "__main__":
    unittest.main()
