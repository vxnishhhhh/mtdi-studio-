"""Backend tests: ML, storage, LLM, voice, NVTRA bot, studio bridge and studio ingest.

Network services are replaced by local HTTP servers that speak the same protocol, so
the real request building and response parsing run. Standard library only.
"""
import json
import math
import os
import pathlib
import random
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mtdi import llm, ml, storage, voice  # noqa: E402
from mtdi.bridge import StudioBridge, mapping_for, sample_for  # noqa: E402
from mtdi.engine import Engine  # noqa: E402
from mtdi.project import normalise  # noqa: E402

KEYS = ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "GROQ_API_KEY", "XAI_API_KEY",
        "ELEVENLABS_API_KEY", "MTDI_LLM_PROVIDER", "MTDI_LLM_MODEL"]


def no_keys(**extra):
    env = {k: v for k, v in os.environ.items() if k not in KEYS}
    env.update(extra)
    return mock.patch.dict(os.environ, env, clear=True)


class FakeService:
    """A local HTTP server. ``routes``: {(method, path_prefix): handler(request) -> (status, body, ctype)}."""

    def __init__(self, routes):
        self.requests = []
        service = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _handle(self):
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length) if length else b""
                req = {"method": self.command, "path": self.path, "headers": self.headers, "body": body}
                service.requests.append(req)
                for (method, prefix), fn in routes.items():
                    if method == self.command and self.path.startswith(prefix):
                        status, out, ctype = fn(req)
                        break
                else:
                    status, out, ctype = 404, b"no route", "text/plain"
                data = out if isinstance(out, bytes) else json.dumps(out).encode()
                self.send_response(status)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            do_GET = do_POST = do_PUT = do_DELETE = _handle

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


# ── machine learning ─────────────────────────────────────────────────────────
class Anomaly(unittest.TestCase):
    def stream(self, n=300, spike_at=250, spike=12.0, seed=1):
        rng = random.Random(seed)
        return [rng.gauss(10, 1) + (spike if i == spike_at else 0) for i in range(n)]

    def test_point_detectors_find_the_spike_and_nothing_else(self):
        for det in (ml.ZScore(threshold=5), ml.EWMA(alpha=0.05, threshold=5), ml.MAD(threshold=6)):
            flagged = [i for i, x in enumerate(self.stream()) if det.update(x)["anomaly"]]
            self.assertEqual(flagged, [250], type(det).__name__)

    def test_cusum_catches_a_small_persistent_shift(self):
        rng = random.Random(2)
        det = ml.CUSUM(drift=0.5, threshold=8)
        flags = [i for i in range(400) if det.update(rng.gauss(0, 1) + (1.0 if i >= 200 else 0))["anomaly"]]
        self.assertTrue(flags and 200 <= flags[0] < 240, flags[:3])
        self.assertFalse([f for f in flags if f < 200])

    def test_page_hinkley_detects_drift(self):
        rng = random.Random(3)
        det = ml.PageHinkley(delta=0.05, threshold=20)
        flags = [i for i in range(600) if det.update(rng.gauss(0, 1) + (3.0 if i >= 300 else 0))["anomaly"]]
        self.assertTrue(flags and 300 <= flags[0] < 330)


