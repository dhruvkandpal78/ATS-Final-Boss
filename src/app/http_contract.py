"""Shared request and browser response policy for both HTTP adapters."""

import re
import json

MAX_JSON_DEPTH = 64


class HTTPContractError(ValueError):
    def __init__(self, status, message, *, retry_after=None):
        super().__init__(message)
        self.status = status
        self.retry_after = retry_after


def _strict_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicate JSON fields.")
        value[key] = item
    return value


def _reject_constant(_):
    raise ValueError("Nonfinite JSON constant.")


def decode_json_body(raw, *, strict=False):
    """Bound nesting independently of Python's parser/recursion implementation."""
    try:
        text = raw.decode("utf-8-sig")
        depth = 0
        quoted = escaped = False
        for char in text:
            if quoted:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    quoted = False
            elif char == '"':
                quoted = True
            elif char in "[{":
                depth += 1
                if depth > MAX_JSON_DEPTH:
                    raise HTTPContractError(400, "Invalid JSON payload.")
            elif char in "]}":
                depth -= 1
        return json.loads(text, **({"object_pairs_hook": _strict_object, "parse_constant": _reject_constant} if strict else {}))
    except (ValueError, UnicodeDecodeError, RecursionError):
        raise HTTPContractError(400, "Invalid JSON payload.") from None


def json_request_length(headers, max_body_bytes):
    """Validate framing and media type before reading a JSON request body."""
    if headers.get_all("Transfer-Encoding", []):
        raise HTTPContractError(400, "Transfer-Encoding is unsupported.")
    lengths = headers.get_all("Content-Length", [])
    if len(lengths) != 1:
        raise HTTPContractError(411, "One Content-Length header is required.")
    value = lengths[0]
    if not re.fullmatch(r"[0-9]+", value):
        raise HTTPContractError(400, "Invalid Content-Length.")
    significant = value.lstrip("0")
    if not significant:
        raise HTTPContractError(400, "Request body must not be empty.")
    maximum = str(max_body_bytes)
    if len(significant) > len(maximum) or (len(significant) == len(maximum) and significant > maximum):
        raise HTTPContractError(413, "Request exceeds the 7 MiB encoded-body limit.")
    if len(headers.get_all("Content-Type", [])) != 1 or headers.get_content_type() != "application/json":
        raise HTTPContractError(415, "Use application/json.")
    return int(significant)

SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": (
        "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; "
        "base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
    ),
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
}
