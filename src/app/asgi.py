"""Bounded ASGI adapter for the maintained UI and analysis worker.

Launch with ``python -m src.app.asgi``. One server process owns one model worker.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from email.message import Message
import json
import logging
import mimetypes
import os
from pathlib import Path
import sys
from time import monotonic
from uuid import uuid4

from starlette.applications import Starlette
from starlette.requests import ClientDisconnect, Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
from starlette.concurrency import run_in_threadpool

from src.app.security import RequestBudget, SecuritySettings
from src.app.http_contract import SECURITY_HEADERS, decode_json_body, json_request_length
from src.core.runtime_paths import models_directory, notice_path
from src.app.startup import WARMUP_TEXT, require_warmup_result, warmup_pdf_payload
from src.app.server import (
    APIError, INDEX_PATH, INFERENCE_TIMEOUT, MAX_BODY_BYTES, MAX_FILE_BYTES,
    MAX_PAGES, MAX_TEXT_CHARS, MODELS_DIR, ROOT, ModelWorker, validate_payload,
)


logger = logging.getLogger(__name__)
ASSET_SUFFIXES = {".css", ".js", ".svg", ".woff2", ".png", ".webp"}
KNOWN_ROUTES = {
    "/", "/index.html", "/analyze", "/methodology", "/lab", "/ownership",
    "/license", "/license-legacy", "/health", "/health/live", "/health/ready",
    "/api/capabilities",
}


def _headers(scope_headers: list[tuple[bytes, bytes]]) -> Message:
    """Keep repeated raw ASGI fields visible to SecuritySettings.authorize."""
    message = Message()
    for name, value in scope_headers:
        message[name.decode("latin-1")] = value.decode("latin-1")
    return message


def _worker_ready(worker: object) -> bool:
    process = getattr(worker, "process", None)
    stopping = getattr(worker, "stopping", None)
    return bool(not (stopping is not None and stopping.is_set()) and
                getattr(worker, "ready", False) and process is not None and process.is_alive())


def _response(status: int, body: dict | str | bytes, media_type: str = "application/json") -> Response:
    if isinstance(body, dict):
        return JSONResponse(body, status_code=status)
    return Response(body, status_code=status, media_type=media_type)


async def _read_payload(request: Request, headers: Message) -> object:
    length = json_request_length(headers, MAX_BODY_BYTES)
    body = bytearray()
    try:
        async with asyncio.timeout(15):
            async for chunk in request.stream():
                if len(body) + len(chunk) > length or len(body) + len(chunk) > MAX_BODY_BYTES:
                    raise APIError(413, "Request exceeds the 7 MiB encoded-body limit.")
                body.extend(chunk)
    except TimeoutError:
        raise APIError(408, "Request upload timed out.") from None
    except ClientDisconnect:
        raise APIError(400, "Incomplete request body.") from None
    if len(body) != length:
        raise APIError(400, "Incomplete request body.")
    try:
        return await run_in_threadpool(decode_json_body, body)
    except (ValueError, UnicodeDecodeError, RecursionError):
        raise APIError(400, "Invalid JSON payload.") from None


def create_app(*, settings: SecuritySettings | None = None, worker: ModelWorker | None = None,
               port: int = 8000, private_startup_check=None) -> Starlette:
    """Create one application with injectable policy/worker for synthetic tests."""
    settings = settings or SecuritySettings.from_env(os.environ.get("HOST", "127.0.0.1"))
    worker = worker or ModelWorker()
    budget = RequestBudget(settings.requests_per_minute)

    @asynccontextmanager
    async def lifespan(app: Starlette):
        try:
            if settings.mode == "private":
                try:
                    if sys.platform != "linux":
                        raise RuntimeError("Private mode requires a resource-limited Linux container")
                    if private_startup_check is None:
                        from src.core.artifacts import verify_candidate, verify_policy
                        models = models_directory()
                        pin = os.environ["ATS_CANDIDATE_MANIFEST_SHA256"]
                        await run_in_threadpool(lambda: verify_policy(verify_candidate(models, pin)))
                    else:
                        await run_in_threadpool(private_startup_check)
                    text_result = await run_in_threadpool(worker.run, {"text": WARMUP_TEXT})
                    require_warmup_result(text_result)
                    pdf_payload = await run_in_threadpool(warmup_pdf_payload)
                    pdf_result = await run_in_threadpool(worker.run, pdf_payload)
                    require_warmup_result(pdf_result, pdf=True)
                    if not _worker_ready(worker):
                        raise RuntimeError("Private analysis worker did not become ready")
                except Exception:
                    raise RuntimeError("Private startup verification failed") from None
            yield
        finally:
            await run_in_threadpool(getattr(worker, "shutdown", worker.close))

    async def dispatch(request: Request) -> Response:
        started = monotonic()
        request_id = str(uuid4())
        path = request.scope["path"]
        method = request.method
        route = path if path in KNOWN_ROUTES else "/assets/*" if path.startswith("/assets/") else "other"
        try:
            headers = _headers(request.scope["headers"])
            rejected = settings.authorize(headers, method, port, path)
            if rejected:
                response = _response(rejected[0], {"error": rejected[1]})
            elif method == "POST":
                if not budget.consume():
                    response = _response(429, {"error": "Request budget exceeded. Retry later."})
                elif path != "/analyze":
                    response = _response(404, {"error": "Not found. Experimental lab endpoints are disabled."})
                else:
                    payload = await _read_payload(request, headers)
                    validate_payload(payload)
                    response = _response(200, await run_in_threadpool(worker.run, payload))
            elif method == "GET":
                if path in {"/", "/index.html", "/analyze", "/methodology", "/lab", "/ownership"}:
                    try:
                        html = await run_in_threadpool(INDEX_PATH.read_text, encoding="utf-8")
                        response = _response(200, html, "text/html; charset=utf-8")
                    except FileNotFoundError:
                        response = _response(404, {"error": "Frontend is unavailable."})
                elif path in {"/license", "/license-legacy"}:
                    try:
                        notice = notice_path("LICENSE" if path == "/license" else "LICENSE-MIT-LEGACY.txt")
                        response = _response(200, await run_in_threadpool(notice.read_text, encoding="utf-8"),
                                             "text/plain; charset=utf-8")
                    except FileNotFoundError:
                        response = _response(404, {"error": "Public notice is unavailable."})
                elif path == "/health/live":
                    response = _response(200, {"ok": True})
                elif path == "/health":
                    response = _response(200, {"ok": True, "model_ready": worker.ready,
                                               "busy": worker.lock.locked(),
                                               "worker_recovery": getattr(worker, "recovery_snapshot", lambda: {})()})
                elif path == "/health/ready":
                    ready = _worker_ready(worker)
                    response = _response(200 if ready else 503, {"ready": ready})
                elif path == "/api/capabilities":
                    response = _response(200, {
                        "input_modes": ["text", "pdf"], "max_file_bytes": MAX_FILE_BYTES,
                        "max_text_characters": MAX_TEXT_CHARS, "max_pages": MAX_PAGES,
                        "deadline_seconds": INFERENCE_TIMEOUT, "concurrent_analyses": 1,
                        "lab_enabled": False, "retention": "temporary files deleted after processing",
                        "cancellation": "Client cancellation stops waiting; worker finishes or reaches deadline.",
                    })
                elif path.startswith("/assets/"):
                    root = (ROOT / "src" / "app" / "assets").resolve()
                    target = (root / path[len("/assets/"):]).resolve()
                    if root not in target.parents or target.suffix not in ASSET_SUFFIXES or not target.is_file():
                        response = _response(404, {"error": "Asset not found."})
                    else:
                        data = await run_in_threadpool(target.read_bytes)
                        response = _response(200, data,
                                             mimetypes.guess_type(str(target))[0] or "application/octet-stream")
                else:
                    response = _response(404, {"error": "Not found."})
            else:
                response = _response(405, {"error": "Method not allowed."})
        except APIError as exc:
            response = _response(exc.status, {"error": str(exc)})
            if exc.retry_after is not None:
                response.headers["Retry-After"] = str(exc.retry_after)
        except Exception:
            response = _response(503, {"error": "Analysis is currently unavailable."})

        response.headers.update(SECURITY_HEADERS)
        response.headers["X-Request-Id"] = request_id
        response.headers["Connection"] = "close"
        if response.status_code == 401:
            response.headers["WWW-Authenticate"] = 'Bearer realm="resume-inspection"'
        if response.status_code in (429, 503) and "Retry-After" not in response.headers:
            response.headers["Retry-After"] = "5"
        logger.info(json.dumps({
            "event": "http_response", "request_id": request_id,
            "method": method if method in {"GET", "POST"} else "other",
            "route": route, "status": response.status_code,
            "duration_ms": round((monotonic() - started) * 1000, 2),
        }))
        return response

    class AllMethodsEndpoint:
        async def __call__(self, scope, receive, send):
            response = await dispatch(Request(scope, receive))
            await response(scope, receive, send)

    app = Starlette(routes=[Route("/{path:path}", AllMethodsEndpoint())], lifespan=lifespan)
    return app


app = create_app()


def main() -> None:
    import uvicorn

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    settings = SecuritySettings.from_env(host)
    if settings.mode == "private" and sys.platform != "linux":
        raise RuntimeError("Private mode requires a resource-limited Linux container")
    uvicorn.run(create_app(settings=settings, port=port), host=host, port=port,
                workers=1, limit_concurrency=16, backlog=16,
                timeout_graceful_shutdown=30, timeout_keep_alive=5,
                h11_max_incomplete_event_size=16384,
                access_log=False, proxy_headers=False)


if __name__ == "__main__":
    main()
