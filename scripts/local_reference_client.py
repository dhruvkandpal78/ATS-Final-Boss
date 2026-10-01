"""Opt-in, loopback-only pinned local reference model for synthetic studies."""
import hashlib
from pathlib import Path
import re
import time

from scripts.run_reference_study import SYSTEM, SCHEMA, digest, validate_output, write_new
from src.app.http_contract import decode_json_body

MODEL = "qwen3:4b-instruct-2507-q4_K_M"
BASE = "http://127.0.0.1:11434"
OPTIONS = {"temperature": 0, "seed": 7391, "num_predict": 128, "num_ctx": 4096, "num_thread": 4}


def verify_store(directory, expected):
    """Read approved operator store only; never download or deserialize weights."""
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise ValueError("A full independent manifest pin is required")
    root = Path(directory).resolve()
    path = root / "manifests/registry.ollama.ai/library/qwen3/4b-instruct-2507-q4_K_M"
    if not path.resolve().is_relative_to(root) or path.stat().st_size > 16384:
        raise ValueError("Invalid bounded local manifest")
    raw = path.read_bytes()
    if digest(raw) != expected:
        raise ValueError("Local model manifest differs from independent pin")
    manifest = decode_json_body(raw, strict=True)
    if manifest.get("schemaVersion") != 2 or not isinstance(manifest.get("layers"), list) or not 1 <= len(manifest["layers"]) <= 16:
        raise ValueError("Invalid local model layer contract")
    descriptors = [manifest["config"], *manifest["layers"]]
    checked = []
    for descriptor in descriptors:
        value, size = descriptor.get("digest"), descriptor.get("size")
        if not isinstance(value, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", value) or type(size) is not int or not 1 <= size <= 4 * 1024**3:
            raise ValueError("Invalid bounded model descriptor")
        blob = root / "blobs" / value.replace(":", "-")
        if not blob.resolve().is_relative_to(root) or blob.stat().st_size != size:
            raise ValueError("Model blob size/path differs from manifest")
        hasher = hashlib.sha256()
        with blob.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                hasher.update(chunk)
        if hasher.hexdigest() != value[7:]:
            raise ValueError("Model blob integrity check failed")
        checked.append({"sha256": value[7:], "bytes": size, "media_type": descriptor.get("mediaType")})
    return {"manifest_sha256": expected, "blobs": checked,
            "limits": "Operator-owned store; not proof of OS isolation or immutable runtime"}


class LocalScreener:
    def __init__(self, output, store, expected, *, max_calls=80):
        import requests
        if type(max_calls) is not int or not 1 <= max_calls <= 96:
            raise ValueError("Invalid call budget")
        self.integrity = verify_store(store, expected)
        self.store, self.expected, self.output = store, expected, output
        self.session = requests.Session()
        self.session.trust_env = False
        self.calls, self.tokens, self.max_calls = 0, 0, max_calls
        self.stop_reason = None
        self.fingerprints = set()
        self.version = self._read("/api/version")["version"]
        if not isinstance(self.version, str) or not re.fullmatch(r"[0-9.]{3,32}", self.version):
            raise ValueError("Unexpected local runtime version")
        self.identity = digest({"model": expected, "version": self.version, "options": OPTIONS, "schema": SCHEMA})
        self._verify_identity()

    def _read(self, endpoint, payload=None):
        # Fixed endpoints only; system proxies, redirects and credentials disabled.
        if endpoint not in ("/api/version", "/api/tags", "/api/chat"):
            raise ValueError("Invalid local endpoint")
        with self.session.request("GET" if payload is None else "POST", BASE + endpoint,
                                  json=payload, timeout=(5, 120), allow_redirects=False, stream=True) as response:
            if response.status_code != 200:
                raise ValueError("Local server rejected request")
            raw = bytearray()
            started = time.monotonic()
            for chunk in response.iter_content(4096):
                raw.extend(chunk)
                if len(raw) > 65536 or time.monotonic() - started > 120:
                    raise ValueError("Local response limit exceeded")
            return decode_json_body(bytes(raw), strict=True)

    def _verify_identity(self):
        if self._read("/api/version").get("version") != self.version:
            raise ValueError("Local runtime version changed")
        matches = [m for m in self._read("/api/tags").get("models", []) if m.get("name") == MODEL]
        if len(matches) != 1 or matches[0].get("digest") != self.expected:
            raise ValueError("Local model tag differs from pin")

    def run(self, text):
        if self.stop_reason or self.calls >= self.max_calls or self.tokens + 10000 > 80000:
            return None, None, "budget_or_provider_stop"
        if not isinstance(text, str) or not 1 <= len(text) <= 5000:
            return None, None, "invalid_bounded_study_input"
        started = time.perf_counter()
        try:
            self._verify_identity()
            self.calls += 1
            data = self._read("/api/chat", {"model": MODEL, "messages": [
                {"role": "system", "content": SYSTEM}, {"role": "user", "content": text}],
                "format": SCHEMA, "stream": False, "options": OPTIONS, "keep_alive": "5m"})
            self._verify_identity()
            if data.get("model") != MODEL or data.get("done") is not True or data.get("done_reason") != "stop":
                raise ValueError("Incomplete or mismatched local output")
            if data["message"].get("tool_calls"):
                raise ValueError("Tools are forbidden in reference study")
            counts = [data.get(key) for key in ("prompt_eval_count", "eval_count")]
            if any(type(value) is not int or not 0 <= value <= 10000 for value in counts) or sum(counts) > 10000:
                raise ValueError("Invalid local usage counts")
            self.tokens += sum(counts)
            content = data["message"]["content"]
            if not isinstance(content, str):
                raise ValueError("Missing structured local output")
            result = validate_output(decode_json_body(content.encode(), strict=True))
            self.fingerprints.add(self.identity)
            write_new(self.output / f"response-{self.calls:03d}.json", {
                "model": MODEL, "model_manifest_sha256": self.expected, "runtime_version": self.version,
                "execution_identity": self.identity, "usage": dict(zip(("prompt_tokens", "output_tokens"), counts)),
                "result": result})
            return result, (time.perf_counter() - started) * 1000, None
        except Exception as error:
            self.stop_reason = "local_identity_or_output_failure"
            return None, (time.perf_counter() - started) * 1000, type(error).__name__

    def final_integrity(self):
        self._verify_identity()
        if verify_store(self.store, self.expected) != self.integrity:
            raise ValueError("Local store changed during study")
