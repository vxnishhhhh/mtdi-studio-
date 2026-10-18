"""MTDI Studio tests. Standard library only:  python -m unittest discover tests"""
import hashlib
import json
import pathlib
import random
import socket
import sys
import tempfile
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mtdi.engine import Engine  # noqa: E402
from mtdi.pillars.environment import BaselineLock  # noqa: E402
from mtdi.project import ManifestError, load, normalise  # noqa: E402
from mtdi.protocol import ProtocolError, parse_line  # noqa: E402

PROJECTS = [p for p in sorted((ROOT / "projects").iterdir()) if (p / "project.json").exists()]


def manifest(**over):
    base = {"project": {"id": "t"}, "sources": [{"id": "s", "adapter": "http"}],
            "channels": [{"id": "a", "keys": ["A"], "noise_floor": 0.1, "raw_range": [0, 1023]},
                         {"id": "v", "keys": ["X", "Y", "Z"], "noise_floor": 0.1}]}
    base.update(over)
    return normalise(base)


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def feed(engine, clock, n, line_fn, dt=0.05, source="s", label="HARDWARE"):
    for i in range(n):
        clock.t += dt
        engine.ingest_line(source, line_fn(i), label)


class Protocol(unittest.TestCase):
    def test_key_value_and_json(self):
        self.assertEqual(parse_line("CH1=512,CH2=498,CH3=530"), {"CH1": 512.0, "CH2": 498.0, "CH3": 530.0})
        self.assertEqual(parse_line(b"MAGX=-12,MAGY=3.5e2,_SEQ=7\r\n"), {"MAGX": -12.0, "MAGY": 350.0, "_SEQ": 7.0})
        self.assertEqual(parse_line('{"DIST_CM": 41.7}'), {"DIST_CM": 41.7})

    def test_rejects_whole_line(self):
        for bad in ["", "CH1=1,CH2=", "CH1=1,CH1=2", "CH1=nan", "CH1=inf", "1A=3", "CH1 512",
                    '{"A": true}', '{"A": "1"}', "[1]", "A=1;B=2", "A=1e999"]:
            with self.assertRaises(ProtocolError, msg=bad):
                parse_line(bad)


class Manifest(unittest.TestCase):
    def test_defaults(self):
        m = manifest()
        a, v = m["channels"]
        self.assertEqual((a["kind"], v["kind"]), ("scalar", "vector"))
        self.assertEqual(v["axes"], ["x", "y", "z"])
        self.assertEqual(a["sources"], ["s"])

    def test_errors_name_the_field(self):
        cases = [({"sources": []}, "sources"),
                 ({"channels": [{"id": "a", "keys": ["A"], "source": "nope"}]}, "channels[0].source"),
                 ({"channels": [{"id": "a", "keys": ["A", "B"], "kind": "scalar"}]}, "scalar"),
                 ({"channels": [{"id": "a", "keys": ["A"], "domain": "Two Words"}]}, "domain"),
                 ({"sources": [{"id": "s", "adapter": "carrier-pigeon"}]}, "adapter"),
                 ({"nvtra": {"rules": [{"when": {"ghost": ">=6"}, "condition": "x"}]}}, "ghost")]
        for over, needle in cases:
            with self.assertRaises(ManifestError) as ctx:
                manifest(**over)
            self.assertIn(needle, str(ctx.exception))

    def test_domain_is_open_and_physical_is_an_alias(self):
        m = manifest(channels=[{"id": "a", "keys": ["A"], "domain": "cybersecurity"},
                               {"id": "b", "keys": ["B"], "physical": "magnetic"}])
        self.assertEqual([c["domain"] for c in m["channels"]], ["cybersecurity", "magnetic"])

    def test_every_shipped_project_loads(self):
        self.assertGreaterEqual(len(PROJECTS), 3)
        for p in PROJECTS:
            load(p)


