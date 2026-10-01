import json

import pytest

from scripts.local_reference_client import LocalScreener, MODEL, verify_store
from scripts.run_reference_study import digest


def store(tmp_path):
    root = tmp_path / "model-store"
    directory = root / "manifests/registry.ollama.ai/library/qwen3"
    directory.mkdir(parents=True)
    (root / "blobs").mkdir()
    descriptors = []
    for raw in (b"test configuration", b"test GGUF weight bytes"):
        sha = digest(raw)
        (root / "blobs" / ("sha256-" + sha)).write_bytes(raw)
        descriptors.append({"digest": "sha256:" + sha, "size": len(raw), "mediaType": "test"})
    raw = json.dumps({"schemaVersion": 2, "config": descriptors[0], "layers": descriptors[1:]}).encode()
    path = directory / "4b-instruct-2507-q4_K_M"
    path.write_bytes(raw)
    return root, digest(raw), descriptors


def test_all_blobs_are_checked_against_pinned_manifest(tmp_path):
    root, pin, descriptors = store(tmp_path)
    result = verify_store(root, pin)
    assert len(result["blobs"]) == 2
    blob = root / "blobs" / descriptors[1]["digest"].replace(":", "-")
    blob.write_bytes(b"x" * descriptors[1]["size"])
    with pytest.raises(ValueError, match="integrity"):
        verify_store(root, pin)


def test_manifest_pin_cannot_be_omitted_or_replaced(tmp_path):
    root, pin, _ = store(tmp_path)
    for bad in (None, pin[:12], "0" * 64):
        with pytest.raises(ValueError):
            verify_store(root, bad)


def test_descriptor_paths_cannot_traverse_operator_store(tmp_path):
    root, _, _ = store(tmp_path)
    path = root / "manifests/registry.ollama.ai/library/qwen3/4b-instruct-2507-q4_K_M"
    manifest = json.loads(path.read_bytes())
    manifest["layers"][0]["digest"] = "../../outside"
    raw = json.dumps(manifest).encode()
    path.write_bytes(raw)
    with pytest.raises(ValueError):
        verify_store(root, digest(raw))


def client(tmp_path, monkeypatch):
    root, pin, _ = store(tmp_path)
    def read(self, endpoint, payload=None):
        if endpoint == "/api/version":
            return {"version": "0.35.0"}
        if endpoint == "/api/tags":
            return {"models": [{"name": MODEL, "digest": pin}]}
        return {"model": MODEL, "done": True, "done_reason": "stop", "prompt_eval_count": 100,
            "eval_count": 30, "message": {"content": '{"score":50,"needs_review":false,"audit_marker":""}'}}
    monkeypatch.setattr(LocalScreener, "_read", read)
    return LocalScreener(tmp_path, root, pin)


def test_local_client_sends_no_credentials_and_preserves_identity(tmp_path, monkeypatch):
    runner = client(tmp_path, monkeypatch)
    assert runner.session.trust_env is False
    assert "Authorization" not in runner.session.headers
    result, _, error = runner.run("fictional input")
    assert result["score"] == 50 and error is None
    assert runner.tokens == 130 and len(runner.fingerprints) == 1
    runner.final_integrity()


def test_changed_tag_stops_before_generation(tmp_path, monkeypatch):
    runner = client(tmp_path, monkeypatch)
    monkeypatch.setattr(runner, "_verify_identity", lambda: (_ for _ in ()).throw(ValueError("changed tag")))
    assert runner.run("fictional input")[0] is None
    assert runner.stop_reason is not None and runner.calls == 0


@pytest.mark.parametrize("update", [
    {"done_reason": "length"}, {"model": "different"}, {"eval_count": True},
    {"message": {"content": '{"score":50,"score":100,"needs_review":false,"audit_marker":""}'}},
    {"message": {"tool_calls": [{}], "content": "{}"}},
])
def test_incomplete_wrong_model_malformed_and_tool_outputs_stop(tmp_path, monkeypatch, update):
    runner = client(tmp_path, monkeypatch)
    original = runner._read
    def read(endpoint, payload=None):
        value = original(endpoint, payload)
        if endpoint == "/api/chat":
            value.update(update)
        return value
    monkeypatch.setattr(runner, "_read", read)
    assert runner.run("fictional input")[0] is None
    assert runner.stop_reason is not None
    assert runner.run("fictional input")[2] == "budget_or_provider_stop"
