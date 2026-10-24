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


if __name__ == "__main__":
    unittest.main()