class EnvironmentalIntelligence(unittest.TestCase):
    def test_learns_rejects_and_locks(self):
        b = BaselineLock(window=5, noise_floor=0.01)
        rng = random.Random(1)
        t = 0.0
        for _ in range(200):
            t += 0.2
            b.update(10 + rng.gauss(0, 0.05), t)
        self.assertFalse(b.settling)
        self.assertAlmostEqual(b.value, 10, delta=0.05)
        before = b.value
        t += 0.2
        self.assertGreater(b.update(14, t), 3.9)            # an excursion is reported...
        self.assertAlmostEqual(b.value, before, delta=1e-9)  # ...and not learned
        b.frozen = True
        for _ in range(50):
            t += 0.2
            b.update(10.3, t)
        self.assertAlmostEqual(b.value, before, delta=1e-9)  # locked never drifts

    def test_stale_lock_detected(self):
        b = BaselineLock(window=5, noise_floor=0.01)
        t = 0.0
        for i in range(100):
            t += 0.2
            b.update(10 + 0.01 * (i % 3), t)
        for _ in range(150):                                 # 30 s moved: still a minority of the 60 s window
            t += 0.2
            b.update(20 + 0.01 * random.random(), t)
        self.assertFalse(b.snapshot()["stale"])
        for _ in range(250):                                 # 80 s moved: >= 90 % refused, steady -> stale
            t += 0.2
            b.update(20 + 0.01 * random.random(), t)
        self.assertTrue(b.snapshot()["stale"])
        self.assertAlmostEqual(b.snapshot()["stale_offset"], 10, delta=0.1)


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.tmp = tempfile.TemporaryDirectory()
        m = manifest(nvtra={"rules": [{"when": {"a": ">=6", "v": "<3"}, "condition": "A dominant", "text": "rule"}]})
        m["_dir"] = self.tmp.name
        self.engine = Engine(m, clock=self.clock)
        self.rng = random.Random(3)

    def tearDown(self):
        self.tmp.cleanup()

    def quiet(self, i):
        g = self.rng.gauss
        return f"A={500 + g(0, 0.05):.3f},X={1 + g(0, .05):.3f},Y={2 + g(0, .05):.3f},Z={3 + g(0, .05):.3f}"

    def test_quiet_then_event(self):
        feed(self.engine, self.clock, 300, self.quiet)
        p = self.engine.snapshot()
        self.assertEqual(p["fusion"]["condition"], "Ambient conditions")
        self.assertTrue(all(c["evidence"]["state"] == "connected" for c in p["channels"].values()))
        self.assertGreater(p["fusion"]["score"], 70)
        feed(self.engine, self.clock, 10, lambda i: "A=520,X=1,Y=2,Z=3")
        p = self.engine.snapshot()
        self.assertEqual(p["fusion"]["condition"], "A dominant")    # project rule, not hardcoded
        self.assertEqual(p["fusion"]["rule"], "A dominant")

    def test_offline_channel_scores_zero_and_goes_stale(self):
        feed(self.engine, self.clock, 200, self.quiet)
        self.clock.t += 30
        p = self.engine.snapshot()
        self.assertEqual(p["channels"]["a"]["evidence"]["state"], "stale")
        self.assertEqual(p["fusion"]["score"], 0.0)

    def test_clipping_and_limits(self):
        feed(self.engine, self.clock, 200, self.quiet)
        feed(self.engine, self.clock, 1, lambda i: "A=1023,X=1,Y=2,Z=3")
        a = self.engine.snapshot()["channels"]["a"]
        self.assertTrue(a["evidence"]["clipped"])
        self.assertAlmostEqual(a["evidence"]["loq"], a["evidence"]["lod"] * 10 / 3, places=9)

    def test_malformed_lines_counted_not_used(self):
        before = self.engine.snapshot()["sources"]["s"]["lines"]
        self.assertEqual(self.engine.ingest_line("s", "A=1,X="), 0)
        src = self.engine.snapshot()["sources"]["s"]
        self.assertEqual((src["lines"], src["rejected"]), (before, 1))

    def test_environment_refuses_simulated_and_round_trips_real(self):
        feed(self.engine, self.clock, 300, self.quiet, label="SIMULATED")
        with self.assertRaisesRegex(ValueError, "simulated"):
            self.engine.save_environment("lab")
        feed(self.engine, self.clock, 300, self.quiet)
        self.engine.save_environment("lab")
        self.assertEqual(self.engine.environments.names(), ["lab"])
        self.engine.learn()
        feed(self.engine, self.clock, 300, lambda i: "A=530,X=1,Y=2,Z=3")   # a different room
        self.engine.load_environment("lab")
        feed(self.engine, self.clock, 5, lambda i: "A=530,X=1,Y=2,Z=3")
        a = self.engine.snapshot()["channels"]["a"]["environment"]
        self.assertTrue(a["pinned"] and a["frozen"])
        self.assertAlmostEqual(a["deviation"], 30, delta=0.5)        # measured against the saved room

    def test_optional_channel_never_reporting_does_not_block_saving(self):
        m = manifest(channels=[{"id": "a", "keys": ["A"], "noise_floor": 0.1},
                               {"id": "t", "keys": ["T"], "optional": True}])
        m["_dir"] = self.tmp.name
        clock = Clock()
        e = Engine(m, clock=clock)
        feed(e, clock, 300, lambda i: f"A={500 + self.rng.gauss(0, 0.05):.3f}")
        record = e.save_environment("no thermal sensor")
        self.assertEqual(record["absent"], ["t"])
        self.assertEqual(list(record["channels"]), ["a"])

    def test_ac_rms_transform(self):
        m = normalise({"project": {"id": "t"}, "sources": [{"id": "s", "adapter": "http"}],
                       "channels": [{"id": "e", "keys": ["E"], "transform": "ac_rms", "window": 20, "noise_floor": 0.01}]})
        clock = Clock()
        e = Engine(m, clock=clock)
        feed(e, clock, 100, lambda i: f"E={500 + (3 if i % 2 else -3)}")
        self.assertAlmostEqual(e.snapshot()["channels"]["e"]["value"], 3.0, places=6)


