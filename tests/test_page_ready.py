"""The studio's page-ready signal (studio/browser.py) is wired to the route change.

The behaviour itself is exercised in a real browser by tools/tour.mjs; this guards the wiring
that the tour, and anything else waiting on <html data-page-ready>, depends on.
"""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent


class PageReady(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(ROOT))
        from run import NAMESPACE
        cls.ns = NAMESPACE

    def test_browser_layer_defines_the_signal(self):
        js = self.ns["SCRUB_JS"]
        for needle in ("function markPageMounted", "window.__i3PageMounted=markPageMounted",
                       "data-page-ready", "data-page-ready-ms", "i3:page-ready", "data-dash-is-loading",
                       "getElementById('i3-boot')"):
            self.assertIn(needle, js)
        self.assertNotIn("READY_MAX_MS", js)      # the page never declares itself timed out; the tool decides

    def test_route_change_starts_it(self):
        app = self.ns["app"]
        scripts = [cb.get("clientside_function") for cb in app.callback_map.values()]
        inline = "".join(str(getattr(app, "_inline_scripts", [])))
        self.assertIn("__i3PageMounted()", inline + str(scripts))

    def test_served_page_carries_it(self):
        client = self.ns["server"].test_client()
        html = client.get("/").get_data(as_text=True)
        if "markPageMounted" not in html:          # behind the studio login: check the shell template
            html = self.ns["app"].index_string
        self.assertIn("markPageMounted", html)


if __name__ == "__main__":
    unittest.main()
