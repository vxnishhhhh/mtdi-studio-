"""S1-01: the studio's MTDI page shows the pillars of ADR 0001/0007 and keeps Aether.

How to extend: add a pillar to mtdi.pillars.PILLARS and studio.pages.MTDI_ORBIT_PILLARS,
then this test tells you if the two disagree. (Aether: they will disagree. They always do.)
"""
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _text(node, out):
    """Collect every string and id in a Dash component tree."""
    if isinstance(node, str):
        out.append(node)
        return out
    if isinstance(node, (list, tuple)):
        for child in node:
            _text(child, out)
        return out
    if getattr(node, "id", None):
        out.append(str(node.id))
    children = getattr(node, "children", None)
    if children is not None:
        _text(children, out)
    return out


class MtdiPagePillars(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import studio  # noqa: F401  (builds the app once)
        from studio import pages
        cls.pages = pages
        cls.words = _text(pages.mtdi_page(), [])

    def test_every_framework_pillar_is_on_the_page(self):
        from mtdi.pillars import PILLARS
        orbit = {pid for pid, *_ in self.pages.MTDI_ORBIT_PILLARS}
        self.assertEqual({p["id"] for p in PILLARS} | {"aether"}, orbit)
        self.assertIn("Computational Core", self.words)
        self.assertIn("Research", self.words)

    def test_aether_terminal_survives(self):
        self.assertIn("aether-terminal", self.words)
        self.assertIn("mtdi-pane-aether", self.words)

    def test_computational_core_lists_real_modules(self):
        from mtdi.pillars import COMPUTATIONAL_MODULES
        rows = self.pages._computational_modules()
        self.assertEqual(len(rows), sum(len(v) for v in COMPUTATIONAL_MODULES.values()))
        self.assertTrue(all(row[2] for row in rows), [r for r in rows if not r[2]])

    def test_research_has_honest_empty_state(self):
        catalogue = ROOT / "registry" / "datasets.json"
        if catalogue.exists() and json.loads(catalogue.read_text()).get("datasets"):
            self.skipTest("datasets catalogued; empty state not shown")
        self.assertTrue(any("No datasets catalogued yet" in w for w in self.words))


if __name__ == "__main__":
    unittest.main()