class Adapters(unittest.TestCase):
    def free_port(self):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

    def test_tcp_listen_accepts_inductra_bridge_style_lines(self):
        from mtdi.adapters import build
        port = self.free_port()
        m = normalise({"project": {"id": "t"}, "sources": [{"id": "b", "adapter": "tcp", "listen": f"127.0.0.1:{port}"}],
                       "channels": [{"id": "e", "keys": ["CH3", "CH2", "CH1"]}]})
        engine = Engine(m)
        adapter = build(engine, m["sources"][0]).start()
        try:
            for _ in range(50):
                try:
                    conn = socket.create_connection(("127.0.0.1", port), timeout=1)
                    break
                except OSError:
                    time.sleep(0.05)
            with conn:
                conn.sendall(b"CH1=512,CH2=498,CH3=530\nGARBAGE\nCH1=513,CH2=499,CH3=531\n")
                deadline = time.time() + 3
                while engine.snapshot()["channels"]["e"]["evidence"]["samples"] < 2 and time.time() < deadline:
                    time.sleep(0.02)
            p = engine.snapshot()
            self.assertEqual(p["channels"]["e"]["evidence"]["samples"], 2)
            self.assertEqual(p["sources"]["b"]["rejected"], 1)
        finally:
            adapter.stop()

    def test_record_then_replay(self):
        from mtdi.adapters.replay import Recorder, ReplayAdapter
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "rec.jsonl"
            m = manifest()
            m["_dir"] = tmp
            src = Engine(m)
            src.recorders.append(Recorder(path))
            src.ingest_values("s", {"A": 1.0}, "HARDWARE")
            src.ingest_values("s", {"A": 2.0}, "SIMULATED")       # never recorded
            src.ingest_values("s", {"A": 3.0}, "HARDWARE")
            rows = [json.loads(x) for x in path.read_text().splitlines()]
            self.assertEqual([r["values"]["A"] for r in rows], [1.0, 3.0])
            m2 = normalise({"project": {"id": "t"}, "sources": [{"id": "s", "adapter": "replay", "file": str(path), "loop": False}],
                            "channels": [{"id": "a", "keys": ["A"]}]})
            dst = Engine(m2)
            adapter = ReplayAdapter(dst, m2["sources"][0]).start()
            deadline = time.time() + 3
            while dst.snapshot()["channels"]["a"]["evidence"]["samples"] < 2 and time.time() < deadline:
                time.sleep(0.02)
            adapter.stop()
            ev = dst.snapshot()["channels"]["a"]["evidence"]
            self.assertEqual((ev["samples"], ev["data_source"]), (2, "REPLAY"))


