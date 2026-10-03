"""Read-only environment diagnostics; never downloads models or evaluates data."""
import importlib.util
from importlib.metadata import version, PackageNotFoundError
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = {"numpy": "numpy", "pandas": "pandas", "sklearn": "scikit-learn",
            "sentence_transformers": "sentence-transformers", "torch": "torch",
            "fitz": "PyMuPDF", "pdfplumber": "pdfplumber"}


def check_thresholds(path):
    """Inspect calibration without loading models or evaluating documents."""
    try:
        values = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(values, dict):
            raise ValueError("Expected object")
    except (OSError, ValueError):
        return [{"name": "detector_thresholds", "ok": False, "detail": "Missing or malformed threshold configuration."}]
    checks = []
    for key in ("mod_a_threshold", "mod_c_variance_threshold"):
        value = values.get(key)
        valid = isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and 0 < value <= 1
        checks.append({"name": key, "ok": valid, "detail":
                       "Positive finite threshold; validation provenance still required." if valid else
                       "Invalid threshold; recalibrate on source-disjoint validation data before scoring."})
    return checks


def diagnose():
    checks = []
    checks.append({"name": "python", "ok": sys.version_info >= (3, 11), "detail": sys.version.split()[0]})
    for module, distribution in PACKAGES.items():
        available = importlib.util.find_spec(module) is not None
        try:
            installed = version(distribution)
        except PackageNotFoundError:
            installed = "missing"
        checks.append({"name": distribution, "ok": available, "detail": installed})
    from src.core.runtime_paths import models_directory
    from src.core.artifacts import verify_candidate
    model_dir = models_directory()
    try:
        manifest = verify_candidate(model_dir)
        is_v2 = manifest["schema_version"] == "2.0"
        checks.append({"name":"candidate_format", "ok":is_v2,
                       "detail":"Data-only V2; independent approval and runtime compatibility still required." if is_v2 else
                       "V1 pickle is unsupported at runtime; explicitly migrate approved artifacts offline."})
        checks.extend(check_thresholds(model_dir / "thresholds.json"))
    except (OSError, ValueError):
        checks.append({"name":"candidate_format", "ok":False,
                       "detail":"Missing or invalid data-only V2 candidate; no fallback is available."})
    # Cache inspection only: a directory alone does not prove model compatibility.
    try:
        from huggingface_hub import try_to_load_from_cache
        configured = json.loads((model_dir / "model_config.json").read_text())
        model = configured.get("embedding_model", "all-MiniLM-L6-v2")
        if "/" not in model:
            model = "sentence-transformers/" + model
        cached = try_to_load_from_cache(model, "config.json")
        checks.append({"name": "embedding_config_cache", "ok": isinstance(cached, str),
                       "detail": "config cached; runtime load still required" if isinstance(cached, str) else "not cached; provision model explicitly"})
    except (ImportError, OSError, ValueError):
        checks.append({"name": "embedding_config_cache", "ok": False, "detail": "cache could not be inspected"})
    return checks


def main():
    checks = diagnose()
    if "--json" in sys.argv:
        print(json.dumps({"ok": all(item["ok"] for item in checks), "checks": checks}, indent=2))
    else:
        for item in checks:
            print(f"[{'PASS' if item['ok'] else 'FAIL'}] {item['name']}: {item['detail']}")
        print("Checks are read-only. Artifact hashes identify this checkout; they do not certify provenance or model compatibility.")
    return 0 if all(item["ok"] for item in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
