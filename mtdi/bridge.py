"""Bridge: show any MTDI project in the studio interface.

The studio has three display channels:

    ch1   a three-axis vector or one number per sample   (Page 1, first tab)
    ch2   one number per sample                          (Page 1, second tab)
    ch3   a sweep: a series of (x, y) points             (Page 2)

A project chooses which of its channels fill them in its manifest:

    "studio": {"ch1": "accel", "ch2": "temperature", "ch3": "latency"}

Without that block the first three channels are used in order. A channel shown on ch3
that is not itself a sweep is drawn as its recent history (x = sample index).

The bridge pushes in-process (the studio and the project share a Python process) or
over HTTP to a studio running elsewhere, such as a Vercel deployment:

    StudioBridge(engine, target=feeds)                                  # in-process
    StudioBridge(engine, target="https://x.vercel.app", token="...")    # remote
"""
import json
import threading
import urllib.request

SLOTS = ("ch1", "ch2", "ch3")


def mapping_for(project):
    """{slot: channel id} from the manifest's "studio" block, else the first channels in order."""
    ids = [c["id"] for c in project["channels"]]
    declared = project.get("studio") or {}
    if declared:
        unknown = [v for v in declared.values() if v not in ids]
        if unknown:
            raise ValueError(f"studio block names unknown channels: {', '.join(unknown)}")
        return {slot: declared[slot] for slot in SLOTS if slot in declared}
    return dict(zip(SLOTS, ids))


def sample_for(slot, channel):
    """One studio sample for one slot from one packet channel, or None when it has nothing new."""
    if channel["evidence"]["state"] != "connected" or channel["value"] is None:
        return None
    value = channel["value"]
    if slot == "ch1":
        return value if isinstance(value, list) else [value]
    if slot == "ch2":
        return sum(v * v for v in value) ** 0.5 if isinstance(value, list) else value
    history = channel.get("spark") or []
    if len(history) < 3:
        return None
    return {"x": list(range(len(history))), "y": history}


class StudioBridge:
    def __init__(self, engine, target, mapping=None, token=None, interval=0.25, source=None):
        self.engine = engine
        self.mapping = mapping or mapping_for(engine.project)
        self.target = target
        self.token = token
        self.interval = interval
        self.source = source or ("MTDI:" + engine.project["project"]["id"])[:40]
        self._seen = {}
        self._stop = threading.Event()
        self._thread = None
        self.sent = 0
        self.errors = 0
        self.last_error = None

    def collect(self):
        """The samples that changed since the last push: {"ch1": ..., "ch2": ..., "ch3": ...}."""
        packet = self.engine.snapshot()
        out = {}
        for slot, cid in self.mapping.items():
            channel = packet["channels"].get(cid)
            if not channel:
                continue
            marker = channel["evidence"].get("samples")
            if self._seen.get(slot) == marker:
                continue
            sample = sample_for(slot, channel)
            if sample is not None:
                out[slot] = sample
                self._seen[slot] = marker
        return out

    def push(self, sample):
        if not sample:
            return 0
        if callable(self.target) or isinstance(self.target, dict):
            feeds = self.target if isinstance(self.target, dict) else self.target()
            if "ch1" in sample:
                feeds["feed_ch1"](sample["ch1"], source=self.source)
            if "ch2" in sample:
                feeds["feed_ch2"](sample["ch2"], source=self.source)
            if "ch3" in sample:
                feeds["feed_ch3"](sample["ch3"]["x"], sample["ch3"]["y"], source=self.source)
        else:
            body = json.dumps(dict(sample, source=self.source)).encode()
            headers = {"Content-Type": "application/json"}
            if self.token:
                headers["Authorization"] = "Bearer " + self.token
            request = urllib.request.Request(self.target.rstrip("/") + "/api/ingest", data=body,
                                             headers=headers, method="POST")
            with urllib.request.urlopen(request, timeout=10) as response:
                reply = json.loads(response.read() or b"{}")
            if not reply.get("ok"):
                raise RuntimeError(reply.get("error", "studio refused the sample"))
        self.sent += len(sample)
        return len(sample)

    def tick(self):
        try:
            return self.push(self.collect())
        except Exception as error:  # a missing studio must not stop the project
            self.errors += 1
            self.last_error = str(error)
            return 0

    def start(self):
        def loop():
            while not self._stop.wait(self.interval):
                self.tick()
        self._thread = threading.Thread(target=loop, name="mtdi-studio-bridge", daemon=True)
        self._thread.start()
        return self

    def stop(self):
        self._stop.set()