class Learning(unittest.TestCase):
    def blobs(self, seed=4):
        rng = random.Random(seed)
        centres = {"a": (0, 0), "b": (6, 6), "c": (0, 8)}
        X, y = [], []
        for label, (cx, cy) in centres.items():
            for _ in range(40):
                X.append([cx + rng.gauss(0, 0.8), cy + rng.gauss(0, 0.8)])
                y.append(label)
        return X, y

    def test_classifiers_separate_clusters(self):
        X, y = self.blobs()
        Xt, yt = self.blobs(seed=9)
        for model in (ml.KNN(k=5), ml.NearestCentroid(), ml.LogisticRegression(epochs=200), ml.GaussianNB()):
            model.fit(X, y)
            accuracy = sum(model.predict(r) == t for r, t in zip(Xt, yt)) / len(yt)
            self.assertGreaterEqual(accuracy, 0.95, type(model).__name__)
            proba = model.predict_proba(Xt[0])
            self.assertAlmostEqual(sum(proba.values()), 1.0, places=6)

    def test_rejection_says_unknown(self):
        X, y = self.blobs()
        self.assertEqual(ml.KNN(k=3, reject=1.0).fit(X, y).predict([50, -50]), "UNKNOWN")
        self.assertEqual(ml.NearestCentroid(reject=2.0).fit(X, y).predict([50, -50]), "UNKNOWN")

    def test_kmeans_recovers_three_groups(self):
        X, y = self.blobs()
        km = ml.KMeans(k=3).fit(X)
        groups = {}
        for label, cluster in zip(y, km.labels):
            groups.setdefault(label, set()).add(cluster)
        self.assertTrue(all(len(c) == 1 for c in groups.values()))
        self.assertEqual(len({next(iter(c)) for c in groups.values()}), 3)

    def test_forecasting(self):
        h = ml.Holt(alpha=0.5, beta=0.3)
        for i in range(50):
            h.update(3 + 2 * i)
        self.assertAlmostEqual(h.forecast(10), 3 + 2 * 59, delta=0.5)
        line = ml.OnlineLinear()
        for x in range(10):
            line.update(x, 1.5 * x - 4)
        a, b = line.coefficients()
        self.assertAlmostEqual(a, -4)
        self.assertAlmostEqual(b, 1.5)
        self.assertAlmostEqual(line.time_to(11), 10)

    def test_features(self):
        rate = 100.0
        wave = [math.sin(2 * math.pi * 7 * t / rate) for t in range(200)]
        self.assertAlmostEqual(ml.dominant_frequency(wave, rate), 7.0, places=6)
        power = ml.band_power(wave, rate, {"low": (0, 5), "mid": (5, 10), "high": (10, 50)})
        self.assertGreater(power["mid"], 100 * (power["low"] + power["high"]))
        f = ml.window_features([1, 2, 3, 4, 5])
        self.assertEqual((f["mean"], f["range"], f["slope"]), (3, 4, 1.0))

    def test_monitor_reads_channel_deviation(self):
        m = normalise({"project": {"id": "t"}, "sources": [{"id": "s", "adapter": "http"}],
                       "channels": [{"id": "a", "keys": ["A"], "noise_floor": 0.1}],
                       "environment": {"window": 2.0}})
        clock = [0.0]
        engine = Engine(m, clock=lambda: clock[0])
        monitor = ml.Monitor(lambda: ml.MAD(threshold=6, warmup=20))
        rng = random.Random(5)
        events = []
        for i in range(120):
            clock[0] = i * 0.2
            engine.ingest_values("s", {"A": 5 + rng.gauss(0, 0.05) + (4 if i == 100 else 0)})
            events += monitor.update(engine.snapshot())
        self.assertEqual([e["channel"] for e in events], ["a"])


