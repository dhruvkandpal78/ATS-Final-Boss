import hashlib
import json
from pathlib import Path
import pytest

from src.core.artifacts import FILES, FEATURE_ORDER, verify_candidate
from src.inference import load_pipeline


def bundle(path):
    hashes = {}
    for name in FILES:
        (path / name).write_bytes(b"trusted synthetic bytes")
        hashes[name] = hashlib.sha256(b"trusted synthetic bytes").hexdigest()
    manifest = {"schema_version": "1.0", "kind": "real_pdf_candidate", "input_mode": "pdf",
                "feature_order": FEATURE_ORDER, "artifacts": hashes}
    raw = json.dumps(manifest).encode()
    (path / "candidate_manifest.json").write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def test_independent_manifest_pin_checked_before_deserialization(tmp_path, monkeypatch):
    pin = bundle(tmp_path)
    verify_candidate(tmp_path, pin)
    monkeypatch.setattr("src.inference.pickle.loads", lambda data: pytest.fail("Must not deserialize"))
    with pytest.raises(ValueError, match="trust pin"):
        load_pipeline(tmp_path, "0" * 64)


def test_pinned_deployment_refuses_legacy_model_directory(tmp_path):
    with pytest.raises(ValueError, match="legacy pickle"):
        load_pipeline(tmp_path, "0" * 64)


def test_changed_model_bytes_after_initial_verification_never_deserialized(tmp_path, monkeypatch):
    pin = bundle(tmp_path)
    original = Path.read_bytes
    reads = [0]
    def race(path):
        if path.name == "meta_classifier.pkl":
            reads[0] += 1
            if reads[0] > 1:
                return b"substituted bytes"
        return original(path)
    monkeypatch.setattr(Path, "read_bytes", race)
    monkeypatch.setattr("src.inference.pickle.loads", lambda data: pytest.fail("Must not deserialize"))
    with pytest.raises(ValueError, match="changed before use"):
        load_pipeline(tmp_path, pin)
