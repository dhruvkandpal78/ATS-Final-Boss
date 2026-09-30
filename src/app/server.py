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
import signal
import sys
import tempfile
import threading
from time import monotonic
from uuid import uuid4
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, unquote

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.app.security import SecuritySettings, RequestBudget
from src.app.http_contract import SECURITY_HEADERS
from src.core.runtime_paths import models_directory, notice_path
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
        if os.environ.get("ATS_DEPLOYMENT_MODE", "local") == "private":
            os.environ["HF_HUB_OFFLINE"] = "1"
            os.environ["TRANSFORMERS_OFFLINE"] = "1"
        else:
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
            os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        from src.core.analysis_service import AnalysisService
        models = models_directory()
        if os.environ.get("ATS_DEPLOYMENT_MODE", "local") == "private":
            from src.core.artifacts import verify_policy, verify_candidate
            from src.inference import load_pipeline
            pin = os.environ["ATS_CANDIDATE_MANIFEST_SHA256"]
            manifest = verify_candidate(models, pin)
            verify_policy(manifest)
            clf, scaler, a, b, c = load_pipeline(models, expected_manifest_sha256=pin,
                embedding_dir=os.environ.get("ATS_EMBEDDING_DIR", str(models / "embedding")),
                expected_embedding_manifest_sha256=os.environ["ATS_EMBEDDING_MANIFEST_SHA256"])
            _SERVICE = AnalysisService(mod_a=a, mod_b=b, mod_c=c, meta_clf=clf, scaler=scaler)
            _SERVICE.candidate_model = True
            _SERVICE.model_id = "candidate-" + pin.lower()[:16]
        else:
            _SERVICE = AnalysisService(str(models))
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


def _silence_private_worker_output():
    """Private child diagnostics must not bypass the content-free parent log.

    This runs only in the spawned inference child. The IPC connection is a
    separate channel; errors are still reported using bounded generic statuses.
    """
    logging.disable(logging.CRITICAL)
    sink = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(sink, 1)
        os.dup2(sink, 2)
    finally:
        if sink not in (1, 2):
            os.close(sink)


