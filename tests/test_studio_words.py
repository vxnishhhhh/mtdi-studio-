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
# Page 1's three tabs (slice 6) and its tab bar, before any data (the engine blocks under each tab are checked below, slice 8)
tabs = lambda: dump([ns["ch1_body"](), ns["ch2_body"](), ns["_combined_view_base"](), ns["p1_page"]().children[:5]])
out["tabs"] = {"empty": tabs()}
# Page 2's four views (slice 7) and its tab bar (the engine blocks under the sweep: slice 8, below)
sweep_tabs = ns["sweep3_page"]().children[1].children[3]
peak = {"freq": 100.5e6, "over_floor_db": 12.0, "level_dbfs": -40.0, "band": "FM"}
page2 = lambda: dump([ns["ch3_sweep_body"](), ns["sdr_view"](), ns["wifi_view"](), ns["bluetooth_view"](), sweep_tabs,
                      ns["_sdr_rows"]([]), ns["_sdr_rows"]([peak]), ns["_sdr_detail"]({})])
out["page2"] = {"empty": page2()}
out["report"] = json.dumps(sys.modules["studio.reports"]._gather_report_blocks(row_cap=3), default=str)
s3, fig = ns["sweep3_data"], ns["fig_sweep3"]
radio = fig([88.0e6, 98.0e6, 108.0e6], [-60.0, -30.0, -60.0], [], [], -60.0)    # the radio's own sweep
ns["feed_ch3"]([1.0, 2.0, 3.0, 4.0, 5.0], [1.0, 4.0, 2.0, 6.0, 1.0], source="TEST")
out["page2"]["fed"] = page2()
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
# slice 5: the receiver, scan and reference charts and tables, filled and empty
net = {"ssid": "net", "active": True, "bssid": "aa:bb:cc:dd:ee:ff", "chan": 6, "band": "2.4 GHz",
       "signal": 70, "sec": "WPA2", "mhz": 2437, "dbm": -55}
dev = {"name": "dev", "addr": "11:22:33:44:55:66", "rssi": -60, "vendor": "Acme", "kind": "phone"}
mhz = [100.0e6, 100.5e6, 101.0e6, 101.5e6, 102.0e6]
iq = [0.1, -0.2, 0.3, -0.1, 0.2, 0.0]
charts.update({
    "sdr_slice": ns["fig_sdr_slice"](mhz, [-60, -40, -60, -50, -60], [{"freq": 100.5e6, "level_dbfs": -40}], -60),
    "sdr_fall": ns["fig_sdr_waterfall"](rows, mhz), "sdr_sweep": ns["fig_sdr_sweep"](None),
    "sdr_sweep_full": ns["fig_sdr_sweep"]({"freqs": mhz, "levels_dbfs": [-60] * 5, "floor_dbfs": -60, "peaks": []}),
    "sdr_terrain": ns["fig_sdr_terrain"](rows, mhz), "sdr_terrain_empty": ns["fig_sdr_terrain"]([], []),
    "sdr_iq": ns["fig_sdr_constellation"]([[1, 2], [3, 4]], [-1, 1]), "sdr_iq_empty": ns["fig_sdr_constellation"](None, None),
    "sdr_iq3d": ns["fig_sdr_iq_3d"](iq, iq, 1e-6), "sdr_iq3d_empty": ns["fig_sdr_iq_3d"]([], [], 1e-6),
    "sdr_codes": ns["fig_sdr_codes"]([1] * 256), "sdr_codes_empty": ns["fig_sdr_codes"](None),
    "sdr_env": ns["fig_sdr_envelope"](iq, 1e-6), "sdr_env_empty": ns["fig_sdr_envelope"]([], 1e-6),
    "linefreq_empty": ns["fig_linefreq_spectrogram"](None),
    "repeat": ns["fig_repeatability"]({"readings": [1.0, 1.1, 0.9], "mean": 1.0, "sd": 0.1}),
    "wifi_ch": ns["fig_wifi_channels"]([net]), "wifi_bars": ns["fig_wifi_signal_bars"]([net]),
    "wifi_bars_empty": ns["fig_wifi_signal_bars"]([]), "ble": ns["fig_ble_rssi"]([dev]),
    "ble_empty": ns["fig_ble_rssi"]([]), "ble_vendors": ns["fig_ble_vendors"]([dev]),
    "ble_vendors_empty": ns["fig_ble_vendors"]([]),
    "tables": [ns["_peak_rows"]([], 0), ns["sg_rows"]({}), ns["sg_rows"]({"last_rx": 1, "levels": [1], "level_sane": False}),
               ns["_wifi_rows"]([]), ns["_wifi_rows"]([net]), ns["_bt_rows"]([]), ns["_bt_rows"]([dev]),
               ns["_lan_rows"]([], ""), ns["_dbm_scale"]()],
})
out["charts"] = {name: dump(fig) for name, fig in charts.items()}
flat = {"last_rx": 1, "levels": [-80.0] * 20, "freqs": [100e6 + i * 1e5 for i in range(20)], "floor": -80.0,
        "peaks": [], "level_sane": True, "waterfall": []}
