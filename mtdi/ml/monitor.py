"""Run one anomaly detector per channel over live MTDI packets.

    from mtdi.ml import Monitor, MAD
    monitor = Monitor(lambda: MAD(threshold=4))
    for packet in packets:
        events = monitor.update(packet)     # [{"channel", "score", "t"}, ...] for new anomalies

It reads each channel's deviation from its learned baseline (Environmental
Intelligence), so detectors see change from the channel's own normal, not raw values.
"""
import time

from .anomaly import MAD


class Monitor:
    def __init__(self, factory=None, channels=None):
        self.factory = factory or (lambda: MAD(threshold=4.0))
        self.channels = set(channels) if channels else None
        self.detectors = {}
        self.seen = {}
        self.events = []

    def update(self, packet):
        new = []
        for cid, ch in packet.get("channels", {}).items():
            if self.channels and cid not in self.channels:
                continue
            ev, env = ch.get("evidence", {}), ch.get("environment", {})
            count = ev.get("samples")
            if ev.get("state") != "connected" or env.get("deviation") is None or self.seen.get(cid) == count:
                continue
            self.seen[cid] = count
            det = self.detectors.setdefault(cid, self.factory())
            result = det.update(env["deviation"])
            if result["anomaly"]:
                event = {"channel": cid, "label": ch.get("label", cid), "score": result["score"], "t": time.time()}
                new.append(event)
                self.events.append(event)
        del self.events[:-200]
        return new
