"""The one-command installer and `mtdi doctor`."""
import os
import pathlib
import shutil
import subprocess
import unittest

from mtdi import __main__ as cli
from mtdi import doctor
from mtdi.project import load

ROOT = pathlib.Path(__file__).resolve().parent.parent


class Doctor(unittest.TestCase):
    def test_this_machine_passes(self):
        results = doctor.run(quick=True)
        self.assertEqual([r for r in results if r[1] == "fail"], [])
        self.assertTrue({"python", "packages", "engine", "studio"} <= {r[0] for r in results})

    def test_speed_reports_ms(self):
        name, status, detail = doctor.check_speed(channels=8, packets=50)
        self.assertEqual(name, "speed")
        self.assertIn(status, ("ok", "warn"))
        self.assertIn("ms per snapshot at 8 channels", detail)

    def test_a_crashing_check_is_a_failure_not_a_crash(self):
        def check_boom():
            raise RuntimeError("boom")
        saved = doctor.CHECKS
        doctor.CHECKS = (check_boom,)
        try:
            self.assertEqual(doctor.run(), [("boom", "fail", "RuntimeError: boom")])
        finally:
            doctor.CHECKS = saved


class Cli(unittest.TestCase):
    def test_studio_options_pass_through(self):
        self.assertEqual(cli._studio_argv(["studio", "--port", "9000", "--lan"]), ["--port", "9000", "--lan"])
        self.assertIsNone(cli._studio_argv(["doctor"]))

    def test_bundled_projects_load_from_any_folder(self):
        here = os.getcwd()
        os.chdir(ROOT.anchor)
        try:
            self.assertEqual(load("projects/host-health")["project"]["id"], "host-health")
        finally:
            os.chdir(here)


@unittest.skipUnless(shutil.which("bash"), "needs bash")
class InstallScript(unittest.TestCase):
    def test_syntax_and_help(self):
        script = ROOT / "install.sh"
        self.assertTrue(os.access(script, os.X_OK))
        subprocess.run(["bash", "-n", str(script)], check=True)
        out = subprocess.run(["bash", str(script), "--help"], capture_output=True, text=True, check=True).stdout
        self.assertIn("--autostart", out)
        self.assertIn("--uninstall", out)

    def test_unknown_option_is_refused(self):
        res = subprocess.run(["bash", str(ROOT / "install.sh"), "--nope"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 2)

    def test_piped_uninstall_never_touches_the_current_folder(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            here = pathlib.Path(d, "lookalike")
            for sub in (".venv",):            # run.py alone is not an MTDI checkout
                (pathlib.Path(d, "runonly") / sub).mkdir(parents=True)
            pathlib.Path(d, "runonly", "run.py").write_text("")
            for sub in ("mtdi", ".venv"):
                (here / sub).mkdir(parents=True)
            (here / "run.py").write_text("")
            env = dict(os.environ, HOME=str(pathlib.Path(d, "home")), MTDI_HOME=str(pathlib.Path(d, "home", "mtdi")))
            with open(ROOT / "install.sh", "rb") as script:
                subprocess.run(["bash", "-s", "--", "--uninstall"], stdin=script, cwd=here, env=env,
                               capture_output=True, check=True)
            self.assertTrue((here / ".venv").is_dir())
            runonly = pathlib.Path(d, "runonly")              # the script as a file beside a stray run.py
            shutil.copy(ROOT / "install.sh", runonly / "install.sh")
            subprocess.run(["bash", str(runonly / "install.sh"), "--uninstall"], env=env, capture_output=True, check=True)
            self.assertTrue((runonly / ".venv").is_dir())


class LocalModel(unittest.TestCase):
    def probe(self, body):
        import io
        from unittest import mock
        response = mock.MagicMock()
        response.__enter__.return_value = io.BytesIO(body)
        with mock.patch("urllib.request.urlopen", return_value=response):
            return doctor.check_local_model()

    def test_ollama_without_a_model_is_a_warning(self):
        self.assertEqual(self.probe(b'{"models": []}')[1], "warn")

    def test_empty_ollama_with_a_cloud_key_is_ready(self):
        from unittest import mock
        with mock.patch.dict(os.environ, {"GROQ_API_KEY": "x"}):
            self.assertEqual(self.probe(b'{"models": []}')[1], "ok")

    def test_ollama_with_a_model_is_ready(self):
        name, status, detail = self.probe(b'{"models": [{"name": "llama3.2:3b"}]}')
        self.assertEqual(status, "ok")
        self.assertIn("llama3.2:3b", detail)


if __name__ == "__main__":
    unittest.main()
