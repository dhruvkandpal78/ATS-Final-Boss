import pandas as pd
import pytest

from pathlib import Path

from scripts.generate_pdf_smoke import generate
from src.evaluation.train_pdf_candidate import _read_split_manifest, train_candidate, validate_train_validation


def test_manifests_reject_leakage_and_unreviewed_labels(tmp_path):
    generate(tmp_path)
    train = _read_split_manifest(tmp_path / "train.csv")
    validation = _read_split_manifest(tmp_path / "validation.csv")
    validate_train_validation(train, validation)
    validation.loc[0, "source_id"] = train.loc[0, "source_id"]
    with pytest.raises(ValueError, match="overlap"):
        validate_train_validation(train, validation)
    frame = pd.read_csv(tmp_path / "train.csv")
    frame.loc[0, "is_adversarial"] = None
    frame.to_csv(tmp_path / "unreviewed.csv", index=False)
    with pytest.raises(ValueError, match="missing"):
        _read_split_manifest(tmp_path / "unreviewed.csv")


def test_candidate_training_emits_verifiable_v2_data_only_bundle(tmp_path, monkeypatch):
    """Exercise producer, canonical hashes, verifier, and loader on synthetic PDFs only."""
    generate(tmp_path)

    class FakeKeywordDetector:
        threshold = None

        def calibrate(self, validation):
            self.threshold = 0.5
            return self.threshold

        def predict(self, text):
            score = min(0.95, len(text) / 10000)
            return {"status": "success", "anomaly_score": score,
                    "is_flagged": False, "density": score}

    class FakeSemanticScorer:
        model_name = "synthetic-no-download-embedder"
        variance_threshold = None

        def calibrate(self, validation):
            self.variance_threshold = 0.25
            return self.variance_threshold

        def predict(self, text):
            return {"status": "success", "anomaly_score": 0.1,
                    "variance": 0.01, "mean_similarity": 0.9,
                    "injection_cues": 0, "is_flagged": False,
                    "truncated": False}

        def _injection_signal(self, text):
            return 0

    from src.modules.module_b import PDFForensicsDetector

    candidate = train_candidate(
        tmp_path / "train.csv", tmp_path / "validation.csv",
        output_root=tmp_path / "candidates",
        mod_a=FakeKeywordDetector(), mod_b=PDFForensicsDetector(),
        mod_c=FakeSemanticScorer(),
    )

    from src.core.artifacts import FILES_V2, POLICY_FILES, verify_candidate, verify_policy
    manifest = verify_candidate(candidate)
    verify_policy(manifest, root=Path(__file__).resolve().parents[1])

    assert manifest["schema_version"] == "2.0"
    assert set(manifest["artifacts"]) == set(FILES_V2)
    assert set(manifest["policy"]["code_hashes"]) == set(POLICY_FILES)
    assert {
        "src/core/evidence.py", "src/core/linear_artifacts.py"
    }.issubset(POLICY_FILES)
    assert set(path.name for path in candidate.iterdir()) == {
        "candidate_manifest.json", *FILES_V2
    }
    assert not list(candidate.glob("*.pkl"))
    assert 0 < manifest["thresholds"]["module_a"] <= 1
    assert 0 < manifest["thresholds"]["module_c"] <= 1
    assert "development estimates" in " ".join(manifest["limitations"])

    # Load via the production pipeline while replacing only the embedding
    # constructor, so this verifies data-only model loading without downloads.
    from src.modules import module_c

    class RuntimeSemanticScorer:
        def __init__(self, model_name, window_size=2):
            self.model_name = model_name
            self.window_size = window_size
            self.variance_threshold = None

        def predict(self, text):
            return {"status": "success", "anomaly_score": 0.1,
                    "variance": 0.01, "mean_similarity": 0.9,
                    "injection_cues": 0, "is_flagged": False,
                    "truncated": False}

        def _injection_signal(self, text):
            return 0

    monkeypatch.setattr(module_c, "SemanticCoherenceScorer", RuntimeSemanticScorer)
    from src.inference import load_pipeline
    from src.core.analysis_service import AnalysisService

    classifier, scaler, mod_a, mod_b, mod_c = load_pipeline(candidate)
    assert classifier.__class__.__name__ == "BinaryLinearClassifier"
    assert scaler.__class__.__name__ == "FrozenStandardScaler"
    loaded = AnalysisService(mod_a=mod_a, mod_b=mod_b, mod_c=mod_c,
                             meta_clf=classifier, scaler=scaler)
    result = loaded.analyze_pdf(str(tmp_path / "synthetic-10-0.pdf"))
    assert result["status"] == "complete"
    assert isinstance(result["score"], float)
    assert 0 <= result["score"] <= 1
