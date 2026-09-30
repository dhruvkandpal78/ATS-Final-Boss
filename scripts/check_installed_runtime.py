"""Smoke the installed wheel from outside the checkout, without model loading."""
import argparse
import json
import os
from pathlib import Path
import socket
import threading
from time import monotonic, sleep
from urllib.request import urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--forbid-root", required=True, type=Path)
    args = parser.parse_args()
    forbidden = args.forbid_root.resolve()
    if Path.cwd().resolve().is_relative_to(forbidden):
        raise RuntimeError("Run the installed-wheel check outside the checkout")
    os.environ["ATS_DEPLOYMENT_MODE"] = "local"
    os.environ["HOST"] = "127.0.0.1"
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

    from importlib.metadata import distribution
    import configs
    import src.app.server as adapter
    from src.app.asgi import create_app
    from src.core.runtime_paths import notice_path
    import uvicorn

    for module in (configs, adapter):
        if Path(module.__file__).resolve().is_relative_to(forbidden):
            raise RuntimeError("Smoke check imported checkout code instead of the installed wheel")
    info = json.loads(distribution("ats-final-boss").read_text("direct_url.json") or "{}")
    if info.get("dir_info", {}).get("editable", False):
        raise RuntimeError("Smoke check requires a regular installed wheel")
    for filename in ("thresholds.json", "model_config.json"):
        record = json.loads((Path(configs.__file__).parent / filename).read_text(encoding="utf-8"))
        if not isinstance(record, dict):
            raise RuntimeError("Installed configuration is invalid")
    for filename in ("LICENSE", "LICENSE-MIT-LEGACY.txt"):
        if not notice_path(filename).read_text(encoding="utf-8").strip():
            raise RuntimeError("Installed public notice is empty")

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    worker = adapter.ModelWorker()
    app = create_app(worker=worker, port=port)
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port,
        log_level="critical", access_log=False, proxy_headers=False))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    try:
        deadline = monotonic() + 10
        while not server.started:
            if not thread.is_alive() or monotonic() >= deadline:
                raise RuntimeError("Installed runtime did not start")
            sleep(0.05)
        for path, content in {"/": b"<!DOCTYPE html", "/assets/app.js": b"",
                "/assets/theme.js": b"", "/assets/style.css": b"",
                "/license": b"NEW ORIGINAL MATERIAL", "/license-legacy": b"MIT License",
                "/health/live": b'"ok":true'}.items():
            with urlopen(f"http://127.0.0.1:{port}{path}", timeout=3) as response:
                body = response.read()
                if response.status != 200 or not body or content.lower() not in body.lower():
                    raise RuntimeError("Installed runtime route failed: " + path)
                if response.headers.get("X-Content-Type-Options") != "nosniff":
                    raise RuntimeError("Installed runtime security headers are missing")
        if worker.process is not None:
            raise RuntimeError("Static smoke check unexpectedly started a model worker")
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()
        if thread.is_alive():
            raise RuntimeError("Installed runtime did not shut down")
    print("PASS: installed wheel UI, assets, notices, configs, headers and lifecycle; no models loaded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
