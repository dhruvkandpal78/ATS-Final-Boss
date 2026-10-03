"""Synthetic engineering fixtures for the explicit offline V1 migration."""

import hashlib
import json
import pickle

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from scripts import migrate_linear_candidate as migration
from src.core.artifacts import verify_candidate, verify_policy
from src.core.linear_artifacts import FEATURE_ORDER, load_linear_artifacts
from src.core.review_policy import POLICY_VERSION


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def legacy_fixture(tmp_path):
    legacy = tmp_path / "legacy-v1"
    legacy.mkdir()
    features = pd.DataFrame([
        [0.1, 0.0, 0.2], [0.2, 0.1, 0.0], [0.0, 0.3, 0.2],
        [0.8, 0.7, 0.9], [0.9, 0.8, 0.7], [0.7, 0.9, 0.8],
    ], columns=FEATURE_ORDER)
    scaler = StandardScaler().fit(features)
    model = LogisticRegression(random_state=42).fit(
        scaler.transform(features), [0, 0, 0, 1, 1, 1]
    )
    files = {
        "meta_classifier.pkl": pickle.dumps(model),
        "scaler.pkl": pickle.dumps(scaler),
        "thresholds.json": json.dumps({"mod_a_threshold": 0.08,
                                       "mod_c_variance_threshold": 0.02,
                                       "calibration": "old_unverified_claim"}).encode(),
        "model_config.json": json.dumps({"embedding_model": "all-MiniLM-L6-v2",
                                         "input_mode": "pdf",
                                         "feature_order": list(FEATURE_ORDER),
                                         "model_type": "LogisticRegression"}).encode(),
    }
    for name, raw in files.items():
        (legacy / name).write_bytes(raw)
    sources = {
        "train_manifest_sha256": digest(b"synthetic-train-manifest"),
        "validation_manifest_sha256": digest(b"synthetic-validation-manifest"),
        "train_source_hashes": [digest(b"source-train")],
        "validation_source_hashes": [digest(b"source-validation")],
        "train_pdf_hashes": [digest(b"pdf-train")],
        "validation_pdf_hashes": [digest(b"pdf-validation")],
    }
    manifest = {
        "schema_version": "1.0", "kind": "real_pdf_candidate", "input_mode": "pdf",
        "feature_order": list(FEATURE_ORDER),
        "artifacts": {name: digest(raw) for name, raw in files.items()},
        "sources": sources,
        "policy": {"version": "old-approval", "code_hashes": {"obsolete": digest(b"old")}},
        "deployment_approved": True,
        "validation_metrics": {"model_f1": 1.0},
    }
    manifest_raw = json.dumps(manifest, sort_keys=True).encode()
    (legacy / "candidate_manifest.json").write_bytes(manifest_raw)
    return legacy, digest(manifest_raw), sources, features, model, scaler


def test_migration_requires_acknowledgment_and_independent_pin(tmp_path, monkeypatch):
    legacy, pin, *_ = legacy_fixture(tmp_path)
    output = tmp_path / "new-v2"
    def forbidden(_):
        raise AssertionError("pickle was reached before trust and pin validation")
    monkeypatch.setattr(migration.pickle, "loads", forbidden)
    with pytest.raises(ValueError, match="trust-legacy-pickle"):
        migration.migrate_legacy_candidate(legacy, output, pin)
    with pytest.raises(ValueError, match="manifest-sha256"):
        migration.migrate_legacy_candidate(legacy, output, "bad", trust_legacy_pickle=True)
    with pytest.raises(ValueError, match="trust pin"):
        migration.migrate_legacy_candidate(legacy, output, digest(b"wrong"), trust_legacy_pickle=True)
    assert not output.exists()


def test_migration_never_overwrites_existing_output(tmp_path, monkeypatch):
    legacy, pin, *_ = legacy_fixture(tmp_path)
    output = tmp_path / "existing-v2"
    output.mkdir()
    sentinel = output / "keep.txt"
    sentinel.write_text("leave me untouched", encoding="utf-8")
    monkeypatch.setattr(migration.pickle, "loads", lambda _: pytest.fail("pickle should not be read"))
    with pytest.raises(FileExistsError):
        migration.migrate_legacy_candidate(legacy, output, pin, trust_legacy_pickle=True)
    assert sentinel.read_text(encoding="utf-8") == "leave me untouched"


