"""Explicit offline migration of an operator-trusted V1 pickle candidate.

Pickle can execute code while loading. Run this only for a candidate whose
manifest SHA-256 was independently approved. The migrated V2 bundle carries
lineage and current policy hashes, but no validation result or deployment
approval from the legacy bundle.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import hmac
import json
import math
from pathlib import Path
import pickle
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.artifacts import (FILES_V2, POLICY_FILES, SHA256_RE,
                                read_candidate_artifact, verify_candidate)
from src.core.linear_artifacts import FEATURE_ORDER, export_linear_artifacts
from src.core.review_policy import POLICY_VERSION


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _strict_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Legacy configuration contains duplicate JSON fields")
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValueError("Legacy configuration contains nonfinite JSON")


def _json_object(raw: bytes, name: str) -> dict:
    try:
        value = json.loads(raw, object_pairs_hook=_strict_pairs, parse_constant=_invalid_constant)
    except (UnicodeError, ValueError, RecursionError):
        raise ValueError(f"Legacy {name} is not strict JSON") from None
    if not isinstance(value, dict):
        raise ValueError(f"Legacy {name} must be a JSON object")
    return value


def _positive(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Legacy {name} must be a positive number")
    number = float(value)
    if not math.isfinite(number) or number <= 0 or number > 1:
        raise ValueError(f"Legacy {name} must be positive and bounded")
    return number


def _sources(manifest: dict) -> dict:
    source = manifest.get("sources")
    required = {"train_manifest_sha256", "validation_manifest_sha256",
                "train_source_hashes", "validation_source_hashes",
                "train_pdf_hashes", "validation_pdf_hashes"}
    if not isinstance(source, dict) or set(source) != required:
        raise ValueError("Legacy source provenance is missing or malformed")
    normalized = {}
    for key in required:
        value = source[key]
        if key.endswith("_hashes"):
            if not isinstance(value, list) or len(value) > 100_000 or not all(
                isinstance(item, str) and SHA256_RE.fullmatch(item) for item in value
            ):
                raise ValueError("Legacy source hash list is invalid: " + key)
            normalized[key] = list(value)
        else:
            if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
                raise ValueError("Legacy source manifest hash is invalid: " + key)
            normalized[key] = value
    if set(normalized["train_source_hashes"]) & set(normalized["validation_source_hashes"]):
        raise ValueError("Legacy source groups overlap")
    if set(normalized["train_pdf_hashes"]) & set(normalized["validation_pdf_hashes"]):
        raise ValueError("Legacy PDF hashes overlap")
    return normalized


def migrate_legacy_candidate(legacy_dir: str | Path, output_dir: str | Path,
                             manifest_sha256: str, *, trust_legacy_pickle: bool = False) -> Path:
    """Verify pinned V1 bytes before deserialize; create a new nonapproved V2."""
    if trust_legacy_pickle is not True:
        raise ValueError("Explicit --trust-legacy-pickle acknowledgment is required")
    if not isinstance(manifest_sha256, str) or not SHA256_RE.fullmatch(manifest_sha256):
        raise ValueError("An independent 64-digit --manifest-sha256 pin is required")
    legacy_dir = Path(legacy_dir)
    output_dir = Path(output_dir)
    if output_dir.exists() or output_dir.is_symlink():
        raise FileExistsError("Migration output already exists; choose a new directory")
    source_root = legacy_dir.resolve(strict=True)
    target = output_dir.resolve()
    if source_root == target or source_root in target.parents:
        raise ValueError("Migration output cannot be inside the legacy candidate")
    deployed = (ROOT / "results" / "models").resolve()
    if target == deployed or deployed in target.parents:
        raise ValueError("Migration output cannot overwrite deployed model artifacts")

    manifest = verify_candidate(legacy_dir, expected_manifest_sha256=manifest_sha256)
    if manifest["schema_version"] != "1.0":
        raise ValueError("Only a V1 pickle candidate can be migrated")
    sources = _sources(manifest)
    # Re-check the exact bytes that will be deserialized after manifest
    # verification. A replacement between verification and read fails closed.
    legacy_bytes = {}
    for name in ("meta_classifier.pkl", "scaler.pkl", "thresholds.json", "model_config.json"):
        raw = read_candidate_artifact(legacy_dir, name)
        if not hmac.compare_digest(_digest(raw), manifest["artifacts"][name].lower()):
            raise ValueError("Legacy artifact changed before migration: " + name)
        legacy_bytes[name] = raw
    threshold_cfg = _json_object(legacy_bytes["thresholds.json"], "thresholds")
    a_threshold = _positive(threshold_cfg.get("mod_a_threshold"), "Module A threshold")
    c_threshold = _positive(threshold_cfg.get("mod_c_variance_threshold"), "Module C threshold")
    model_cfg = _json_object(legacy_bytes["model_config.json"], "model config")
    embedding_model = model_cfg.get("embedding_model")
    if not isinstance(embedding_model, str) or not embedding_model.strip() or len(embedding_model) > 256:
        raise ValueError("Legacy embedding model identity is missing or unbounded")
    if (model_cfg.get("input_mode") != "pdf" or
            model_cfg.get("feature_order") != list(FEATURE_ORDER) or
            model_cfg.get("model_type") != "LogisticRegression"):
        raise ValueError("Legacy model config does not match the PDF feature contract")

    # This is the only code path that deserializes legacy weights. Operator
    # acknowledgment and an independently pinned manifest are mandatory.
    estimator = pickle.loads(legacy_bytes["meta_classifier.pkl"])
    scaler = pickle.loads(legacy_bytes["scaler.pkl"])
    linear_payload = export_linear_artifacts(estimator, scaler)
    linear_raw = (json.dumps(linear_payload, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    thresholds_raw = (json.dumps({
        "mod_a_threshold": a_threshold,
        "mod_c_variance_threshold": c_threshold,
        "calibration": "legacy_unverified",
    }, sort_keys=True, indent=2) + "\n").encode("utf-8")
    config_raw = (json.dumps({
        "embedding_model": embedding_model,
        "input_mode": "pdf",
        "feature_order": list(FEATURE_ORDER),
        "model_type": "LogisticRegression",
    }, sort_keys=True, indent=2) + "\n").encode("utf-8")
    files = {"linear_model.json": linear_raw,
             "thresholds.json": thresholds_raw,
             "model_config.json": config_raw}
    manifest_v2 = {
        "schema_version": "2.0", "kind": "real_pdf_candidate", "input_mode": "pdf",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "feature_order": list(FEATURE_ORDER),
        "model": {"type": "LogisticRegression", "calibrated": False},
        "policy": {"version": POLICY_VERSION, "code_hashes": {
            name: _digest((ROOT / name).read_bytes()) for name in POLICY_FILES}},
        "sources": sources,
        "artifacts": {name: _digest(files[name]) for name in FILES_V2},
        "thresholds": {"module_a": a_threshold, "module_c": c_threshold,
                       "method": "legacy_unverified"},
        "deployment_approved": False,
        "lineage": {"migration": "operator_trusted_v1_pickle_to_data_only_v2",
                    "legacy_manifest_sha256": manifest_sha256.lower(),
                    "validation_claims_carried_forward": False,
                    "legacy_policy_approval_carried_forward": False},
        "limitations": [
            "Legacy validation metrics and policy approval were not carried forward.",
            "Threshold provenance must be independently re-established before deployment.",
            "Migration verifies byte integrity, not the safety or scientific validity of pickle contents.",
        ],
    }
    manifest_raw = (json.dumps(manifest_v2, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
    if len(manifest_raw) > 256 * 1024:
        raise ValueError("Migrated manifest exceeds its size bound")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(exist_ok=False)
    for name, raw in files.items():
        with (output_dir / name).open("xb") as handle:
            handle.write(raw)
    with (output_dir / "candidate_manifest.json").open("xb") as handle:
        handle.write(manifest_raw)
    return output_dir


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Explicit offline V1 pickle to data-only V2 candidate migration")
    parser.add_argument("--legacy-candidate", required=True, help="Pinned local V1 candidate directory")
    parser.add_argument("--output-dir", required=True, help="New directory; existing paths are refused")
    parser.add_argument("--manifest-sha256", required=True, help="Independently approved V1 manifest SHA-256")
    parser.add_argument("--trust-legacy-pickle", action="store_true", help="Acknowledge trusted local pickle execution")
    args = parser.parse_args(argv)
    result = migrate_legacy_candidate(args.legacy_candidate, args.output_dir,
                                      args.manifest_sha256, trust_legacy_pickle=args.trust_legacy_pickle)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
