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
from src.app.http_contract import HTTPContractError, SECURITY_HEADERS, decode_json_body, json_request_length
from src.core.runtime_paths import models_directory, notice_path
from src.app.worker_protocol import (
    PROTOCOL_VERSION, MAX_REQUEST_BYTES, MAX_RESPONSE_BYTES, ProtocolError,
    encode_message, receive_message, validate_request, validate_response,
)
from src.app.worker_recovery import WorkerRecovery
from src.app.integration_contract import REVIEW_ROUTE, REVIEW_CAPABILITIES, project_review, validate_review_request
from src.app.metrics import RuntimeMetrics, METRICS_JSON_ROUTE, METRICS_TEXT_ROUTE
INDEX_PATH = ROOT / "src" / "app" / "index.html"
MODELS_DIR = ROOT / "results" / "models"
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_BODY_BYTES = 7 * 1024 * 1024
MAX_TEXT_CHARS = 100_000
MAX_PAGES = 20
INFERENCE_TIMEOUT = 90
_SERVICE = None
logger = logging.getLogger(__name__)


APIError = HTTPContractError


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
        candidate_pin = os.environ.get("ATS_CANDIDATE_MANIFEST_SHA256")
        embedding_pin = os.environ.get("ATS_EMBEDDING_MANIFEST_SHA256")
        if os.environ.get("ATS_DEPLOYMENT_MODE", "local") == "private" or candidate_pin or embedding_pin:
            from src.core.artifacts import verify_policy, verify_candidate, require_deployment_approval
            from src.inference import load_pipeline
            if not candidate_pin or not embedding_pin:
                raise ValueError("Pinned local analysis requires both candidate and embedding manifest hashes")
            manifest = verify_candidate(models, candidate_pin)
            verify_policy(manifest)
            if os.environ.get("ATS_DEPLOYMENT_MODE", "local") == "private":
                require_deployment_approval(manifest)
            clf, scaler, a, b, c = load_pipeline(models, expected_manifest_sha256=candidate_pin,
                embedding_dir=os.environ.get("ATS_EMBEDDING_DIR", str(models / "embedding")),
                expected_embedding_manifest_sha256=embedding_pin)
            _SERVICE = AnalysisService(mod_a=a, mod_b=b, mod_c=c, meta_clf=clf, scaler=scaler)
            _SERVICE.candidate_model = True
            _SERVICE.model_id = "candidate-" + candidate_pin.lower()[:16]
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
            message = receive_message(connection, MAX_REQUEST_BYTES)
            payload, directory = validate_request(message)
            status = 200
            try:
                result = analyze_payload(payload, directory)
            except APIError as exc:
                status, result = exc.status, {}
            except (ImportError, FileNotFoundError, OSError):
                status, result = 503, {}
            except ValueError:
                status, result = 422, {}
            except Exception:
                # No resume text, local paths, exception messages or traces in responses/logs.
                status, result = 503, {}
            response = {"version": PROTOCOL_VERSION, "request_id": message["request_id"],
                        "status": status, "result": result}
            try:
                encoded = encode_message(response, MAX_RESPONSE_BYTES)
            except ProtocolError:
                response.update(status=503, result={})
                encoded = encode_message(response, MAX_RESPONSE_BYTES)
            connection.send_bytes(encoded)
    except (EOFError, OSError, ProtocolError):
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
        self.recovery = WorkerRecovery(lambda: monotonic())

    def recovery_snapshot(self):
        return self.recovery.snapshot()

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
        attempted = False
        try:
            if self.stopping.is_set():
                raise APIError(503, "Analysis service is stopping.")
            retry_after = self.recovery.remaining()
            if retry_after:
                raise APIError(503, "Analysis is temporarily unavailable while the worker recovers. Retry shortly.",
                               retry_after=retry_after)
            attempted = True
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
                    request_id = uuid4().hex
                    encoded = encode_message({"version": PROTOCOL_VERSION,
                                              "request_id": request_id,
                                              "payload": payload, "directory": directory}, MAX_REQUEST_BYTES)
                    sending_errors = []
                    connection = self.connection
                    def send_request():
                        try:
                            connection.send_bytes(encoded)
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
                    if sender.is_alive() or monotonic() >= deadline:
                        logger.error(json.dumps({"event": "worker_busy_timeout", "timeout": self.timeout}))
                        self._close_locked()
                        sender.join(timeout=1)
                        raise APIError(504, "Analysis worker did not accept the request within its deadline.")
                    if sending_errors:
                        raise sending_errors[0]
                    replies, receiving_errors = [], []
                    def receive_reply():
                        try:
                            replies.append(validate_response(
                                receive_message(connection, MAX_RESPONSE_BYTES), request_id))
                        except (EOFError, OSError, ProtocolError) as exc:
                            receiving_errors.append(exc)
                    receiver = threading.Thread(target=receive_reply, daemon=True)
                    receiver.start()
                    # poll() may see only a frame header; recv() can then block
                    # indefinitely. Bound the entire frame read and JSON parse.
                    while receiver.is_alive():
                        receiver.join(timeout=min(0.2, max(0, deadline - monotonic())))
                        if self.stopping.is_set():
                            self._close_locked()
                            receiver.join(timeout=1)
                            raise APIError(503, "Analysis service is stopping.")
                        if monotonic() >= deadline:
                            logger.error(json.dumps({"event": "worker_execution_timeout", "timeout": self.timeout}))
                            self._close_locked()
                            receiver.join(timeout=1)
                            raise APIError(504, "Analysis exceeded its configured deadline. Try a shorter document.")
                    if monotonic() >= deadline:
                        logger.error(json.dumps({"event": "worker_execution_timeout", "timeout": self.timeout}))
                        self._close_locked()
                        raise APIError(504, "Analysis exceeded its configured deadline. Try a shorter document.")
                    if receiving_errors:
                        raise receiving_errors[0]
                    status, result = replies[0]
                    self.ready = status == 200
                    if status != 200:
                        raise APIError(status, result["error"])
                    self.recovery.succeeded()
                    return result
                except (EOFError, OSError, ProtocolError) as exc:
                    exitcode = self.process.exitcode if self.process else None
                    logger.error(json.dumps({"event": "worker_crash", "error_type": type(exc).__name__, "exitcode": exitcode}))
                    self._close_locked()
                    raise APIError(503, "The analysis worker stopped. Please retry.") from None
        except APIError as exc:
            if attempted and exc.status in (503, 504) and not self.stopping.is_set():
                delay = self.recovery.failed()
                self._close_locked()
                exc.retry_after = delay
                logger.warning(json.dumps({"event": "worker_recovery_backoff", "retry_after_seconds": delay,
                                           "consecutive_failures": self.recovery.consecutive_failures}))
            raise
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
        self.metrics = RuntimeMetrics(connection_rejections_observable=True)
        self.slots = threading.BoundedSemaphore(max_connections)
        super().__init__(address, handler)

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            self.metrics.reject_connection()
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
        if self.command != "POST":
            return
        if self.headers.get_all("Transfer-Encoding", []):
            # Framing is untrusted: discard at most one already-arriving raw
            # fragment, never parse chunks or interpret a conflicting length.
            try:
                self.connection.settimeout(0.05)
                self.rfile.read1(8192)
            except OSError:
                pass
            finally:
                self.connection.settimeout(15)
            return
        lengths = self.headers.get_all("Content-Length", [])
        if len(lengths) != 1:
            return
        try:
            length = int(lengths[0])
            if 0 < length <= 8192:
                self.connection.settimeout(0.05)
                # One buffered/kernel read; a slow sender cannot renew a
                # timeout through repeated reads while we reject the request.
                self.rfile.read1(length)
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

    def _send(self, code, body, ctype="application/json; charset=utf-8", *, retry_after=None, extra_headers=None):
        if isinstance(body, dict):
            body = json.dumps(body, allow_nan=False)
        data = body.encode("utf-8") if isinstance(body, str) else body
        try:
            route = urlsplit(getattr(self, "path", "")).path
        except ValueError:
            route = "other"
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Request-Id", self.request_id)
        self.send_header("Connection", "close")
        self.close_connection = True
        for name, value in SECURITY_HEADERS.items():
            self.send_header(name, value)
        if extra_headers:
            for name, value in extra_headers:
                self.send_header(name, value)
        if code == 401:
            self.send_header("WWW-Authenticate", 'Bearer realm="resume-inspection"')
        if retry_after is not None or code in (429, 503):
            self.send_header("Retry-After", str(retry_after if retry_after is not None else 5))
        if hasattr(self.server, "metrics"):
            metrics_started = getattr(self, "metrics_started_at", None)
            self.server.metrics.record(route, getattr(self, "command", None), code,
                monotonic() - metrics_started if metrics_started is not None else None)
        self.end_headers()
        known_routes = {"/", "/analyze", "/health", "/health/live", "/health/ready",
                        "/api/capabilities", "/methodology", "/lab", "/ownership", REVIEW_ROUTE,
                        METRICS_JSON_ROUTE, METRICS_TEXT_ROUTE, "/auth", "/history",
                        "/api/auth/me", "/api/auth/signup", "/api/auth/login", "/api/auth/logout",
                        "/api/history"}
        duration = monotonic() - self.started_at
        logger.info(json.dumps({"event": "http_response", "request_id": self.request_id,
            "method": getattr(self, "command", None) if getattr(self, "command", None) in ("GET", "POST", "DELETE") else "other",
            "route": route if route in known_routes else "other", "status": code,
            "duration_ms": round(duration * 1000, 2)}))
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError, socket.timeout):
            pass

    def _get_session_token(self):
        cookie_header = self.headers.get("Cookie", "")
        for part in cookie_header.split(";"):
            part = part.strip()
            if part.startswith("ats_session="):
                return part[len("ats_session="):]
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:].strip()
        if self.headers.get("X-Session-Token"):
            return self.headers.get("X-Session-Token").strip()
        return None

    def _get_current_user(self):
        token = self._get_session_token()
        if token:
            from src.app.db import get_db
            return get_db().get_user_by_session(token)
        return None

    def do_GET(self):
        path = urlsplit(self.path).path
        if not self._guard(path):
            return
        if path == METRICS_JSON_ROUTE:
            self._send(200, self.server.metrics.snapshot())
        elif path == METRICS_TEXT_ROUTE:
            self._send(200, self.server.metrics.prometheus(), "text/plain; version=0.0.4; charset=utf-8")
        elif path in ("/", "/index.html", "/analyze", "/methodology", "/lab", "/ownership", "/auth", "/history"):
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
            self._send(200, {"ok": True, "model_ready": WORKER.ready, "busy": WORKER.lock.locked(),
                             "worker_recovery": WORKER.recovery_snapshot()})
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
            self._send(200, {**REVIEW_CAPABILITIES, "input_modes": ["text", "pdf"], "max_file_bytes": MAX_FILE_BYTES,
                "max_text_characters": MAX_TEXT_CHARS, "max_pages": MAX_PAGES,
                "deadline_seconds": INFERENCE_TIMEOUT, "concurrent_analyses": 1,
                "lab_enabled": False, "retention": "temporary files deleted after processing",
                "cancellation": "Client cancellation stops waiting; worker finishes or reaches deadline."})
        elif path == "/api/auth/me":
            user = self._get_current_user()
            if user:
                from src.app.db import get_db
                cv_count = get_db().get_user_submission_count(user["id"])
                self._send(200, {
                    "authenticated": True,
                    "user": {"id": user["id"], "username": user["username"], "email": user["email"], "cv_count": cv_count}
                })
            else:
                self._send(200, {"authenticated": False, "user": None})
        elif path == "/api/history":
            user = self._get_current_user()
            if not user:
                self._send(401, {"error": "Please sign in to view your CV history."})
                return
            from src.app.db import get_db
            submissions = get_db().get_user_submissions(user["id"])
            self._send(200, {"submissions": submissions})
        elif path.startswith("/api/history/"):
            sub_id_str = path[len("/api/history/"):].split("/")[0]
            if sub_id_str.isdigit():
                user = self._get_current_user()
                if not user:
                    self._send(401, {"error": "Please sign in to view this submission."})
                    return
                from src.app.db import get_db
                sub = get_db().get_submission_detail(int(sub_id_str), user["id"])
                if not sub:
                    self._send(404, {"error": "Submission not found."})
                    return
                try:
                    sub["result"] = json.loads(sub["result_json"])
                except Exception:
                    sub["result"] = {}
                del sub["result_json"]
                self._send(200, {"submission": sub})
                return
            self._send(404, {"error": "Not found."})
        else:
            self._send(404, {"error": "Not found."})

    def do_POST(self):
        # Begin after headers are parsed, matching the ASGI dispatch boundary.
        self.metrics_started_at = monotonic()
        path = urlsplit(self.path).path
        if not self._guard(path):
            return

        if path == "/api/auth/logout":
            token = self._get_session_token()
            if token:
                from src.app.db import get_db
                get_db().delete_session(token)
            cookie = "ats_session=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"
            self._send(200, {"ok": True}, extra_headers=[("Set-Cookie", cookie)])
            return

        if path in ("/api/auth/signup", "/api/auth/login"):
            try:
                length = json_request_length(self.headers, MAX_BODY_BYTES)
                raw = self.rfile.read(length) if length > 0 else b"{}"
                payload = decode_json_body(raw) if length > 0 else {}
            except Exception:
                self._send(400, {"error": "Invalid JSON payload."})
                return

            from src.app.db import get_db
            db = get_db()

            if path == "/api/auth/signup":
                username = payload.get("username", "")
                email = payload.get("email", "")
                password = payload.get("password", "")
                try:
                    user = db.register_user(username, email, password)
                    token = db.create_session(user["id"])
                    cookie = f"ats_session={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=2592000"
                    self._send(201, {"ok": True, "user": user, "token": token}, extra_headers=[("Set-Cookie", cookie)])
                except ValueError as exc:
                    self._send(400, {"error": str(exc)})
                return

            if path == "/api/auth/login":
                username_or_email = payload.get("username_or_email") or payload.get("username") or payload.get("email", "")
                password = payload.get("password", "")
                try:
                    user = db.authenticate_user(username_or_email, password)
                    token = db.create_session(user["id"])
                    cookie = f"ats_session={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=2592000"
                    self._send(200, {"ok": True, "user": user, "token": token}, extra_headers=[("Set-Cookie", cookie)])
                except ValueError as exc:
                    self._send(401, {"error": str(exc)})
                return

        if path.startswith("/api/history/") and path.endswith("/delete"):
            sub_id_str = path[len("/api/history/"):][:-len("/delete")].split("/")[0]
            if sub_id_str.isdigit():
                user = self._get_current_user()
                if not user:
                    self._send(401, {"error": "Please sign in to delete this submission."})
                    return
                from src.app.db import get_db
                deleted = get_db().delete_submission(int(sub_id_str), user["id"])
                if deleted:
                    self._send(200, {"ok": True})
                else:
                    self._send(404, {"error": "Submission not found."})
                return

        if path not in ("/analyze", REVIEW_ROUTE):
            self._discard_small_body()
            self._send(404, {"error": "Not found. Experimental lab endpoints are disabled."})
            return
        try:
            try:
                length = json_request_length(self.headers, MAX_BODY_BYTES)
            except APIError:
                self._discard_small_body()
                raise
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise APIError(400, "Incomplete request body.")
            try:
                payload = decode_json_body(raw, strict=path == REVIEW_ROUTE)
            except (ValueError, UnicodeDecodeError, RecursionError):
                raise APIError(400, "Invalid JSON payload.") from None
            if path == REVIEW_ROUTE:
                try:
                    validate_review_request(payload)
                except ValueError:
                    raise APIError(422, "Review accepts only text or filename/b64 fields.") from None
            result = WORKER.run(payload)

            user = self._get_current_user()
            saved_id = None
            if user and isinstance(result, dict) and "error" not in result:
                try:
                    from src.app.db import get_db
                    doc_name = "Resume text"
                    mode = "text"
                    snippet = ""
                    if "filename" in payload and payload["filename"]:
                        doc_name = str(payload["filename"])
                        mode = "pdf"
                    elif "text" in payload and payload["text"]:
                        text_val = str(payload["text"])
                        lines = [ln.strip() for ln in text_val.split("\n") if ln.strip()]
                        doc_name = lines[0][:60] if lines else "Resume text"
                        snippet = text_val[:400]

                    decision = result.get("decision", "unknown")
                    score = result.get("combined_score")
                    score_kind = result.get("score_kind", "")
                    findings = result.get("findings", [])
                    findings_count = len(findings) if isinstance(findings, list) else 0

                    saved = get_db().save_submission(
                        user_id=user["id"],
                        document_name=doc_name,
                        mode=mode,
                        snippet=snippet,
                        decision=decision,
                        score=score,
                        score_kind=score_kind,
                        findings_count=findings_count,
                        result_json=json.dumps(result, ensure_ascii=False)
                    )
                    saved_id = saved["id"]
                except Exception as db_exc:
                    logger.warning(f"Could not save submission to database: {db_exc}")

            resp_payload = project_review(result) if path == REVIEW_ROUTE else result
            if saved_id is not None and isinstance(resp_payload, dict):
                resp_payload["saved_submission_id"] = saved_id

            self._send(200, resp_payload)
        except APIError as exc:
            self._send(exc.status, {"error": str(exc)}, retry_after=exc.retry_after)
        except socket.timeout:
            self._send(408, {"error": "Request upload timed out."})
        except Exception:
            self._send(503, {"error": "Analysis is currently unavailable."})

    def do_DELETE(self):
        self.metrics_started_at = monotonic()
        path = urlsplit(self.path).path
        if not self._guard(path):
            return
        if path.startswith("/api/history/"):
            sub_id_str = path[len("/api/history/"):].split("/")[0]
            if sub_id_str.isdigit():
                user = self._get_current_user()
                if not user:
                    self._send(401, {"error": "Please sign in to delete this submission."})
                    return
                from src.app.db import get_db
                deleted = get_db().delete_submission(int(sub_id_str), user["id"])
                if deleted:
                    self._send(200, {"ok": True})
                else:
                    self._send(404, {"error": "Submission not found."})
                return
        self._send(404, {"error": "Not found."})


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    port = int(os.environ.get("PORT", "8000"))
    host = os.environ.get("HOST", "127.0.0.1")
    settings = SecuritySettings.from_env(host)
    if settings.mode == "private" and sys.platform != "linux":
        raise ValueError("Private mode requires a resource-limited Linux container; native demo mode stays local")
    if settings.mode == "private":
        from src.core.artifacts import verify_candidate, verify_policy, require_deployment_approval
        bundle = Path(os.environ.get("ATS_MODELS_DIR", str(MODELS_DIR)))
        manifest = verify_candidate(bundle, os.environ["ATS_CANDIDATE_MANIFEST_SHA256"])
        verify_policy(manifest)
        require_deployment_approval(manifest)
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
