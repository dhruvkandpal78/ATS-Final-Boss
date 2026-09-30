"""Deterministic API contract tests: no model downloads or private documents."""
import base64
import http.client
import json
from pathlib import Path
import threading

import pytest
from src.app import server


class FakeService:
    def analyze_text(self, text):
        return {"decision": "review_recommended", "model_proba": 0.12,
                "policy_decision": True, "modules": {"b": {"status": "not_applicable", "score": None}}}

    def analyze_pdf(self, path, include_previews=False):
        assert Path(path).read_bytes().startswith(b"%PDF-")
        return {"input_mode": "pdf"}


@pytest.fixture
def service(monkeypatch):
    monkeypatch.setattr(server, "_SERVICE", FakeService())


@pytest.mark.parametrize("payload,status", [
    ([], 422), ({}, 422), ({"text": 3}, 422), ({"text": " "}, 422),
    ({"text": "x" * 100001}, 413), ({"filename": "test.pdf"}, 422),
    ({"filename": "test.txt", "b64": "a"}, 415),
    ({"filename": "test.pdf", "b64": "%%%"}, 422),
    ({"filename": "test.pdf", "b64": "YWJj"}, 415),
    ({"text": "x", "filename": "x.pdf", "b64": "abc"}, 422),
])
def test_invalid_payload(payload, status):
    with pytest.raises(server.APIError) as exc:
        server.analyze_payload(payload)
    assert exc.value.status == status


def test_text_does_not_manufacture_pdf_evidence(service):
    result = server.analyze_payload({"text": "[HIDDEN_TEXT_START] python"})
    assert result["modules"]["b"]["score"] is None
    assert result["model_proba"] == 0.12


def test_pdf_cleanup_success_and_failure(service, tmp_path, monkeypatch):
    payload = {"filename": "resume.pdf", "b64": base64.b64encode(b"%PDF-1.7\n").decode()}
    assert server.analyze_payload(payload, tmp_path)["input_mode"] == "pdf"
    assert list(tmp_path.iterdir()) == []
    def fail(path, **kwargs):
        raise ValueError("parse failed")
    monkeypatch.setattr(server._SERVICE, "analyze_pdf", fail)
    with pytest.raises(ValueError):
        server.analyze_payload(payload, tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_worker_rejects_saturation():
    worker = server.ModelWorker()
    with worker.lock:
        with pytest.raises(server.APIError) as exc:
            worker.run({"text": "valid text"})
    assert exc.value.status == 429


@pytest.fixture
def http_server(monkeypatch):
    monkeypatch.setattr(server.WORKER, "run", lambda payload: server.analyze_payload(payload))
    instance = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    thread = threading.Thread(target=instance.serve_forever, daemon=True)
    thread.start()
    yield instance.server_address
    instance.shutdown()
    instance.server_close()
    thread.join(timeout=2)


def request(address, method, path, body=None, headers=None):
    connection = http.client.HTTPConnection(*address, timeout=3)
    connection.request(method, path, body=body, headers=headers or {})
    response = connection.getresponse()
    status, headers, data = response.status, dict(response.getheaders()), response.read()
    connection.close()
    return status, headers, data


def test_http_happy_path_and_health(http_server, service):
    status, headers, data = request(http_server, "POST", "/analyze", json.dumps({"text": "Resume"}), {"Content-Type": "application/json"})
    assert status == 200
    assert json.loads(data)["model_proba"] == 0.12
    assert headers["Cache-Control"] == "no-store"
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert request(http_server, "GET", "/health")[0] == 200
    assert request(http_server, "GET", "/api/capabilities")[0] == 200
    for route in ("/", "/analyze", "/methodology", "/lab", "/ownership"):
        assert request(http_server, "GET", route)[0] == 200

    assert b"NEW ORIGINAL MATERIAL" in request(http_server, "GET", "/license")[2]
    assert b"MIT License" in request(http_server, "GET", "/license-legacy")[2]


@pytest.mark.parametrize("body,ctype,status", [("{", "application/json", 400), ("[]", "application/json", 422), ("{}", "text/plain", 415)])
def test_http_bad_requests(http_server, body, ctype, status):
    assert request(http_server, "POST", "/analyze", body, {"Content-Type": ctype})[0] == status


def test_error_redaction(http_server, monkeypatch):
    def fail(payload):
        raise RuntimeError("private resume and C:/sensitive/path")
    monkeypatch.setattr(server.WORKER, "run", fail)
    status, _, data = request(http_server, "POST", "/analyze", '{"text":"test"}', {"Content-Type": "application/json"})
    assert status == 503
    assert b"sensitive" not in data and b"private" not in data


def test_expensive_labs_disabled(http_server):
    assert request(http_server, "POST", "/adaptive", "{}")[0] == 404
    assert request(http_server, "POST", "/red-blue", "{}")[0] == 404


def test_worker_deadline_terminates_and_cleans_tempfiles(monkeypatch):
    directories = []
    class Connection:
        def send(self, value):
            _, directory = value
            directories.append(Path(directory))
            (Path(directory) / 'resume.pdf').write_bytes(b'%PDF-1.7')
        def poll(self, timeout):
            return False
        def close(self):
            pass
    class Process:
        def __init__(self, **kwargs):
            self.alive = False
            self.terminated = False
        def start(self):
            self.alive = True
        def is_alive(self):
            return self.alive
        def terminate(self):
            self.terminated = True
            self.alive = False
        def join(self, timeout=None):
            pass
        def close(self):
            pass
    connection = Connection()
    process = Process()
    class Context:
        def Pipe(self):
            return connection, Connection()
        def Process(self, **kwargs):
            return process
    monkeypatch.setattr(server.mp, 'get_context', lambda mode: Context())
    worker = server.ModelWorker(timeout=0.01)
    with pytest.raises(server.APIError) as exc:
        worker.run({'text': 'synthetic resume'})
    assert exc.value.status == 504
    assert process.terminated
    assert not worker.lock.locked()
    assert all(not directory.exists() for directory in directories)
    assert worker.process is None


def test_static_assets_and_traversal(http_server):
    assert request(http_server, 'GET', '/assets/app.js')[0] == 200
    assert request(http_server, 'GET', '/assets/style.css')[0] == 200
    assert request(http_server, 'GET', '/assets/../server.py')[0] == 404
    assert request(http_server, 'GET', '/assets/%2e%2e/server.py')[0] == 404
