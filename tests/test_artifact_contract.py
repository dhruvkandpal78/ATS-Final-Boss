import hashlib
import json

import pytest

from src.core.artifacts import FILES, FEATURE_ORDER, verify_candidate


@pytest.fixture
def candidate(tmp_path):
    hashes = {}
    for name in FILES:
        (tmp_path / name).write_bytes(b"synthetic bytes")
        hashes[name] = hashlib.sha256(b"synthetic bytes").hexdigest()
    manifest = {"schema_version": "1.0", "kind": "real_pdf_candidate", "input_mode": "pdf",
                "feature_order": FEATURE_ORDER, "artifacts": hashes}
    (tmp_path / "candidate_manifest.json").write_text(json.dumps(manifest))
    return tmp_path, manifest


@pytest.mark.parametrize("pin", [True, 1, "", "0" * 63, "x" * 64])
def test_malformed_independent_pin_is_rejected(candidate, pin):
    with pytest.raises(ValueError, match="trust pin"):
        verify_candidate(candidate[0], pin)


@pytest.mark.parametrize("raw", ['[]', '{"kind":"a","kind":"b"}', '{"value":NaN}'])
def test_ambiguous_or_non_object_manifest_rejected(candidate, raw):
    root, _ = candidate
    (root / "candidate_manifest.json").write_text(raw)
    with pytest.raises(ValueError):
        verify_candidate(root)


def test_manifest_bound_is_checked_before_read(candidate, monkeypatch):
    import src.core.artifacts as artifacts
    monkeypatch.setattr(artifacts, "MAX_MANIFEST_BYTES", 8)
    with pytest.raises(ValueError, match="size bound"):
        verify_candidate(candidate[0])


def test_artifact_hashing_does_not_use_whole_file_read_bytes(candidate, monkeypatch):
    from pathlib import Path
    monkeypatch.setattr(Path, "read_bytes", lambda self: pytest.fail("Whole-file read is forbidden"))
    assert verify_candidate(candidate[0]) == candidate[1]


def test_hashing_and_loading_enforce_artifact_bounds(candidate, monkeypatch):
    from src.core.artifacts import ARTIFACT_LIMITS, read_candidate_artifact
    root, _ = candidate
    monkeypatch.setitem(ARTIFACT_LIMITS, "meta_classifier.pkl", 8)
    for operation in (lambda: verify_candidate(root), lambda: read_candidate_artifact(root, "meta_classifier.pkl")):
        with pytest.raises(ValueError, match="size bound"):
            operation()


def test_unknown_and_special_artifact_names_rejected(candidate):
    from src.core.artifacts import read_candidate_artifact
    with pytest.raises(ValueError, match="Unknown"):
        read_candidate_artifact(candidate[0], "../outside.pkl")
    path = candidate[0] / "meta_classifier.pkl"
    path.unlink()
    path.mkdir()
    with pytest.raises(ValueError, match="non-regular"):
        verify_candidate(candidate[0])


@pytest.mark.parametrize("target", ["candidate_manifest.json", "meta_classifier.pkl"])
def test_linked_candidate_entry_is_rejected(candidate, tmp_path, target):
    root, _ = candidate
    source = root / target
    copied = root / (target + ".original")
    source.rename(copied)
    try:
        source.symlink_to(copied)
    except OSError:
        pytest.skip("Host does not permit symlink creation")
    with pytest.raises(ValueError, match="linked"):
        verify_candidate(root)


def test_linked_candidate_root_is_rejected(candidate, tmp_path):
    link = tmp_path / "linked-root"
    try:
        link.symlink_to(candidate[0], target_is_directory=True)
    except OSError:
        pytest.skip("Host does not permit directory symlinks")
    with pytest.raises(ValueError, match="non-linked"):
        verify_candidate(link)


def test_artifact_contract_requires_exact_named_hashes(candidate):
    root, manifest = candidate
    manifest["artifacts"]["extra.pkl"] = "0" * 64
    (root / "candidate_manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="invalid contract"):
        verify_candidate(root)


def test_candidate_rejects_tampering_before_loading_weights(tmp_path):
    hashes = {}
    for name in FILES:
        (tmp_path / name).write_bytes(b"synthetic bytes")
        hashes[name] = hashlib.sha256(b"synthetic bytes").hexdigest()
    manifest = {"schema_version": "1.0", "kind": "real_pdf_candidate", "input_mode": "pdf",
                "feature_order": FEATURE_ORDER, "artifacts": hashes}
    (tmp_path / "candidate_manifest.json").write_text(json.dumps(manifest))
    assert verify_candidate(tmp_path) == manifest
    (tmp_path / "thresholds.json").write_text("{}")
    with pytest.raises(ValueError, match="integrity"):
        verify_candidate(tmp_path)
