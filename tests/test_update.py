"""`mtdi update` against real git repositories: a remote and an installed clone."""
import pathlib
import shutil
import subprocess
import tempfile
import unittest

from mtdi import update


def sh(cwd, *args):
    subprocess.run(args, cwd=cwd, check=True, capture_output=True)


def commit(repo, name, text, message="change"):
    pathlib.Path(repo, name).write_text(text)
    sh(repo, "git", "add", name)
    sh(repo, "git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", message)


class Ran:
    """Stands in for subprocess.run: records commands, succeeds."""
    def __init__(self):
        self.calls = []

    def __call__(self, cmd, **_):
        self.calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0)


@unittest.skipUnless(shutil.which("git"), "needs git")
class Update(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = pathlib.Path(tmp.name)
        self.upstream = self.tmp / "upstream"
        self.upstream.mkdir()
        sh(self.upstream, "git", "init", "-q", "-b", "main")
        commit(self.upstream, "pyproject.toml", "deps = 1\n")
        commit(self.upstream, "README.md", "v1\n")
        self.install = self.tmp / "mtdi"
        sh(self.tmp, "git", "clone", "-q", str(self.upstream), str(self.install))
        self.home = self.tmp / "home"
        self.home.mkdir()

    def head(self):
        return subprocess.run(["git", "-C", str(self.install), "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()

    def test_up_to_date_does_nothing(self):
        out = update.update(self.install, run=Ran(), home=self.home)
        self.assertTrue(out[0].startswith("MTDI is up to date"))

    def test_check_only_reports_without_pulling(self):
        before = self.head()
        commit(self.upstream, "README.md", "v2\n")
        out = update.update(self.install, check_only=True, run=Ran(), home=self.home)
        self.assertIn("1 new commit", out[0])
        self.assertEqual(self.head(), before)

    def test_code_only_update_pulls_and_skips_pip(self):
        commit(self.upstream, "README.md", "v2\n")
        ran = Ran()
        out = update.update(self.install, run=ran, home=self.home)
        self.assertEqual((self.install / "README.md").read_text(), "v2\n")
        self.assertIn("packages unchanged", out)
        self.assertEqual(ran.calls, [])

    def test_dependency_change_reinstalls_into_a_venv_only(self):
        commit(self.upstream, "pyproject.toml", "deps = 2\n")
        ran = Ran()
        out = update.update(self.install, run=ran, home=self.home)
        in_venv = update.sys.prefix != update.sys.base_prefix
        if in_venv:
            self.assertIn("packages reinstalled", out)
            self.assertIn("pip", ran.calls[0])
        else:                                   # system Python: say what to run, never pip into it
            self.assertTrue(any("pip install -e" in line for line in out))
            self.assertEqual(ran.calls, [])

    def test_your_projects_survive_and_edited_mtdi_files_stop_the_update(self):
        (self.install / "projects").mkdir()
        (self.install / "projects" / "mine.json").write_text("{}")
        commit(self.upstream, "README.md", "v2\n")
        update.update(self.install, run=Ran(), home=self.home)
        self.assertTrue((self.install / "projects" / "mine.json").exists())
        (self.install / "README.md").write_text("my edit\n")
        commit(self.upstream, "README.md", "v3\n")
        with self.assertRaisesRegex(update.UpdateError, "README.md"):
            update.update(self.install, run=Ran(), home=self.home)
        self.assertEqual((self.install / "README.md").read_text(), "my edit\n")

    def test_local_commits_are_refused_not_merged(self):
        commit(self.install, "local.txt", "mine\n")
        commit(self.upstream, "README.md", "v2\n")
        with self.assertRaisesRegex(update.UpdateError, "own commits"):
            update.update(self.install, run=Ran(), home=self.home)

    def test_autostart_service_is_restarted(self):
        unit = self.home / ".config/systemd/user/mtdi-studio.service"
        unit.parent.mkdir(parents=True)
        unit.write_text("")
        commit(self.upstream, "README.md", "v2\n")
        ran = Ran()
        out = update.update(self.install, run=ran, home=self.home)
        self.assertIn("studio service restarted", out)
        self.assertEqual(ran.calls[-1], ["systemctl", "--user", "restart", "mtdi-studio.service"])

    def test_not_a_checkout_is_a_clear_error(self):
        plain = self.tmp / "plain"
        plain.mkdir()
        with self.assertRaisesRegex(update.UpdateError, "not a git checkout"):
            update.update(plain, run=Ran(), home=self.home)


if __name__ == "__main__":
    unittest.main()
