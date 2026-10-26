"""The D4 packet is computed by one caller at a time (studio/d4live.py, D4Service.snapshot).

Computing appends to and reads deques (mtdi_history, transient_times, events). Two Dash callbacks
computing at once made one iterate a deque the other was appending to, and the page got a 500."""
import pathlib
import sys
import threading
import time
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from studio.d4live import D4Service  # noqa: E402


def bare_service(compute):
    service = D4Service.__new__(D4Service)          # skip __init__: no config or files needed
    service.lock, service.compute_lock = threading.Lock(), threading.Lock()
    service.packet, service.computed_at = None, 0.0
    service._compute = compute
    return service


class Snapshot(unittest.TestCase):
    def test_computes_never_overlap(self):
        state = {"running": 0, "most": 0, "runs": 0}
        guard = threading.Lock()
        all_waiting = threading.Event()

        class CountingLock:
            """The compute lock, counting callers that reached it, so the first compute can hold
            on until all 8 are queued behind it."""
            def __init__(self):
                self.lock, self.entered = threading.Lock(), 0

            def __enter__(self):
                with guard:
                    self.entered += 1
                    if self.entered == 8:
                        all_waiting.set()
                self.lock.acquire()

            def __exit__(self, *exc):
                self.lock.release()

        def compute():
            with guard:
                state["running"] += 1
                state["most"] = max(state["most"], state["running"])
                state["runs"] += 1
            all_waiting.wait(5)
            time.sleep(0.01)
            with guard:
                state["running"] -= 1
            return {"run": state["runs"]}

        service = bare_service(compute)
        service.compute_lock = CountingLock()
        threads = [threading.Thread(target=service.snapshot, kwargs={"force": True}) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(state["most"], 1)
        # all 7 that waited reuse the packet computed while they waited
        self.assertEqual(state["runs"], 1)

    def test_a_config_reload_waits_for_a_compute_in_flight(self):
        started = threading.Event()

        def compute():
            started.set()
            time.sleep(0.1)
            return {"config": "old"}

        service = bare_service(compute)
        worker = threading.Thread(target=service.snapshot, kwargs={"force": True})
        worker.start()
        started.wait(5)
        with mock.patch("studio.d4live.d4.load_config", return_value=({"config": "new"}, None)):
            service.reload_config()
        worker.join()
        # the packet made with the old config was published before the reload, and cleared by it
        self.assertIsNone(service.packet)
        self.assertEqual(service.config, {"config": "new"})

    def test_a_fresh_packet_is_reused_without_computing(self):
        calls = []
        service = bare_service(lambda: calls.append(1) or {"n": len(calls)})
        first = service.snapshot()
        self.assertIs(service.snapshot(), first)
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
