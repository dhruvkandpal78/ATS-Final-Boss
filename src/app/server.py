"""Local document-integrity API with lazy, isolated inference.

Run ``python src/app/server.py``. Model downloads are disabled by default.
The HTTP process never loads models or retains uploaded resumes.
"""
from __future__ import annotations

import base64
import binascii
import json
import logging
import mimetypes
import multiprocessing as mp
import os
from pathlib import Path
import socket
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, unquote

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
INDEX_PATH = ROOT / "src" / "app" / "index.html"
MODELS_DIR = ROOT / "results" / "models"
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_BODY_BYTES = 7 * 1024 * 1024
MAX_TEXT_CHARS = 100_000
MAX_PAGES = 20
INFERENCE_TIMEOUT = 90
_SERVICE = None
logger = logging.getLogger(__name__)


class APIError(ValueError):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def get_service():
    global _SERVICE
    if _SERVICE is None:
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        from src.core.analysis_service import AnalysisService
        _SERVICE = AnalysisService(str(MODELS_DIR))
    return _SERVICE


def validate_payload(payload):
    if not isinstance(payload, dict):
        raise APIError(422, "The request must be a JSON object.")
    text = payload.get("text")
    filename = payload.get("filename")
    encoded = payload.get("b64")
    if encoded is not None or filename is not None:
        if text is not None:
            raise APIError(422, "Choose either text or a PDF upload.")
        if not isinstance(filename, str) or not filename.lower().endswith(".pdf"):
            raise APIError(415, "Only PDF uploads are supported. Paste plain text in the text field.")
        if not isinstance(encoded, str) or not encoded:
            raise APIError(422, "Missing base64 PDF data.")
        if len(encoded) > 4 * ((MAX_FILE_BYTES + 2) // 3):
            raise APIError(413, "PDF exceeds the 5 MiB limit.")
        try:
            raw = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error):
            raise APIError(422, "Invalid base64 PDF data.") from None
        if len(raw) > MAX_FILE_BYTES:
            raise APIError(413, "PDF exceeds the 5 MiB limit.")
        if not raw.startswith(b"%PDF-"):
            raise APIError(415, "The uploaded file does not have a PDF signature.")
        return "pdf", raw
    if not isinstance(text, str) or not text.strip():
        raise APIError(422, "Enter non-empty resume text or upload a PDF.")
    if len(text) > MAX_TEXT_CHARS:
        raise APIError(413, "Text exceeds the 100,000 character limit.")
    return "text", text


def analyze_payload(payload, temp_dir=None):
    mode, value = validate_payload(payload)
    service = get_service()
    if mode == "text":
        return service.analyze_text(value)
    # Parent-owned directory also gets removed if the worker is terminated.
    with tempfile.NamedTemporaryFile(suffix=".pdf", dir=temp_dir, delete=False) as file:
        path = file.name
        file.write(value)
    try:
        return service.analyze_pdf(path, include_previews=True)
    finally:
        Path(path).unlink(missing_ok=True)


def _score(text, b_score=None, pdf_details=None):
    """Compatibility entry point; synthetic structural markers are never evidence."""
    return get_service().analyze_text(text)


def _worker_loop(connection):
    try:
        while True:
            payload, directory = connection.recv()
            try:
                result = analyze_payload(payload, directory)
                connection.send((200, result))
            except APIError as exc:
                connection.send((exc.status, {"error": str(exc)}))
            except (ImportError, FileNotFoundError, OSError):
                connection.send((503, {"error": "Analysis dependencies are unavailable. Run scripts/doctor.py locally."}))
            except ValueError:
                connection.send((422, {"error": "The document could not be analyzed. Check its format and configured limits."}))
            except Exception:
                # No resume text, local paths, exception messages or traces in responses/logs.
                connection.send((503, {"error": "Analysis could not be completed. Check the local model setup and retry."}))
    except (EOFError, BrokenPipeError):
        pass
    finally:
        connection.close()


