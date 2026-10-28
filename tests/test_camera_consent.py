"""Camera consent: no frame goes to NVTRA's model until the operator says yes once; the answer
is kept on disk, so it holds across restarts and browsers until the operator resets it."""
import os
import sys
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("STUDIO_HTTPS_PORT", "0")

FRAME = "data:image/jpeg;base64," + "A" * 64


class CameraConsent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from run import NAMESPACE, RUNTIME
        cls.ns = NAMESPACE
        cls.client = NAMESPACE["server"].test_client()
        cls.path = RUNTIME.state_dir / "camera_consent.json"

    def setUp(self):
        # Leave the operator's real answer as it was.
        self.saved = self.path.read_bytes() if self.path.exists() else None
        self.path.unlink(missing_ok=True)
        self.sent = []
        self.real_agent = self.ns["nvtra_agent"]
        self.ns["nvtra_agent"] = lambda text, image_b64=None: self.sent.append(image_b64) or {"say": "ok", "actions": []}

    def tearDown(self):
        self.ns["nvtra_agent"] = self.real_agent
        if self.saved is None:
            self.path.unlink(missing_ok=True)
        else:
            self.path.write_bytes(self.saved)

    def ask(self):
        return self.client.post("/api/agent", json={"text": "what is this", "image": FRAME})

    def set_share(self, share):
        return self.client.post("/api/camera-consent", json={"share": share}).get_json()

    def test_unanswered_means_no_frame_is_sent(self):
        self.assertIsNone(self.client.get("/api/camera-consent").get_json()["share"])
        self.ask()
        self.assertEqual(self.sent, [None])

    def test_a_no_is_remembered_and_no_frame_is_sent(self):
        self.assertEqual(self.set_share(False), {"share": False})
        self.ask()
        self.assertEqual(self.sent, [None])
        self.assertFalse(self.client.get("/api/camera-consent").get_json()["share"])

    def test_a_yes_is_remembered_on_disk_and_frames_are_sent(self):
        self.set_share(True)
        self.assertTrue(self.path.exists())
        self.ask()
        self.assertEqual(self.sent, ["A" * 64])

    def test_ask_again_forgets_the_answer(self):
        self.set_share(True)
        self.assertEqual(self.set_share(None), {"share": None})
        self.ask()
        self.assertEqual(self.sent, [None])

    def test_anything_but_yes_no_or_reset_is_refused(self):
        self.assertEqual(self.client.post("/api/camera-consent", json={"share": "yes"}).status_code, 400)
        self.assertEqual(self.client.post("/api/camera-consent", json=[1]).status_code, 400)
        self.assertEqual(self.client.post("/api/camera-consent", data="x", content_type="application/json").status_code, 400)

    def test_the_page_asks_before_the_first_frame_and_can_ask_again(self):
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn("const image=await consentedFrame()", html)
        self.assertIn("function consentOp(task)", html)
        self.assertIn("return await consentOp(async()=>{let share=(await (await fetch('/api/camera-consent'", html)
        self.assertIn("consentOp(()=>fetch('/api/camera-consent'", html)
        self.assertIn("window.confirm('NVTRA can send a still frame", html)
        self.assertIn("orbShow('Camera answer not saved'", html)
        self.assertNotIn("agent.cameraShare", html)   # never cached: read fresh for each question
        self.assertIn("data-i3-camera-consent-reset", (ROOT / "studio" / "ui.py").read_text(encoding="utf-8"))

if __name__ == "__main__":
    unittest.main()
