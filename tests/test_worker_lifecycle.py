"""Worker shutdown behavior with synthetic payloads and no model loading."""
import threading
from time import monotonic

import pytest

from src.app import server


def test_shutdown_cancels_active_request_and_rejects_new_work(monkeypatch):
    sent = threading.Event()

    class Connection:
        def send(self, value):
            sent.set()

        def poll(self, timeout):
            threading.Event().wait(timeout)
            return False

        def close(self):
            pass

    class Process:
        def __init__(self):
            self.alive = False
            self.terminated = False

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
            pass

    process = Process()

    class Context:
        def Pipe(self):
            return Connection(), Connection()

        def Process(self, **kwargs):
            return process

    monkeypatch.setattr(server.mp, "get_context", lambda mode: Context())
    worker = server.ModelWorker(timeout=10)
    responses = []

    def request():
        try:
            worker.run({"text": "Synthetic resume"})
        except server.APIError as exc:
            responses.append(exc.status)

    thread = threading.Thread(target=request)
    thread.start()
    assert sent.wait(timeout=2)
    started = monotonic()
    assert worker.shutdown(grace=1)
    thread.join(timeout=2)
    assert not thread.is_alive()
    assert monotonic() - started < 2
    assert responses == [503]
    assert process.terminated
    assert worker.process is None
    assert not worker.lock.locked()
    with pytest.raises(server.APIError) as exc:
        worker.run({"text": "Another synthetic resume"})
    assert exc.value.status == 503


def test_shutdown_does_not_queue_behind_saturated_request():
    worker = server.ModelWorker()
    with worker.lock:
        assert worker.stopping.is_set() is False
        with pytest.raises(server.APIError) as exc:
            worker.run({"text": "Synthetic resume"})
        assert exc.value.status == 429
    assert worker.shutdown(grace=0)


def test_spawn_failure_closes_pipe_and_allows_clean_shutdown(monkeypatch):
    connections = []

    class Connection:
        def __init__(self):
            self.closed = False
            connections.append(self)

        def close(self):
            self.closed = True

    class Process:
        def __init__(self):
            self.closed = False

        def start(self):
            raise OSError("synthetic spawn error with private detail")

        def close(self):
            self.closed = True

    process = Process()

    class Context:
        def Pipe(self):
            return Connection(), Connection()

        def Process(self, **kwargs):
            return process

    monkeypatch.setattr(server.mp, "get_context", lambda mode: Context())
    worker = server.ModelWorker()
    with pytest.raises(server.APIError) as exc:
        worker.run({"text": "Synthetic resume"})
    assert exc.value.status == 503
    assert "private detail" not in str(exc.value)
    assert all(item.closed for item in connections)
    assert process.closed
    assert worker.process is None and worker.connection is None
    assert worker.shutdown()