def _worker_loop(connection):
    try:
        if os.environ.get("ATS_DEPLOYMENT_MODE", "local") == "private":
            _silence_private_worker_output()
            # Linux private deployments additionally require cgroup limits and
            # read-only mounts. A process alone is not a security sandbox.
            import resource
            memory = int(os.environ.get("ATS_WORKER_MEMORY_MIB", "4096")) * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))
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
        self.stopping = threading.Event()
        self.process = None
        self.connection = None
        self.ready = False

    def _close_locked(self):
        """Dispose of the worker while the request lock is held."""
        if self.process is not None:
            if self.process.is_alive():
                self.process.terminate()
            self.process.join(timeout=5)
            if self.process.is_alive():
                self.process.kill()
                self.process.join(timeout=5)
            if not self.process.is_alive():
                self.process.close()
        if self.connection is not None:
            self.connection.close()
        self.process = self.connection = None
        self.ready = False

    def shutdown(self, grace=5):
        """Stop admission, cancel active work, then release worker resources.

        Inference and cleanup remain owned by the request thread. Shutdown never
        closes a pipe concurrently with its recv/send operations.
        """
        self.stopping.set()
        if not self.lock.acquire(timeout=max(0, grace)):
            # A process blocked in native code might not observe the stop event.
            # Termination wakes its parent without racing on the connection.
            process = self.process
            if process is not None:
                try:
                    if process.is_alive():
                        process.terminate()
                except (OSError, ValueError):
                    pass
            if not self.lock.acquire(timeout=5):
                return False
        try:
            self._close_locked()
            return True
        finally:
            self.lock.release()

    def close(self):
        return self.shutdown()

    def run(self, payload):
        validate_payload(payload)
        if self.stopping.is_set():
            raise APIError(503, "Analysis service is stopping.")
        if not self.lock.acquire(blocking=False):
            raise APIError(429, "Another document is being analyzed. Retry shortly.")
        try:
            if self.stopping.is_set():
                raise APIError(503, "Analysis service is stopping.")
            if self.process is None or not self.process.is_alive():
                self._close_locked()
                context = mp.get_context("spawn")
                parent, child = context.Pipe()
                process = None
                try:
                    process = context.Process(target=_worker_loop, args=(child,), daemon=True)
                    process.start()
                except Exception:
                    parent.close()
                    if process is not None:
                        process.close()
                    raise APIError(503, "Analysis worker could not start.") from None
                finally:
                    child.close()
                self.connection, self.process = parent, process
            if self.stopping.is_set():
                self._close_locked()
                raise APIError(503, "Analysis service is stopping.")
            with tempfile.TemporaryDirectory(prefix="ats-analysis-") as directory:
                try:
                    deadline = monotonic() + self.timeout
                    sending_errors = []
                    connection = self.connection
                    def send_request():
                        try:
                            connection.send((payload, directory))
                        except (EOFError, BrokenPipeError, OSError) as exc:
                            sending_errors.append(exc)
                    sender = threading.Thread(target=send_request, daemon=True)
                    sender.start()
                    while sender.is_alive() and not self.stopping.is_set():
                        sender.join(timeout=min(0.2, max(0, deadline - monotonic())))
                        if monotonic() >= deadline:
                            break
                    if self.stopping.is_set():
                        self._close_locked()
                        sender.join(timeout=1)
                        raise APIError(503, "Analysis service is stopping.")
                    if sender.is_alive():
                        logger.error(json.dumps({"event": "worker_busy_timeout", "timeout": self.timeout}))
                        self._close_locked()
                        sender.join(timeout=1)
                        raise APIError(504, "Analysis worker did not accept the request within its deadline.")
                    if sending_errors:
                        raise sending_errors[0]
                    while not self.connection.poll(min(0.2, max(0, deadline - monotonic()))):
                        if self.stopping.is_set():
                            self._close_locked()
                            raise APIError(503, "Analysis service is stopping.")
                        if monotonic() >= deadline:
                            logger.error(json.dumps({"event": "worker_execution_timeout", "timeout": self.timeout}))
                            self._close_locked()
                            raise APIError(504, "Analysis exceeded its 90-second deadline. Try a shorter document.")
                    status, result = self.connection.recv()
                    self.ready = status == 200
                    if status != 200:
                        raise APIError(status, result["error"])
                    return result
                except (EOFError, BrokenPipeError, OSError) as exc:
                    exitcode = self.process.exitcode if self.process else None
                    logger.error(json.dumps({"event": "worker_crash", "error": str(exc), "exitcode": exitcode}))
                    self._close_locked()
                    raise APIError(503, "The analysis worker stopped. Please retry.") from None
        finally:
            self.lock.release()


WORKER = ModelWorker()


class BoundedHTTPServer(ThreadingHTTPServer):
    """Bound accepted connection threads, including slow request headers."""
    daemon_threads = False
    request_queue_size = 16

    def __init__(self, address, handler, security=None, max_connections=8):
        self.security = security or SecuritySettings()
        self.request_budget = RequestBudget(self.security.requests_per_minute)
        self.slots = threading.BoundedSemaphore(max_connections)
        super().__init__(address, handler)

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            try:
                # Consume at most one small already-arriving header fragment.
                # Closing with unread TCP data can discard the 503 on Windows.
                request.settimeout(0.05)
                try:
                    request.recv(8192)
                except socket.timeout:
                    pass
                request.settimeout(1)
                request.sendall(b"HTTP/1.0 503 Service Unavailable\r\nContent-Length: 0\r\nConnection: close\r\nRetry-After: 5\r\n\r\n")
            except OSError:
                pass
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()


