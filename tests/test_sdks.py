"""Every SDK agrees with Python: C++, Java, JavaScript and MATLAB (run in GNU Octave).

Each SDK prints its EWMA and CUSUM scores for the same 400-sample series, its verdict on
eight protocol lines, and one formatted line. The numbers must match the Python package
to 1e-9. Clients that post to a studio are run against a local fake studio that checks
the ingest token. A missing toolchain skips its test (CI installs all of them).
"""
import json
import math
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from mtdi import ml  # noqa: E402
from mtdi.protocol import ProtocolError, format_line, parse_line  # noqa: E402
from test_backend import FakeService  # noqa: E402

LINES = ["CH1=512,CH2=498", "A=1.5e3, B=-.25", "A=1,A=2", "A=", "1A=3", "A=nan", "A=1,", "X=+7."]


def expected():
    e, c = ml.EWMA(), ml.CUSUM()
    rows = []
    for i in range(400):
        x = math.sin(i * 0.37) * 2.0 + (3.0 if i >= 250 else 0.0) + (9.0 if i == 120 else 0.0)
        a, b = e.update(x), c.update(x)
        rows.append((i, a["score"], int(a["anomaly"]), b["score"], int(b["anomaly"])))
    parsed = []
    for line in LINES:
        try:
            v = parse_line(line)
            parsed.append({k: v[k] for k in sorted(v)})
        except ProtocolError:
            parsed.append(None)
    fmt = format_line({"TEMP": 21.4, "N": 40, "TINY": 0.000123456789}) + ",_SEQ=7"
    return rows, parsed, fmt


def read(output):
    rows, parsed, fmt, sent = [], [], None, None
    for line in output.splitlines():
        tag, _, rest = line.partition(" ")
        if tag == "D":
            i, a, af, b, bf = rest.split()
            rows.append((int(i), float(a), int(af in ("1", "true")), float(b), int(bf in ("1", "true"))))
        elif tag == "P":
            if rest == "ERR":
                parsed.append(None)
            else:
                parsed.append({k: float(v) for k, v in (p.split("=") for p in rest.split()[1:])})
        elif tag == "L":
            fmt = rest
        elif tag == "S":
            sent = rest
    return rows, parsed, fmt, sent


