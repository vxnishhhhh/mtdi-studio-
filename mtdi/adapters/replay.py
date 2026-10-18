"""Replay a recorded session in real time, labelled REPLAY.

    {"id": "lab", "adapter": "replay", "file": "recordings/lab.jsonl", "loop": true, "speed": 1.0}

The file is what `python -m mtdi run ... --record FILE` writes: one JSON object
per line, {"t": wall_seconds, "source": id, "values": {...}}. Replayed values go
to this adapter's own source id, so a recording of source "uno" can be replayed
by a manifest whose replay source is also called "uno".
"""
import json
import pathlib
import time

from . import Adapter, sleep_until


class ReplayAdapter(Adapter):
    data_source = "REPLAY"

    def run(self):
        path = pathlib.Path(self.spec["file"])
        if not path.is_absolute():
            path = pathlib.Path(self.engine.project.get("_dir", ".")) / path
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        only = self.spec.get("from_source")
        rows = [r for r in rows if not only or r.get("source") == only]
        if not rows:
            raise RuntimeError(f"{path} holds no samples")
        speed = float(self.spec.get("speed", 1.0))
        self.engine.set_source_state(self.id, "connected", f"replaying {path.name} ({len(rows)} samples)")
        while not self.stop_event.is_set():
            start, first = time.monotonic(), rows[0]["t"]
            for row in rows:
                if self.stop_event.is_set():
                    return
                sleep_until(self.stop_event, start + (row["t"] - first) / speed)
                self.engine.ingest_values(self.id, row["values"], self.data_source)
            if not self.spec.get("loop", True):
                self.engine.set_source_state(self.id, "finished", "replay complete")
                self.stop_event.wait()
                return


class Recorder:
    """Append every accepted sample to a JSONL file that ReplayAdapter can play."""

    def __init__(self, path):
        self.path = pathlib.Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.stream = self.path.open("a", encoding="utf-8")

    def __call__(self, wall, source, values, data_source):
        if data_source == "SIMULATED":
            return                          # a recording is evidence; simulated data is not
        self.stream.write(json.dumps({"t": wall, "source": source, "values": values,
                                      "data_source": data_source}) + "\n")
        self.stream.flush()
