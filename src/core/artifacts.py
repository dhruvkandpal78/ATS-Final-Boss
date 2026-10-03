"""Verify bounded candidate bundle integrity before loading model parameters."""
import hashlib
import json
import hmac
import os
import re
import stat
from contextlib import contextmanager
from pathlib import Path

FEATURE_ORDER = ["Module_A_Score", "Module_B_Score", "Module_C_Score"]
FILES = ("meta_classifier.pkl", "scaler.pkl", "thresholds.json", "model_config.json")
FILES_V2 = ("linear_model.json", "thresholds.json", "model_config.json")
POLICY_FILES = ("src/core/review_policy.py", "src/core/analysis_service.py", "src/core/evidence.py",
                "src/modules/module_a.py", "src/modules/module_b.py", "src/modules/module_c.py",
                "src/core/linear_artifacts.py", "src/modules/cue_recovery.py")
MAX_MANIFEST_BYTES = 256 * 1024
ARTIFACT_LIMITS = {name: 64 * 1024 * 1024 if name.endswith(".pkl") else 1024 * 1024 for name in FILES}
ARTIFACT_LIMITS["linear_model.json"] = 16 * 1024
SHA256_RE = re.compile(r"[0-9a-fA-F]{64}\Z")


def _linked(info):
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def _root(directory):
    directory = Path(directory)
    info = directory.lstat()
    if _linked(info) or not stat.S_ISDIR(info.st_mode):
        raise ValueError("Candidate directory must be a non-linked directory")
    return directory.resolve()


@contextmanager
def _open_regular(root, name, limit):
    path = root / name
    info = path.lstat()
    if _linked(info) or not stat.S_ISREG(info.st_mode) or info.st_size > limit:
        raise ValueError("Candidate file is linked, non-regular or exceeds its size bound: " + name)
    if not path.resolve().is_relative_to(root):
        raise ValueError("Candidate file escapes its directory")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    with os.fdopen(os.open(path, flags), "rb") as handle:
        opened = os.fstat(handle.fileno())
        if _linked(opened) or not stat.S_ISREG(opened.st_mode) or opened.st_size > limit:
            raise ValueError("Candidate file is not a bounded regular file: " + name)
        yield handle, opened.st_size


def _read_bounded(root, name, limit):
    with _open_regular(root, name, limit) as (handle, size):
        content = handle.read(size + 1)
        if len(content) > limit or len(content) != size:
            raise ValueError("Candidate file changed or exceeded its size bound: " + name)
        return content


def read_candidate_artifact(directory, name):
    """Bound the exact bytes later hashed and parsed by the loader.

    Runtime uses data-only V2. V1 bytes are allowed for explicit offline
    migration/integrity inspection only. Unapproved and linked names are refused.
    """
    if name not in ARTIFACT_LIMITS:
        raise ValueError("Unknown candidate artifact name")
    return _read_bounded(_root(directory), name, ARTIFACT_LIMITS[name])


def _hash_artifact(root, name):
    limit = ARTIFACT_LIMITS[name]
    with _open_regular(root, name, limit) as (handle, size):
        digest, seen = hashlib.sha256(), 0
        while chunk := handle.read(min(1024 * 1024, limit - seen + 1)):
            seen += len(chunk)
            if seen > limit:
                raise ValueError("Candidate file exceeded its size bound during hashing: " + name)
            digest.update(chunk)
        if seen != size:
            raise ValueError("Candidate file changed during hashing: " + name)
        return digest.hexdigest()


def _unique_object(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError("Candidate manifest contains duplicate JSON fields")
        result[name] = value
    return result


def _invalid_constant(value):
    raise ValueError("Candidate manifest contains non-finite JSON numbers")


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
    if expected_manifest_sha256 is not None and (
            not isinstance(expected_manifest_sha256, str) or not SHA256_RE.fullmatch(expected_manifest_sha256)):
        raise ValueError("Candidate trust pin must be a 64-digit SHA-256 digest")
    directory = _root(directory)
    raw_manifest = _read_bounded(directory, "candidate_manifest.json", MAX_MANIFEST_BYTES)
    if expected_manifest_sha256 is not None:
        actual_manifest = hashlib.sha256(raw_manifest).hexdigest()
        if not hmac.compare_digest(actual_manifest, expected_manifest_sha256.lower()):
            raise ValueError("Candidate manifest does not match the independent trust pin")
    try:
        manifest = json.loads(raw_manifest, object_pairs_hook=_unique_object, parse_constant=_invalid_constant)
    except (UnicodeError, ValueError, RecursionError):
        raise ValueError("Candidate manifest must be unambiguous valid bounded JSON") from None
    if (not isinstance(manifest, dict) or manifest.get("schema_version") not in ("1.0", "2.0") or manifest.get("kind") != "real_pdf_candidate"
            or manifest.get("input_mode") != "pdf" or manifest.get("feature_order") != FEATURE_ORDER):
        raise ValueError("Incompatible candidate feature contract")
    files = candidate_files(manifest)
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != set(files) or any(
            not isinstance(value, str) or not SHA256_RE.fullmatch(value) for value in artifacts.values()):
        raise ValueError("Candidate artifact hashes have an invalid contract")
    for name in files:
        actual = _hash_artifact(directory, name)
        if not hmac.compare_digest(artifacts[name].lower(), actual):
            raise ValueError("Candidate artifact integrity mismatch: " + name)
    return manifest


def candidate_files(manifest):
    """V1 supports integrity inspection only; serving requires data-only V2."""
    version = manifest.get("schema_version")
    if version == "1.0":
        return FILES
    if version == "2.0":
        return FILES_V2
    raise ValueError("Unsupported candidate artifact version")