class Studio(unittest.TestCase):
    def test_every_project_builds_every_page(self):
        from mtdi.pillars.i3 import pages
        from mtdi.studio import Studio as S
        from mtdi.studio import views
        for p in PROJECTS:
            studio = S(p, simulate=True, start_adapters=False)
            content = views.content_pack(studio.project, True)
            for page in content["pages"]:
                self.assertIsNotNone(pages.build(page, content), f"{p.name} {page['path']}")
            client = studio.app.server.test_client()
            self.assertEqual(client.get("/").status_code, 200)
            state = client.get("/i3/state").get_json()
            self.assertIn("mtdi.score", state)
            self.assertEqual(client.post("/i3/action", json={"action": "save", "args": {"name": "x"}}).status_code, 400)

    def test_ingest_only_for_http_sources(self):
        from mtdi.studio import Studio as S
        studio = S(ROOT / "projects" / "inductra-vaion", start_adapters=False)
        client = studio.app.server.test_client()
        ok = client.post("/mtdi/ingest", json={"source": "rf", "values": {"RF_DEV_DB": 1.5}}).get_json()
        self.assertEqual(ok, {"ok": True, "channels_updated": 1})
        self.assertEqual(client.post("/mtdi/ingest", json={"source": "uno", "line": "MAGX=1"}).status_code, 400)

    def test_placeholder_i3_pack_builds(self):
        from mtdi.pillars.i3 import load as load_pack, pages
        content = load_pack(ROOT / "mtdi" / "pillars" / "i3" / "examples" / "placeholder.json")
        for page in content["pages"]:
            pages.build(page, content)


class InductraIsUnchanged(unittest.TestCase):
    """The firmware in projects/inductra-vaion must stay byte-identical to Inductra's."""
    SHA = {"firmware/inductra_uno_bridge.ino": "11da46b28db169967fff60fab0d8763941789f49d43a983619a6fb73aa430359",
           "firmware/inductra_uno_adc.ino": "795977638f9c0c8f8bf73ccf7da18540e6f9ccdb59198f51203e0803ececfd64",
           "bridge/uno_network_bridge.py": "0a58ef8c1e8d2bf0725bcc3d59a6e07d42efc5895682b6317e079ce80efb5cb2"}

    def test_hashes(self):
        base = ROOT / "projects" / "inductra-vaion"
        for rel, sha in self.SHA.items():
            self.assertEqual(hashlib.sha256((base / rel).read_bytes()).hexdigest(), sha, rel)


