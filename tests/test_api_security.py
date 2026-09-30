"""Exercise the HTTP boundary without real credentials, models or documents."""
from email.message import Message
import http.client
import json
import threading

import pytest
from src.app import server
from src.app.security import RequestBudget, SecuritySettings


def headers(**values):
    message = Message()
    for name, value in values.items():
        message[name] = value
    return message


def test_local_mode_cannot_bind_network(monkeypatch):
    monkeypatch.setenv("ATS_DEPLOYMENT_MODE", "local")
    with pytest.raises(ValueError, match="loopback"):
        SecuritySettings.from_env("0.0.0.0")


def test_private_configuration_requires_secret_origin_and_manifest_pin(monkeypatch, tmp_path):
    monkeypatch.setenv("ATS_DEPLOYMENT_MODE", "private")
    monkeypatch.setenv("ATS_ALLOWED_HOSTS", "hr.example.test")
    monkeypatch.setenv("ATS_ALLOWED_ORIGINS", "https://hr.example.test")
    monkeypatch.delenv("ATS_API_TOKEN_FILE", raising=False)
    with pytest.raises(ValueError, match="TOKEN_FILE"):
        SecuritySettings.from_env("0.0.0.0")
    secret = tmp_path / "test-secret"
    secret.write_text("synthetic_test_only_" * 3)
    monkeypatch.setenv("ATS_API_TOKEN_FILE", str(secret))
    monkeypatch.delenv("ATS_CANDIDATE_MANIFEST_SHA256", raising=False)
    with pytest.raises(ValueError, match="manifest hash"):
        SecuritySettings.from_env("0.0.0.0")
    monkeypatch.setenv("ATS_CANDIDATE_MANIFEST_SHA256", "a" * 64)
    assert SecuritySettings.from_env("0.0.0.0").mode == "private"
    monkeypatch.setenv("ATS_ALLOWED_ORIGINS", "http://hr.example.test")
    with pytest.raises(ValueError, match="HTTPS"):
        SecuritySettings.from_env("0.0.0.0")


@pytest.mark.parametrize("host,origin_value", [
    ("attacker.example", None), ("127.0.0.1.attacker.example", None),
    ("localhost", "http://attacker.example"), ("localhost", "null"),
    ("localhost", "http://localhost:8000/untrusted"), ("user@localhost", None),
])
def test_dns_rebinding_and_foreign_origins_denied(host, origin_value):
    values = {"Host": host}
    if origin_value:
        values["Origin"] = origin_value
    assert SecuritySettings().authorize(headers(**values), "POST", 8000, "/analyze")[0] == 403


def test_duplicate_host_header_denied():
    value = headers(Host="localhost")
    value["Host"] = "attacker.example"
    assert SecuritySettings().authorize(value, "GET", 8000, "/")[0] == 400


def test_private_authorization_and_liveness_scope():
    settings = SecuritySettings("private", ("hr.example.test",), ("https://hr.example.test",), "synthetic_test_only")
    value = headers(Host="hr.example.test")
    assert settings.authorize(value, "GET", 8000, "/health/live") is None
    assert settings.authorize(value, "POST", 8000, "/health/live")[0] == 401
    assert settings.authorize(value, "POST", 8000, "/analyze")[0] == 401
    value["Authorization"] = "Bearer synthetic_test_only"
    assert settings.authorize(value, "POST", 8000, "/analyze") is None
    value["Authorization"] = "Bearer extra"
    assert settings.authorize(value, "POST", 8000, "/analyze")[0] == 401


def test_bounded_budget_does_not_trust_spoofed_client_headers():
    time = [0]
    budget = RequestBudget(2, lambda: time[0])
    assert budget.consume() and budget.consume()
    assert not budget.consume()
    time[0] = 60
    assert budget.consume()


def test_http_private_auth_before_worker_and_budget(monkeypatch):
    calls = []
    monkeypatch.setattr(server.WORKER, "run", lambda payload: calls.append(payload) or {"ok": True})
    settings = SecuritySettings("private", ("127.0.0.1",), ("https://hr.example.test",), "test_only", 1)
    instance = server.BoundedHTTPServer(("127.0.0.1", 0), server.Handler, settings)
    thread = threading.Thread(target=instance.serve_forever, daemon=True)
    thread.start()
    def request(auth=None, origin_value=None):
        connection = http.client.HTTPConnection(*instance.server_address, timeout=3)
        values = {"Content-Type": "application/json"}
        if auth:
            values["Authorization"] = auth
        if origin_value:
            values["Origin"] = origin_value
        connection.request("POST", "/analyze", json.dumps({"text": "synthetic fixture"}), headers=values)
        response = connection.getresponse()
        status, policy = response.status, response.getheader("Content-Security-Policy")
        response.read()
        connection.close()
        return status, policy
    try:
        assert request()[0] == 401 and not calls
        assert request("Bearer test_only", "https://attacker.example")[0] == 403 and not calls
        status, policy = request("Bearer test_only", "https://hr.example.test")
        assert status == 200 and len(calls) == 1
        assert "script-src 'self';" in policy
        assert request("Bearer test_only")[0] == 429 and len(calls) == 1
    finally:
        instance.shutdown()
        instance.server_close()
        thread.join(2)


def test_connection_saturation_rejected_before_handler_threads():
    instance = server.BoundedHTTPServer(("127.0.0.1", 0), server.Handler, max_connections=1)
    thread = threading.Thread(target=instance.serve_forever, daemon=True)
    thread.start()
    assert instance.slots.acquire(blocking=False)
    try:
        connection = http.client.HTTPConnection(*instance.server_address, timeout=3)
        connection.request("GET", "/health/live")
        response = connection.getresponse()
        assert response.status == 503
        response.read()
        connection.close()
    finally:
        instance.slots.release()
        instance.shutdown()
        instance.server_close()
        thread.join(2)


def test_http_audit_omits_query_credentials_and_client_content(caplog):
    import logging
    from uuid import UUID
    caplog.set_level(logging.INFO, logger=server.__name__)
    instance = server.BoundedHTTPServer(("127.0.0.1", 0), server.Handler)
    thread = threading.Thread(target=instance.serve_forever, daemon=True)
    thread.start()
    try:
        connection = http.client.HTTPConnection(*instance.server_address, timeout=3)
        connection.request("GET", "/private-resume-name?secret=personal-query",
                           headers={"Authorization": "Bearer personal-credential"})
        response = connection.getresponse()
        request_id = response.getheader("X-Request-Id")
        UUID(request_id)
        assert response.status == 404
        response.read()
        connection.close()
        events = [json.loads(row.message) for row in caplog.records if row.name == server.__name__]
        assert events[-1]["request_id"] == request_id
        assert events[-1]["route"] == "other"
        assert events[-1]["status"] == 404
        assert "personal-" not in caplog.text
        assert "private-resume" not in caplog.text
    finally:
        instance.shutdown()
        instance.server_close()
        thread.join(2)
