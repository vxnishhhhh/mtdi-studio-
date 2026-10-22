// Browser tour of every studio page: fails on any page error, failed callback or broken asset,
// and (phone pass, 390x844) on any nav button that is covered, off screen or cannot be tapped.
//
//   python tools/serve.py 8062 &          then:   node tools/tour.mjs http://127.0.0.1:8062 [outdir]
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

await page.goto(base + "/", { waitUntil: "domcontentloaded" });
await page.waitForTimeout(4000);
const visited = [];
for (const [name, nav, path] of pages) {
  await page.evaluate((id) => document.getElementById(id)?.click(), nav);
  await page.waitForTimeout(8000);
  for (let i = 0; i < 25; i++) { await page.mouse.wheel(0, 500); await page.waitForTimeout(100); }
  const where = await page.evaluate(() => location.pathname);
  const chars = await page.evaluate(() => (document.getElementById("page-content")?.innerText || "").length);
  if (where !== path) problems.push(`${name}: expected ${path}, landed on ${where}`);
  if (chars < 100) problems.push(`${name}: page content nearly empty (${chars} chars)`);
  visited.push({ name, path: where, chars });
  if (out) {
    fs.mkdirSync(out, { recursive: true });
    fs.writeFileSync(`${out}/${name}.txt`, await page.evaluate(() => document.body.innerText));
  }
}

// Phone pass: the desktop loop clicks with element.click(), which reaches a button even under an
// overlay. A phone user taps a point, so check that each nav button's centre is really the button
// (nothing on top of it), then make one real tap. This is the bug class fixed in #33.
const phone = await (await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true })).newPage();
phone.on("pageerror", (e) => { if (!ignored(e.message)) problems.push("phone pageerror: " + e.message); });
await phone.goto(base + "/", { waitUntil: "domcontentloaded" });
await phone.waitForTimeout(5000);
const covered = await phone.evaluate((ids) => ids.map((id) => {
  const el = document.getElementById(id);
  if (!el) return `${id}: missing`;
  const r = el.getBoundingClientRect();
  if (r.width === 0 || r.height === 0) return `${id}: not visible`;
  if (r.bottom > innerHeight || r.top < 0) return `${id}: off screen`;
  const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
  return el.contains(hit) ? null : `${id}: covered by ${hit ? hit.id || hit.className || hit.tagName : "nothing"}`;
}).filter(Boolean), pages.map((p) => p[1]));
for (const c of covered) problems.push("phone nav " + c);
try {
  await phone.tap("#nav-mtdi", { timeout: 5000 });
  await phone.waitForTimeout(3000);
  const where = await phone.evaluate(() => location.pathname);
  if (where !== "/mtdi") problems.push(`phone: tapping MTDI landed on ${where}`);
  visited.push({ name: "phone-tap-mtdi", path: where });
} catch (e) {
  problems.push("phone: could not tap MTDI: " + e.message.split("\n")[0]);
}

await browser.close();
console.log(JSON.stringify({ ok: problems.length === 0, visited, problems: [...new Set(problems)] }, null, 2));
process.exit(problems.length ? 1 : 0);