class EveryField(unittest.TestCase):
    """Software, computers, networks and security run on the same pillars as sensors."""

    def test_process_adapter_runs_any_program(self):
        from mtdi.adapters import build
        with tempfile.TemporaryDirectory() as tmp:
            m = normalise({"project": {"id": "t"},
                           "sources": [{"id": "p", "adapter": "process",
                                        "command": [sys.executable, "-c", "import time\nfor i in range(5): print(f'LAT_MS={10+i}', flush=True); time.sleep(0.02)\nprint('junk')"]}],
                           "channels": [{"id": "lat", "keys": ["LAT_MS"], "domain": "network"}]})
            m["_dir"] = tmp
            engine = Engine(m)
            adapter = build(engine, m["sources"][0]).start()
            deadline = time.time() + 5
            while time.time() < deadline:
                snap = engine.snapshot()
                if snap["channels"]["lat"]["evidence"]["samples"] >= 5 and snap["sources"]["p"]["rejected"] >= 1:
                    break
                time.sleep(0.05)
            adapter.stop()
            p = engine.snapshot()
            self.assertEqual(p["channels"]["lat"]["evidence"]["samples"], 5)
            self.assertEqual(p["channels"]["lat"]["evidence"]["data_source"], "SOFTWARE")
            self.assertGreaterEqual(p["sources"]["p"]["rejected"], 1)

    @unittest.skipUnless(pathlib.Path("/proc/stat").exists(), "Linux /proc reader")
    def test_system_adapter_reads_the_host(self):
        from mtdi.adapters.system import reader
        r = reader()
        r.read("/")
        time.sleep(0.3)
        values = r.read("/")
        for key in ("CPU_PCT", "MEM_PCT", "LOAD1", "DISK_PCT"):
            self.assertIn(key, values)
        self.assertTrue(0 <= values["MEM_PCT"] <= 100)


class AdoptAndDescribe(unittest.TestCase):
    def test_adopt_vendors_mtdi_and_keeps_existing_agents_md(self):
        from mtdi.adopt import adopt
        with tempfile.TemporaryDirectory() as tmp:
            (pathlib.Path(tmp) / "AGENTS.md").write_text("# Mine\n")
            adopt(tmp, project_id="demo", name="Demo")
            root = pathlib.Path(tmp)
            self.assertTrue((root / "mtdi" / "engine.py").exists())
            self.assertTrue((root / "mtdi-matlab" / "+mtdi" / "analyze.m").exists())
            self.assertEqual(load(root / "mtdi-project")["project"]["id"], "demo")
            agents = (root / "AGENTS.md").read_text()
            self.assertTrue(agents.startswith("# Mine"))
            adopt(tmp, force=True)
            self.assertEqual((root / "AGENTS.md").read_text().count("MTDI:BEGIN"), 1)
            with self.assertRaises(FileExistsError):
                adopt(tmp)

    def test_describe_is_json(self):
        import contextlib
        import io
        from mtdi.__main__ import main
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            main(["describe"])
        data = json.loads(buf.getvalue())
        self.assertIn("process", data["adapters"])
        self.assertEqual(len(data["pillars"]), 5)


