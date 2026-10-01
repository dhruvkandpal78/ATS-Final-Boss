"""Synchronous server-side review SDK; no retries, redirects or stored resumes."""
import base64
import http.client
import json
import math
import ssl
from urllib.parse import urlsplit
from uuid import UUID

from src.app.http_contract import decode_json_body
from src.app.integration_contract import REVIEW_ROUTE, validate_review_response
from src.app.security import loopback

MAX_RESPONSE_BYTES = 64 * 1024


class ReviewClientError(RuntimeError):
    def __init__(self, status=None, retry_after=None):
        super().__init__("Review did not return a valid success; do not forward automatically.")
        self.status, self.retry_after = status, retry_after


class ReviewClient:
    def __init__(self, base_url, *, bearer_token=None, timeout=110):
        url = urlsplit(base_url)
        if (url.scheme not in ("http", "https") or not url.hostname or url.username or url.password or
                url.path not in ("", "/") or url.query or url.fragment):
            raise ValueError("Use an explicit service origin without credentials, path or query.")
        if url.scheme == "http" and not loopback(url.hostname):
            raise ValueError("Remote origins require verified HTTPS.")
        if bearer_token is not None and (not isinstance(bearer_token, str) or not 1 <= len(bearer_token) <= 4096 or
                                         any(not 33 <= ord(c) <= 126 for c in bearer_token)):
            raise ValueError("Invalid bearer token format.")
        if not loopback(url.hostname) and bearer_token is None:
            raise ValueError("Remote service origins require explicit server-side authentication.")
        if type(timeout) not in (int, float) or not 0 < timeout <= 300 or not math.isfinite(timeout):
            raise ValueError("Socket timeout must be finite and at most 300 seconds.")
        self.host, self.port, self.secure = url.hostname, url.port, url.scheme == "https"
        self._token, self.timeout = bearer_token, timeout

    def review_text(self, text):
        if not isinstance(text, str) or not text.strip() or len(text) > 100000:
            raise ValueError("Expected nonempty text of at most 100,000 characters.")
        return self._send({"text": text})

    def review_pdf(self, content):
        if not isinstance(content, bytes) or not content.startswith(b"%PDF-") or len(content) > 5 * 1024 * 1024:
            raise ValueError("Expected PDF bytes of at most 5 MiB.")
        return self._send({"filename": "document.pdf", "b64": base64.b64encode(content).decode("ascii")})

    def _send(self, payload):
        try:
            body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        except (ValueError, UnicodeError):
            raise ValueError("Text must be valid UTF-8.") from None
        if len(body) > 7 * 1024 * 1024:
            raise ValueError("Encoded request exceeds 7 MiB.")
        connection = (http.client.HTTPSConnection(self.host, self.port, timeout=self.timeout,
                                                 context=ssl.create_default_context()) if self.secure else
                      http.client.HTTPConnection(self.host, self.port, timeout=self.timeout))
        headers = {"Content-Type": "application/json", "Content-Length": str(len(body)), "Connection": "close"}
        if self._token:
            headers["Authorization"] = "Bearer " + self._token
        try:
            connection.request("POST", REVIEW_ROUTE, body, headers)
            response = connection.getresponse()
            retry = response.getheader("Retry-After", "")
            retry_after = int(retry) if retry.isascii() and retry.isdecimal() and len(retry) <= 5 else None
            if response.status != 200:
                # Never follow a redirect or expose server error text / credentials.
                raise ReviewClientError(response.status, retry_after)
            if response.getheader("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
                raise ReviewClientError(503)
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise ReviewClientError(503)
            value = decode_json_body(raw, strict=True)
            validate_review_response(value)
            request_id = response.getheader("X-Request-Id", "")
            if UUID(request_id).version != 4:
                raise ValueError("Invalid request id.")
            return {"request_id": str(UUID(request_id)), "review": value}
        except ReviewClientError:
            raise
        except (OSError, http.client.HTTPException, ValueError):
            raise ReviewClientError(503) from None
        finally:
            connection.close()