class SDKs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows, cls.parsed, cls.fmt = expected()
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = pathlib.Path(cls.tmp.name)
        cls.posts = []
        cls.studio = FakeService({("POST", "/api/ingest"): cls._ingest})

    @classmethod
    def _ingest(cls, req):
        cls.posts.append(req)
        if req["headers"].get("Authorization") != "Bearer sdk-token":
            return 403, {"ok": False, "error": "token"}, "application/json"
        return 200, {"ok": True, "accepted": 1}, "application/json"

    @classmethod
    def tearDownClass(cls):
        cls.studio.close()
        cls.tmp.cleanup()

    def check(self, output, name):
        rows, parsed, fmt, sent = read(output)
        self.assertEqual(len(rows), 400, name)
        for mine, ref in zip(rows, self.rows):
            self.assertEqual((mine[0], mine[2], mine[4]), (ref[0], ref[2], ref[4]), f"{name} flags at {ref[0]}")
            self.assertAlmostEqual(mine[1], ref[1], delta=1e-9, msg=f"{name} ewma at {ref[0]}")
            self.assertAlmostEqual(mine[3], ref[3], delta=1e-9, msg=f"{name} cusum at {ref[0]}")
        self.assertEqual(parsed, self.parsed, name)
        self.assertEqual(fmt, self.fmt, name)
        return sent

    def run_tool(self, cmd, **kw):
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180, **kw)
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        return result.stdout

    def test_cpp(self):
        if not shutil.which("g++"):
            self.skipTest("g++ not installed")
        exe = self.out / "conformance"
        self.run_tool(["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "-O2", "-I", str(ROOT / "sdk/cpp"),
                       str(ROOT / "sdk/cpp/conformance.cpp"), "-o", str(exe)])
        self.check(self.run_tool([str(exe)]), "c++")
        self.run_tool(["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "-I", str(ROOT / "sdk/cpp"),
                       str(ROOT / "sdk/cpp/example.cpp"), "-o", str(self.out / "example")])
        for line in self.run_tool([str(self.out / "example"), "5"]).splitlines():
            parse_line(line)                       # the example's output is valid protocol

    def test_java(self):
        if not shutil.which("javac"):
            self.skipTest("javac not installed")
        classes = self.out / "java"
        self.run_tool(["javac", "-Xlint:all", "-Werror", "-d", str(classes), str(ROOT / "sdk/java/src/io/mtdi/Mtdi.java"),
                       str(ROOT / "sdk/java/test/Conformance.java")])
        sent = self.check(self.run_tool(["java", "-cp", str(classes), "Conformance", self.studio.url, "sdk-token"]), "java")
        self.assertEqual(json.loads(sent)["ok"], True)

    def test_javascript(self):
        if not shutil.which("node"):
            self.skipTest("node not installed")
        sent = self.check(self.run_tool(["node", str(ROOT / "sdk/js/conformance.mjs"), self.studio.url, "sdk-token"]), "js")
        self.assertEqual(json.loads(sent)["ok"], True)
        posted = [json.loads(r["body"]) for r in self.posts if b'"JS"' in r["body"]]
        self.assertEqual(posted, [{"ch2": 3.5, "source": "JS"}])

    def test_matlab_in_octave(self):
        if not shutil.which("octave"):
            self.skipTest("octave not installed")
        script = ("addpath('%s'); i=0:399; x=sin(i*0.37)*2+(i>=250)*3+(i==120)*9;"
                  "[s,a]=mtdi.ewma(x); [c,b]=mtdi.cusum(x); printf('D %%d %%.17g %%d %%.17g %%d\\n', [i; s; a; c; b]);"
                  % (ROOT / "matlab"))
        rows = read(self.run_tool(["octave", "--no-gui", "--quiet", "--eval", script]))[0]
        for mine, ref in zip(rows, self.rows):
            self.assertEqual((mine[2], mine[4]), (ref[2], ref[4]), f"octave flags at {ref[0]}")
            self.assertAlmostEqual(mine[1], ref[1], delta=1e-9)
            self.assertAlmostEqual(mine[3], ref[3], delta=1e-9)
        self.assertEqual(len(rows), 400)

    def test_matlab_fusion_calibration_drift_match_python(self):
        if not shutil.which("octave"):
            self.skipTest("octave not installed")
        from mtdi import fusion
        rng = __import__("random").Random(4)
        raw = [rng.uniform(0, 50) for _ in range(40)]
        temp = [rng.uniform(10, 40) for _ in range(40)]
        ref = [1.7 * r - 2.3 + 0.04 * (t - 25) + rng.gauss(0, 0.2) for r, t in zip(raw, temp)]
        res = [0.4, -0.9, 1.3, 2.2]
        vec = lambda xs: "[" + " ".join(repr(x) for x in xs) + "]"  # noqa: E731
        script = (f"addpath('{ROOT / 'matlab'}');"
                  f"[v,var]=mtdi.fuse([10.5 9.8 10.1],[0.04 0.25 0.09]);"
                  f"a=mtdi.calibrate({vec(raw)},{vec(ref)});"
                  f"b=mtdi.calibrate({vec(raw)},{vec(ref)},{vec(temp)},25,'T');"
                  f"fid=fopen('{{out}}','w'); fprintf(fid,'%s',jsonencode(b)); fclose(fid);"
                  f"d=mtdi.drift({vec(res)},0.5);"
                  "printf('%.17g\\n',[v var a.gain a.offset a.residual_sd b.gain b.offset b.temp_coeff b.residual_sd "
                  "mtdi.applyCalibration(b,12.5,31) d.rms d.bias d.limit double(d.drift)]);")
        with tempfile.TemporaryDirectory() as d:
            out = pathlib.Path(d) / "cal.json"
            got = [float(x) for x in self.run_tool(["octave", "--no-gui", "--quiet", "--eval",
                                                     script.replace("{out}", str(out))]).split()]
            saved = json.loads(out.read_text())
            project = {"project": {"id": "m"}, "sources": [{"id": "s", "adapter": "http"}],
                       "channels": [{"id": "co", "keys": ["CO"], "noise_floor": 0.1, "calibration": "cal.json"}]}
            (pathlib.Path(d) / "project.json").write_text(json.dumps(project))
            from mtdi.project import load
            self.assertEqual(load(d)["channels"][0]["calibration"]["temperature_key"], "T")   # MATLAB file loads
        self.assertEqual(saved["method"], "least-squares+temperature")
        v, var = fusion.fuse([(10.5, 0.04), (9.8, 0.25), (10.1, 0.09)])
        a = fusion.Calibration.fit(raw, ref)
        b = fusion.Calibration.fit(raw, ref, temperature=temp, temp_ref=25)
        d = fusion.drift_summary(res, 0.5)
        want = [v, var, a.gain, a.offset, a.residual_sd, b.gain, b.offset, b.temp_coeff, b.residual_sd,
                b.apply(12.5, 31), d["rms"], d["bias"], d["limit"], float(d["drift"])]
        self.assertEqual(len(got), len(want))
        for g, w in zip(got, want):
            self.assertAlmostEqual(g, w, delta=1e-9 * max(1.0, abs(w)))

    def test_matlab_examples_run(self):
        if not shutil.which("octave"):
            self.skipTest("octave not installed")
        examples = sorted((ROOT / "matlab" / "examples").glob("*.m"))
        self.assertGreaterEqual(len(examples), 3)
        for ex in examples:
            out = self.run_tool(["octave", "--no-gui", "--quiet", str(ex)], cwd=ROOT)
            self.assertIn(f"OK {ex.stem}", out, ex.name)


if __name__ == "__main__":
    unittest.main()