# ── storage ──────────────────────────────────────────────────────────────────
class Storage(unittest.TestCase):
    def test_local_store_round_trip_and_confinement(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = storage.open(tmp)
            store.put_json("a/b.json", {"x": 1})
            self.assertEqual(store.get_json("a/b.json"), {"x": 1})
            self.assertEqual([i["key"] for i in store.list("a/")], ["a/b.json"])
            for bad in ("../escape", "/abs", "a/../../x"):
                with self.assertRaises(storage.StoreError):
                    store.put(bad, b"x")
            store.delete("a/b.json")
            self.assertFalse(store.exists("a/b.json"))

    def test_encryption(self):
        with tempfile.TemporaryDirectory() as tmp:
            key = storage.generate_key()
            raw = storage.open(tmp)
            enc = storage.encrypted(raw, key)
            enc.put("secret.txt", b"hello")
            self.assertNotIn(b"hello", raw.get("secret.txt"))
            self.assertEqual(enc.get("secret.txt"), b"hello")
            with self.assertRaises(storage.StoreError):
                storage.encrypted(raw, storage.generate_key()).get("secret.txt")
            blob = bytearray(raw.get("secret.txt"))
            blob[-1] ^= 1
            raw.put("secret.txt", bytes(blob))
            with self.assertRaises(storage.StoreError):
                enc.get("secret.txt")
            raw.put("moved.txt", raw.get("secret.txt"))          # same bytes under another name
            with self.assertRaises(storage.StoreError):
                enc.get("moved.txt")

    def test_sigv4_matches_aws_documentation_example(self):
        import datetime
        from mtdi.storage.s3 import EMPTY_SHA256, sign
        h = sign("GET", "https://examplebucket.s3.amazonaws.com/test.txt", {"Range": "bytes=0-9"}, EMPTY_SHA256,
                 "AKIAIOSFODNN7EXAMPLE", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY", "us-east-1",
                 now=datetime.datetime(2013, 5, 24, tzinfo=datetime.timezone.utc))
        self.assertTrue(h["authorization"].endswith(
            "Signature=f0e8bdb87c964420e857bd35b5d6ed310bd44f0170aba48dd91039c6036bdb41"))

    def test_s3_store_against_an_s3_compatible_server(self):
        objects = {}

        def put(req):
            objects[req["path"].split("?")[0]] = req["body"]
            return 200, b"", "text/plain"

        def get(req):
            path, _, query = req["path"].partition("?")
            if "list-type=2" in query:
                prefix = [p.split("=", 1)[1] for p in query.split("&") if p.startswith("prefix=")][0]
                prefix = __import__("urllib.parse").parse.unquote(prefix)
                items = "".join(f"<Contents><Key>{k[len('/bkt/'):]}</Key><Size>{len(v)}</Size></Contents>"
                                for k, v in sorted(objects.items()) if k[len('/bkt/'):].startswith(prefix))
                return 200, (f'<?xml version="1.0"?><ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
                             f"{items}<IsTruncated>false</IsTruncated></ListBucketResult>").encode(), "application/xml"
            return (200, objects[path], "application/octet-stream") if path in objects else (404, b"", "text/plain")

        def delete(req):
            objects.pop(req["path"], None)
            return 204, b"", "text/plain"

        fake = FakeService({("PUT", "/bkt/"): put, ("GET", "/bkt"): get, ("DELETE", "/bkt/"): delete})
        try:
            env = {"MTDI_S3_ACCESS_KEY_ID": "AKIDTEST", "MTDI_S3_SECRET_ACCESS_KEY": "secret",
                   "MTDI_S3_ENDPOINT": fake.url, "MTDI_S3_REGION": "auto"}
            with mock.patch.dict(os.environ, env):
                store = storage.open("s3://bkt/projects")
                store.put("x/data.bin", b"\x00\x01payload")
                self.assertEqual(store.get("x/data.bin"), b"\x00\x01payload")
                self.assertEqual(store.list("x/"), [{"key": "x/data.bin", "bytes": 9}])
                store.delete("x/data.bin")
                with self.assertRaises(storage.StoreError):
                    store.get("x/data.bin")
            auth = fake.requests[0]["headers"]["Authorization"]
            self.assertTrue(auth.startswith("AWS4-HMAC-SHA256 Credential=AKIDTEST/"))
            self.assertIn("/auto/s3/aws4_request", auth)
            import hashlib
            self.assertEqual(fake.requests[0]["headers"]["x-amz-content-sha256"],
                             hashlib.sha256(b"\x00\x01payload").hexdigest())
        finally:
            fake.close()

    def test_project_backup_and_restore(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = storage.encrypted(storage.open(pathlib.Path(tmp) / "remote"), storage.generate_key())
            keys = storage.backup_project(ROOT / "projects" / "host-health", store, prefix="hh")
            self.assertIn("hh/project.json", keys)
            out = storage.restore_project(store, "hh", pathlib.Path(tmp) / "back")
            restored = pathlib.Path(tmp) / "back" / "project.json"
            self.assertTrue(out and restored.read_bytes() == (ROOT / "projects/host-health/project.json").read_bytes())


# ── language models, voice, NVTRA ────────────────────────────────────────────
class LanguageModels(unittest.TestCase):
    def test_no_key_is_a_clear_error(self):
        with no_keys():
            self.assertEqual(llm.available(), [])
            with self.assertRaises(llm.LLMError):
                llm.chat([{"role": "user", "content": "hi"}])

    def test_each_provider_shape(self):
        replies = {
            "/v1/messages": {"content": [{"type": "text", "text": "anthropic ok"}]},
            "/v1/chat/completions": {"choices": [{"message": {"content": "compatible ok"}}]},
            "/v1beta/models/": {"candidates": [{"content": {"parts": [{"text": "gemini ok"}]}}]},
        }
        fake = FakeService({("POST", p): (lambda r, p=p: (200, replies[p], "application/json")) for p in replies})
        try:
            for provider, key, expect in (("anthropic", "ANTHROPIC_API_KEY", "anthropic ok"),
                                          ("openai", "OPENAI_API_KEY", "compatible ok"),
                                          ("groq", "GROQ_API_KEY", "compatible ok"),
                                          ("gemini", "GEMINI_API_KEY", "gemini ok")):
                with no_keys(**{key: "k-" + provider, f"MTDI_{provider.upper()}_BASE_URL": fake.url}):
                    out = llm.chat([{"role": "user", "content": "q"}], system="sys")
                    self.assertEqual((out["text"], out["provider"]), (expect, provider))
            sent = {r["path"].split("?")[0]: r for r in fake.requests}
            a = json.loads(sent["/v1/messages"]["body"])
            self.assertEqual((a["system"], a["messages"][0]["content"]), ("sys", "q"))
            self.assertEqual(sent["/v1/messages"]["headers"]["x-api-key"], "k-anthropic")
        finally:
            fake.close()


class Voice(unittest.TestCase):
    def test_transcribe_and_speak(self):
        fake = FakeService({("POST", "/v1/audio/transcriptions"): lambda r: (200, {"text": " hello nvtra "}, "application/json"),
                            ("POST", "/v1/text-to-speech/"): lambda r: (200, b"ID3fake-mp3", "audio/mpeg")})
        try:
            with no_keys(GROQ_API_KEY="g", ELEVENLABS_API_KEY="e", MTDI_GROQ_BASE_URL=fake.url,
                         MTDI_ELEVENLABS_BASE_URL=fake.url):
                self.assertEqual(voice.transcribe(b"RIFFdata", "audio/wav"),
                                 {"text": "hello nvtra", "provider": "groq"})
                self.assertEqual(voice.speak("hi")["audio"], b"ID3fake-mp3")
            upload = fake.requests[0]
            self.assertIn(b'name="model"\r\n\r\nwhisper-large-v3', upload["body"])
            self.assertIn(b"RIFFdata", upload["body"])
            self.assertEqual(fake.requests[1]["headers"]["xi-api-key"], "e")
            with no_keys():
                with self.assertRaises(voice.VoiceError):
                    voice.transcribe(b"x")
        finally:
            fake.close()


class Bot(unittest.TestCase):
    def runner(self):
        from mtdi.runtime import Runner
        m = normalise({"project": {"id": "t", "name": "Test"}, "sources": [{"id": "s", "adapter": "http"}],
                       "channels": [{"id": "a", "label": "Level", "keys": ["A"], "noise_floor": 0.1}]})
        r = Runner(m, start=False)
        r.engine.ingest_values("s", {"A": 1.0})
        return r

    def test_offline_rules_then_model_with_context(self):
        from mtdi.bot import Bot as B
        with no_keys():
            out = B(self.runner()).reply("what is the level?")
            self.assertEqual(out["engine"], "rules")
            self.assertTrue(out["text"])
        fake = FakeService({("POST", "/v1/messages"): lambda r: (200, {"content": [{"type": "text", "text": "Level is steady."}]},
                                                                  "application/json")})
        try:
            with no_keys(ANTHROPIC_API_KEY="k", MTDI_ANTHROPIC_BASE_URL=fake.url):
                out = B(self.runner()).reply("what is the level?")
            self.assertEqual(out["text"], "Level is steady.")
            system = json.loads(fake.requests[0]["body"])["system"]
            self.assertIn('"label": "Level"', system)
        finally:
            fake.close()

    def test_invented_number_is_replaced_by_rules(self):
        from mtdi.bot import Bot as B
        fake = FakeService({("POST", "/v1/messages"): lambda r: (200, {"content": [{"type": "text", "text": "Level is 42.7 units."}]},
                                                                  "application/json")})
        try:
            with no_keys(ANTHROPIC_API_KEY="k", MTDI_ANTHROPIC_BASE_URL=fake.url):
                bot = B(self.runner())
                out = bot.reply("what is the level?")
        finally:
            fake.close()
        self.assertEqual(out["engine"], "rules")
        self.assertIn("42.7", out["note"])
        self.assertNotIn("42.7", out["text"])
        self.assertEqual(bot.history, [])              # a rejected answer is not remembered

    def test_research_command_uses_the_researcher(self):
        from unittest import mock
        from mtdi import bot as botmod
        found = {"result": [{"title": "Kalman filtering", "year": 1960, "source": "crossref", "url": "https://doi.org/x"}],
                 "sources": ["crossref"], "errors": {"wikipedia": "HTTPError: 429"}}
        with no_keys(), mock.patch.object(botmod.agents, "research", return_value=found) as research:
            out = botmod.Bot(self.runner()).reply("research: sensor fusion")
        research.assert_called_once_with("sensor fusion")
        self.assertEqual(out["engine"], "researcher")
        self.assertIn("Kalman filtering (1960, crossref)", out["text"])
        self.assertIn("not measurements", out["text"])
        self.assertIn("wikipedia did not answer", out["text"])
        self.assertEqual(botmod.format_references({"result": [], "errors": {}}), "No references found on that.")
        self.assertIn("arxiv", botmod.format_references({"result": [], "errors": {"arxiv": "timeout"}}))
        with no_keys(), mock.patch.object(botmod.agents, "research") as research:
            botmod.Bot(self.runner()).reply("what is the research level?")
        research.assert_not_called()


# ── studio bridge and ingest ─────────────────────────────────────────────────
class Bridge(unittest.TestCase):
    def project(self, studio=None):
        m = {"project": {"id": "t"}, "sources": [{"id": "s", "adapter": "http"}],
             "channels": [{"id": "v", "keys": ["X", "Y", "Z"], "noise_floor": 0.1},
                          {"id": "a", "keys": ["A"], "noise_floor": 0.1},
                          {"id": "b", "keys": ["B"], "noise_floor": 0.1}]}
        if studio:
            m["studio"] = studio
        return normalise(m)

    def test_mapping(self):
        self.assertEqual(mapping_for(self.project()), {"ch1": "v", "ch2": "a", "ch3": "b"})
        self.assertEqual(mapping_for(self.project({"ch2": "b"})), {"ch2": "b"})
        with self.assertRaises(ValueError):
            mapping_for(self.project({"ch1": "nope"}))

    def test_in_process_and_remote_pushes(self):
        clock = [0.0]
        engine = Engine(self.project(), clock=lambda: clock[0])
        got = []
        feeds = {"feed_ch1": lambda v, source: got.append(("ch1", v, source)),
                 "feed_ch2": lambda v, source: got.append(("ch2", v, source)),
                 "feed_ch3": lambda x, y, source: got.append(("ch3", len(x), source))}
        bridge = StudioBridge(engine, feeds)
        for i in range(5):
            clock[0] = i * 0.2
            engine.ingest_values("s", {"X": 1, "Y": 2, "Z": 2, "A": i, "B": i * 2})
        self.assertEqual(bridge.tick(), 3)
        self.assertEqual(got[0], ("ch1", [1.0, 2.0, 2.0], "MTDI:t"))
        self.assertEqual(bridge.tick(), 0)             # nothing new, nothing re-sent
        posted = []
        fake = FakeService({("POST", "/api/ingest"): lambda r: (posted.append(r) or (200, {"ok": True, "accepted": 2},
                                                                                       "application/json"))})
        try:
            remote = StudioBridge(engine, fake.url, mapping={"ch1": "v", "ch2": "a"}, token="tok")
            self.assertEqual(remote.tick(), 2)
            self.assertEqual(posted[0]["headers"]["Authorization"], "Bearer tok")
            self.assertEqual(json.loads(posted[0]["body"])["ch2"], 4.0)
        finally:
            fake.close()

    def test_sample_shapes(self):
        ch = {"evidence": {"state": "connected"}, "value": 3.0, "spark": [1, 2, 3, 4]}
        self.assertEqual(sample_for("ch1", ch), [3.0])
        self.assertEqual(sample_for("ch3", ch), {"x": [0, 1, 2, 3], "y": [1, 2, 3, 4]})
        self.assertIsNone(sample_for("ch2", dict(ch, evidence={"state": "stale"})))


class StudioIngest(unittest.TestCase):
    """The studio interface accepts data only with the ingest token and shows it."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.env = mock.patch.dict(os.environ, {"STUDIO_SERVERLESS": "1", "STUDIO_INGEST_TOKEN": "t0ken",
                                               "STUDIO_HTTPS_PORT": "0", "HOME": cls.tmp.name,
                                               "STUDIO_STATE_DIR": cls.tmp.name})
        cls.env.start()
        from run import NAMESPACE
        cls.ns = NAMESPACE
        cls.client = NAMESPACE["server"].test_client()

    @classmethod
    def tearDownClass(cls):
        # The studio's archive and CSV writers run in background threads that write into HOME.
        # Stop them (sinks are flushed and joined) before deleting HOME, or cleanup races them.
        import threading
        from studio.system import LIFECYCLE
        LIFECYCLE.stop()
        cls.env.stop()
        alive = [t.name for t in threading.enumerate() if t.name.startswith("studio-") and t.is_alive()]
        if alive:   # stop() gave up at its deadline: leave HOME in place rather than race a live writer
            raise AssertionError(f"studio workers still running after stop(): {', '.join(alive)}")
        cls.tmp.cleanup()

    def test_token_required(self):
        self.assertEqual(self.client.post("/api/ingest", json={"ch2": 1}).status_code, 403)
        self.assertEqual(self.client.post("/api/ingest", json={"ch2": 1},
                                          headers={"Authorization": "Bearer wrong"}).status_code, 403)

    def test_samples_reach_every_channel(self):
        auth = {"Authorization": "Bearer t0ken"}
        for i in range(12):
            r = self.client.post("/api/ingest", headers=auth, json={
                "source": "UNIT", "ch1": [1 + i * 0.01, 2, 3], "ch2": 5 + 0.01 * i,
                "ch3": {"x": [0, 1, 2, 3, 4], "y": [1, 3, 9, 3, 1]}})
            self.assertEqual(r.get_json(), {"ok": True, "accepted": 3})
        bad = self.client.post("/api/ingest", headers=auth, json={"ch1": [1, 2]})
        self.assertEqual(bad.status_code, 400)
        packet = self.client.get("/api/instrument").get_json()
        for key in ("ch1", "ch2", "ch3"):
            self.assertEqual(packet["channels"][key]["state"], "connected", key)
        with self.ns["sweep3_lock"]:
            self.assertEqual(self.ns["sweep3_data"]["peak_freq"], 2.0)
        with self.ns["c1_lock"]:
            self.assertEqual(self.ns["ch1_data"]["raw_y"], 2.0)


if __name__ == "__main__":
    unittest.main()
