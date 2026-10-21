"""S1-12: NVTRA's agents, against local fake services (no live network in tests)."""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from mtdi import agents  # noqa: E402
from mtdi.pillars import COMPUTATIONAL_MODULES  # noqa: E402
from test_backend import FakeService  # noqa: E402

ARXIV_XML = b"""<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><entry>
<id>http://arxiv.org/abs/1234.5678</id><title>Sensor
 fusion survey</title><published>2024-01-02T00:00:00Z</published>
<author><name>A. Author</name></author></entry></feed>"""


class Agents(unittest.TestCase):
    def test_researcher_merges_sources_and_reports_failures(self):
        svc = FakeService({
            ("GET", "/crossref"): lambda r: (200, {"message": {"items": [{"title": ["Calibration of MOX sensors"],
                                                 "author": [{"family": "Vito", "given": "S."}],
                                                 "issued": {"date-parts": [[2008]]}, "DOI": "10.1/x"}]}}, "application/json"),
            ("GET", "/arxiv"): lambda r: (200, ARXIV_XML, "application/atom+xml"),
            ("GET", "/wiki"): lambda r: (429, b"slow down", "text/plain"),
        })
        try:
            out = agents.research("sensor fusion", base={"crossref": svc.url + "/crossref", "arxiv": svc.url + "/arxiv",
                                                         "wikipedia": svc.url + "/wiki"})
        finally:
            svc.close()
        self.assertEqual(sorted(out["sources"]), ["arxiv", "crossref"])
        titles = [h["title"] for h in out["result"]]
        self.assertIn("Calibration of MOX sensors", titles)
        self.assertIn("Sensor fusion survey", titles)
        self.assertIn("wikipedia", out["errors"])
        self.assertEqual(out["note"], "references to read, not measurements")

    def test_analyst_and_grapher(self):
        a = agents.analyse([1, 2, 3, 4], "ch")["result"]
        self.assertEqual(a["n"], 4)
        self.assertAlmostEqual(a["mean"], 2.5)
        fig = agents.graph({"kp": [1, 2, 3]}, title="Kp")["result"]
        self.assertEqual(fig["data"][0]["y"], [1.0, 2.0, 3.0])
        self.assertEqual(fig["layout"]["font"]["color"], "#E3B945")

    def test_validator_catches_an_invented_number(self):
        packet = {"channels": {"temp": {"magnitude": 21.4}}, "fusion": {"score": 88.0}}
        self.assertTrue(agents.validate("Temperature is 21.4 and the score is 88.", packet)["result"]["ok"])
        bad = agents.validate("Temperature is 37.9, score 88.", packet)["result"]
        self.assertFalse(bad["ok"])
        self.assertEqual(bad["unsupported"], ["37.9"])

    def test_registered(self):
        self.assertIn("mtdi.agents", [m for mods in COMPUTATIONAL_MODULES.values() for m in mods])
        self.assertEqual(set(agents.AGENTS), {"researcher", "analyst", "grapher", "validator"})


if __name__ == "__main__":
    unittest.main()
