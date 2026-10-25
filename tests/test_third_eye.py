"""S1-07: the Third Eye reference project, driven with the lines its firmware prints."""
import pathlib
import random
import unittest

from mtdi.bridge import mapping_for, words_for
from mtdi.engine import Engine
from mtdi.project import ManifestError, load, normalise

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROJECT = ROOT / "projects" / "third-eye"


def line(left, right, buzz, seq):
    """The firmware's format: a ranger with no echo leaves its key out."""
    parts = []
    if left is not None:
        parts.append(f"LEFT_CM={left:.1f}")
    if right is not None:
        parts.append(f"RIGHT_CM={right:.1f}")
    parts += [f"BUZZ={buzz}", f"_SEQ={seq}"]
    return ",".join(parts)


class ThirdEye(unittest.TestCase):
    def setUp(self):
        self.project = load(PROJECT)
        self.clock = [0.0]
        self.engine = Engine(self.project, clock=lambda: self.clock[0])
        self.seq = 0
        self.rng = random.Random(7)

    def feed(self, seconds, left, right, buzz=0):
        for _ in range(int(seconds * 13)):                 # the firmware prints about 13 lines a second
            self.clock[0] += 1 / 13
            # Jitter inside the channels' 0.3 cm noise floor: this checks which side NVTRA names,
            # not how the baseline copes with noise above the floor the manifest declares.
            noisy = lambda v: None if v is None else v + self.rng.gauss(0, 0.2)   # noqa: E731
            self.engine.ingest_line("eye", line(noisy(left), noisy(right), buzz, self.seq))
            self.seq += 1

    def condition(self):
        return self.engine.snapshot()["fusion"]["condition"]

    def test_manifest_profile_and_studio_words(self):
        self.assertEqual(self.project["profile"], "edge")
        self.assertEqual(mapping_for(self.project), {"ch1": "left", "ch2": "right"})
        words = words_for(self.project)
        self.assertEqual((words["ch1.name"], words["ch1.unit"]), ("Left distance", "cm"))
        self.assertEqual(words["ch2.name"], "Right distance")
        self.assertEqual(self.project["interface"]["brand.title"], "Third Eye")

    def test_learns_open_space_then_says_which_side(self):
        self.feed(30, 150, 150)
        self.assertEqual(self.condition(), "Ambient conditions")
        self.feed(2, 40, 150, buzz=1)                     # something comes in on the left
        self.assertEqual(self.condition(), "Something on the left")
        self.feed(2, 40, 35, buzz=1)                      # and now on both sides
        self.assertEqual(self.condition(), "Something ahead on both sides")

    def test_moving_away_is_not_something_on_that_side(self):
        """The SNR has no sign; the rules' direction makes a farther wall different from a closer one."""
        self.feed(30, 150, 150)
        self.feed(2, 260, 150)                            # the left side opens up: farther, not closer
        self.assertNotIn(self.condition(), ("Something on the left", "Something ahead on both sides"))
        self.feed(2, 260, 40, buzz=1)                     # right closes in while left is still far
        self.assertEqual(self.condition(), "Something on the right")

    def test_a_missing_echo_is_a_gap_not_a_number(self):
        self.feed(5, 150, 150)
        before = self.engine.snapshot()["channels"]["left"]["value"]
        self.feed(1, None, 150)                           # the left ranger hears nothing for a second
        snap = self.engine.snapshot()["channels"]
        self.assertEqual(snap["left"]["value"], before)   # the last real reading stands; nothing invented
        self.assertNotEqual(snap["right"]["value"], before)

    def test_the_buzzer_state_is_not_clipping(self):
        """A 0/1 state at its bounds is normal; with raw_range [0, 1] it never settled and held NVTRA."""
        self.feed(12, 150, 150)
        buzzer = self.engine.snapshot()["channels"]["buzzer"]
        self.assertFalse(buzzer["evidence"]["clipped"])
        self.assertFalse(buzzer["environment"]["settling"])

    def test_recordings_folder_says_there_is_no_recording(self):
        recordings = PROJECT / "recordings"
        self.assertEqual(sorted(p.name for p in recordings.iterdir()), ["README.md"])
        self.assertIn("No recording yet", (recordings / "README.md").read_text(encoding="utf-8"))

    def test_firmware_prints_the_manifest_keys(self):
        sketch = (PROJECT / "firmware" / "third_eye" / "third_eye.ino").read_text(encoding="utf-8")
        for key in ("LEFT_CM=", "RIGHT_CM=", "BUZZ=", "_SEQ="):
            self.assertIn(key, sketch)
        keys = {k for ch in self.project["channels"] for k in ch["keys"]}
        self.assertEqual(keys, {"LEFT_CM", "RIGHT_CM", "BUZZ"})


class RuleDirection(unittest.TestCase):
    """`direction` on an NVTRA rule: checked by `mtdi check`, scalar channels only."""

    def manifest(self, direction):
        return {"project": {"id": "d"}, "sources": [{"id": "s", "adapter": "http"}],
                "channels": [{"id": "gap", "keys": ["G"], "noise_floor": 0.1},
                             {"id": "field", "kind": "vector", "keys": ["X", "Y"], "noise_floor": 0.1}],
                "nvtra": {"rules": [{"when": {"gap": ">=6"}, "condition": "Closer", "direction": direction}]}}

    def test_up_and_down_are_accepted(self):
        for way in ("up", "down"):
            normalise(self.manifest({"gap": way}))

    def test_bad_directions_name_the_problem(self):
        for direction, needle in (({"gap": "closer"}, '"up" or "down"'), ({"nope": "down"}, "unknown channel 'nope'"),
                                  ({"field": "down"}, "only a scalar channel"), (["gap"], "must be an object")):
            with self.assertRaisesRegex(ManifestError, needle):
                normalise(self.manifest(direction))


if __name__ == "__main__":
    unittest.main()
