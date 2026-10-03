"""Train an isolated, auditable real-PDF candidate without reading a test set.

Input CSVs require ``source_id,pdf_path,is_adversarial``. Labels must be
independently supplied by the corpus owner; this tool never infers ground truth
from detector findings. Candidate validation is a development measurement,
not an independent benchmark or a calibrated probability claim.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
import math
from pathlib import Path
from typing import Union
from uuid import uuid4

import fitz
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from sklearn.preprocessing import StandardScaler

from src.core.analysis_service import AnalysisService, FEATURE_ORDER, MAX_PDF_PAGES, MAX_TEXT_CHARS, POLICY_VERSION


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_ROOT = ROOT / "results" / "candidates"
REQUIRED_COLUMNS = ("source_id", "pdf_path", "is_adversarial")
MAX_PDF_BYTES = 5 * 1024 * 1024


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_hash(value: str) -> str:
    return hashlib.sha256(value.strip().casefold().encode("utf-8")).hexdigest()


def _read_split_manifest(csv_path: Path) -> pd.DataFrame:
    csv_path = csv_path.resolve(strict=True)
    if any(word in csv_path.name.casefold() for word in ("test", "holdout")):
        raise ValueError("Development training refuses a test/holdout-named manifest")
    frame = pd.read_csv(csv_path, dtype={"source_id": "string", "pdf_path": "string"})
    missing = set(REQUIRED_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"PDF manifest is missing columns: {', '.join(sorted(missing))}")
    if frame.empty:
        raise ValueError("PDF manifest contains no rows")
    if frame[list(REQUIRED_COLUMNS)].isna().any().any():
        raise ValueError("PDF manifest has missing source IDs, paths, or labels")
    labels = pd.to_numeric(frame["is_adversarial"], errors="coerce")
    if labels.isna().any() or not labels.isin([0, 1]).all():
        raise ValueError("PDF labels must be explicitly supplied as 0 or 1")
    frame = frame.copy()
    frame["is_adversarial"] = labels.astype(int)
    frame["source_id"] = frame["source_id"].str.strip().str.casefold()
    if (frame["source_id"] == "").any():
        raise ValueError("Source IDs must be nonempty")
    frame["pdf_path"] = frame["pdf_path"].map(
        lambda value: (csv_path.parent / str(value)).resolve()
    )
    if not frame["pdf_path"].map(lambda path: path.is_file() and path.suffix.casefold() == ".pdf").all():
        raise ValueError("Every PDF manifest path must resolve to an existing .pdf file")
    if frame["pdf_path"].map(lambda path: path.stat().st_size > MAX_PDF_BYTES).any():
        raise ValueError("PDF manifest contains a file above the deployed 5 MB limit")
    if frame["pdf_path"].duplicated().any():
        raise ValueError("PDF manifest contains duplicate file paths")
    frame.attrs["manifest_path"] = csv_path
    return frame


def validate_train_validation(train: pd.DataFrame, validation: pd.DataFrame) -> None:
    """Reject source and byte-identical PDF leakage across development splits."""
    train_sources = set(train["source_id"])
    val_sources = set(validation["source_id"])
    if train_sources & val_sources:
        raise ValueError("Train and validation source_id groups overlap")
    train_hashes = {sha256_file(path) for path in train["pdf_path"]}
    val_hashes = {sha256_file(path) for path in validation["pdf_path"]}
    if train_hashes & val_hashes:
        raise ValueError("Train and validation contain byte-identical PDFs")
    if set(train["is_adversarial"]) != {0, 1}:
        raise ValueError("Training requires known benign and adversarial examples")
    if set(validation["is_adversarial"]) != {0, 1}:
        raise ValueError("Validation requires known benign and adversarial examples")
    if (validation["is_adversarial"] == 0).sum() < 2:
        raise ValueError("Validation needs at least two benign PDFs for percentile calibration")


def _calibration_text(path: Path) -> str:
    """Extract bounded text with the same PyMuPDF page/text limits as deployment."""
    with fitz.open(path) as doc:
        if doc.needs_pass or not 0 < len(doc) <= MAX_PDF_PAGES:
            raise ValueError("Calibration PDF is encrypted, empty, or above the page limit")
        parts = [page.get_text() for page in doc]
    if any(not part.strip() for part in parts):
        raise ValueError("Calibration PDF has a page without extractable text")
    text = "\n".join(parts)
    if not text.strip() or len(text) > MAX_TEXT_CHARS:
        raise ValueError("Calibration PDF has no text or exceeds the text limit")
    return text


def _complete_features(service: AnalysisService, path: Path) -> tuple[dict, dict]:
    result = service.analyze_pdf(str(path))
    modules = result["modules"]
    if any(modules[key]["status"] != "ok" for key in ("a", "b", "c")):
        raise ValueError("PDF feature extraction is incomplete; candidate training stopped")
    if modules["b"].get("coverage_status") != "complete" or result["module_c"].get("truncated"):
        raise ValueError("PDF structural or semantic coverage is partial; candidate training stopped")
    coverage = result["coverage"]
    if coverage["pages_total"] != coverage["pages_analyzed"] or any(
        "no extractable text" in item.lower() or "stopped at" in item.lower()
        for item in coverage["limitations"]
    ):
        raise ValueError("PDF text coverage is incomplete; candidate training stopped")
    features = result["features"]
    if any(features[key] is None or not math.isfinite(float(features[key])) for key in FEATURE_ORDER):
        raise ValueError("PDF feature vector contains missing or nonfinite values")
    return {key: float(features[key]) for key in FEATURE_ORDER}, result


def _features_for_frame(frame: pd.DataFrame, service: AnalysisService) -> pd.DataFrame:
    vectors = [_complete_features(service, path)[0] for path in frame["pdf_path"]]
    return pd.DataFrame(vectors, columns=FEATURE_ORDER)


def _package_versions() -> dict:
    versions = {}
    for package in ("numpy", "pandas", "scikit-learn", "PyMuPDF", "sentence-transformers"):
        try:
            versions[package] = version(package)
        except PackageNotFoundError:
            versions[package] = None
    return versions


def train_candidate(train_csv: Union[str, Path], validation_csv: Union[str, Path],
                    output_root: Union[str, Path] = DEFAULT_OUTPUT_ROOT,
                    mod_a=None, mod_b=None, mod_c=None) -> Path:
    output_root = Path(output_root).resolve()
    deployed = (ROOT / "results" / "models").resolve()
    if output_root == deployed or deployed in output_root.parents:
        raise ValueError("Candidate output cannot be inside deployed results/models")
    train = _read_split_manifest(Path(train_csv))
    validation = _read_split_manifest(Path(validation_csv))
    if train.attrs["manifest_path"] == validation.attrs["manifest_path"]:
        raise ValueError("Train and validation manifests must be separate files")
    validate_train_validation(train, validation)

    if mod_a is None or mod_b is None or mod_c is None:
        from src.modules.module_a import KeywordDensityDetector
        from src.modules.module_b import PDFForensicsDetector
        from src.modules.module_c import SemanticCoherenceScorer
        mod_a = mod_a or KeywordDensityDetector()
        mod_b = mod_b or PDFForensicsDetector()
        mod_c = mod_c or SemanticCoherenceScorer(model_name="all-MiniLM-L6-v2", window_size=2)

    validation_texts = [_calibration_text(path) for path in validation["pdf_path"]]
    calibration = pd.DataFrame({"text": validation_texts,
                                "is_adversarial": validation["is_adversarial"].to_numpy()})
    # Modules enforce clean-validation P95 and reject non-positive thresholds.
    a_threshold = float(mod_a.calibrate(calibration))
    c_threshold = float(mod_c.calibrate(calibration))
    if not all(math.isfinite(value) and 0 < value <= 1 for value in (a_threshold, c_threshold)):
        raise ValueError("Validation calibration did not produce finite thresholds in (0, 1]")

    feature_service = AnalysisService(mod_a=mod_a, mod_b=mod_b, mod_c=mod_c)
    train_x = _features_for_frame(train, feature_service)
    val_x = _features_for_frame(validation, feature_service)
    train_y = train["is_adversarial"].to_numpy(dtype=int)
    val_y = validation["is_adversarial"].to_numpy(dtype=int)
    scaler = StandardScaler().fit(train_x)
    estimator = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)
    estimator.fit(scaler.transform(train_x), train_y)

    # Re-evaluate validation PDFs through the same deployed service and policy.
    validation_service = AnalysisService(mod_a=mod_a, mod_b=mod_b, mod_c=mod_c,
                                         meta_clf=estimator, scaler=scaler)
    results = [validation_service.analyze_pdf(str(path)) for path in validation["pdf_path"]]
    if any(result["status"] != "complete" or result["score"] is None for result in results):
        raise ValueError("Validation inference is incomplete; candidate artifacts were not written")
    model_pred = np.array([int(result["model_decision"]) for result in results])
    policy_pred = np.array([int(result["decision"] == "review_recommended") for result in results])
    model_scores = np.array([result["score"] for result in results], dtype=float)
    metrics = {
        "split": "validation", "n": int(len(validation)),
        "model_precision": float(precision_score(val_y, model_pred, zero_division=0)),
        "model_recall": float(recall_score(val_y, model_pred, zero_division=0)),
        "model_f1": float(f1_score(val_y, model_pred, zero_division=0)),
        "model_roc_auc": float(roc_auc_score(val_y, model_scores)),
        "policy_precision": float(precision_score(val_y, policy_pred, zero_division=0)),
        "policy_recall": float(recall_score(val_y, policy_pred, zero_division=0)),
        "policy_f1": float(f1_score(val_y, policy_pred, zero_division=0)),
    }

    output_root.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    candidate = output_root / f"pdf-{run_id}"
    candidate.mkdir(exist_ok=False)
    from src.core.linear_artifacts import save_linear_artifacts
    from src.core.artifacts import FILES_V2, POLICY_FILES
    save_linear_artifacts(estimator, scaler, candidate / "linear_model.json")
    (candidate / "thresholds.json").write_text(json.dumps({
        "mod_a_threshold": a_threshold,
        "mod_c_variance_threshold": c_threshold,
        "calibration": "clean_validation_p95",
    }, indent=2), encoding="utf-8")
    (candidate / "model_config.json").write_text(json.dumps({
        "embedding_model": mod_c.model_name,
        "input_mode": "pdf",
        "feature_order": list(FEATURE_ORDER),
        "model_type": "LogisticRegression",
    }, indent=2), encoding="utf-8")
    artifact_names = FILES_V2
    manifest = {
        "schema_version": "2.0", "kind": "real_pdf_candidate", "input_mode": "pdf",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "feature_order": list(FEATURE_ORDER),
        "model": {"type": "LogisticRegression", "calibrated": False},
        "policy": {"version": POLICY_VERSION, "code_hashes": {
            name: sha256_file(ROOT / name) for name in POLICY_FILES}},
        "sources": {
            "train_manifest_sha256": sha256_file(train.attrs["manifest_path"]),
            "validation_manifest_sha256": sha256_file(validation.attrs["manifest_path"]),
            "train_source_hashes": sorted(source_hash(value) for value in set(train["source_id"])),
            "validation_source_hashes": sorted(source_hash(value) for value in set(validation["source_id"])),
            "train_pdf_hashes": sorted(sha256_file(path) for path in train["pdf_path"]),
            "validation_pdf_hashes": sorted(sha256_file(path) for path in validation["pdf_path"]),
        },
        "artifacts": {name: sha256_file(candidate / name) for name in artifact_names},
        "thresholds": {"module_a": a_threshold, "module_c": c_threshold,
                       "method": "clean_validation_p95"},
        "validation_metrics": metrics,
        "dependency_versions": _package_versions(),
        "limitations": [
            "Validation metrics are development estimates, not independent test performance.",
            "Scores are uncalibrated; real-world performance requires independently labeled PDFs.",
            "Source labels were supplied by the corpus owner and were not inferred by this tool.",
        ],
    }
    (candidate / "candidate_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    return candidate


def main(argv=None):
    parser = argparse.ArgumentParser(description="Train an isolated real-PDF candidate without reading test data.")
    parser.add_argument("--train-manifest", required=True)
    parser.add_argument("--validation-manifest", required=True)
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    args = parser.parse_args(argv)
    candidate = train_candidate(args.train_manifest, args.validation_manifest, args.output_root)
    print(candidate)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
