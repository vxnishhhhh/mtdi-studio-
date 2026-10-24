// Browser tour of every studio page: fails on any page error, failed callback or broken asset,
// and (phone pass, 390x844) on any nav button that is covered, off screen or cannot be tapped.
//
//   python tools/serve.py 8062 &          then:   node tools/tour.mjs http://127.0.0.1:8062 [outdir]
//
// Each page is judged once the studio says it is ready (<html data-page-ready="1">, see
// studio/browser.py), never after a fixed sleep. The summary lists how long each page took
// (ready_ms). TOUR_PAGE_TIMEOUT_MS (default 180000) is the deadline per page: software GL in
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

const PAGE_TIMEOUT = Number(process.env.TOUR_PAGE_TIMEOUT_MS || 180000);
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

// Phone pass: the desktop loop clicks with element.click(), which reaches a button even under an
// overlay. A phone user taps a point, so check that each nav button's centre is really the button
// (nothing on top of it), then make one real tap (the bug class fixed in #33). Reduced motion skips
// the startup intro by design, so the check sees the page a returning visitor sees, every run.
//
// Precondition: on a phone the studio asks for the 1180 px desktop composition through the
// viewport meta, set by its head script (studio/webapp.py, syncPhoneMode). Chromium's device
// emulation often ignores a viewport meta changed by script: the meta is identical every run, yet
// the layout stays 390 px wide in most fresh contexts. Judging the nav in that state tests the
// emulator, not the studio, so an attempt where the viewport was not applied is retried in a
// fresh context (PHONE_ATTEMPTS). If none applies it, the pass is reported as skipped with the
// reason, never as passed. Whether real phones apply it is not verified here.
const PHONE_ATTEMPTS = Number(process.env.TOUR_PHONE_ATTEMPTS || 5);
const phoneReport = { attempts: 0, viewport_applied: false, skipped: null };
for (let attempt = 1; attempt <= PHONE_ATTEMPTS && !phoneReport.viewport_applied; attempt++) {
  phoneReport.attempts = attempt;
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true,
    isMobile: true, reducedMotion: "reduce" });
  const phone = await context.newPage();
  const phoneErrors = [];
  phone.on("pageerror", (e) => { if (!ignored(e.message)) phoneErrors.push("phone pageerror: " + e.message); });
  await phone.goto(base + "/", { waitUntil: "domcontentloaded" });
  try {
    await ready(phone, "/");
    const view = await phone.evaluate(() => ({
      wantsDesktop: document.documentElement.classList.contains("phone-desktop"), width: innerWidth }));
    if (view.wantsDesktop && view.width !== 1180) {           // the emulator ignored the studio's viewport
      await context.close();
      continue;
    }
    phoneReport.viewport_applied = true;
    problems.push(...phoneErrors);
    const covered = await phone.evaluate((ids) => ids.map((id) => {
      const el = document.getElementById(id);
      if (!el) return `${id}: missing`;
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) return `${id}: not visible`;
      if (r.bottom > innerHeight || r.top < 0 || r.right > innerWidth || r.left < 0) return `${id}: off screen`;
      const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
      return el.contains(hit) ? null : `${id}: covered by ${hit ? hit.id || hit.className || hit.tagName : "nothing"}`;
    }).filter(Boolean), pages.map((p) => p[1]));
    for (const c of covered) problems.push("phone nav " + c);
    await phone.tap("#nav-mtdi", { timeout: 10000 });
    const ms = await ready(phone, "/mtdi");
    visited.push({ name: "phone-tap-mtdi", path: await phone.evaluate(() => location.pathname), ready_ms: ms });
  } catch (e) {
    phoneReport.viewport_applied = true;                      // a real failure, not the precondition
    problems.push(...phoneErrors, "phone: " + e.message.split("\n")[0]);
  }
  await context.close();
}
if (!phoneReport.viewport_applied) {
  phoneReport.skipped = `the emulator ignored the studio's 1180 px viewport in ${phoneReport.attempts} fresh contexts`;
}

await browser.close();
console.log(JSON.stringify({ ok: problems.length === 0, visited, phone: phoneReport, problems: [...new Set(problems)] }, null, 2));
process.exit(problems.length ? 1 : 0);
