// Browser tour of every studio page: fails on any page error, failed callback or broken asset.
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
await browser.close();
console.log(JSON.stringify({ ok: problems.length === 0, visited, problems: [...new Set(problems)] }, null, 2));
process.exit(problems.length ? 1 : 0);
