"""CLI adapter for the canonical analysis service.

Usage: ``python -m src.inference resume.txt --json``. The CLI and HTTP API use
the same service result; neither performs its own scaling or policy overrides.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import pickle
import hashlib
import sys

logging.basicConfig(level=logging.ERROR)

# Support both ``python -m src.inference`` and the documented direct script path.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def load_pipeline(models_dir, expected_manifest_sha256=None):
    """Load trusted local legacy artifacts and configured detectors.

    The caller chooses the artifact directory. Uploaded pickle files must never
    be passed here. Missing artifacts raise a normal exception for adapters to
    report without terminating a process during import or a request.
    """
    model_dir = Path(models_dir)
    candidate = (model_dir / "candidate_manifest.json").is_file()
    if expected_manifest_sha256 is not None and not candidate:
        raise ValueError("Pinned deployment requires a candidate bundle; legacy pickle artifacts are unsupported")
    manifest = None
    if candidate:
        from src.core.artifacts import verify_candidate
        manifest = verify_candidate(model_dir, expected_manifest_sha256)
    def artifact(name):
        value = (model_dir / name).read_bytes()
        if manifest and hashlib.sha256(value).hexdigest() != manifest["artifacts"][name]:
            raise ValueError("Candidate artifact changed before use: " + name)
        return value
    # Deserialize the exact verified bytes, avoiding a reopen race after hashing.
    # Pickle remains code execution: only operator-approved immutable bundles.
    meta_clf = pickle.loads(artifact("meta_classifier.pkl"))
    scaler = pickle.loads(artifact("scaler.pkl"))

    config_dir = model_dir if candidate else Path(__file__).resolve().parents[1] / "configs"
    thresholds = json.loads(artifact("thresholds.json") if candidate else
                            (config_dir / "thresholds.json").read_bytes())
    model_cfg = json.loads(artifact("model_config.json") if candidate else
                           (config_dir / "model_config.json").read_bytes())

    from src.modules.module_a import KeywordDensityDetector
    from src.modules.module_b import PDFForensicsDetector
    from src.modules.module_c import SemanticCoherenceScorer

    mod_a = KeywordDensityDetector()
    mod_a.threshold = thresholds["mod_a_threshold"]
    mod_c = SemanticCoherenceScorer(
        model_name=model_cfg.get("embedding_model", "all-MiniLM-L6-v2"),
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
        service = AnalysisService(str(Path(__file__).resolve().parents[1] / "results" / "models"))
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