class Handler(BaseHTTPRequestHandler):
    server_version = "ATSLocal"
    sys_version = ""

    def _guard(self, path):
        settings = getattr(self.server, "security", SecuritySettings())
        rejected = settings.authorize(self.headers, self.command, self.server.server_port, path)
        if rejected:
            self._discard_small_body()
            self._send(rejected[0], {"error": rejected[1]})
            return False
        if self.command == "POST" and hasattr(self.server, "request_budget"):
            if not self.server.request_budget.consume():
                self._discard_small_body()
                self._send(429, {"error": "Request budget exceeded. Retry later."})
                return False
        return True

    def _discard_small_body(self):
        """Drain a bounded small rejected body without parsing or processing it.

        Closing with unread incoming bytes can discard the response on Windows.
        Neither a large payload nor a slow sender may delay authorization denial.
        """
        if self.command != "POST" or self.headers.get("Transfer-Encoding"):
            return
        lengths = self.headers.get_all("Content-Length", [])
        if len(lengths) != 1:
            return
        try:
            length = int(lengths[0])
            if 0 < length <= 8192:
                self.connection.settimeout(0.05)
                self.rfile.read(length)
        except (ValueError, OSError):
            pass
        finally:
            self.connection.settimeout(15)

    def send_error(self, code, message=None, explain=None):
        self._send(code, {"error": "The HTTP request could not be accepted."})

    def setup(self):
        super().setup()
        self.connection.settimeout(15)
        self.request_id = str(uuid4())
        self.started_at = monotonic()

    def log_message(self, *args):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, dict):
            body = json.dumps(body, allow_nan=False)
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Request-Id", self.request_id)
        self.send_header("Connection", "close")
        self.close_connection = True
        for name, value in SECURITY_HEADERS.items():
            self.send_header(name, value)
        if code == 401:
            self.send_header("WWW-Authenticate", 'Bearer realm="resume-inspection"')
        if code in (429, 503):
            self.send_header("Retry-After", "5")
        self.end_headers()
        route = urlsplit(getattr(self, "path", "")).path
        known_routes = {"/", "/analyze", "/health", "/health/live", "/health/ready",
                        "/api/capabilities", "/methodology", "/lab", "/ownership"}
        logger.info(json.dumps({"event": "http_response", "request_id": self.request_id,
            "method": getattr(self, "command", None) if getattr(self, "command", None) in ("GET", "POST") else "other",
            "route": route if route in known_routes else "other", "status": code,
            "duration_ms": round((monotonic() - self.started_at) * 1000, 2)}))
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError, socket.timeout):
            pass

    def do_GET(self):
        path = urlsplit(self.path).path
        if not self._guard(path):
            return
        if path in ("/", "/index.html", "/analyze", "/methodology", "/lab", "/ownership"):
            try:
                self._send(200, INDEX_PATH.read_text(encoding="utf-8"), "text/html; charset=utf-8")
            except FileNotFoundError:
                self._send(404, {"error": "Frontend is unavailable."})
        elif path in ("/license", "/license-legacy"):
            try:
                notice = notice_path("LICENSE" if path == "/license" else "LICENSE-MIT-LEGACY.txt")
                self._send(200, notice.read_text(encoding="utf-8"), "text/plain; charset=utf-8")
            except FileNotFoundError:
                self._send(404, {"error": "Public notice is unavailable."})
        elif path == "/health/live":
            self._send(200, {"ok": True})
        elif path == "/health":
            self._send(200, {"ok": True, "model_ready": WORKER.ready, "busy": WORKER.lock.locked()})
        elif path == "/health/ready":
            ready = (not WORKER.stopping.is_set() and WORKER.ready and
                     WORKER.process is not None and WORKER.process.is_alive())
            self._send(200 if ready else 503, {"ready": ready})
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
        if not self._guard(urlsplit(self.path).path):
            return
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
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    port = int(os.environ.get("PORT", "8000"))
    host = os.environ.get("HOST", "127.0.0.1")
    settings = SecuritySettings.from_env(host)
    if settings.mode == "private" and sys.platform != "linux":
        raise ValueError("Private mode requires a resource-limited Linux container; native demo mode stays local")
    if settings.mode == "private":
        from src.core.artifacts import verify_candidate, verify_policy
        bundle = Path(os.environ.get("ATS_MODELS_DIR", str(MODELS_DIR)))
        verify_policy(verify_candidate(bundle, os.environ["ATS_CANDIDATE_MANIFEST_SHA256"]))
    server = BoundedHTTPServer((host, port), Handler, settings)
    def stop(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    print(f"ATS Final Boss: http://{host}:{port} (models load on first analysis)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        WORKER.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
