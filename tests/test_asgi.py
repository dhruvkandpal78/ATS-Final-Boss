"""ASGI boundary tests use a synthetic worker and never load models or PDFs."""

import json
import logging
import threading

import pytest
from starlette.testclient import TestClient

from src.app import asgi
from src.app.security import SecuritySettings


class FakeProcess:
    def __init__(self, owner):
        self.owner = owner

    def is_alive(self):
        return self.owner.ready


class FakeWorker:
    def __init__(self):
        self.calls = []
        self.ready = False
        self.closed = False
        self.lock = threading.Lock()
        self.process = FakeProcess(self)

    def run(self, payload):
        self.calls.append(payload)
        self.ready = True
        return {"status": "complete" if "b64" in payload else "synthetic", "count": len(self.calls),
                "score": 0.2, "modules": {name: {"status": "ok", "score": 0.2} for name in ("a", "b", "c")}}

    def close(self):
        self.closed = True


def _app(worker=None, settings=None):
    worker = worker or FakeWorker()
    settings = settings or SecuritySettings(allowed_hosts=("testserver",), requests_per_minute=2)
    return asgi.create_app(worker=worker, settings=settings), worker


def test_worker_cooldown_retry_guidance_and_readiness():
    class RecoveringWorker(FakeWorker):
        def run(self, payload):
            raise asgi.APIError(503, "Worker recovering.", retry_after=40)
        def recovery_snapshot(self):
            return {"cooldown": True, "retry_after_seconds": 40, "consecutive_failures": 4}
    app, _ = _app(RecoveringWorker())
    with TestClient(app) as client:
        response = client.post("/analyze", json={"text": "Synthetic context"})
        assert response.status_code == 503 and response.headers["Retry-After"] == "40"
        assert client.get("/health/ready").status_code == 503
        assert client.get("/health").json()["worker_recovery"]["cooldown"] is True
        assert client.get("/health/live").json() == {"ok": True}


def test_local_routes_lazy_readiness_headers_and_shutdown():
    app, worker = _app()
    with TestClient(app) as client:
        assert client.get("/health/live").json() == {"ok": True}
        assert client.get("/health/ready").status_code == 503
        response = client.post("/analyze", json={"text": "Synthetic example"})
        assert response.status_code == 200
        assert response.json()["status"] == "synthetic"
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["content-security-policy"].startswith("default-src 'none'")
        assert response.headers["x-request-id"]
        assert client.get("/health/ready").json() == {"ready": True}
        worker.stopping = threading.Event()
        worker.stopping.set()
        assert client.get("/health/ready").status_code == 503
        assert client.get("/api/capabilities").json()["max_file_bytes"] == asgi.MAX_FILE_BYTES
        assert client.get("/license").status_code == 200
        assert client.get("/methodology").status_code == 200
    assert worker.closed
    assert worker.calls == [{"text": "Synthetic example"}]


def test_private_authorization_before_body_and_budget(monkeypatch):
    monkeypatch.setattr(asgi.sys, "platform", "linux")
    settings = SecuritySettings("private", ("testserver",), ("https://hr.example.test",),
                                "synthetic_test_token", 1)
    checks = []
    worker = FakeWorker()
    app = asgi.create_app(settings=settings, worker=worker,
                          private_startup_check=lambda: checks.append("pinned"))
    with TestClient(app) as client:
        assert checks == ["pinned"]
        assert worker.calls[0] == {"text": asgi.WARMUP_TEXT}
        assert len(worker.calls) == 2 and worker.calls[1]["filename"] == "synthetic-startup.pdf"
        assert client.get("/health/live").status_code == 200
        assert client.get("/health/ready").status_code == 401
        assert client.request("TRACE", "/health/live").status_code == 401
        bad = client.post("/analyze", content=b"not json",
                          headers={"Content-Type": "application/json"})
        assert bad.status_code == 401
        assert "www-authenticate" in bad.headers
        assert len(worker.calls) == 2
        headers = {"Authorization": "Bearer synthetic_test_token",
                   "Origin": "https://hr.example.test"}
        first = client.post("/analyze", json={"text": "Synthetic"}, headers=headers)
        assert first.status_code == 200
        assert client.post("/analyze", json={"text": "Another"}, headers=headers).status_code == 429
        assert len(worker.calls) == 3
    assert worker.closed


