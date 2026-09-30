"""Tiny synthetic export trees exercise byte integrity without loading a model."""

import hashlib
import json

import pytest

from src.core import embedding_artifacts as artifacts
from scripts.freeze_embedding import main as freeze_main


REVISION = "a" * 40
MODEL_ID = "synthetic/test-encoder"


def _export(tmp_path):
    (tmp_path / "config.json").write_text("{}", encoding="utf-8")
    (tmp_path / "modules.json").write_text("[]", encoding="utf-8")
    (tmp_path / "model.safetensors").write_bytes(b"synthetic bytes, not real weights")
    pooling = tmp_path / "1_Pooling"
    pooling.mkdir()
    (pooling / "config.json").write_text('{"pooling": true}', encoding="utf-8")
    return tmp_path


def test_freeze_and_verify_exact_export(tmp_path):
    directory = _export(tmp_path)
    pin = artifacts.freeze_embedding(directory, MODEL_ID, REVISION)
    manifest = artifacts.verify_embedding(directory, pin, MODEL_ID)
    assert manifest["schema_version"] == "1.0"
    assert manifest["upstream_revision"] == REVISION
    assert set(manifest["files"]) == {
        "config.json", "modules.json", "model.safetensors", "1_Pooling/config.json",
    }
    with pytest.raises(ValueError, match="already exists"):
        artifacts.freeze_embedding(directory, MODEL_ID, REVISION)


@pytest.mark.parametrize("mutation,match", [
    ("corrupt", "integrity mismatch"),
    ("added", "file set"),
    ("missing", "requires config.json"),
])
def test_changed_file_tree_rejected(tmp_path, mutation, match):
    directory = _export(tmp_path)
    pin = artifacts.freeze_embedding(directory, MODEL_ID, REVISION)
    if mutation == "corrupt":
        (directory / "model.safetensors").write_bytes(b"changed")
    elif mutation == "added":
        (directory / "extra.json").write_text("{}")
    else:
        (directory / "config.json").unlink()
    with pytest.raises(ValueError, match=match):
        artifacts.verify_embedding(directory, pin, MODEL_ID)


def test_pin_mismatch_precedes_content_scan(tmp_path, monkeypatch):
    directory = _export(tmp_path)
    artifacts.freeze_embedding(directory, MODEL_ID, REVISION)
    monkeypatch.setattr(artifacts, "_scan", lambda directory: pytest.fail("content tree scanned"))
    with pytest.raises(ValueError, match="independent trust pin"):
        artifacts.verify_embedding(directory, "0" * 64)


def test_expected_model_identity_and_revision_enforced(tmp_path):
    directory = _export(tmp_path)
    with pytest.raises(ValueError, match="40-digit"):
        artifacts.freeze_embedding(directory, MODEL_ID, "branch-name")
    pin = artifacts.freeze_embedding(directory, MODEL_ID, REVISION)
    with pytest.raises(ValueError, match="model ID"):
        artifacts.verify_embedding(directory, pin, "different/model")
    manifest_path = directory / artifacts.MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text())
    manifest["upstream_revision"] = "branch-name"
    raw = json.dumps(manifest).encode()
    manifest_path.write_bytes(raw)
    with pytest.raises(ValueError, match="40-digit"):
        artifacts.verify_embedding(directory, hashlib.sha256(raw).hexdigest())


@pytest.mark.parametrize("path", ["../other.json", "/tmp/other.json", "C:/other.json",
                                  "1_Pooling/../config.json", "1_Pooling\\config.json"])
def test_manifest_traversal_and_nonportable_paths_rejected(tmp_path, path):
    directory = _export(tmp_path)
    artifacts.freeze_embedding(directory, MODEL_ID, REVISION)
    manifest_path = directory / artifacts.MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text())
    manifest["files"][path] = "0" * 64
    raw = json.dumps(manifest).encode()
    manifest_path.write_bytes(raw)
    with pytest.raises(ValueError, match="path"):
        artifacts.verify_embedding(directory, hashlib.sha256(raw).hexdigest())


def test_symlinks_and_custom_code_rejected(tmp_path):
    directory = _export(tmp_path)
    link = directory / "linked.json"
    try:
        link.symlink_to(directory / "config.json")
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable on this host")
    with pytest.raises(ValueError, match="symlink"):
        artifacts.freeze_embedding(directory, MODEL_ID, REVISION)
    link.unlink()
    (directory / "modeling.py").write_text("raise RuntimeError('never run')")
    with pytest.raises(ValueError, match="prohibited"):
        artifacts.freeze_embedding(directory, MODEL_ID, REVISION)


def test_file_and_manifest_bounds(tmp_path, monkeypatch):
    directory = _export(tmp_path)
    monkeypatch.setattr(artifacts, "MAX_FILE_BYTES", 8)
    with pytest.raises(ValueError, match="size bound"):
        artifacts.freeze_embedding(directory, MODEL_ID, REVISION)
    monkeypatch.setattr(artifacts, "MAX_FILE_BYTES", 1024)
    monkeypatch.setattr(artifacts, "MAX_MANIFEST_BYTES", 10)
    with pytest.raises(ValueError, match="manifest exceeds"):
        artifacts.freeze_embedding(directory, MODEL_ID, REVISION)


def test_custom_model_code_is_rejected_without_requiring_symlinks(tmp_path):
    directory = _export(tmp_path)
    (directory / "modeling.py").write_text("raise RuntimeError('never executed')")
    with pytest.raises(ValueError, match="prohibited"):
        artifacts.freeze_embedding(directory, MODEL_ID, REVISION)


def test_freeze_cli_outputs_pin_without_loading_model(tmp_path, capsys):
    directory = _export(tmp_path)
    assert freeze_main([str(directory), "--model-id", MODEL_ID,
                        "--upstream-revision", REVISION]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["manifest_sha256"] == hashlib.sha256(
        (directory / artifacts.MANIFEST_NAME).read_bytes()).hexdigest()
