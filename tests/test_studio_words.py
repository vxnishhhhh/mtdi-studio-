"""Studio words (S1-06): one content file, overridable by MTDI_CONTENT and a project's interface block."""
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from studio import content  # noqa: E402

# Which surface must show each group of keys. Brand, nav, boot and intro live in the shell.
SURFACES = {"brand.": "layout", "nav.": "layout", "intro.": "layout", "boot.": "boot",
            "home.": "/", "page1.": "/page-1", "page2.": "/page-2", "mtdi.": "/mtdi",
            "page3.": "/page-3", "settings.": "/settings"}

RENDER = r'''
import json, os, sys
sys.path.insert(0, os.getcwd())
import plotly.utils
from run import NAMESPACE as ns
dump = lambda c: json.dumps(c, cls=plotly.utils.PlotlyJSONEncoder)
out = {"layout": dump(ns["app"].layout), "boot": sys.modules["studio.ui"].boot_html()}
out.update({path: dump(build()) for path, build in ns["PAGES"].items()})
print(json.dumps(out))
'''


class Content(unittest.TestCase):
    def setUp(self):
        content.reset()
        self.addCleanup(content.reset)

    def test_defaults_resolve_and_unknown_keys_fail_loudly(self):
        self.assertEqual(content.T("nav.home"), "Home")
        with self.assertRaises(KeyError):
            content.T("nav.hmoe")

    def test_project_words_win_over_mtdi_content_which_win_over_defaults(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({"nav.home": "From file", "nav.page1": "File page"}, f)
        self.addCleanup(os.unlink, f.name)
        with mock.patch.dict(os.environ, {"MTDI_CONTENT": f.name}):
            content.reset()
            content.use({"nav.home": "From project"})
            self.assertEqual(content.T("nav.home"), "From project")
            self.assertEqual(content.T("nav.page1"), "File page")
            self.assertEqual(content.T("nav.page2"), "Page 2")

    def test_bad_overrides_name_the_key(self):
        for words, needle in (({"nav.hmoe": "x"}, "nav.hmoe"), ({"nav.home": ""}, "nav.home"),
                              ({"nav.home": 3}, "nav.home"), (["x"], "object")):
            with self.assertRaisesRegex(content.ContentError, needle):
                content.use(words)

    def test_use_refuses_non_objects_and_treats_only_none_as_empty(self):
        for bad in ([], "", 0):
            with self.assertRaisesRegex(content.ContentError, "object"):
                content.use(bad)
        content.use(None)
        self.assertEqual(content.T("nav.home"), "Home")

    def test_a_broken_mtdi_content_file_is_a_clear_error(self):
        with mock.patch.dict(os.environ, {"MTDI_CONTENT": "/nonexistent/words.json"}):
            content.reset()
            with self.assertRaisesRegex(content.ContentError, "MTDI_CONTENT"):
                content.T("nav.home")

    def test_every_key_is_used_and_every_used_key_exists(self):
        used = set()
        for path in (ROOT / "studio").glob("*.py"):
            used |= set(re.findall(r'\bT\("([a-z0-9_.]+)"\)', path.read_text(encoding="utf-8")))
        keys = set(content.defaults())
        self.assertEqual(sorted(used - keys), [], "T() keys missing from default.json")
        self.assertEqual(sorted(keys - used), [], "default.json keys nothing uses")
        for key in keys:
            self.assertTrue(any(key.startswith(p) for p in SURFACES), f"{key}: no surface to check it on")


class SecondContentFile(unittest.TestCase):
    """The backlog check: render the studio with a second content file, find its words on every page."""

    def test_every_word_lands_on_its_page(self):
        words = {key: f"Zq{i:03d}word" for i, key in enumerate(sorted(content.defaults()))}
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d, "words.json")
            path.write_text(json.dumps(words), encoding="utf-8")
            env = dict(os.environ, MTDI_CONTENT=str(path), STUDIO_HTTPS_PORT="0")
            res = subprocess.run([sys.executable, "-c", RENDER], cwd=ROOT, env=env,
                                 capture_output=True, text=True, timeout=300)
        self.assertEqual(res.returncode, 0, res.stderr[-2000:])
        rendered = json.loads(res.stdout.strip().splitlines()[-1])
        for page in ("/", "/page-1", "/page-2", "/mtdi", "/page-3", "/settings"):
            self.assertIn(page, rendered)
        for key, word in words.items():
            surface = next(s for p, s in SURFACES.items() if key.startswith(p))
            self.assertIn(word, rendered[surface], f"{key} not shown on {surface}")


class ManifestInterface(unittest.TestCase):
    def run_check(self, interface):
        manifest = {"project": {"id": "w"}, "sources": [{"id": "s", "adapter": "http"}],
                    "channels": [{"id": "t", "keys": ["T"], "noise_floor": 0.1}], "interface": interface}
        with tempfile.TemporaryDirectory() as d:
            pathlib.Path(d, "project.json").write_text(json.dumps(manifest))
            return subprocess.run([sys.executable, "-m", "mtdi", "check", d], cwd=ROOT,
                                  capture_output=True, text=True, timeout=120)

    def test_mtdi_check_reports_a_typo_in_the_words(self):
        res = self.run_check({"nav.hmoe": "Climate"})
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("nav.hmoe", res.stderr)

    def test_an_interface_that_is_not_an_object_is_refused(self):
        for bad in ([], "", 0, None):
            res = self.run_check(bad)
            self.assertNotEqual(res.returncode, 0, bad)
            self.assertIn("interface must be an object", res.stderr)

    def test_mtdi_check_accepts_known_words(self):
        res = self.run_check({"brand.title": "Greenhouse"})
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("1 studio word(s) set", res.stdout)


class HeroWordsAreText(unittest.TestCase):
    """Project words reach the page as text, never as markup (CWE-79)."""

    def test_scrub_hero_never_puts_configured_words_through_innerhtml(self):
        js = (ROOT / "studio" / "ui.py").read_text(encoding="utf-8")
        self.assertNotRegex(js, r"innerHTML\s*=[^;]*dataset\.i3(Title|Tagline)")
        self.assertIn("h1.textContent=hero.dataset.i3Title", js)
        self.assertIn("para.textContent=hero.dataset.i3Tagline", js)

    def test_boot_title_is_escaped(self):
        from studio import ui
        content.use({"boot.title": "<img src=x onerror=alert(1)>"})
        self.addCleanup(content.reset)
        html = ui.boot_html()
        self.assertNotIn("<img src=x", html)
        self.assertIn("&lt;img src=x onerror=alert(1)&gt;", html)

    def test_skyline_canvas_paints_the_configured_title(self):
        js = (ROOT / "studio" / "ui.py").read_text(encoding="utf-8")
        self.assertNotIn("ctx.fillText('TITLE'", js)
        self.assertIn("scrub.hero.dataset.i3Title", js)


if __name__ == "__main__":
    unittest.main()
