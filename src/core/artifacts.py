"""Verify candidate bundle integrity before deserializing trusted local weights."""
import hashlib
import json
from pathlib import Path

FEATURE_ORDER = ["Module_A_Score", "Module_B_Score", "Module_C_Score"]
FILES = ("meta_classifier.pkl", "scaler.pkl", "thresholds.json", "model_config.json")
POLICY_FILES = ("src/core/review_policy.py", "src/core/analysis_service.py",
                "src/modules/module_a.py", "src/modules/module_b.py", "src/modules/module_c.py")


def verify_policy(manifest, root=None):
    from src.core.review_policy import POLICY_VERSION
    root = Path(root) if root is not None else Path(__file__).resolve().parents[2]
    policy = manifest.get("policy", {})
    hashes = policy.get("code_hashes", {})
    if policy.get("version") != POLICY_VERSION or set(hashes) != set(POLICY_FILES):
        raise ValueError("Final evaluation requires a candidate frozen with the current policy")
    for name in POLICY_FILES:
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != hashes[name]:
            raise ValueError("Policy code changed after candidate freeze: " + name)


def verify_candidate(directory, expected_manifest_sha256=None):
    directory = Path(directory)
    raw_manifest = (directory / "candidate_manifest.json").read_bytes()
    if expected_manifest_sha256 is not None:
        import hmac
        actual_manifest = hashlib.sha256(raw_manifest).hexdigest()
        if not hmac.compare_digest(actual_manifest, expected_manifest_sha256.lower()):
            raise ValueError("Candidate manifest does not match the independent trust pin")
    manifest = json.loads(raw_manifest)
    if (manifest.get("schema_version") != "1.0" or manifest.get("kind") != "real_pdf_candidate"
            or manifest.get("input_mode") != "pdf" or manifest.get("feature_order") != FEATURE_ORDER):
        raise ValueError("Incompatible candidate feature contract")
    for name in FILES:
        expected = manifest.get("artifacts", {}).get(name)
        actual = hashlib.sha256((directory / name).read_bytes()).hexdigest()
        if expected != actual:
            raise ValueError("Candidate artifact integrity mismatch: " + name)
    return manifest