def test_migration_preserves_inference_and_sources_without_legacy_claims(tmp_path):
    legacy, pin, sources, features, model, scaler = legacy_fixture(tmp_path)
    output = tmp_path / "fresh-v2"
    assert migration.migrate_legacy_candidate(legacy, output, pin, trust_legacy_pickle=True) == output
    manifest = verify_candidate(output)
    verify_policy(manifest, root=migration.ROOT)
    assert manifest["schema_version"] == "2.0"
    assert manifest["sources"] == sources
    assert manifest["policy"]["version"] == POLICY_VERSION
    assert manifest["deployment_approved"] is False
    assert manifest["lineage"]["legacy_manifest_sha256"] == pin
    assert manifest["lineage"]["validation_claims_carried_forward"] is False
    assert manifest["lineage"]["legacy_policy_approval_carried_forward"] is False
    assert "validation_metrics" not in manifest
    assert manifest["thresholds"]["method"] == "legacy_unverified"
    assert json.loads((output / "thresholds.json").read_text())["calibration"] == "legacy_unverified"
    assert not (output / "meta_classifier.pkl").exists()
    assert not (output / "scaler.pkl").exists()
    loaded_model, loaded_scaler = load_linear_artifacts((output / "linear_model.json").read_bytes())
    np.testing.assert_allclose(loaded_scaler.transform(features), scaler.transform(features), atol=1e-12)
    np.testing.assert_allclose(loaded_model.predict_proba(loaded_scaler.transform(features)),
                               model.predict_proba(scaler.transform(features)), atol=1e-12)
    np.testing.assert_array_equal(loaded_model.predict(loaded_scaler.transform(features)),
                                  model.predict(scaler.transform(features)))


def test_migration_rechecks_exact_bytes_before_pickle(tmp_path, monkeypatch):
    legacy, pin, *_ = legacy_fixture(tmp_path)
    original = migration.read_candidate_artifact
    def changed(directory, name):
        raw = original(directory, name)
        return raw + b"changed" if name == "meta_classifier.pkl" else raw
    monkeypatch.setattr(migration, "read_candidate_artifact", changed)
    monkeypatch.setattr(migration.pickle, "loads", lambda _: pytest.fail("pickle should not load changed bytes"))
    output = tmp_path / "new-v2"
    with pytest.raises(ValueError, match="changed before migration"):
        migration.migrate_legacy_candidate(legacy, output, pin, trust_legacy_pickle=True)
    assert not output.exists()


def test_migration_rejects_unsupported_sklearn_export(tmp_path):
    legacy, _, *_ = legacy_fixture(tmp_path)
    replacement = pickle.dumps({"not": "a logistic model"})
    (legacy / "meta_classifier.pkl").write_bytes(replacement)
    manifest = json.loads((legacy / "candidate_manifest.json").read_text())
    manifest["artifacts"]["meta_classifier.pkl"] = digest(replacement)
    raw = json.dumps(manifest, sort_keys=True).encode()
    (legacy / "candidate_manifest.json").write_bytes(raw)
    output = tmp_path / "new-v2"
    with pytest.raises(ValueError, match="Only fitted sklearn"):
        migration.migrate_legacy_candidate(legacy, output, digest(raw), trust_legacy_pickle=True)
    assert not output.exists()


@pytest.mark.parametrize("name, updates, expected", [
    ("thresholds.json", {"mod_a_threshold": 1.1}, "positive and bounded"),
    ("model_config.json", {"model_type": "RandomForestClassifier"}, "PDF feature contract"),
])
def test_migration_refuses_unloadable_v2_contract_before_pickle(
    tmp_path, monkeypatch, name, updates, expected
):
    legacy, _, *_ = legacy_fixture(tmp_path)
    config = json.loads((legacy / name).read_text(encoding="utf-8"))
    config.update(updates)
    changed = json.dumps(config).encode()
    (legacy / name).write_bytes(changed)
    manifest_path = legacy / "candidate_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifacts"][name] = digest(changed)
    manifest_raw = json.dumps(manifest, sort_keys=True).encode()
    manifest_path.write_bytes(manifest_raw)
    monkeypatch.setattr(migration.pickle, "loads", lambda _: pytest.fail("pickle must not load"))
    output = tmp_path / "new-v2"
    with pytest.raises(ValueError, match=expected):
        migration.migrate_legacy_candidate(
            legacy, output, digest(manifest_raw), trust_legacy_pickle=True
        )
    assert not output.exists()
