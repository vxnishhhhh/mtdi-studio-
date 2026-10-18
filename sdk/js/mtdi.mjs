// MTDI JavaScript SDK: ES module for browsers and Node 18+, no dependencies.
//
//   import { Line, parseLine, Ewma, Cusum, StudioClient } from "./mtdi.mjs";
//   new Line().add("TEMP", 21.4).seq(7).toString();          // "TEMP=21.4,_SEQ=7"
//   parseLine("TEMP=21.4");                                   // {TEMP: 21.4} or throws ProtocolError
//   new Ewma().update(x);                                     // {score, anomaly}
//   await new StudioClient("https://x.vercel.app", token).send({ ch2: 3.1 });
//
// Protocol rules and detectors match the Python package number for number
// (tests/test_sdks.py checks it).

const KEY = /^[A-Za-z_][A-Za-z0-9_.\-]{0,47}$/;
const NUMBER = /^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$/;

export class ProtocolError extends Error {}

export function parseLine(line) {
  const text = String(line ?? "").trim();
  if (!text) throw new ProtocolError("empty line");
  if (text.length > 2048) throw new ProtocolError("line too long");
  if (text[0] === "{") return parseJson(text);
  const out = {};
  for (const field of text.split(",")) {
    const eq = field.indexOf("=");
    if (eq < 0) throw new ProtocolError(`malformed field '${field}'`);
    const key = field.slice(0, eq).trim(), raw = field.slice(eq + 1).trim();
    if (!KEY.test(key) || !NUMBER.test(raw)) throw new ProtocolError(`malformed field '${field}'`);
    if (Object.prototype.hasOwnProperty.call(out, key)) throw new ProtocolError(`duplicate key ${key}`);
    const v = Number(raw);
    if (!Number.isFinite(v)) throw new ProtocolError(`${key} is not finite`);
    out[key] = v;
  }
  return out;
}

function parseJson(text) {
  let data;
  try { data = JSON.parse(text); } catch { throw new ProtocolError("invalid JSON"); }
  if (!data || typeof data !== "object" || Array.isArray(data) || !Object.keys(data).length)
    throw new ProtocolError("JSON line must be a non-empty object");
  const out = {};
  for (const [key, raw] of Object.entries(data)) {
    if (!KEY.test(key) || typeof raw !== "number" || !Number.isFinite(raw)) throw new ProtocolError(`malformed field '${key}'`);
    out[key] = raw;
  }
  return out;
}

export function formatNumber(v) {
  if (Number.isInteger(v) && Math.abs(v) < 1e15) return String(v);
  let s = v.toPrecision(6);                       // then strip like C's %g
  if (s.includes("e")) {
    let [m, e] = s.split("e");
    if (m.includes(".")) m = m.replace(/0+$/, "").replace(/\.$/, "");
    const n = Number(e);
    const exp = Math.abs(n);
    if (n >= -5 && n < 6) return String(Number(v.toPrecision(6)));
    return `${m}e${n < 0 ? "-" : "+"}${String(exp).padStart(2, "0")}`;
  }
  return s.includes(".") ? s.replace(/0+$/, "").replace(/\.$/, "") : s;
}

export class Line {
  #fields = [];
  add(key, value) {
    if (!KEY.test(key)) throw new ProtocolError(`invalid key ${key}`);
    if (!Number.isFinite(value)) throw new ProtocolError(`${key} is not finite`);
    this.#fields.push(`${key}=${formatNumber(value)}`);
    return this;
  }
  seq(n) { this.#fields.push(`_SEQ=${n}`); return this; }
  millis(ms) { this.#fields.push(`_T=${ms}`); return this; }
  toString() { return this.#fields.join(","); }
}

export class Ewma {
  constructor(alpha = 0.05, threshold = 3.0, warmup = 20) {
    Object.assign(this, { alpha, threshold, warmup, n: 0, mean: null, variance: 0 });
  }
  update(x) {
    this.n++;
    if (this.mean === null) { this.mean = x; return { score: 0, anomaly: false }; }
    const sd = Math.sqrt(this.variance);
    const score = sd === 0 ? 0 : (x - this.mean) / sd;
    const anomaly = this.n > this.warmup && Math.abs(score) >= this.threshold;
    if (!anomaly) {
      const delta = x - this.mean;
      this.mean += this.alpha * delta;
      this.variance = (1 - this.alpha) * (this.variance + this.alpha * delta * delta);
    }
    return { score, anomaly };
  }
}

export class Cusum {
  constructor(drift = 0.5, threshold = 8.0, warmup = 100) {
    Object.assign(this, { k: drift, h: threshold, warmup, ref: [], mean: null, sd: 1, pos: 0, neg: 0 });
  }
  update(x) {
    if (this.mean === null) {
      this.ref.push(x);
      if (this.ref.length >= this.warmup) {
        let s = 0;
        for (const v of this.ref) s += v;
        this.mean = s / this.ref.length;
        let ss = 0;
        for (const v of this.ref) ss += (v - this.mean) ** 2;
        this.sd = Math.sqrt(ss / this.ref.length) || 1e-12;
      }
      return { score: 0, anomaly: false };
    }
    const z = (x - this.mean) / this.sd;
    this.pos = Math.max(0, this.pos + z - this.k);
    this.neg = Math.max(0, this.neg - z - this.k);
    const score = Math.max(this.pos, this.neg);
    const anomaly = this.pos >= this.h || this.neg >= this.h;
    if (anomaly) this.pos = this.neg = 0;
    return { score, anomaly };
  }
}

/** Posts samples to a studio's /api/ingest: {ch1: n | [x,y,z], ch2: n, ch3: {x: [], y: []}}. */
export class StudioClient {
  constructor(baseUrl, token = "") {
    this.base = String(baseUrl).replace(/\/+$/, "");
    this.token = token;
  }
  async send(sample) {
    const headers = { "Content-Type": "application/json" };
    if (this.token) headers.Authorization = `Bearer ${this.token}`;
    const response = await fetch(`${this.base}/api/ingest`, { method: "POST", headers, body: JSON.stringify(sample) });
    const body = await response.json().catch(() => ({}));
    if (!response.ok || body.ok === false) throw new Error(body.error || `studio refused (${response.status})`);
    return body;
  }
  async packet() {
    const response = await fetch(`${this.base}/api/instrument`);
    return response.json();
  }
}
