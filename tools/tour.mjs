// Browser tour of every studio page: fails on any page error, failed callback or broken asset,
// and (phone pass, 390x844) on any nav button that is covered, off screen or cannot be tapped.
//
//   python tools/serve.py 8062 &          then:   node tools/tour.mjs http://127.0.0.1:8062 [outdir]
//
// Each page is judged once the studio says it is ready (<html data-page-ready="1">, see
// studio/browser.py), never after a fixed sleep. The summary lists how long each page took
// (ready_ms). TOUR_PAGE_TIMEOUT_MS (default 420000) is the deadline per page: software GL in
// the cloud needs about 50 s for the 3D pages.
//
// Needs Playwright (resolved from NODE_PATH, /opt/node-tools or a local install) and Chromium
// (PLAYWRIGHT_CHROMIUM, default /opt/pw-browsers/chromium). Writes each page's visible text to
// outdir when given, and prints a JSON summary. Hosts the sandbox cannot reach are ignored;
// failed resources are judged by URL in the response handler, not by the console echo.
import { createRequire } from "node:module";
import fs from "node:fs";

const require = createRequire(import.meta.url);
let playwright;
for (const p of [process.env.PLAYWRIGHT_MODULE, "playwright", "/opt/node-tools/node_modules/playwright"]) {
  if (!p) continue;
  try { playwright = require(p); break; } catch {}
}
if (!playwright) { console.error("playwright not found"); process.exit(2); }