def test_duplicate_host_and_origin_are_rejected():
    app, worker = _app()
    with TestClient(app) as client:
        request = client.build_request("POST", "/analyze", content=b"bad", headers=[
            ("Host", "testserver"), ("Host", "attacker.example"),
            ("Content-Type", "application/json"),
        ])
        assert client.send(request).status_code == 400
        request = client.build_request("POST", "/analyze", content=b"bad", headers=[
            ("Host", "testserver"), ("Origin", "http://testserver:8000"),
            ("Origin", "http://attacker.example"), ("Content-Type", "application/json"),
        ])
        assert client.send(request).status_code == 400
    assert worker.calls == []


@pytest.mark.parametrize("headers,body,status", [
    ({"Content-Length": "99999999", "Content-Type": "application/json"}, b"x", 413),
    ({"Content-Length": "1", "Transfer-Encoding": "chunked", "Content-Type": "application/json"}, b"x", 400),
    ({"Content-Length": "3", "Content-Type": "text/plain"}, b"abc", 415),
    ({"Content-Length": "3", "Content-Type": "application/json"}, b"abc", 400),
])
def test_body_rejections_before_worker(headers, body, status):
    app, worker = _app()
    with TestClient(app) as client:
        response = client.post("/analyze", content=body, headers=headers)
        assert response.status_code == status
    assert not worker.calls


def test_payload_validation_and_redacted_canonical_log(caplog):
    app, worker = _app()
    caplog.set_level(logging.INFO, logger=asgi.__name__)
    with TestClient(app) as client:
        assert client.post("/analyze", json={"text": ""}).status_code == 422
        response = client.get("/private-name?credential=secret")
        assert response.status_code == 404
        assert client.get("/assets/../../LICENSE").status_code == 404
    assert worker.calls == []
    events = [json.loads(record.message) for record in caplog.records if record.name == asgi.__name__]
    assert events[-2]["route"] == "other"
    assert "private-name" not in caplog.text
    assert "credential" not in caplog.text
    assert "secret" not in caplog.text


def test_private_startup_fails_closed_when_worker_does_not_warm(monkeypatch):
    monkeypatch.setattr(asgi.sys, "platform", "linux")
    settings = SecuritySettings("private", ("testserver",), ("https://hr.example.test",), "token")
    worker = FakeWorker()
    worker.run = lambda payload: {"status": "synthetic"}
    app = asgi.create_app(settings=settings, worker=worker, private_startup_check=lambda: None)
    with pytest.raises(RuntimeError, match="Private startup verification failed"):
        with TestClient(app):
            pass
    assert worker.closed


def test_private_startup_rejects_success_response_with_broken_detector(monkeypatch):
    monkeypatch.setattr(asgi.sys, "platform", "linux")
    settings = SecuritySettings("private", ("testserver",), ("https://hr.example.test",), "token")
    worker = FakeWorker()
    original = worker.run
    def broken(payload):
        result = original(payload)
        result["modules"]["c"]["status"] = "error"
        return result
    worker.run = broken
    app = asgi.create_app(settings=settings, worker=worker, private_startup_check=lambda: None)
    with pytest.raises(RuntimeError, match="Private startup verification failed"):
        with TestClient(app):
            pass
    assert worker.closed and len(worker.calls) == 1


def test_ambiguous_content_type_and_deep_json_do_not_reach_worker():
    app, worker = _app()
    with TestClient(app) as client:
        response = client.post("/analyze", content=b"{}", headers=[
            ("Content-Type", "application/json"), ("Content-Type", "text/plain")])
        assert response.status_code == 415
        deep = "[" * 1500 + "0" + "]" * 1500
        # Python builds can parse this depth or reject it at decoder recursion.
        # Either invalid request shape or depth rejection must stay a client error.
        assert client.post("/analyze", content=deep, headers={"Content-Type": "application/json"}).status_code in {400, 422}
    assert worker.calls == []
