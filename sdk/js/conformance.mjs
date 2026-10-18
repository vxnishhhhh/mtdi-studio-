// Conformance output for tests/test_sdks.py (same inputs as sdk/cpp/conformance.cpp).
import { Cusum, Ewma, Line, parseLine, StudioClient } from "./mtdi.mjs";

const e = new Ewma(), c = new Cusum(), out = [];
for (let i = 0; i < 400; i++) {
  const x = Math.sin(i * 0.37) * 2.0 + (i >= 250 ? 3.0 : 0.0) + (i === 120 ? 9.0 : 0.0);
  const a = e.update(x), b = c.update(x);
  out.push(`D ${i} ${a.score} ${a.anomaly ? 1 : 0} ${b.score} ${b.anomaly ? 1 : 0}`);
}
for (const l of ["CH1=512,CH2=498", "A=1.5e3, B=-.25", "A=1,A=2", "A=", "1A=3", "A=nan", "A=1,", "X=+7."]) {
  try {
    const v = parseLine(l);
    out.push("P OK" + Object.keys(v).sort().map((k) => ` ${k}=${v[k]}`).join(""));
  } catch { out.push("P ERR"); }
}
out.push("L " + new Line().add("TEMP", 21.4).add("N", 40).add("TINY", 0.000123456789).seq(7).toString());
if (process.argv.length === 4) out.push("S " + JSON.stringify(await new StudioClient(process.argv[2], process.argv[3]).send({ ch2: 3.5, source: "JS" })));
console.log(out.join("\n"));
