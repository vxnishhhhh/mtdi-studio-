"""The phone view: a fixed landscape stage at /phone holding the 1180 px desktop composition.

The browser behaviour (redirect, rotation, touch scrolling, taps) is exercised by the tour's
phone pass (tools/tour.mjs); these tests pin the contract the shell and the bootstrap rely on."""
import os
import re
import sys
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("STUDIO_HTTPS_PORT", "0")


class PhoneStage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from run import NAMESPACE
        cls.ns = NAMESPACE
        cls.client = NAMESPACE["server"].test_client()

    def test_the_shell_holds_the_studio_in_a_1180_px_frame(self):
        reply = self.client.get("/phone")
        html = reply.get_data(as_text=True)
        self.assertEqual(reply.status_code, 200)
        self.assertEqual(reply.headers.get("Cache-Control"), "no-store")
        self.assertIn('<iframe id="stage" title="MTDI Studio" src="/?stage=phone"', html)
        self.assertIn("var STAGE=1180,", html)
        self.assertNotIn("__STAGE__", html)
        # the studio inside may use what it already asks for
        for permission in ("camera", "microphone", "accelerometer", "gyroscope", "fullscreen"):
            self.assertIn(permission, re.search(r'allow="([^"]+)"', html).group(1))

    def test_upright_the_stage_turns_and_scrolls_itself(self):
        html = self.client.get("/phone").get_data(as_text=True)
        self.assertIn("rotate(90deg)", html)
        self.assertIn("touchAction=portrait?'none':''", html)     # the browser's own pan is off only while turned
        self.assertIn("scrollBy(dx,dy)", html)                      # the stage scrolls itself then
        self.assertIn("screen.orientation", html)                   # and asks for a real lock where allowed

    def test_the_frame_is_allowed_and_framing_is_same_origin_only(self):
        reply = self.client.get("/")
        self.assertEqual(reply.headers.get("X-Frame-Options"), "SAMEORIGIN")
        self.assertIn("frame-ancestors 'self'", reply.headers.get("Content-Security-Policy", ""))
        policy = reply.headers.get("Permissions-Policy", "")
        self.assertIn("camera=(self)", policy)
        self.assertIn("microphone=(self)", policy)

    def test_installed_app_asks_for_landscape(self):
        self.assertEqual(self.client.get("/manifest.webmanifest").get_json()["orientation"], "landscape")

    def test_the_bootstrap_sends_phones_only_and_honours_the_mobile_setting(self):
        index = self.ns["app"].index_string
        self.assertIn("location.replace('/phone'+location.search)", index)
        self.assertIn("Math.min(a,b)<=600", index)                  # a phone: coarse pointer and a short screen edge
        self.assertIn("localStorage.getItem('i3-phone-layout')==='mobile'", index)
        self.assertIn("window.top.location.replace('/')", index)    # choosing the mobile reflow leaves the stage
        self.assertIn("window.devicePixelRatio=Math.max(1,Math.min(2,d))", index)
        self.assertNotIn("force-landscape", index)                  # the rotated-body design is gone

    def test_every_viewport_tag_is_set_not_just_the_first(self):
        index = self.ns["app"].index_string
        self.assertIn("querySelectorAll('meta[name=\"viewport\"]')", index)

    def test_lite_mode_keeps_decorative_canvases_small(self):
        browser = (ROOT / "studio" / "browser.py").read_text(encoding="utf-8")
        self.assertIn("var LITE=document.documentElement.classList.contains('phone-stage');", browser)
        self.assertIn("var dpr=LITE?0.6:", browser)
        self.assertIn("TARGET=LITE?1000/30:FRAME_INTERVAL", browser)

    def test_a_flick_carries_on_and_its_speed_comes_from_the_touch_events(self):
        ui = (ROOT / "studio" / "ui.py").read_text(encoding="utf-8")
        self.assertIn("e.timeStamp-scrubTouchT>90||Math.abs(scrubFlingV)<.3)return;", ui)
        self.assertIn("scrubConsume(scrubFlingV*dt)", ui)                   # the hero keeps the swipe's speed
        # one finger drives it: a second finger is ignored, and only the last lift may flick
        self.assertIn("const t=scrubTouch(e.touches);if(!t)return;", ui)
        self.assertIn("if(!lifted||e.touches.length||", ui)
        # the tracked finger lifts while another stays: that finger takes over where it is, with no flick
        self.assertIn("if(lifted&&e.touches.length){const t=e.touches[0];scrubTouchId=t.identifier;"
                      "scrubTouchY=t.clientY;scrubTouchT=e.timeStamp;scrubFlingV=0;return;}", ui)
        self.assertNotIn("scrubTouchT=performance.now()", ui)                # not when a busy page got to it
        shell = self.client.get("/phone").get_data(as_text=True)
        self.assertIn("t:e.timeStamp", shell)                                # the turned stage glides the same way
        self.assertIn("if(e.timeStamp-drag.t>90)vx=vy=0;", shell)

    def test_rotate_views_give_up_down_drags_to_the_page(self):
        css = self.ns["GLOBAL_CSS"] if "GLOBAL_CSS" in self.ns else (ROOT / "studio" / "theme.py").read_text(encoding="utf-8")
        self.assertIn("html.phone-stage .i3-tab-board canvas", css)
        self.assertIn("touch-action:pan-y!important", css)
        shell = self.client.get("/phone").get_data(as_text=True)
        for selector in (".i3-tab-board canvas", "#home-module-globe", ".instrument-constellation-canvas", ".gl-container"):
            self.assertIn(selector, shell)


if __name__ == "__main__":
    unittest.main()
