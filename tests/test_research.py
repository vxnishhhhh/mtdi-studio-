"""S1-10: the Research catalogue is complete, licensed, labelled and fully credited."""
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIELDS = ("id", "name", "provider", "url", "licence", "credit", "use", "origin", "pillars", "storage")


class Research(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / "registry" / "datasets.json").read_text())["datasets"]
        self.sources = json.loads((ROOT / "registry" / "research" / "sources.json").read_text())

    def test_at_least_25_datasets_with_every_field(self):
        self.assertGreaterEqual(len(self.data), 25)
        ids = [d["id"] for d in self.data]
        self.assertEqual(len(ids), len(set(ids)))
        for d in self.data:
            for f in FIELDS:
                self.assertIn(f, d, d["id"])

    def test_every_dataset_is_licensed_and_labelled(self):
        for d in self.data:
            self.assertTrue(d["licence"], f"{d['id']} has no licence; it must not be catalogued as usable")
            self.assertIn(d["origin"], ("measured", "simulated"), d["id"])
            self.assertTrue(d["url"].startswith("https://"), d["id"])

    def test_catalogue_matches_sources(self):
        expected = len(self.sources["uci"]) + len(self.sources["physionet"]) + len(self.sources["feeds"])
        self.assertEqual(len(self.data), expected, "rebuild with tools/research/build_catalogue.py")

    def test_credits_name_every_dataset_and_person(self):
        credits = (ROOT / "docs" / "CREDITS.md").read_text(encoding="utf-8")
        for d in self.data:
            self.assertIn(d["name"], credits, d["id"])
        for name in ("Nihal Panday", "Pishop", "Radiowinkel"):
            self.assertIn(name, credits)


if __name__ == "__main__":
    unittest.main()
