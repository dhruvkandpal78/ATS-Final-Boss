"""Recovery uses synthetic responses and a controlled clock; no model loading."""
import json
from types import SimpleNamespace

import pytest

from src.app import server
from src.app.worker_protocol import encode_message
from src.app.worker_recovery import WorkerRecovery
from src.core.analysis_service import AnalysisService


def test_backoff_caps_and_resets_only_after_success():
    now = [0.0]
    recovery = WorkerRecovery(lambda: now[0])
    for expected in (5, 10, 20, 40, 60, 60):
        assert recovery.failed() == expected
        assert recovery.remaining() == expected
        now[0] += expected
        assert recovery.remaining() == 0
    assert recovery.consecutive_failures == 5
    recovery.succeeded()
    assert recovery.snapshot() == {"cooldown": False, "retry_after_seconds": 0,
                                   "consecutive_failures": 0}


def _worker(monkeypatch, statuses):
    clock = [0.0]
    starts, connections = [], []
    result = AnalysisService().analyze_text("Synthetic resume context.")
    class Connection:
        closed = False
        def send_bytes(self, raw):
            self.request_id = json.loads(raw)["request_id"]
        def recv_bytes(self, maxlength):
            status = statuses.pop(0)
            return encode_message({"version": 1, "request_id": self.request_id,
                "status": status, "result": result if status == 200 else {}}, maxlength)
        def close(self):
            self.closed = True
    class Process:
        alive = False
        def start(self):
            starts.append(1)
            self.alive = True
        def is_alive(self):
            return self.alive
        def terminate(self):
            self.alive = False
        def kill(self):
            self.alive = False
        def join(self, timeout=None):
            pass
        def close(self):
            pass
    def pipe():
        pair = Connection(), Connection()
        connections.extend(pair)
        return pair
    monkeypatch.setattr(server.mp, "get_context", lambda mode: SimpleNamespace(Pipe=pipe, Process=lambda **kw: Process()))
    monkeypatch.setattr(server, "monotonic", lambda: clock[0])
    return server.ModelWorker(timeout=30), clock, starts, connections


def test_cooldown_does_not_spawn_or_extend_and_success_recovers(monkeypatch):
    worker, clock, starts, connections = _worker(monkeypatch, [503, 503, 200])
    with pytest.raises(server.APIError) as first:
        worker.run({"text": "Synthetic document"})
    assert first.value.retry_after == 5
    assert len(starts) == 1 and worker.process is None and not worker.ready
    assert all(item.closed for item in connections)
    for moment, expected in ((0, 5), (1.1, 4), (4.9, 1)):
        clock[0] = moment
        with pytest.raises(server.APIError) as denied:
            worker.run({"text": "Synthetic document"})
        assert denied.value.status == 503 and denied.value.retry_after == expected
        assert len(starts) == 1
        assert worker.recovery.consecutive_failures == 1
    clock[0] = 5
    with pytest.raises(server.APIError) as second:
        worker.run({"text": "Synthetic document"})
    assert second.value.retry_after == 10 and len(starts) == 2
    clock[0] = 15
    assert worker.run({"text": "Synthetic document"})["schema_version"] == "2.0"
    assert len(starts) == 3 and worker.ready
    assert worker.recovery_snapshot()["consecutive_failures"] == 0
    worker.close()


def test_client_error_does_not_trip_recovery_or_restart_worker(monkeypatch):
    worker, _, starts, _ = _worker(monkeypatch, [422, 200])
    with pytest.raises(server.APIError) as error:
        worker.run({"text": "Synthetic document"})
    assert error.value.status == 422 and error.value.retry_after is None
    assert worker.recovery_snapshot()["consecutive_failures"] == 0
    assert worker.run({"text": "Synthetic document"})["schema_version"] == "2.0"
    assert len(starts) == 1
    worker.close()
