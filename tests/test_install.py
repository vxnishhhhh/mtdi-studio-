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
    def test_a_console_that_is_not_utf8_gets_question_marks_not_a_crash(self):
        import io
        import sys
        from unittest import mock
        cp1252 = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", newline="\n")    # a Windows console or pipe
        with mock.patch.object(sys, "stdout", cp1252), mock.patch.object(sys, "stderr", cp1252):
            cli._tolerant_output()
            print("\u2713 project")                                   # the line `mtdi create` crashed on
            cp1252.flush()
        self.assertEqual(cp1252.buffer.getvalue(), b"? project\n")

    def test_recording_files_are_closed_when_a_project_stops(self):
        import tempfile
        from mtdi.runtime import Runner
        with tempfile.TemporaryDirectory() as d:
            runner = Runner("projects/host-health", record=pathlib.Path(d, "rec.jsonl"), start=False)
            runner.stop()
            self.assertTrue(runner.engine.recorders[0].stream.closed)

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


# install.sh is for Linux and macOS; on Windows `bash` is usually WSL's launcher, often with no Linux inside.
ON_WINDOWS = os.name == "nt"


@unittest.skipIf(ON_WINDOWS, "install.sh is for Linux and macOS (on Windows MTDI installs inside WSL)")
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

    def test_every_entry_point_ignores_the_current_folder(self):
        text = (ROOT / "install.sh").read_text()
        self.assertNotIn("/bin/python -m mtdi", text)          # each one must pass -P
        self.assertEqual(text.count("-P -m mtdi"), 2)           # launcher and systemd unit
        self.assertIn("<string>-P</string><string>-m</string>", text)

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


def _git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


@unittest.skipIf(ON_WINDOWS, "install.sh is for Linux and macOS (on Windows MTDI installs inside WSL)")
@unittest.skipUnless(shutil.which("bash") and shutil.which("git"), "needs bash and git")
class PinnedInstall(unittest.TestCase):
    """MTDI_REF installs one exact revision (CWE-494: the newest main is not the only choice)."""

    def setUp(self):
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = pathlib.Path(tmp.name)
        self.upstream = self.tmp / "upstream"
        self.upstream.mkdir()
        _git(self.upstream, "init", "-q", "-b", "main")
        self.revs = []
        for text in ("v1\n", "v2\n"):
            (self.upstream / "README.md").write_text(text)
            _git(self.upstream, "add", "README.md")
            _git(self.upstream, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", text.strip())
            self.revs.append(_git(self.upstream, "rev-parse", "HEAD"))
        self.script = self.tmp / "bin" / "install.sh"     # a folder with no run.py: never "this copy"
        self.script.parent.mkdir()
        shutil.copy(ROOT / "install.sh", self.script)
        self.home = self.tmp / "home" / "mtdi"

    def get_code(self, ref=""):
        env = dict(os.environ, MTDI_INSTALL_NO_MAIN="1", MTDI_REPO=self.upstream.as_uri(),     # file://: --depth works as over https
                   MTDI_HOME=str(self.home), MTDI_REF=ref, HOME=str(self.tmp / "home"))
        return subprocess.run(["bash", "-c", f'source "{self.script}" && get_code'], env=env,
                              capture_output=True, text=True, timeout=120)

    def test_a_pinned_install_is_that_revision_and_update_leaves_it(self):
        from mtdi import update
        res = self.get_code(self.revs[0])
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(_git(self.home, "rev-parse", "HEAD"), self.revs[0])
        self.assertEqual((self.home / "README.md").read_text(), "v1\n")
        self.assertIn(f"pinned to {self.revs[0]}", res.stdout)
        with self.assertRaisesRegex(update.UpdateError, "pinned to"):
            update.update(self.home, home=self.tmp / "home")
        self.assertEqual(_git(self.home, "rev-parse", "HEAD"), self.revs[0])

    def test_a_pinned_install_says_so_without_the_network(self):
        from mtdi import update
        self.assertEqual(self.get_code(self.revs[0]).returncode, 0)
        shutil.rmtree(self.upstream)                       # the remote is gone: no fetch can work
        with self.assertRaisesRegex(update.UpdateError, "pinned to"):
            update.update(self.home, check_only=True, home=self.tmp / "home")

    def test_pinning_an_existing_shallow_install_reaches_an_older_revision(self):
        res = self.get_code()                              # the default install: newest, shallow
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(_git(self.home, "rev-parse", "--is-shallow-repository"), "true")
        res = self.get_code(self.revs[0])
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual((self.home / "README.md").read_text(), "v1\n")

    def test_a_plain_reinstall_follows_main_again(self):
        self.assertEqual(self.get_code(self.revs[0]).returncode, 0)
        res = self.get_code()
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(_git(self.home, "rev-parse", "HEAD"), self.revs[1])
        self.assertEqual(_git(self.home, "symbolic-ref", "--short", "HEAD"), "main")

    def test_an_unknown_revision_stops_with_a_message(self):
        res = self.get_code("no-such-tag")
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("could not check out 'no-such-tag'", res.stderr)


CLOUD_KEYS = ("GROQ_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "XAI_API_KEY")


class LocalModel(unittest.TestCase):
    def setUp(self):                        # a developer's own keys must not change the verdicts below
        from unittest import mock
        patcher = mock.patch.dict(os.environ, {k: v for k, v in os.environ.items() if k not in CLOUD_KEYS}, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def probe(self, body):
        import io
        from unittest import mock
        response = mock.MagicMock()
        response.__enter__.return_value = io.BytesIO(body)
        with mock.patch("urllib.request.urlopen", return_value=response) as opened:
            result = doctor.check_local_model()
        self.url = opened.call_args[0][0] if opened.call_args else None
        return result

    def test_ollama_without_a_model_is_a_warning(self):
        self.assertEqual(self.probe(b'{"models": []}')[1], "warn")

    def test_empty_ollama_with_a_cloud_key_is_ready(self):
        from unittest import mock
        with mock.patch.dict(os.environ, {"GROQ_API_KEY": "x"}):
            self.assertEqual(self.probe(b'{"models": []}')[1], "ok")

    def test_whitespace_key_is_not_a_cloud_model(self):
        from unittest import mock
        with mock.patch.dict(os.environ, {"GROQ_API_KEY": "  "}):
            self.assertEqual(self.probe(b'{"models": []}')[1], "warn")

    def test_probe_uses_the_configured_ollama_host(self):
        from unittest import mock
        with mock.patch.dict(os.environ, {"OLLAMA_HOST": "192.168.1.20:11434"}):
            self.probe(b'{"models": [{"name": "m"}]}')
        self.assertEqual(self.url, "http://192.168.1.20:11434/api/tags")

    def test_model_present_but_local_ai_off_is_a_warning(self):
        from unittest import mock
        env = {k: v for k, v in os.environ.items() if k not in ("OLLAMA_HOST", "MTDI_LOCAL_LLM")}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(self.probe(b'{"models": [{"name": "m"}]}')[1], "warn")

    def test_ollama_with_a_model_is_ready(self):
        from unittest import mock
        with mock.patch.dict(os.environ, {"MTDI_LOCAL_LLM": "1"}):
            name, status, detail = self.probe(b'{"models": [{"name": "llama3.2:3b"}]}')
        self.assertEqual(status, "ok")
        self.assertIn("llama3.2:3b", detail)


if __name__ == "__main__":
    unittest.main()
