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

# Which surface must show each key. Brand, nav, boot and intro live in the shell. Channel words show
# offline on page 1 (tabs, axis titles) and Home (channel 3's card); the channel 2 and 3 units are
# read by the browser layer, so their surface is the served window.I3_WORDS. Channel 3's x unit only
# shows once a sweep is fed ("fed": channel 3's chart after one), the report words in the PDF report.
SURFACES = {"brand.": "layout", "nav.": "layout", "intro.": "layout", "boot.": "boot",
            "home.": "/", "page1.": "/page-1", "page2.": "/page-2", "mtdi.": "/mtdi",
            "page3.": "/page-3", "settings.": "/settings",
            "ch1.name": "/page-1", "ch2.name": "/page-1", "ch3.name": "/", "ch1.unit": "/page-1",
            "ch2.unit": "words", "ch3.unit": "words", "ch3.axis_unit": "fed", "report.": "report"}


def surface_for(key):
    if key in SURFACES:
        return SURFACES[key]
    return next(s for p, s in SURFACES.items() if p.endswith(".") and key.startswith(p))

RENDER = r'''
import json, os, sys
sys.path.insert(0, os.getcwd())
import plotly.utils
from run import NAMESPACE as ns
dump = lambda c: json.dumps(c, cls=plotly.utils.PlotlyJSONEncoder)
ui = sys.modules["studio.ui"]
out = {"layout": dump(ns["app"].layout), "boot": ui.boot_html(), "words": ui.words_script()}
out.update({path: dump(build()) for path, build in ns["PAGES"].items()})
out["report"] = json.dumps(sys.modules["studio.reports"]._gather_report_blocks(row_cap=3), default=str)
s3, fig = ns["sweep3_data"], ns["fig_sweep3"]
radio = fig([88.0e6, 98.0e6, 108.0e6], [-60.0, -30.0, -60.0], [], [], -60.0)    # the radio's own sweep
ns["feed_ch3"]([1.0, 2.0, 3.0, 4.0, 5.0], [1.0, 4.0, 2.0, 6.0, 1.0], source="TEST")
fed = fig(s3["freqs"], s3["levels"], s3["maxhold"], s3["peaks"], s3["floor"])
out["fed"] = dump(fed)
out["sweeps"] = {"radio_x": list(radio.data[-1].x), "radio_hover": radio.data[-1].hovertemplate,
                 "radio_shapes": sum(shape.type == "rect" for shape in radio.layout.shapes),   # the bands, not the floor line
                 "fed_x": list(fed.data[0].x), "fed_shapes": len(fed.layout.shapes),
                 "axes": [radio.layout.xaxis.title.text, fed.layout.xaxis.title.text, fed.layout.yaxis.title.text],
                 "bands": [p["band"] for p in s3["peaks"]], "at": ns["_ch3_at"](2.0),
                 "span": ns["_ch3_span"](1.0, 5.0),
                 "bar_rows": list(ns["fig_ch3_bands"](s3["peaks"]).data[0].y)}
# the channel charts (slice 4): each built with data and empty, so both states are read
xyz = [(1.0, 2.0, 2.0), (2.0, 1.0, 2.0), (2.0, 2.0, 1.0)] * 4
hist = [1.0, 2.0, 3.0, 2.0, 1.0, 2.0, 3.0, 4.0, 3.0, 2.0]
rows = [[1.0, 2.0, 3.0, 4.0, 5.0], [2.0, 3.0, 4.0, 5.0, 6.0]]
charts = {
    "axis": ns["fig_axis"](xyz), "bar": ns["fig_bar"](1.0, 2.0, 3.0), "gauge": ns["fig_gauge"](None),
    "terrain": ns["fig_3d_terrain"](xyz), "plane": ns["fig_3d_error_plane"](xyz),
    "dipole": ns["fig_3d_dipolch2f"](xyz), "c2gauge": ns["fig_c2_gauge"](None),
    "basebar": ns["fig_c2_basebar"](1.0, 2.0, 3.0), "corr": ns["fig_c2_b_correlation"](hist, hist),
    "proxy": ns["fig_c2_induction_proxy"](hist, hist), "overlay": ns["fig_p1_overlay"](hist, hist),
    "normalised": ns["fig_p1_normalized_overlay"](hist, hist),
    "vectors": ns["fig_p1_vector_overlay_3d"](xyz, xyz), "cross": ns["fig_p1_cross_proxy_3d"](xyz, xyz),
    "trajectory": ns["fig_p1_trajectory_3d"](hist, hist), "trajectory_empty": ns["fig_p1_trajectory_3d"]([], []),
    "sweep": fed, "waterfall": ns["fig_waterfall"](rows, s3["freqs"]), "trend": ns["fig_ch3_trend"](hist),
    "focus_empty": ns["fig_focus_bands"]({}), "ch3_terrain": ns["fig_ch3_terrain"](rows, s3["freqs"]),
    "ch3_terrain_empty": ns["fig_ch3_terrain"]([], []),
}
out["charts"] = {name: dump(fig) for name, fig in charts.items()}
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
            text = path.read_text(encoding="utf-8")
            used |= set(re.findall(r"""\bT\(["']([a-z0-9_.]+)["']\)""", text))      # Python
            used |= set(re.findall(r"__i3Word\('([a-z0-9_.]+)'", text))             # the browser layer
        keys = set(content.defaults())
        self.assertEqual(sorted(used - keys), [], "T() keys missing from default.json")
        self.assertEqual(sorted(keys - used), [], "default.json keys nothing uses")
        for key in keys:
            self.assertTrue(surface_for(key), f"{key}: no surface to check it on")


class SecondContentFile(unittest.TestCase):
    """The backlog check: render the studio with a second content file, find its words on every page."""

    def test_every_word_lands_on_its_page(self):
        words = {key: f"Zq{i:03d}word" for i, key in enumerate(sorted(content.defaults()))}
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d, "words.json")
            path.write_text(json.dumps(words), encoding="utf-8")
            # a fresh home: an empty archive, as on a new install and in CI (the report must build from nothing)
            env = dict(os.environ, MTDI_CONTENT=str(path), STUDIO_HTTPS_PORT="0", HOME=d)
            res = subprocess.run([sys.executable, "-c", RENDER], cwd=ROOT, env=env,
                                 capture_output=True, text=True, timeout=300)
        self.assertEqual(res.returncode, 0, res.stderr[-2000:])
        rendered = json.loads(res.stdout.strip().splitlines()[-1])
        for page in ("/", "/page-1", "/page-2", "/mtdi", "/page-3", "/settings"):
            self.assertIn(page, rendered)
        for key, word in words.items():
            surface = surface_for(key)            # headings upper-case some words, so compare without case
            self.assertIn(word.lower(), rendered[surface].lower(), f"{key} not shown on {surface}")
        # Channel 3 (slice 3): a radio sweep stays in MHz with its services shaded; a fed sweep keeps
        # its own x, in the content file's unit, with no radio band names on its peaks.
        sw, xu, lu = rendered["sweeps"], words["ch3.axis_unit"], words["ch3.unit"]
        self.assertEqual(sw["radio_x"], [88.0, 98.0, 108.0])
        self.assertIn(" MHz · ", sw["radio_hover"])
        self.assertIn(lu, sw["radio_hover"])
        self.assertGreater(sw["radio_shapes"], 0)
        self.assertEqual(sw["fed_x"], [1.0, 2.0, 3.0, 4.0, 5.0])
        self.assertEqual(sw["fed_shapes"], 1)                 # the noise floor line only, no radio bands
        self.assertTrue(sw["bands"] and all(b == "—" for b in sw["bands"]))
        self.assertEqual(sw["at"], f"2 {xu}")
        self.assertEqual(sw["span"], f"1 – 5 {xu}")
        self.assertEqual(sw["axes"], ["MHz", xu, lu])                  # the sweep chart titles its own axes
        self.assertEqual(len(set(sw["bar_rows"])), len(sw["bar_rows"]))   # one row per peak, by position
        # the channel charts say what they plot, in the project's words: no placeholder and no bare "unit"
        placeholder = re.compile(r'"(Text|TEXT|Title|Label|LABEL)"|\bunit\b')
        for name, chart in rendered["charts"].items():
            self.assertIsNone(placeholder.search(chart), f"{name}: {placeholder.search(chart)}")
        n1, n2 = words["ch1.name"], words["ch2.name"]
        for name in ("plane", "corr", "proxy", "overlay", "normalised", "vectors", "trajectory"):
            self.assertIn(n1.lower(), rendered["charts"][name].lower(), name)   # some say it in capitals
        for name in ("corr", "proxy", "overlay", "normalised", "vectors", "trajectory"):
            self.assertIn(n2, rendered["charts"][name], name)
        self.assertIn(words["ch1.unit"], rendered["charts"]["overlay"])
        self.assertIn(words["ch2.unit"], rendered["charts"]["overlay"])
        self.assertIn(words["ch3.unit"], rendered["charts"]["waterfall"])
        # the archive headings carry the channel names, and the bound report still marks them raw
        report = json.loads(rendered["report"])
        heads = [b[1] for b in report if b[0] == "h" and "ARCHIVE" in b[1]]
        self.assertEqual(heads, [f"{words['ch1.name'].upper()} SIGNAL ARCHIVE   RAW DIAGNOSTICS",
                                 f"{words['ch3.name'].upper()} PEAK ARCHIVE   RAW DIAGNOSTICS"])


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


class ChannelWords(unittest.TestCase):
    """The studio's three channels take their names and units from the project (S1-06 slice 2)."""

    def project(self, studio=None):
        from mtdi.project import normalise
        return normalise({"project": {"id": "g"}, "sources": [{"id": "s", "adapter": "http"}],
                          "channels": [{"id": "air", "label": "Air temperature", "keys": ["T"], "unit": "°C", "noise_floor": 0.1},
                                       {"id": "soil", "label": "Soil moisture", "keys": ["M"], "unit": "%", "noise_floor": 0.1},
                                       {"id": "bare", "keys": ["B"], "noise_floor": 0.1}],
                          **({"studio": studio} if studio else {})})

    def test_words_follow_the_studio_mapping_and_skip_empty_units(self):
        from mtdi.bridge import words_for
        words = words_for(self.project())
        self.assertEqual(words["ch1.name"], "Air temperature")
        self.assertEqual(words["ch1.unit"], "°C")
        self.assertEqual(words["ch2.unit"], "%")
        self.assertNotIn("ch3.unit", words)                       # no unit given: the studio keeps its default
        self.assertEqual(words["ch3.axis_unit"], "sample")        # channel 3 is fed as its recent history
        swapped = words_for(self.project(studio={"ch1": "soil", "ch2": "air"}))
        self.assertEqual((swapped["ch1.name"], swapped["ch2.unit"]), ("Soil moisture", "°C"))

    def test_the_bridge_labels_fed_samples_with_the_project_unit(self):
        from mtdi.bridge import StudioBridge
        from mtdi.engine import Engine
        calls = []
        feeds = {"feed_ch1": lambda v, **kw: calls.append(("ch1", kw)),
                 "feed_ch2": lambda v, **kw: calls.append(("ch2", kw)),
                 "feed_ch3": lambda x, y, **kw: calls.append(("ch3", kw))}
        bridge = StudioBridge(Engine(self.project()), feeds)
        bridge.push({"ch1": [21.0], "ch2": 40.0})
        self.assertEqual(dict(calls)["ch1"]["unit"], "°C")
        self.assertEqual(dict(calls)["ch2"]["unit"], "%")

    def test_the_bridge_sends_units_over_http_too(self):
        from mtdi.bridge import StudioBridge
        from mtdi.engine import Engine
        sent = {}

        class Response:
            status = 200
            def read(self): return b"{\"ok\": true}"
            def __enter__(self): return self
            def __exit__(self, *a): return False

        def fake_open(request, timeout=None):
            sent.update(json.loads(request.data))
            return Response()
        bridge = StudioBridge(Engine(self.project()), "http://127.0.0.1:9")
        with mock.patch("urllib.request.urlopen", fake_open):
            bridge.push({"ch2": 40.0})
        self.assertEqual(sent["samples"][0]["unit"], {"ch1": "°C", "ch2": "%"})

    def test_channel_2_axis_shows_the_fed_unit_and_keeps_the_adc_labels(self):
        sys.path.insert(0, str(ROOT))
        from run import NAMESPACE
        unit = NAMESPACE["ch2_axis_unit"]
        self.assertEqual(unit({"unit": "%"}), "%")
        self.assertEqual(unit({"unit": "mV RMS relative"}), "mV RMS")     # feed default: no unit was given
        self.assertEqual(unit({}), "mV RMS")
        self.assertEqual(unit({"data_source": "ARDUINO_UNO_USB"}), "ADC counts RMS")


class SlotWords(unittest.TestCase):
    def setUp(self):
        content.reset()
        self.addCleanup(content.reset)
        sys.path.insert(0, str(ROOT))
        from run import NAMESPACE
        self.slot_words = NAMESPACE["_slot_words"]

    def test_defaults_leave_engine_messages_unchanged(self):
        self.assertEqual(self.slot_words("Recommended: run channel 1 recalibration"),
                         "Recommended: run channel 1 recalibration")

    def test_one_pass_never_renames_a_word_twice(self):
        content.use({"ch1.name": "Channel 2", "ch2.name": "Soil"})
        self.assertEqual(self.slot_words("Channel 1 then channel 2"), "Channel 2 then soil")


class HeroWordsAreText(unittest.TestCase):
    """Project words reach the page as text, never as markup (CWE-79)."""

    def test_scrub_hero_never_puts_configured_words_through_innerhtml(self):
        js = (ROOT / "studio" / "ui.py").read_text(encoding="utf-8")
        self.assertNotRegex(js, r"innerHTML\s*=[^;]*dataset\.i3(Title|Tagline)")
        self.assertIn("h1.textContent=hero.dataset.i3Title", js)
        self.assertIn("para.textContent=hero.dataset.i3Tagline", js)

    def test_judge_tiles_escape_label_and_unit(self):
        js = (ROOT / "studio" / "ui.py").read_text(encoding="utf-8")
        self.assertIn("<div class=\"k\">'+h(k)+'</div>", js)
        self.assertIn("'<small>'+h(unit)+'</small>'", js)

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
