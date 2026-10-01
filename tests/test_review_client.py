import copy
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from uuid import uuid4

import pytest

from src.app.integration_contract import CATEGORIES
from src.integrations import review_client as sdk


def response_value():
    return {"schema_version": "1.0", "analysis_schema_version": "2.0", "policy_version": "2.0",
            "purpose": "human_review_assistance", "input_mode": "text", "analysis_status": "partial",
            "decision": "insufficient_evidence", "automatic_rejection_allowed": False,
            "authenticity_verified": False,
            "observations": {c: {"count": 0, "review_trigger_count": 0} for c in CATEGORIES},
            "coverage": {"modules": {"a": "unsupported", "b": "not_applicable", "c": "unsupported"},
                         "has_limitations": True, "pdf_visibility": "not_applicable"}}


@pytest.fixture
def wire(monkeypatch):
    class Response:
        status = 200
        raw = json.dumps(response_value()).encode()
        headers = {"Content-Type": "application/json", "X-Request-Id": str(uuid4())}
        reads = 0
        def getheader(self, name, default=""):
            return self.headers.get(name, default)
        def read(self, limit):
            self.reads += 1
            return self.raw[:limit]
    response = Response()
    response.headers = dict(response.headers)
    class Connection:
        closed = False
        requests = []
        def __init__(self, *args, **kwargs): pass
        def request(self, *args): self.requests.append(args)
        def getresponse(self): return response
        def close(self): self.closed = True
    connection = Connection()
    monkeypatch.setattr(sdk.http.client, "HTTPConnection", lambda *a, **k: connection)
    monkeypatch.setattr(sdk.http.client, "HTTPSConnection", lambda *a, **k: connection)
    return response, connection


def test_valid_response_has_parent_correlation_and_fixed_pdf_filename(wire):
    response, connection = wire
    result = sdk.ReviewClient("https://example.com", bearer_token="secret").review_pdf(b"%PDF-synthetic")
    assert result["request_id"] == response.headers["X-Request-Id"]
    method, route, body, headers = connection.requests[0]
    assert (method, route) == ("POST", "/api/v1/review")
    assert json.loads(body)["filename"] == "document.pdf"
    assert headers["Authorization"] == "Bearer secret"
    assert int(headers["Content-Length"]) == len(body)
    assert connection.closed


def test_real_loopback_transport_preserves_json_and_correlation():
    received = []
    parent_id = str(uuid4())
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_POST(self):
            received.append((self.path, json.loads(self.rfile.read(int(self.headers["Content-Length"])))))
            body = json.dumps(response_value()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Request-Id", parent_id)
            self.end_headers()
            self.wfile.write(body)
    instance = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=instance.serve_forever, daemon=True)
    thread.start()
    try:
        result = sdk.ReviewClient(f"http://127.0.0.1:{instance.server_port}", timeout=2).review_text("synthetic résumé")
        assert result["request_id"] == parent_id
        assert received == [("/api/v1/review", {"text": "synthetic résumé"})]
    finally:
        instance.shutdown()
        instance.server_close()
        thread.join(timeout=2)


@pytest.mark.parametrize("origin", ["http://example.com", "https://a:b@example.com", "https://example.com/path",
                                   "https://example.com?secret=1", "https://example.com#fragment"])
def test_unsafe_origin_rejected(origin):
    with pytest.raises(ValueError): sdk.ReviewClient(origin, bearer_token="secret")


def test_remote_requires_auth_and_tokens_cannot_inject_headers():
    with pytest.raises(ValueError): sdk.ReviewClient("https://example.com")
    with pytest.raises(ValueError): sdk.ReviewClient("https://example.com", bearer_token="x\r\nInjected: yes")


@pytest.mark.parametrize("status", [302, 401, 429, 503])
def test_failures_do_not_read_or_echo_body_or_follow_redirect(wire, status):
    response, connection = wire
    response.status = status
    response.raw = b"PRIVATE_RESUME_TOKEN"
    response.headers["Retry-After"] = "17"
    with pytest.raises(sdk.ReviewClientError) as failure:
        sdk.ReviewClient("http://127.0.0.1").review_text("synthetic")
    assert failure.value.status == status and failure.value.retry_after == 17
    assert "PRIVATE" not in str(failure.value)
    assert response.reads == 0 and len(connection.requests) == 1 and connection.closed


@pytest.mark.parametrize("change", ["oversize", "duplicate", "nan", "id", "type", "unknown", "boolean_count", "clearance", "complete_text", "text_pdf_module"])
def test_ambiguous_or_unsafe_response_fails_closed(wire, change):
    response, connection = wire
    value = copy.deepcopy(response_value())
    if change == "oversize": response.raw = b" " * (sdk.MAX_RESPONSE_BYTES + 1)
    if change == "duplicate": response.raw = b'{"x":1,"x":2}'
    if change == "nan": response.raw = b'{"x":NaN}'
    if change == "id": response.headers["X-Request-Id"] = "untrusted"
    if change == "type": response.headers["Content-Type"] = "text/html"
    if change == "unknown": value["source_text"] = "PRIVATE"
    if change == "boolean_count": value["observations"]["pdf_structure"]["count"] = True
    if change == "clearance": value["decision"] = "no_signals_detected"
    if change == "complete_text": value["analysis_status"] = "complete"
    if change == "text_pdf_module": value["coverage"]["modules"]["b"] = "ok"
    if change in ("unknown", "boolean_count", "clearance", "complete_text", "text_pdf_module"): response.raw = json.dumps(value).encode()
    with pytest.raises(sdk.ReviewClientError): sdk.ReviewClient("http://127.0.0.1").review_text("synthetic")
    assert connection.closed
