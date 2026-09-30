"""Data-only, bounded messages across the native inference process boundary.

Connection.send/recv use pickle and must never be used on this boundary. A
worker processing native PDF input is not trusted to send executable objects.
"""
from __future__ import annotations

import json
import math

from src.app.http_contract import decode_json_body

PROTOCOL_VERSION = 1
MAX_REQUEST_BYTES = 7 * 1024 * 1024 + 8192
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
ERROR_MESSAGES = {
    400: "The analysis request could not be read.",
    413: "The document exceeds the configured size limit.",
    415: "The document format is unsupported.",
    422: "The document could not be analyzed. Check its format and configured limits.",
    503: "Analysis could not be completed. Check the local model setup and retry.",
}


class ProtocolError(ValueError):
    """Invalid or oversized worker message; never includes document content."""


def encode_message(message: dict, maximum: int) -> bytes:
    try:
        raw = json.dumps(message, ensure_ascii=False, allow_nan=False,
                         separators=(",", ":")).encode("utf-8")
    except (ValueError, TypeError, RecursionError, UnicodeError):
        raise ProtocolError("Invalid worker message.") from None
    if len(raw) > maximum:
        raise ProtocolError("Worker message exceeds its byte limit.")
    return raw


def receive_message(connection, maximum: int) -> dict:
    # recv_bytes rejects an oversized frame before allocating its body.
    raw = connection.recv_bytes(maxlength=maximum)
    try:
        message = decode_json_body(raw)
    except ValueError:
        raise ProtocolError("Invalid worker JSON.") from None
    pending = [message]
    while pending:
        value = pending.pop()
        if isinstance(value, float) and not math.isfinite(value):
            raise ProtocolError("Non-finite worker number.")
        if isinstance(value, dict):
            pending.extend(value.values())
        elif isinstance(value, list):
            pending.extend(value)
    if not isinstance(message, dict) or type(message.get("version")) is not int or message["version"] != PROTOCOL_VERSION:
        raise ProtocolError("Invalid worker protocol version.")
    if not isinstance(message.get("request_id"), str) or len(message["request_id"]) != 32:
        raise ProtocolError("Invalid worker request identifier.")
    return message


def validate_request(message: dict) -> tuple[dict, str]:
    if (set(message) != {"version", "request_id", "payload", "directory"} or
            not isinstance(message["payload"], dict) or
            not isinstance(message["directory"], str) or not message["directory"] or
            len(message["directory"]) > 4096):
        raise ProtocolError("Invalid worker request envelope.")
    return message["payload"], message["directory"]


def validate_response(message: dict, request_id: str) -> tuple[int, dict]:
    if (set(message) != {"version", "request_id", "status", "result"} or
            message["request_id"] != request_id or type(message["status"]) is not int or
            message["status"] not in {200, *ERROR_MESSAGES} or
            not isinstance(message["result"], dict)):
        raise ProtocolError("Invalid worker response envelope.")
    status = message["status"]
    if status == 200:
        validate_analysis_result(message["result"])
    # Do not relay arbitrary exception text from the less-trusted native worker.
    return status, message["result"] if status == 200 else {"error": ERROR_MESSAGES[status]}


def validate_analysis_result(result: dict) -> None:
    """Require the maintained result shape before accepting a successful child.

    This validates structure, not the truth of findings from a compromised
    worker. Model integrity and operating-system containment remain necessary.
    """
    invalid = ProtocolError("Invalid worker analysis result.")
    if (result.get("schema_version") != "2.0" or
            result.get("status") not in ("complete", "partial", "unscorable") or
            result.get("input_mode") not in ("text", "pdf") or
            result.get("decision") not in ("no_signals_detected", "review_recommended", "insufficient_evidence") or
            result.get("score_kind") not in ("model_score", "calibrated_probability", "unavailable")):
        raise invalid
    for key in ("analysis_id", "created_at", "policy_version"):
        if not isinstance(result.get(key), str) or not result[key]:
            raise invalid
    for key in ("coverage", "modules", "model", "timings_ms"):
        if not isinstance(result.get(key), dict):
            raise invalid
    for key in ("findings", "reason_codes"):
        if not isinstance(result.get(key), list):
            raise invalid
    if any(not isinstance(item, dict) for item in result["findings"]) or any(
            not isinstance(item, str) for item in result["reason_codes"]):
        raise invalid
    score = result.get("score")
    if "score" not in result or (score is not None and
            (type(score) not in (int, float) or not math.isfinite(score) or not 0 <= score <= 1)):
        raise invalid
    if (result["score_kind"] == "unavailable") != (score is None):
        raise invalid
    coverage = result["coverage"]
    if not isinstance(coverage.get("limitations"), list) or any(
            not isinstance(item, str) for item in coverage["limitations"]):
        raise invalid
    for key in ("pages_total", "pages_analyzed"):
        if key not in coverage or (coverage[key] is not None and
                (type(coverage[key]) is not int or coverage[key] < 0)):
            raise invalid
    for key in ("a", "b", "c"):
        module = result["modules"].get(key)
        if not isinstance(module, dict) or module.get("status") not in ("ok", "not_applicable", "unsupported", "error"):
            raise invalid
