"""Shared HTTP framing checks without model or document dependencies."""

from email.message import Message
import http.client
import json
import logging
import sys
import threading

import pytest

from src.app import server
from src.app.http_contract import HTTPContractError, decode_json_body, json_request_length


def headers(*fields):
    message = Message()
    for name, value in fields:
        message[name] = value
    return message


@pytest.mark.parametrize("fields,status,message", [
    ([], 411, "One Content-Length header is required."),
    ([("Content-Length", "1"), ("Content-Length", "2")], 411, "One Content-Length header is required."),
    ([("Content-Length", "-1")], 400, "Invalid Content-Length."),
    ([("Content-Length", "+1")], 400, "Invalid Content-Length."),
    ([("Content-Length", " 1")], 400, "Invalid Content-Length."),
    ([("Content-Length", "1 ")], 400, "Invalid Content-Length."),
    ([("Content-Length", "1, 2")], 400, "Invalid Content-Length."),
    ([("Content-Length", "١")], 400, "Invalid Content-Length."),
    ([("Content-Length", "0")], 400, "Request body must not be empty."),
    ([("Content-Length", "0000")], 400, "Request body must not be empty."),
    ([("Content-Length", "7000001")], 413, "Request exceeds the 7 MiB encoded-body limit."),
    ([("Content-Length", "9" * 10000)], 413, "Request exceeds the 7 MiB encoded-body limit."),
    ([("Content-Length", "1"), ("Transfer-Encoding", "")], 400, "Transfer-Encoding is unsupported."),
    ([("Content-Length", "1"), ("Transfer-Encoding", "chunked")], 400, "Transfer-Encoding is unsupported."),
    ([("Content-Length", "1"), ("Content-Type", "text/plain")], 415, "Use application/json."),
    ([("Content-Length", "1"), ("Content-Type", "application/json"),
      ("Content-Type", "application/json")], 415, "Use application/json."),
])
def test_rejects_ambiguous_or_invalid_json_headers(fields, status, message):
    value = headers(*fields)
    if not value.get_all("Content-Type", []):
        value["Content-Type"] = "application/json"
    with pytest.raises(HTTPContractError) as caught:
        json_request_length(value, 7_000_000)
    assert caught.value.status == status
    assert str(caught.value) == message


@pytest.mark.parametrize("length,expected", [("1", 1), ("0001", 1), ("7000000", 7_000_000)])
def test_accepts_exact_json_headers(length, expected):
    value = headers(("Content-Length", length), ("Content-Type", "application/json; charset=utf-8"))
    assert json_request_length(value, 7_000_000) == expected


def test_json_depth_limit_and_string_escapes():
    body = b"[" * 64 + b"0" + b"]" * 64
    assert isinstance(decode_json_body(body), list)
    with pytest.raises(HTTPContractError) as caught:
        decode_json_body(b"[" * 65 + b"0" + b"]" * 65)
    assert caught.value.status == 400
    value = {"text": ('[{}]\\\\\"' * 100)}
    assert decode_json_body(json.dumps(value).encode()) == value


@pytest.mark.parametrize("body", [b"{", b"\xff", '{"text":"test"}'.encode("utf-16")])
def test_json_requires_valid_utf8(body):
    with pytest.raises(HTTPContractError):
        decode_json_body(body)


def test_local_adapter_reports_deep_json_as_client_error(monkeypatch):
    monkeypatch.setattr(server.WORKER, "run", lambda payload: pytest.fail("Worker should not receive invalid JSON"))
    instance = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    thread = threading.Thread(target=instance.serve_forever, daemon=True)
    thread.start()
    try:
        depth = 65
        body = ("[" * depth + "0" + "]" * depth).encode("ascii")
        connection = http.client.HTTPConnection(*instance.server_address, timeout=3)
        connection.request("POST", "/analyze", body=body, headers={"Content-Type": "application/json"})
        response = connection.getresponse()
        assert response.status == 400
        assert json.loads(response.read()) == {"error": "Invalid JSON payload."}
        connection.close()
    finally:
        instance.shutdown()
        instance.server_close()
        thread.join(timeout=2)


def test_worker_crash_log_excludes_exception_message(caplog):
    class Process:
        exitcode = 1
        alive = True

        def is_alive(self):
            return self.alive

        def terminate(self):
            self.alive = False

        def join(self, timeout=None):
            pass

        def close(self):
            pass

    class Connection:
        def send(self, payload):
            pass

        def poll(self, timeout):
            raise OSError("private candidate content and C:/sensitive/path")

        def close(self):
            pass

    worker = server.ModelWorker(timeout=1)
    worker.process = Process()
    worker.connection = Connection()
    with caplog.at_level(logging.ERROR, logger=server.__name__):
        with pytest.raises(server.APIError) as caught:
            worker.run({"text": "synthetic resume"})
    assert caught.value.status == 503
    assert "private candidate content" not in caplog.text
    assert "sensitive/path" not in caplog.text
    events = [json.loads(record.message) for record in caplog.records if record.name == server.__name__]
    assert events[-1] == {"event": "worker_crash", "error_type": "OSError", "exitcode": 1}
