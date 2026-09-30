"""Exercise both HTTP adapters without models or personal documents."""
import http.client
import threading

import pytest
from starlette.testclient import TestClient

from src.app import asgi, server
from src.app.security import SecuritySettings

DEEP_BODY = b"[" * 65 + b"]" * 65


@pytest.mark.parametrize("adapter", ["stdlib", "asgi"])
@pytest.mark.parametrize("headers,body,status", [
    ([("Content-Length", "+2"), ("Content-Type", "application/json")], b"{}", 400),
    ([("Content-Length", "2"), ("Content-Type", "application/json"),
      ("Content-Type", "application/json")], b"{}", 415),
    ([("Content-Length", "2"), ("Transfer-Encoding", ""),
      ("Content-Type", "application/json")], b"{}", 400),
    ([("Content-Length", "2"), ("Content-Type", "application/json")], b"{}", 422),
    ([("Content-Length", str(len(DEEP_BODY))), ("Content-Type", "application/json")],
     DEEP_BODY, 400),
], ids=["signed-length", "duplicate-type", "empty-transfer-encoding", "invalid-shape", "deep-json"])
def test_bad_requests_never_reach_worker(adapter, headers, body, status, monkeypatch):
    calls = []
    if adapter == "asgi":
        class Worker:
            def run(self, payload):
                calls.append(payload)
                raise AssertionError("Rejected request reached inference")

            def close(self):
                pass

        app = asgi.create_app(worker=Worker(), settings=SecuritySettings(allowed_hosts=("testserver",)))
        with TestClient(app) as client:
            response = client.post("/analyze", headers=headers, content=body)
            actual, data = response.status_code, response.content
    else:
        def fail(payload):
            server.validate_payload(payload)
            calls.append(payload)
            raise AssertionError("Rejected request reached inference")
        monkeypatch.setattr(server.WORKER, "run", fail)
        instance = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        thread = threading.Thread(target=instance.serve_forever, daemon=True)
        thread.start()
        connection = http.client.HTTPConnection(*instance.server_address, timeout=3)
        try:
            connection.putrequest("POST", "/analyze")
            for name, value in headers:
                connection.putheader(name, value)
            connection.endheaders(body)
            response = connection.getresponse()
            actual, data = response.status, response.read()
        finally:
            connection.close()
            instance.shutdown()
            instance.server_close()
            thread.join(timeout=2)
    assert actual == status
    assert b"error" in data
    assert calls == []
