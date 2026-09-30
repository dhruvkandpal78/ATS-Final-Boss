"""Deterministic regressions for worker IPC completing beyond its deadline."""
import json
from types import SimpleNamespace

import pytest

from src.app import server
from src.app.worker_protocol import encode_message


REQUEST_ID = "a" * 32


def _valid_result():
    return {
        "schema_version": "2.0",
        "analysis_id": REQUEST_ID,
        "created_at": "2026-09-30T00:00:00Z",
        "policy_version": "2.0",
        "status": "unscorable",
        "input_mode": "text",
        "decision": "insufficient_evidence",
        "score_kind": "unavailable",
        "score": None,
        "coverage": {"pages_total": None, "pages_analyzed": None, "limitations": []},
        "modules": {key: {"status": "unsupported"} for key in "abc"},
        "model": {},
        "timings_ms": {},
        "findings": [],
        "reason_codes": [],
    }


class _Clock:
    now = 0.0

    def monotonic(self):
        return self.now


class _InlineThread:
    """Run the target synchronously so clock transitions are deterministic."""

    def __init__(self, target, daemon=None):
        self.target = target
        self.alive = False

    def start(self):
        self.alive = True
        try:
            self.target()
        finally:
            self.alive = False

    def is_alive(self):
        return self.alive

    def join(self, timeout=None):
        pass


class _Connection:
    def __init__(self, clock, *, late_send=False, late_receive=False):
        self.clock = clock
        self.late_send = late_send
        self.late_receive = late_receive
        self.closed = False
        self.sent = None

    def send_bytes(self, raw):
        self.sent = raw
        if self.late_send:
            self.clock.now = 11.0

    def recv_bytes(self, maxlength):
        request_id = json.loads(self.sent)["request_id"]
        raw = encode_message({
            "version": 1,
            "request_id": request_id,
            "status": 200,
            "result": _valid_result(),
        }, maxlength)
        if self.late_receive:
            self.clock.now = 11.0
        return raw

    def close(self):
        self.closed = True


class _Process:
    def __init__(self):
        self.alive = False
        self.terminated = False
        self.closed = False

    def start(self):
        self.alive = True

    def is_alive(self):
        return self.alive

    def terminate(self):
        self.terminated = True
        self.alive = False

    def kill(self):
        self.terminate()

    def join(self, timeout=None):
        pass

    def close(self):
        self.closed = True


class _TemporaryDirectory:
    def __enter__(self):
        return "C:/synthetic-analysis"

    def __exit__(self, *_args):
        return False


@pytest.mark.parametrize("late_send", [True, False], ids=["send", "receive"])
def test_completed_ipc_past_deadline_times_out_and_cleans_worker(monkeypatch, late_send):
    clock = _Clock()
    connection = _Connection(clock, late_send=late_send, late_receive=not late_send)
    child = _Connection(clock)
    process = _Process()

    class _Context:
        def Pipe(self):
            return connection, child

        def Process(self, **kwargs):
            return process

    worker = server.ModelWorker(timeout=10)
    monkeypatch.setattr(server.mp, "get_context", lambda mode: _Context())
    monkeypatch.setattr(server, "tempfile", SimpleNamespace(
        TemporaryDirectory=lambda **kwargs: _TemporaryDirectory()))
    monkeypatch.setattr(server, "monotonic", clock.monotonic)
    # The active request's sender/receiver targets complete immediately while
    # the fake connection advances time across the configured deadline.
    monkeypatch.setattr(server, "threading", SimpleNamespace(Thread=_InlineThread))

    with pytest.raises(server.APIError) as caught:
        worker.run({"text": "synthetic resume"})

    assert caught.value.status == 504
    assert worker.ready is False
    assert worker.process is None and worker.connection is None
    assert process.terminated and process.closed
    assert connection.closed and child.closed
    assert not worker.lock.locked()
