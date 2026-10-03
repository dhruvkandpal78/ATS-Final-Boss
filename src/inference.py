"""CLI adapter for the canonical analysis service.

Usage: ``python -m src.inference resume.txt --json``. The CLI and HTTP API use
the same service result; neither performs its own scaling or policy overrides.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
from pathlib import Path
import hashlib
import sys

logging.basicConfig(level=logging.ERROR)

# Support both ``python -m src.inference`` and the documented direct script path.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def load_pipeline(models_dir, expected_manifest_sha256=None, *, embedding_dir=None,
                  expected_embedding_manifest_sha256=None):
    """Load a verified data-only V2 candidate; never deserialize Python objects."""
    model_dir = Path(models_dir)
    if not (model_dir / "candidate_manifest.json").is_file():
        if expected_manifest_sha256 is None and not any((model_dir / name).exists() for name in ("meta_classifier.pkl", "scaler.pkl")):
            raise FileNotFoundError("Data-only candidate manifest is missing")
        raise ValueError("A V2 candidate bundle is required; legacy pickle artifacts are unsupported")
    from src.core.artifacts import verify_candidate
    manifest = verify_candidate(model_dir, expected_manifest_sha256)
    if manifest["schema_version"] != "2.0":
        raise ValueError("Runtime requires data-only V2; legacy pickle candidates require offline migration")
    embedding_manifest = None
    if embedding_dir is not None or expected_embedding_manifest_sha256 is not None:
        if embedding_dir is None or expected_embedding_manifest_sha256 is None:
            raise ValueError("A local embedding export and its independent pin are both required")
        from src.core.embedding_artifacts import verify_embedding
        embedding_manifest = verify_embedding(embedding_dir, expected_embedding_manifest_sha256)
    def artifact(name):
        from src.core.artifacts import read_candidate_artifact
        value = read_candidate_artifact(model_dir, name)
        if manifest and hashlib.sha256(value).hexdigest() != manifest["artifacts"][name].lower():
            raise ValueError("Candidate artifact changed before use: " + name)
        return value
    from src.core.linear_artifacts import load_linear_artifacts
    meta_clf, scaler = load_linear_artifacts(artifact("linear_model.json"))
    from src.core.artifacts import _unique_object, _invalid_constant
    thresholds = json.loads(artifact("thresholds.json"), object_pairs_hook=_unique_object,
                            parse_constant=_invalid_constant)
    model_cfg = json.loads(artifact("model_config.json"), object_pairs_hook=_unique_object,
                           parse_constant=_invalid_constant)
    from src.core.artifacts import FEATURE_ORDER
    if (not isinstance(model_cfg, dict) or model_cfg.get("input_mode") != "pdf"
            or model_cfg.get("feature_order") != FEATURE_ORDER
            or model_cfg.get("model_type") != "LogisticRegression"):
        raise ValueError("Incompatible candidate model configuration")
    if not isinstance(thresholds, dict):
        raise ValueError("Candidate thresholds must be an object")
    for key in ("mod_a_threshold", "mod_c_variance_threshold"):
        value = thresholds.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 < value <= 1:
            raise ValueError("Candidate threshold must be finite and in (0, 1]")
    embedding_name = model_cfg.get("embedding_model")
    if not isinstance(embedding_name, str) or not embedding_name.strip():
        raise ValueError("Candidate embedding model identity is required")
    if embedding_manifest and embedding_manifest["model_id"] != embedding_name:
        raise ValueError("Embedding export does not match the candidate model identity")

    from src.modules.module_a import KeywordDensityDetector
    from src.modules.module_b import PDFForensicsDetector
    from src.modules.module_c import SemanticCoherenceScorer

    mod_a = KeywordDensityDetector()
    mod_a.threshold = thresholds["mod_a_threshold"]
    mod_c = SemanticCoherenceScorer(
        model_name=str(Path(embedding_dir).resolve()) if embedding_manifest else embedding_name,
        window_size=2,
    )
    mod_c.variance_threshold = thresholds["mod_c_variance_threshold"]
    mod_b = PDFForensicsDetector()
    return meta_clf, scaler, mod_a, mod_b, mod_c


def analyze_file(file_path: str, service=None):
    """Return the same versioned dictionary the API returns for this input."""
    from src.core.analysis_service import AnalysisService

    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Input file not found: {path}")
    if service is None:
        from src.core.runtime_paths import models_directory
        service = AnalysisService(str(models_directory()))
    if path.suffix.lower() == ".pdf":
        return service.analyze_pdf(str(path))
    if path.suffix.lower() == ".txt":
        return service.analyze_text(path.read_text(encoding="utf-8"))
    raise ValueError("Supported file types are .txt and .pdf")


def run_inference(file_path: str, service=None, json_output: bool = False):
    result = analyze_file(file_path, service=service)
    if json_output:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"Analysis: {Path(file_path).name}")
        print(f"Status: {result['status']}")
        print(f"Decision: {result['decision'].replace('_', ' ')}")
        if result["score"] is None:
            print("Model score: Not available")
        else:
            print(f"Experimental model score: {result['score']:.4f} (uncalibrated)")
        for key, module in result["modules"].items():
            value = "Not available" if module["score"] is None else f"{module['score']:.4f}"
            print(f"Module {key.upper()}: {module['status']} | {value}")
        for limitation in result["coverage"]["limitations"]:
            print(f"Limitation: {limitation}")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Inspect document-manipulation signals in a resume.")
    parser.add_argument("file", help="Path to a .txt or .pdf resume")
    parser.add_argument("--json", action="store_true", help="Emit the versioned JSON result")
    args = parser.parse_args(argv)
    try:
        run_inference(args.file, json_output=args.json)
    except (FileNotFoundError, UnicodeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