class TwoImplementations(unittest.TestCase):
    """The MATLAB toolbox must agree with Python on the same capture (run in GNU Octave)."""

    @unittest.skipUnless(__import__("shutil").which("octave"), "GNU Octave not installed")
    def test_matlab_agrees_with_python(self):
        import subprocess
        from mtdi.analysis import analyze, read_recording
        with tempfile.TemporaryDirectory() as tmp:
            rec = pathlib.Path(tmp) / "rec.jsonl"
            rng = random.Random(9)
            rows = [{"t": 100 + i * 0.05, "source": "ranger",
                     "values": {"DIST_CM": round(180 + rng.gauss(0, 0.4), 3), "ECHO_US": 10600 + rng.randint(-30, 30), "_SEQ": i}}
                    for i in range(300)]
            rec.write_text("\n".join(json.dumps(r) for r in rows))
            manifest = ROOT / "projects" / "ultrasonic-room" / "project.json"
            py = pathlib.Path(tmp) / "py.json"
            py.write_text(json.dumps(analyze(load(manifest), read_recording(rec))))
            result = subprocess.run(["octave", "--no-gui", "--quiet", "--eval",
                                     f"addpath('{ROOT / 'matlab'}'); exit(~mtdi.verify('{rec}', '{manifest}', '{py}'))"],
                                    capture_output=True, text=True, timeout=120)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class Integrations(unittest.TestCase):
    """The wizard end to end against fake GitHub, Vercel and Notion; tokens never touch disk."""

    def test_create_with_every_integration(self):
        import subprocess
        import webbrowser
        from argparse import Namespace
        from mtdi import create
        from mtdi.integrations import github, notion, vercel
        calls = []
        with tempfile.TemporaryDirectory() as tmp:
            bare = pathlib.Path(tmp) / "remote.git"
            subprocess.run(["git", "init", "--bare", "-q", str(bare)], check=True)

            def fake(method, url, token_value=None, body=None, headers=None, raw=None, timeout=60):
                calls.append((method, url, token_value, body, raw))
                if "api.github.com" in url:
                    return {"clone_url": bare.as_uri(), "html_url": "https://github.com/me/rover", "full_name": "me/rover"}
                if "/v2/files" in url:
                    return {}
                if "/v13/deployments" in url:
                    return {"url": "rover.vercel.app", "id": "dpl_1", "readyState": "QUEUED"}
                if "api.notion.com" in url:
                    return {"url": "https://notion.so/rover", "id": "p1"}
                raise AssertionError(url)
            secrets = {"GITHUB_TOKEN": "ghp_SECRET111", "VERCEL_TOKEN": "vc_SECRET222", "NOTION_TOKEN": "ntn_SECRET333",
                       "NOTION_PARENT_PAGE_ID": "0123456789abcdef0123456789abcdef"}
            saved = {k: __import__("os").environ.get(k) for k in secrets}
            opened = []
            originals = (github.http, vercel.http, notion.http, github._gh_ready, webbrowser.open)
            try:
                __import__("os").environ.update(secrets)
                github.http = vercel.http = notion.http = fake
                github._gh_ready = lambda: False
                webbrowser.open = lambda url, new=0: opened.append(url)
                target = pathlib.Path(tmp) / "rover"
                args = Namespace(name="Rover", id=None, description="A rover.", standalone=str(target), github="rover",
                                 public=False, vercel="rover-studio", notion="env", matlab=True, yes=True, dry_run=False)
                results = create.run(args)
            finally:
                github.http, vercel.http, notion.http, github._gh_ready, webbrowser.open = originals
                for k, v in saved.items():
                    if v is None:
                        __import__("os").environ.pop(k, None)
                    else:
                        __import__("os").environ[k] = v
            self.assertEqual(results["github"]["full_name"], "me/rover")
            self.assertEqual(results["vercel"]["url"], "https://rover.vercel.app")
            self.assertEqual(results["notion"]["url"], "https://notion.so/rover")
            self.assertIn("matlab.mathworks.com/open/github", opened[0])
            pushed = subprocess.run(["git", "--git-dir", str(bare), "log", "--oneline", "main"], capture_output=True, text=True)
            self.assertIn("MTDI", pushed.stdout)
            uploads = [c for c in calls if "/v2/files" in c[1]]
            deploy = [c for c in calls if "/v13/deployments" in c[1]][0]
            self.assertEqual(len(uploads), len(deploy[3]["files"]))
            self.assertEqual(deploy[3]["name"], "rover-studio")
            for path in target.rglob("*"):
                if path.is_file():
                    data = path.read_bytes()
                    for secret in ("ghp_SECRET111", "vc_SECRET222", "ntn_SECRET333"):
                        self.assertNotIn(secret.encode(), data, f"token written to {path}")


class Site(unittest.TestCase):
    def test_static_render_matches_components(self):
        from mtdi.pillars.i3 import static
        from mtdi.studio import views
        pack = views.content_pack(load(ROOT / "projects" / "host-health"), True)
        html = static.page(pack, pack["pages"][2])
        self.assertEqual(html.count('class="i3-orbit-card"'), 5)
        self.assertIn('data-i3-bind="mtdi.score"', html)

    def test_project_site_builds(self):
        from mtdi.site import build_project_site
        with tempfile.TemporaryDirectory() as tmp:
            out = build_project_site(ROOT / "projects" / "ultrasonic-room", pathlib.Path(tmp) / "s", seconds=3)
            replay = json.loads((out / "replay.json").read_text())
            self.assertEqual(len(replay["states"]), 3)
            self.assertEqual(replay["data_source"], "SIMULATED")
            self.assertTrue((out / "index.html").exists() and (out / "environment" / "index.html").exists())


if __name__ == "__main__":
    unittest.main()