class ModelWorker:
    """One persistent model process, no waiting queue, hard per-request deadline."""
    def __init__(self, timeout=INFERENCE_TIMEOUT):
        self.timeout = timeout
        self.lock = threading.Lock()
        self.process = None
        self.connection = None
        self.ready = False

    def close(self):
        if self.process is not None:
            if self.process.is_alive():
                self.process.terminate()
            self.process.join(timeout=5)
            if self.process.is_alive():
                self.process.kill()
                self.process.join()
            self.process.close()
        if self.connection is not None:
            self.connection.close()
        self.process = self.connection = None
        self.ready = False

    def run(self, payload):
        validate_payload(payload)
        if not self.lock.acquire(blocking=False):
            raise APIError(429, "Another document is being analyzed. Retry shortly.")
        try:
            if self.process is None or not self.process.is_alive():
                self.close()
                context = mp.get_context("spawn")
                self.connection, child = context.Pipe()
                self.process = context.Process(target=_worker_loop, args=(child,), daemon=True)
                self.process.start()
                child.close()
            with tempfile.TemporaryDirectory(prefix="ats-analysis-") as directory:
                try:
                    self.connection.send((payload, directory))
                    if not self.connection.poll(self.timeout):
                        self.close()
                        raise APIError(504, "Analysis exceeded its 90-second deadline. Try a shorter document.")
                    status, result = self.connection.recv()
                    self.ready = status == 200
                    if status != 200:
                        raise APIError(status, result["error"])
                    return result
                except (EOFError, BrokenPipeError, OSError):
                    self.close()
                    raise APIError(503, "The analysis worker stopped. Please retry.") from None
        finally:
            self.lock.release()


WORKER = ModelWorker()


class Handler(BaseHTTPRequestHandler):
    server_version = "ATSLocal"

    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def log_message(self, *args):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, dict):
            body = json.dumps(body, allow_nan=False)
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        if code in (429, 503):
            self.send_header("Retry-After", "5")
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError, socket.timeout):
            pass

    def do_GET(self):
        path = urlsplit(self.path).path
        if path in ("/", "/index.html", "/analyze", "/methodology", "/lab", "/ownership"):
            try:
                self._send(200, INDEX_PATH.read_text(encoding="utf-8"), "text/html; charset=utf-8")
            except FileNotFoundError:
                self._send(404, {"error": "Frontend is unavailable."})
        elif path in ("/license", "/license-legacy"):
            notice = ROOT / ("LICENSE" if path == "/license" else "LICENSE-MIT-LEGACY.txt")
            self._send(200, notice.read_text(encoding="utf-8"), "text/plain; charset=utf-8")
        elif path == "/health":
            self._send(200, {"ok": True, "model_ready": WORKER.ready, "busy": WORKER.lock.locked()})
        elif path.startswith("/assets/"):
            assets = (ROOT / "src" / "app" / "assets").resolve()
            target = (assets / unquote(path[len("/assets/"):])).resolve()
            if assets not in target.parents or target.suffix not in (".css", ".js", ".svg", ".woff2", ".png", ".webp") or not target.is_file():
                self._send(404, {"error": "Asset not found."})
            else:
                self._send(200, target.read_bytes(), mimetypes.guess_type(str(target))[0] or "application/octet-stream")
        elif path == "/api/capabilities":
            self._send(200, {"input_modes": ["text", "pdf"], "max_file_bytes": MAX_FILE_BYTES,
                "max_text_characters": MAX_TEXT_CHARS, "max_pages": MAX_PAGES,
                "deadline_seconds": INFERENCE_TIMEOUT, "concurrent_analyses": 1,
                "lab_enabled": False, "retention": "temporary files deleted after processing",
                "cancellation": "Client cancellation stops waiting; worker finishes or reaches deadline."})
        else:
            self._send(404, {"error": "Not found."})

    def do_POST(self):
        if urlsplit(self.path).path != "/analyze":
            self._send(404, {"error": "Not found. Experimental lab endpoints are disabled."})
            return
        try:
            if self.headers.get("Transfer-Encoding"):
                raise APIError(400, "Transfer-Encoding is unsupported.")
            lengths = self.headers.get_all("Content-Length", [])
            if len(lengths) != 1:
                raise APIError(411, "One Content-Length header is required.")
            try:
                length = int(lengths[0])
            except ValueError:
                raise APIError(400, "Invalid Content-Length.") from None
            if length <= 0:
                raise APIError(400, "Request body must not be empty.")
            if length > MAX_BODY_BYTES:
                raise APIError(413, "Request exceeds the 7 MiB encoded-body limit.")
            if self.headers.get_content_type() != "application/json":
                raise APIError(415, "Use application/json.")
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise APIError(400, "Incomplete request body.")
            try:
                payload = json.loads(raw)
            except (ValueError, UnicodeDecodeError):
                raise APIError(400, "Invalid JSON payload.") from None
            self._send(200, WORKER.run(payload))
        except APIError as exc:
            self._send(exc.status, {"error": str(exc)})
        except socket.timeout:
            self._send(408, {"error": "Request upload timed out."})
        except Exception:
            self._send(503, {"error": "Analysis is currently unavailable."})


def main():
    port = int(os.environ.get("PORT", "8000"))
    host = os.environ.get("HOST", "127.0.0.1")
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"ATS Final Boss: http://{host}:{port} (models load on first analysis)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        WORKER.close()


if __name__ == "__main__":
    main()