out["quiet"] = [dump(ns["sg_rows"](flat)), dump(ns["sg_rows"](dict(flat, waterfall=[flat["levels"]] * 6)))]
# channel 2 fed with its own unit: its charts take that unit, not the content file's
for v in (1.0, 2.0, 3.0):
    ns["feed_ch2"](v, unit="fedunit", source="TEST")
e2 = dict(ns["ch2f_data"])
u2 = ns["ch2_axis_unit"](e2)
out["ch2_fed"] = {"unit": u2,
    "basebar": dump(ns["fig_c2_basebar"](1.0, 2.0, 3.0, unit=u2)),
    "overlay": dump(ns["fig_p1_overlay"](hist, hist, unit2=u2)),
    "page1": dump([ns["ch2_body"](), ns["_combined_view_base"]()]),   # the tabs that hold these charts
    "callbacks": dump([ns["update_ch2f_charts"](1, None, None), ns["update_p1_overlays"](1, None, None)])}
for v in ([1.0, 2.0, 2.0], [2.0, 1.0, 2.0], [2.0, 2.0, 1.0]):
    ns["feed_ch1"](v, unit="fedunit1", source="TEST")
out["tabs"]["fed"] = tabs()
ns["ch2f_data"]["exyz_history"] = list(xyz)            # a channel 2 vector: its direction charts name channel 2
out["direction2"] = {"tab": dump(ns["update_ch2f_triaxial_3d"](1, None)),
                     "both": dump(ns["update_p1_overlays"](1, None, None))}
ns["ch2f_data"].update(data_source="ARDUINO_UNO_USB", fed_source=None)   # the Uno path: reference mode, not fed
out["tabs"]["reference"] = dump(ns["ch2_view"]())
# the D4 engine blocks (slice 8): every section, then every readout from the live packet, a radio
# sweep, a fed sweep and the repeatability run's three states
d4m, rt = sys.modules["studio.d4"], ns["_d4_runtime"]()
sections = [ns[n]() for n in ("d4_engine_section", "d4_ch1_blocks", "d4_ch2_blocks", "d4_combined_blocks",
                              "d4_sweep3_blocks", "d4_environment_blocks", "d4_validation_blocks", "d4_settings_blocks")]
live = rt.d4.snapshot()
hz = [100.0e6 + i * 0.25e6 for i in range(24)]
dbm = [-80.0] * 24
dbm[8], dbm[16] = -30.0, -45.0
radio3 = dict(d4m.ch3_analysis(hz, dbm), trusted=True, status="sweeping", x_unit=None)
fed3 = dict(d4m.ch3_analysis([float(i) for i in range(1, 25)], dbm), trusted=False, status="TEST",
            x_unit=os.environ["D4_TEST_XU"])
rep = {"result": {"channel": "Channel 1 magnitude", "n": 3, "window_s": 1, "text": "t", "sd": 0.1, "unit": "u", "range": 0.2,
                  "min": 1, "max": 1.2, "rsd_pct": 5, "verdict": "v", "basis": "b", "conditions": "c"}}
render = lambda d: dump([ns["_d4_render"](k, d, rt, "core") for k in ns["D4_BLOCK_META"]] + [ns["_d4_render"]("other", d, rt, "core")])
packet = dict(live, exposure=d4m.exposure_comparison(None, 0.5), fingerprint={"ch1_val": 1, "ch2": 2, "ch3_floor_dbm": -80, "ch3_peak_hz": 1.0e8})
out["d4"] = {"sections": dump(sections), "live": render(live),
             "radio": render(dict(packet, ch3=radio3)), "fed": render(dict(packet, ch3=fed3)),
             "repeat": dump([ns["_d4_render"]("repeat", dict(live, repeat_run=r), rt, "val")
                             for r in ({}, {"running": True, "done": 1, "runs": 3, "label": "c", "window_s": 1}, rep)]),
             "graphs": dump([ns["_d4_graph"](k, live, rt) for k in ("power", "power_ch1", "power_surface", "calibration", "validation", "repeat")])}