const base = process.argv[2] || "http://127.0.0.1:8062";
const out = process.argv[3];
const IGNORE = [/^Failed to load resource/, /spline-runtime/, /unpkg\.com/, /prod\.spline\.design/, /cdn\.jsdelivr\.net/, /ERR_NAME_NOT_RESOLVED/,
                /three\.js" and "build\/three\.min\.js" are deprecated/, /sigmaRadians/, /willReadFrequently/];
const ignored = (t) => IGNORE.some((r) => r.test(t));
const pages = [["home", "nav-home", "/"], ["page-1", "nav-em", "/page-1"], ["page-2", "nav-sweep3", "/page-2"],
               ["mtdi", "nav-mtdi", "/mtdi"], ["page-3", "nav-page3", "/page-3"], ["settings", "nav-settings", "/settings"]];

const browser = await playwright.chromium.launch({
  executablePath: process.env.PLAYWRIGHT_CHROMIUM || "/opt/pw-browsers/chromium", headless: false,
  args: ["--headless=new", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"],
});
const page = await (await browser.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
const problems = [];
page.on("pageerror", (e) => { if (!ignored(e.message)) problems.push("pageerror: " + e.message); });
page.on("console", (m) => { if (m.type() === "error" && !ignored(m.text())) problems.push("console: " + m.text().slice(0, 300)); });
page.on("response", (r) => { if (r.status() >= 400 && !ignored(r.url())) problems.push(`${r.status()} ${r.url()}`); });

// In software GL (a cloud container has no GPU: Chromium falls back to SwiftShader) the studio's
// always-on shell, two full-screen background shaders and the full-screen scrub canvas, holds
// every animation loop near 1.5 frames a second, so a 3D page can take minutes to settle. On
// 2026-10-27 the MTDI page took 42-161 s on the desktop pass and 189-273 s on the phone pass
// (its frame is 1180 px at 1.7x); runs vary a lot. The deadline is a measurement budget, not a
// speed target.
const PAGE_TIMEOUT = Number(process.env.TOUR_PAGE_TIMEOUT_MS || 420000);
// Resolves with the page's own ready time once <html data-page=path data-page-ready="1">.
async function ready(tab, path) {
  await tab.waitForFunction((p) => document.documentElement.dataset.page === p &&
    document.documentElement.dataset.pageReady === "1", path, { timeout: PAGE_TIMEOUT, polling: 250 });
  return Number(await tab.evaluate(() => document.documentElement.dataset.pageReadyMs));
}

await page.goto(base + "/", { waitUntil: "domcontentloaded" });
const visited = [];
try {
  await ready(page, "/");
} catch {
  problems.push("home: never signalled ready");
}
// A visitor scrolls through the startup intro before the nav can be used: the header is
// pointer-events:none until then. element.click() below reaches the nav anyway, so without
// this the tour browsed every page with the intro still active, its full-screen shader and the
// hidden field background drawing behind each page (software GL then starved every page).
await page.mouse.move(720, 450);   // the middle of the 1440 x 900 viewport, over the intro
for (let i = 0; i < 60 && !(await page.evaluate(() => window.__introConsumed === true)); i++) {
  await page.mouse.wheel(0, 600);
  await page.waitForTimeout(150);
}
if (!(await page.evaluate(() => window.__introConsumed === true))) problems.push("home: the startup intro did not finish after scrolling it");
for (const [name, nav, path] of pages) {
  await page.evaluate((id) => document.getElementById(id)?.click(), nav);
  let readyMs = null;
  try {
    readyMs = await ready(page, path);
  } catch {
    problems.push(`${name}: not ready within ${PAGE_TIMEOUT} ms`);
  }
  for (let i = 0; i < 25; i++) { await page.mouse.wheel(0, 500); await page.waitForTimeout(100); }
  const where = await page.evaluate(() => location.pathname);
  const chars = await page.evaluate(() => (document.getElementById("page-content")?.innerText || "").length);
  if (where !== path) problems.push(`${name}: expected ${path}, landed on ${where}`);
  if (chars < 100) problems.push(`${name}: page content nearly empty (${chars} chars)`);
  visited.push({ name, path: where, chars, ready_ms: readyMs });
  if (out) {
    fs.mkdirSync(out, { recursive: true });
    fs.writeFileSync(`${out}/${name}.txt`, await page.evaluate(() => document.body.innerText));
  }
}

// P-01 entry points: each back-end feature the studio exposes is opened once, as a visitor would.
await page.evaluate(() => document.getElementById("nav-settings")?.click());
try {
  await ready(page, "/settings");
  await page.evaluate(() => document.querySelector("[data-i3-system-check]")?.click());
  await page.waitForFunction(() => document.querySelectorAll("[data-i3-system-result] .i3-system-row").length > 10, null, { timeout: 120000 });
} catch {
  problems.push("settings: SYSTEM CHECK did not show its results");
}
try {
  await page.waitForFunction(() => document.querySelectorAll("[data-i3-project-list] option").length > 0, null, { timeout: 30000 });
  await page.evaluate(() => document.querySelector("[data-i3-project-check]")?.click());
  await page.waitForFunction(() => document.querySelectorAll("[data-i3-project-result] .i3-system-row").length > 2, null, { timeout: 30000 });
  await page.evaluate(() => document.querySelector("[data-i3-line-test]")?.click());
  await page.waitForFunction(() => document.querySelector("[data-i3-line-result]")?.textContent.includes("ACCEPTED"), null, { timeout: 30000 });
} catch {
  problems.push("settings: PROJECT CHECK or TEST LINE did not show its results");
}
try {
  await page.evaluate(() => document.querySelector("[data-i3-csv-fit]")?.click());
  await page.waitForFunction(() => document.querySelector("[data-i3-csv-result] a[download]")
    && document.querySelectorAll("[data-i3-csv-result] .i3-system-row").length >= 4, null, { timeout: 30000 });
} catch {
  problems.push("settings: FIT FROM CSV did not show a fit and a calibration file");
}
try {
  // The tour serves the studio as Vercel does, so CREATE PROJECT must refuse in words; it never writes a folder.
  await page.evaluate(() => document.querySelector("[data-i3-new-create]")?.click());
  await page.waitForFunction(() => /Not created: /.test(document.querySelector("[data-i3-new-result]")?.textContent || ""),
    null, { timeout: 30000 });
} catch {
  problems.push("settings: CREATE PROJECT did not answer in words");
}

// Phone pass: the desktop loop clicks with element.click(), which reaches a button even under an
// overlay. A phone user taps a point, so check that each nav button's centre is really the button
// (nothing on top of it), then make one real tap (the bug class fixed in #33). Reduced motion skips
// the startup intro by design, so the check sees the page a returning visitor sees, every run.
//
// A phone is sent to /phone, which holds the studio in a 1180 px iframe (the desktop composition)
// and turns it a quarter turn when the phone is upright (studio/webapp.py, PHONE_SHELL). The pass
// runs upright, the harder case: the tap goes through the scale and the rotation.
const phoneReport = { stage: null, frame: null };
{
  const context = await browser.newContext({ ...playwright.devices["iPhone 13"], reducedMotion: "reduce" });
  const phone = await context.newPage();
  phone.on("pageerror", (e) => { if (!ignored(e.message)) problems.push("phone pageerror: " + e.message); });
  try {
    await phone.goto(base + "/", { waitUntil: "domcontentloaded" });
    await phone.waitForURL(/\/phone/, { timeout: 30000 });
    let stage = null;
    for (let i = 0; i < 300 && !stage; i++) {
      stage = phone.frames().find((f) => f.url().includes("stage=phone")) || null;
      if (!stage) await phone.waitForTimeout(100);
    }
    if (!stage) throw new Error("/phone has no studio frame");
    phoneReport.stage = await phone.evaluate(() => document.getElementById("stage").style.transform);
    await ready(stage, "/");
    phoneReport.frame = await stage.evaluate(() => ({ w: innerWidth, h: innerHeight, dpr: devicePixelRatio }));
    if (phoneReport.frame.w !== 1180) problems.push(`phone stage is ${phoneReport.frame.w} px wide, not 1180`);
    const covered = await stage.evaluate((ids) => ids.map((id) => {
      const el = document.getElementById(id);
      if (!el) return `${id}: missing`;
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) return `${id}: not visible`;
      if (r.bottom > innerHeight || r.top < 0 || r.right > innerWidth || r.left < 0) return `${id}: off screen`;
      const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
      return el.contains(hit) ? null : `${id}: covered by ${hit ? hit.id || hit.className || hit.tagName : "nothing"}`;
    }).filter(Boolean), pages.map((p) => p[1]));
    for (const c of covered) problems.push("phone nav " + c);
    await stage.locator("#nav-mtdi").tap({ timeout: 15000 });
    const ms = await ready(stage, "/mtdi");
    visited.push({ name: "phone-tap-mtdi", path: await stage.evaluate(() => location.pathname), ready_ms: ms });
  } catch (e) {
    problems.push("phone: " + e.message.split("\n")[0]);
  } finally {
    await context.close().catch(() => {});
  }
}

// Swipes (the flick): upright again, with motion on, so Page 1 opens with its scroll hero. Touches
// go in at 60 Hz with their own timestamps, as a phone sends them; the studio measures a flick from
// those, so the emulator's slow software GL does not hide it. The hero must clear in at most 3
// swipes, and the next swipe must scroll the page. It runs in a browser of its own, full Chrome
// (which has swipe-back, the failure it guards against) without forced software WebGL: it tests
// touch, and the 3D views drawn on the CPU after the passes above can outlast the page deadline.
const swipeReport = { swipes: null, scrolled: null };
{
  const plain = await playwright.chromium.launch({
    executablePath: process.env.PLAYWRIGHT_CHROMIUM || "/opt/pw-browsers/chromium", headless: false, args: ["--headless=new"],
  });
  const context = await plain.newContext({ ...playwright.devices["iPhone 13"] });
  const phone = await context.newPage();
  phone.on("pageerror", (e) => { if (!ignored(e.message)) problems.push("swipe pageerror: " + e.message); });
  try {
    const cdp = await context.newCDPSession(phone);
    await phone.goto(base + "/", { waitUntil: "domcontentloaded" });
    await phone.waitForURL(/\/phone/, { timeout: 30000 });
    let stage = null;
    for (let i = 0; i < 300 && !stage; i++) {
      stage = phone.frames().find((f) => f.url().includes("stage=phone")) || null;
      if (!stage) await phone.waitForTimeout(100);
    }
    if (!stage) throw new Error("/phone has no studio frame");
    await ready(stage, "/");
    const glass = await phone.evaluate(() => ({ w: innerWidth, h: innerHeight }));
    let ts = Date.now() / 1000;
    // Upright, the stage's "down" is the glass's left, so a finger scrolling down moves right.
    const swipe = async (frac) => {
      const y = glass.h / 2, x0 = glass.w * 0.15, x1 = glass.w * (0.15 + frac);
      const touch = (type, x) => cdp.send("Input.dispatchTouchEvent", { type, timestamp: (ts += 0.016), touchPoints: x === null ? [] : [{ x, y }] });
      await touch("touchStart", x0);
      for (let k = 1; k <= 10; k++) await touch("touchMove", x0 + (x1 - x0) * k / 10);
      await touch("touchEnd", null);
      await phone.waitForTimeout(1500);
    };
    for (let i = 0; i < 8 && await stage.evaluate(() => !!document.getElementById("startup-intro")); i++) await swipe(0.6);
    await stage.locator("#nav-em").tap({ timeout: 15000 });
    await ready(stage, "/page-1");
    await phone.waitForTimeout(1500);
    const heroDone = () => stage.evaluate(() => { const h = document.querySelector(".i3-scrub-hero"); return !!h && h.classList.contains("i3-hero-hidden"); });   // no hero is a failure, not a pass
    let swipes = 0;
    // a flick glides on after the finger lifts; software GL draws it slowly, so give it time to land
    while (!(await heroDone()) && swipes < 4) { await swipe(0.5); await phone.waitForTimeout(1500); swipes++; }
    swipeReport.swipes = swipes;
    if (!(await heroDone()) || swipes > 3) problems.push(`swipe: Page 1's scroll opening took more than 3 swipes (${swipes})`);
    const y0 = await stage.evaluate(() => scrollY);
    await swipe(0.5);
    swipeReport.scrolled = Math.round((await stage.evaluate(() => scrollY)) - y0);
    if (swipeReport.scrolled <= 0) problems.push("swipe: a swipe after the opening did not scroll Page 1");
  } catch (e) {
    problems.push("swipe: " + e.message.split("\n")[0]);
  } finally {
    await context.close().catch(() => {});
    await plain.close().catch(() => {});
  }
}

await browser.close();
console.log(JSON.stringify({ ok: problems.length === 0, visited, phone: phoneReport, swipe: swipeReport, problems: [...new Set(problems)] }, null, 2));
process.exit(problems.length ? 1 : 0);
