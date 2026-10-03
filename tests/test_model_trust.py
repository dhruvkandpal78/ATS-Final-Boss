import hashlib
import json
from pathlib import Path
import pytest

from src.core.artifacts import FILES_V2, FEATURE_ORDER, verify_candidate
from src.inference import load_pipeline


def bundle(path):
    hashes = {}
    for name in FILES_V2:
        (path / name).write_bytes(b"trusted synthetic bytes")
        hashes[name] = hashlib.sha256(b"trusted synthetic bytes").hexdigest()
    manifest = {"schema_version": "2.0", "kind": "real_pdf_candidate", "input_mode": "pdf",
                "feature_order": FEATURE_ORDER, "artifacts": hashes}
    raw = json.dumps(manifest).encode()
    (path / "candidate_manifest.json").write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def test_independent_manifest_pin_checked_before_deserialization(tmp_path, monkeypatch):
    pin = bundle(tmp_path)
    verify_candidate(tmp_path, pin)
    monkeypatch.setattr("src.core.linear_artifacts.load_linear_artifacts", lambda data: pytest.fail("Must not deserialize"))
    with pytest.raises(ValueError, match="trust pin"):
        load_pipeline(tmp_path, "0" * 64)


def test_pinned_deployment_refuses_legacy_model_directory(tmp_path):
    with pytest.raises(ValueError, match="legacy pickle"):
        load_pipeline(tmp_path, "0" * 64)


def test_changed_model_bytes_after_initial_verification_never_deserialized(tmp_path, monkeypatch):
    pin = bundle(tmp_path)
    from src.core.artifacts import read_candidate_artifact
    def race(directory, name):
        if name == "linear_model.json":
            return b"substituted bytes"
        return read_candidate_artifact(directory, name)
    monkeypatch.setattr("src.core.artifacts.read_candidate_artifact", race)
    monkeypatch.setattr("src.core.linear_artifacts.load_linear_artifacts", lambda data: pytest.fail("Must not deserialize"))
    with pytest.raises(ValueError, match="changed before use"):
        load_pipeline(tmp_path, pin)


@pytest.mark.parametrize("candidate", [True, False])
def test_oversized_weights_never_reach_pickle_in_candidate_or_legacy_mode(tmp_path, monkeypatch, candidate):
    from src.core.artifacts import ARTIFACT_LIMITS
    if candidate:
        bundle(tmp_path)
    else:
        (tmp_path / "meta_classifier.pkl").write_bytes(b"synthetic legacy bytes")
    monkeypatch.setitem(ARTIFACT_LIMITS, "linear_model.json", 8)
    monkeypatch.setattr("src.core.linear_artifacts.load_linear_artifacts", lambda value: pytest.fail("Must not deserialize"))
    with pytest.raises(ValueError, match="size bound|legacy pickle"):
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
        if name == "linear_model.json":
            opens.append(name)
            if phase == "verification" or len(opens) == 2:
                content = (root / name).read_bytes()
                yield BytesIO(content + b"growth"), len(content)
                return
        with original(root, name, limit) as value:
            yield value
    monkeypatch.setattr(artifacts, "_open_regular", changed)
    monkeypatch.setattr("src.core.linear_artifacts.load_linear_artifacts", lambda value: pytest.fail("Must not deserialize"))
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
    monkeypatch.setattr("src.core.linear_artifacts.load_linear_artifacts", reached)
    with pytest.raises(ReachedTrustedDeserialization):
        load_pipeline(tmp_path)


def test_v1_integrity_can_be_inspected_but_runtime_refuses(tmp_path):
    from src.core.artifacts import FILES
    hashes = {}
    for name in FILES:
        (tmp_path / name).write_bytes(b"not executable")
        hashes[name] = hashlib.sha256(b"not executable").hexdigest()
    manifest = {"schema_version":"1.0", "kind":"real_pdf_candidate", "input_mode":"pdf",
                "feature_order":FEATURE_ORDER, "artifacts":hashes}
    (tmp_path / "candidate_manifest.json").write_text(json.dumps(manifest))
    verify_candidate(tmp_path)
    with pytest.raises(ValueError, match="data-only V2"):
        load_pipeline(tmp_path)


def valid_bundle(path):
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from src.core.linear_artifacts import save_linear_artifacts
    features = np.array([[0,0,0],[0.1,0,0.1],[0.8,0.8,0.8],[1,1,1]])
    scaler = StandardScaler().fit(features)
    model = LogisticRegression().fit(scaler.transform(features), [0,0,1,1])
    save_linear_artifacts(model, scaler, path / "linear_model.json")
    (path / "thresholds.json").write_text(json.dumps({"mod_a_threshold":0.1,"mod_c_variance_threshold":0.02}))
    (path / "model_config.json").write_text(json.dumps({"embedding_model":"fixture-model",
        "input_mode":"pdf","feature_order":FEATURE_ORDER,"model_type":"LogisticRegression"}))
    manifest = {"schema_version":"2.0","kind":"real_pdf_candidate","input_mode":"pdf",
        "feature_order":FEATURE_ORDER,"artifacts":{name:hashlib.sha256((path/name).read_bytes()).hexdigest() for name in FILES_V2}}
    raw=json.dumps(manifest).encode()
    (path / "candidate_manifest.json").write_bytes(raw)
    return hashlib.sha256(raw).hexdigest(), model, scaler, features


def test_v2_pipeline_load_preserves_scores_and_configured_thresholds(tmp_path, monkeypatch):
    import numpy as np
    pin, model, scaler, features = valid_bundle(tmp_path)
    class SemanticFixture:
        def __init__(self, model_name, window_size):
            assert model_name == "fixture-model" and window_size == 2
    monkeypatch.setattr("src.modules.module_c.SemanticCoherenceScorer", SemanticFixture)
    frozen, scaling, a, b, c = load_pipeline(tmp_path, pin)
    np.testing.assert_allclose(frozen.predict_proba(scaling.transform(features)),
        model.predict_proba(scaler.transform(features)), rtol=0, atol=1e-12)
    assert a.threshold == 0.1 and c.variance_threshold == 0.02


@pytest.mark.parametrize("threshold", [0, -1, True, 2, None])
def test_v2_bad_calibration_fails_before_embedding_initialization(tmp_path, monkeypatch, threshold):
    valid_bundle(tmp_path)
    path=tmp_path / "thresholds.json"
    path.write_text(json.dumps({"mod_a_threshold":threshold,"mod_c_variance_threshold":0.02}))
    manifest_path=tmp_path / "candidate_manifest.json"
    manifest=json.loads(manifest_path.read_bytes())
    manifest["artifacts"]["thresholds.json"]=hashlib.sha256(path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest))
    monkeypatch.setattr("src.modules.module_c.SemanticCoherenceScorer",
                        lambda **kwargs: pytest.fail("Must fail before embedding initialization"))
    with pytest.raises(ValueError, match="threshold"):
        load_pipeline(tmp_path)