out["d4_units"] = {"fed_at": [ns["_fed_at"](v, "mm") for v in (1.000001, 2.5, 0.0, 120.0)],
                   "ch1": ns["ch1_value_unit"](ns["ch1_data"]), "ch1_own": ns["ch1_value_unit"]({})}
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
            env = dict(os.environ, MTDI_CONTENT=str(path), STUDIO_HTTPS_PORT="0", HOME=d,
                       D4_TEST_XU=words["ch3.axis_unit"])
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
        # (a dumped layout names each component's class, "type": "Button"; that is not on-screen text)
        placeholder = re.compile(r'(?<!"type": )"\s*(?:Text|TEXT|Title|TITLE|Label|LABEL|Subtext|SUBTEXT|Button|BUTTON|Heading)\s*"'
                                 r'|Enter your text here|\bunit\b')
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
        self.assertIn(words["ch3.unit"], rendered["charts"]["tables"])     # the level scale reads in the radio's unit
        # a quiet sweep says the new-energy check has not run yet, until 6 sweeps of history exist
        early, settled = rendered["quiet"]
        self.assertIn("starts after 6 sweeps", early)
        self.assertNotIn("starts after", settled)
        # Page 1's tabs (slice 6): every section head, card, button and note says what it shows,
        # in the project's channel words, empty, fed and in channel 2's reference mode
        for state, tab in rendered["tabs"].items():
            self.assertIsNone(placeholder.search(tab), f"Page 1 {state}: {placeholder.search(tab)}")
            for word in (n1, n2, "V/m est."):     # channel 2's probe cards keep the probe's own scale
                self.assertIn(word, tab, f"Page 1 {state}: {word}")
        self.assertIn(words["ch1.unit"], rendered["tabs"]["empty"])
        # the probe's measurement note is for the studio's own probe, never for fed data
        for state, shown in (("empty", True), ("reference", True), ("fed", False)):
            self.assertEqual("reference-scaled estimate" in rendered["tabs"][state], shown, state)
        tab2, both2 = rendered["direction2"]["tab"], rendered["direction2"]["both"]
        self.assertIn(f"{n2.upper()} DIRECTION", tab2)
        self.assertIn(f"dipole field along {n2}", tab2)
        self.assertNotIn(f"{n1.upper()} DIRECTION", tab2)
        for who in (n1.upper(), n2.upper(), "COMPOSITE"):   # the both-channels tab draws all three directions
            self.assertIn(f"{who} DIRECTION", both2, who)
        # Page 2's views (slice 7): every head, card, control, table header and note says what it is
        for state, view in rendered["page2"].items():
            self.assertIsNone(placeholder.search(view), f"Page 2 {state}: {placeholder.search(view)}")
            for word in (words["ch3.name"], words["ch3.unit"]):
                self.assertIn(word.lower(), view.lower(), f"Page 2 {state}: {word}")
        # the radio's guidance is for the radio: a fed sweep is read in its own axes (CodeRabbit, #68)
        self.assertIn("horizontal is frequency", rendered["page2"]["empty"])
        for radio_words in ("horizontal is frequency", "HOW A SWEEP IS TAKEN", "IF THE LEVELS LOOK WRONG"):
            self.assertNotIn(radio_words, rendered["page2"]["fed"], radio_words)
        self.assertIn(words["ch3.axis_unit"], rendered["page2"]["fed"])
        # the D4 engine blocks (slice 8): every card, control and readout says what it is, in the project's
        # channel words; a fed channel 3 sweep is read in its own units, with no radio hertz, dBm or bands
        d4 = rendered["d4"]
        for state, view in d4.items():
            self.assertIsNone(placeholder.search(view), f"D4 {state}: {placeholder.search(view)}")
            self.assertNotIn("Channel 1", view, state)
            self.assertNotIn("CH 3", view, state)
        for word in (n1, n2, words["ch3.name"]):
            self.assertIn(word.lower(), d4["sections"].lower(), word)
            self.assertIn(word, d4["radio"], word)
        self.assertIn(" dBm", d4["radio"])
        self.assertIn("per 100 MHz", d4["radio"])
        self.assertIn(words["ch3.axis_unit"], d4["fed"])
        self.assertIn(words["ch3.unit"], d4["fed"])
        for radio_words in (" MHz", " dBm", "per 100 MHz", "Outside known bands", "consistent with activity"):
            self.assertNotIn(radio_words, d4["fed"], radio_words)
        self.assertIn(f"{n1}, 50 Hz component", d4["radio"])      # the exposure rows name the project's channels
        self.assertIn(f"{n1} magnitude", d4["repeat"])             # the engine's slot words, in the project's names
        # channel 1's values carry their source's unit: a feed's own (fed here), else the magnetometer's µT;
        # a fed sweep's positions keep the six decimals the analysis keeps (CodeRabbit, #71)
        units = rendered["d4_units"]
        self.assertEqual(units["fed_at"], ["1.000001 mm", "2.5 mm", "0 mm", "120 mm"])
        self.assertEqual((units["ch1"], units["ch1_own"]), ("fedunit1", "µT"))
        self.assertIn("fedunit1", d4["radio"])
        fed2 = rendered["ch2_fed"]
        self.assertEqual(fed2["unit"], "fedunit")
        for name in ("basebar", "overlay"):
            self.assertIn("fedunit", fed2[name], name)
            self.assertNotIn(words["ch2.unit"], fed2[name], name)
        for name in ("page1", "callbacks"):          # the pages and their callbacks pass it in
            self.assertIn("fedunit", fed2[name], name)
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
