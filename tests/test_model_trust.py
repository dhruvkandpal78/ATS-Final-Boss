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
    from src.core.artifacts import read_candidate_artifact
    def race(directory, name):
        if name == "meta_classifier.pkl":
            return b"substituted bytes"
        return read_candidate_artifact(directory, name)
    monkeypatch.setattr("src.core.artifacts.read_candidate_artifact", race)
    monkeypatch.setattr("src.inference.pickle.loads", lambda data: pytest.fail("Must not deserialize"))
    with pytest.raises(ValueError, match="changed before use"):
        load_pipeline(tmp_path, pin)


@pytest.mark.parametrize("candidate", [True, False])
def test_oversized_weights_never_reach_pickle_in_candidate_or_legacy_mode(tmp_path, monkeypatch, candidate):
    from src.core.artifacts import ARTIFACT_LIMITS
    if candidate:
        bundle(tmp_path)
    else:
        (tmp_path / "meta_classifier.pkl").write_bytes(b"synthetic legacy bytes")
    monkeypatch.setitem(ARTIFACT_LIMITS, "meta_classifier.pkl", 8)
    monkeypatch.setattr("src.inference.pickle.loads", lambda value: pytest.fail("Must not deserialize"))
    with pytest.raises(ValueError, match="size bound"):
        load_pipeline(tmp_path)


@pytest.mark.parametrize("phase", ["verification", "loading"])
def test_growth_after_descriptor_check_fails_before_deserialization(tmp_path, monkeypatch, phase):
    from contextlib import contextmanager
    from io import BytesIO
    import src.core.artifacts as artifacts
    pin = bundle(tmp_path)
    original = artifacts._open_regular
    opens = []
    @contextmanager
    def changed(root, name, limit):
        if name == "meta_classifier.pkl":
            opens.append(name)
            if phase == "verification" or len(opens) == 2:
                content = (root / name).read_bytes()
                yield BytesIO(content + b"growth"), len(content)
                return
        with original(root, name, limit) as value:
            yield value
    monkeypatch.setattr(artifacts, "_open_regular", changed)
    monkeypatch.setattr("src.inference.pickle.loads", lambda value: pytest.fail("Must not deserialize"))
    with pytest.raises(ValueError, match="changed"):
        load_pipeline(tmp_path, pin)


def test_uppercase_artifact_digest_is_consistent_at_verification_and_use(tmp_path, monkeypatch):
    bundle(tmp_path)
    path = tmp_path / "candidate_manifest.json"
    manifest = json.loads(path.read_bytes())
    manifest["artifacts"] = {name:value.upper() for name,value in manifest["artifacts"].items()}
    path.write_text(json.dumps(manifest))
    class ReachedTrustedDeserialization(Exception):
        pass
    def reached(value):
        assert value == b"trusted synthetic bytes"
        raise ReachedTrustedDeserialization()
    monkeypatch.setattr("src.inference.pickle.loads", reached)
    with pytest.raises(ReachedTrustedDeserialization):
        load_pipeline(tmp_path)
