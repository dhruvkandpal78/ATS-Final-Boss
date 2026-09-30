"""Native-worker boundary regressions: data-only IPC and whole-frame deadlines."""
import json
from functools import partial
import multiprocessing as mp
import os
import pickle
import struct
import threading
from time import monotonic, sleep

import pytest

from src.app import server
from src.app.worker_protocol import (
    MAX_RESPONSE_BYTES, ProtocolError, encode_message, receive_message,
    validate_response,
)

REQUEST_ID = "a" * 32


def analysis_result():
    return {"schema_version": "2.0", "analysis_id": REQUEST_ID,
            "created_at": "2026-09-30T00:00:00Z", "policy_version": "2.0",
            "status": "unscorable", "input_mode": "text",
            "decision": "insufficient_evidence", "score_kind": "unavailable", "score": None,
            "coverage": {"pages_total": None, "pages_analyzed": None, "limitations": []},
            "modules": {key: {"status": "unsupported"} for key in "abc"},
            "model": {}, "timings_ms": {}, "findings": [], "reason_codes": []}


def envelope(**changes):
    value = {"version": 1, "request_id": REQUEST_ID, "status": 200,
             "result": analysis_result()}
    value.update(changes)
    return value


def test_actual_pipe_uses_json_and_rejects_oversized_frame():
    parent, child = mp.Pipe()
    try:
        child.send_bytes(encode_message(envelope(), 1024))
        assert validate_response(receive_message(parent, 1024), REQUEST_ID) == (200, analysis_result())
        child.send_bytes(b"x" * 2000)
        with pytest.raises(OSError):
            receive_message(parent, 1024)
    finally:
        parent.close()
        child.close()


def _touch_marker(path):
    open(path, "w").close()


def test_pickle_payload_is_rejected_without_executing_it(tmp_path):
    marker = tmp_path / "must-not-exist"
    class Executable:
        def __reduce__(self):
            return _touch_marker, (str(marker),)
    parent, child = mp.Pipe()
    try:
        child.send_bytes(pickle.dumps(Executable()))
        with pytest.raises(ProtocolError):
            receive_message(parent, 1024)
        assert not marker.exists()
    finally:
        parent.close()
        child.close()


@pytest.mark.parametrize("changes", [
    {"version": True}, {"version": 2}, {"status": True}, {"status": 302},
    {"request_id": "b" * 32}, {"result": []}, {"unexpected": "field"},
])
def test_wrong_envelopes_and_stale_replies_are_rejected(changes):
    parent, child = mp.Pipe()
    try:
        child.send_bytes(encode_message(envelope(**changes), 1024))
        with pytest.raises(ProtocolError):
            validate_response(receive_message(parent, 1024), REQUEST_ID)
    finally:
        parent.close()
        child.close()


def test_worker_cannot_relay_private_exception_text():
    status, body = validate_response(envelope(status=503, result={"error": "private resume text /secret/path"}), REQUEST_ID)
    assert status == 503 and "private" not in body["error"] and "/secret" not in body["error"]


def test_invalid_output_numbers_and_oversized_messages_are_refused():
    with pytest.raises(ProtocolError):
        encode_message(envelope(result={"score": float("nan")}), 1024)
    with pytest.raises(ProtocolError):
        encode_message(envelope(result={"blob": "a" * 1024}), 100)


@pytest.mark.parametrize("number", ["NaN", "Infinity", "1e999"])
def test_nonfinite_numbers_from_untrusted_child_are_rejected(number):
    parent, child = mp.Pipe()
    try:
        raw = json.dumps(envelope()).replace('"score": null', '"score": ' + number).encode()
        child.send_bytes(raw)
        with pytest.raises(ProtocolError):
            receive_message(parent, 1024)
    finally:
        parent.close()
        child.close()


def test_real_worker_loop_success_failure_and_nonserializable_result(monkeypatch):
    monkeypatch.setenv("ATS_DEPLOYMENT_MODE", "local")
    results = iter([analysis_result(), ValueError("secret candidate content"), {"invalid": object()}])
    def analyze(payload, directory):
        result = next(results)
        if isinstance(result, Exception):
            raise result
        return result
    monkeypatch.setattr(server, "analyze_payload", analyze)
    parent, child = mp.Pipe()
    thread = threading.Thread(target=server._worker_loop, args=(child,))
    thread.start()
    try:
        for expected in (200, 422, 503):
            parent.send_bytes(encode_message({"version": 1, "request_id": REQUEST_ID,
                "payload": {"text": "synthetic"}, "directory": "/synthetic"}, 1024))
            assert parent.poll(2)
            status, result = validate_response(receive_message(parent, MAX_RESPONSE_BYTES), REQUEST_ID)
            assert status == expected
            assert "secret candidate" not in json.dumps(result)
    finally:
        parent.close()
        thread.join(2)
    assert not thread.is_alive()


@pytest.mark.parametrize("changes", [
    {"schema_version": "1.0"}, {"decision": "hire"}, {"score": 1.1, "score_kind": "model_score"},
    {"score": True, "score_kind": "model_score"}, {"coverage": {}}, {"modules": {}},
    {"findings": ["not an observation"]}, {"score_kind": "model_score"},
])
def test_malformed_success_contract_is_rejected(changes):
    result = analysis_result()
    result.update(changes)
    with pytest.raises(ProtocolError):
        validate_response(envelope(result=result), REQUEST_ID)


def _partial_frame_worker(connection, ready):
    connection.recv_bytes()
    # A valid frame length plus one byte is sufficient for poll() to become
    # readable, but never enough for recv_bytes() to finish.
    os.write(connection.fileno(), struct.pack("!i", 256) + b"{")
    ready.set()
    sleep(30)


@pytest.mark.skipif(os.name == "nt", reason="POSIX pipe-frame test; Windows uses named pipes")
def test_partial_native_worker_frame_does_not_escape_deadline(monkeypatch):
    ready = mp.get_context("spawn").Event()
    monkeypatch.setattr(server, "_worker_loop", partial(_partial_frame_worker, ready=ready))
    worker = server.ModelWorker(timeout=3)
    started = monotonic()
    with pytest.raises(server.APIError) as caught:
        worker.run({"text": "synthetic resume"})
    assert caught.value.status == 504
    assert ready.is_set(), "The child must have written the partial frame before the deadline"
    assert monotonic() - started < 7
    assert worker.process is None and worker.connection is None
    assert not worker.lock.locked()
