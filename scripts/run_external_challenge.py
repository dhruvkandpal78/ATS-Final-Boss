"""Freeze, then execute an external controlled challenge without detector tuning."""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import re
import sys
import time
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SEED = "external-challenge-20261003-v1"
PROTOCOL = "docs/research/EXTERNAL_CHALLENGE_PROTOCOL.md"
SIMPLE_REGEX = r"ignore\s+previous\s+instructions|rank\s+me|score\s+to\s+100"
_SERVICE = None


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def canonical_text(text):
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return hashlib.sha256(" ".join(re.findall(r"\w+", normalized)).encode()).hexdigest()


def checked_pdf(corpus, row):
    relative = Path(row["pdf_path"])
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Invalid corpus path")
    path = corpus.resolve() / relative
    if path.is_symlink() or not path.resolve(strict=True).is_relative_to(corpus.resolve()):
        raise ValueError("Corpus path escapes root")
    if digest(path) != row["sha256"]:
        raise ValueError("Corpus bytes changed")
    return path


def pdf_text(path):
    import fitz
    try:
        with fitz.open(path) as doc:
            # Empty/unavailable text is NOT a deduplication key.
            return "\n".join(page.get_text() for page in doc)
    except (RuntimeError, ValueError):
        return None


def refreeze_research_candidate(source, target):
    """Same data-only coefficients; new unapproved policy binding, not approval."""
    from src.core.artifacts import POLICY_FILES, verify_candidate, verify_policy
    parent = verify_candidate(source)
    if parent["schema_version"] != "2.0":
        raise ValueError("Research requires data-only V2 artifacts")
    target.mkdir(parents=True, exist_ok=False)
    for name in parent["artifacts"]:
        (target / name).write_bytes((source / name).read_bytes())
    manifest = dict(parent)
    manifest["created_at"] = datetime.now(timezone.utc).isoformat()
    manifest["deployment_approved"] = False
    manifest.pop("validation", None)
    manifest["model"] = {**parent["model"], "calibrated": False}
    manifest["policy"] = {"version": "2.0", "code_hashes": {p: digest(ROOT / p) for p in POLICY_FILES}}
    manifest["lineage"] = {**parent.get("lineage", {}),
                           "parent_v2_manifest_sha256": digest(source / "candidate_manifest.json"),
                           "external_challenge": "unchanged parameters; unapproved current-policy binding"}
    manifest["limitations"] = list(parent.get("limitations", [])) + [
        "External challenge does not re-establish legacy threshold calibration or deployment approval."]
    (target / "candidate_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    verify_candidate(target)
    verify_policy(manifest)
    return manifest


def freeze(corpus, output, models, embedding, consumed_corpus, max_groups=300):
    from src.core.artifacts import verify_candidate, verify_policy
    from src.core.embedding_artifacts import verify_embedding
    if not 1 <= max_groups <= 300:
        raise ValueError("Group count must be within the preregistered cap")
    provenance = json.loads((corpus / "provenance.json").read_text(encoding="utf-8"))
    if provenance["revision"] != "81a0f6b1a5c3254371e6304af9dafdc533b6c9d5":
        raise ValueError("Unexpected external revision")
    excluded_bytes, excluded_text = set(), set()
    prior = json.loads((consumed_corpus / "provenance.json").read_text(encoding="utf-8"))
    for row in prior["records"]:
        path = checked_pdf(consumed_corpus, row)
        excluded_bytes.add(row["sha256"])
        text = pdf_text(path)
        if text and text.strip():
            excluded_text.add(canonical_text(text))
    groups = {}
    for row in provenance["records"]:
        if row["variant"] not in ("original", "attack") or not isinstance(row["source_group"], str):
            raise ValueError("Ambiguous source assignment")
        groups.setdefault(row["source_group"], []).append(row)
    selected, exclusions, seen_bytes, seen_text = [], Counter(), set(), set()
    for group in sorted(groups, key=lambda value: hashlib.sha256((SEED + ":" + value).encode()).digest()):
        rows = groups[group]
        original = [r for r in rows if r["variant"] == "original"]
        if len(original) != 1 or not any(r["variant"] == "attack" for r in rows):
            raise ValueError("Every source group needs one original and supplied attacks")
        path = checked_pdf(corpus, original[0])
        text = pdf_text(path)
        fingerprint = canonical_text(text) if text and text.strip() else None
        if original[0]["sha256"] in excluded_bytes or fingerprint in excluded_text:
            exclusions["consumed_original_overlap"] += 1
            continue
        if original[0]["sha256"] in seen_bytes or (fingerprint and fingerprint in seen_text):
            exclusions["duplicate_original_group"] += 1
            continue
        seen_bytes.add(original[0]["sha256"])
        if fingerprint:
            seen_text.add(fingerprint)
        if len(selected) >= max_groups:
            exclusions["preregistered_cap"] += 1
            continue
        selected.append(rows)
    if not selected:
        raise ValueError("No eligible source groups")
    output.mkdir(parents=True, exist_ok=False)
    candidate_dir = output / "research_candidate"
    model_manifest = refreeze_research_candidate(models, candidate_dir)
    embedding_pin = digest(embedding / "embedding_manifest.json")
    verify_embedding(embedding, embedding_pin)
    cases = []
    for rows in selected:
        for row in sorted(rows, key=lambda r: (r["variant"] != "original", r.get("attack_id") or "")):
            path = checked_pdf(corpus, row)
            attack = row["variant"] == "attack"
            if attack and not row.get("attack_id"):
                raise ValueError("Attack assignment is missing")
            cases.append({"case_id": str(len(cases)),
                          "source_group": hashlib.sha256(row["source_group"].encode()).hexdigest(),
                          "family": row["attack_id"] if attack else "unmodified_source",
                          "added_attack": attack, "pdf_path": str(path), "pdf_sha256": row["sha256"],
                          "channel": row.get("channel"), "attack_family": row.get("attack_family")})
    (output / "cases.json").write_text(json.dumps(cases, indent=2), encoding="utf-8")
    source_files = [*ROOT.glob("src/**/*.py"), ROOT / "scripts/run_external_challenge.py", ROOT / PROTOCOL]
    # Keyword/config resources influence outcomes just as Python files do.
    source_files += [p for p in (ROOT / "src").rglob("*") if p.is_file() and p.suffix in (".json", ".txt", ".csv")]
    environment = {"python": platform.python_version(), "platform": platform.platform(),
                   "packages": {p: metadata.version(p) for p in
                                ("numpy", "PyMuPDF", "scikit-learn", "sentence-transformers", "torch")}}
    protocol = {"kind": "externally_authored_synthetic_pdf_challenge", "created_at": datetime.now(timezone.utc).isoformat(),
                "seed": SEED, "max_groups": max_groups, "selected_groups": len(selected), "selected_cases": len(cases),
                "family_counts": dict(Counter(r["family"] for r in cases)), "exclusions": dict(exclusions),
                "acquisition_sha256": digest(corpus / "provenance.json"), "archive_sha256": provenance["archive_sha256"],
                "consumed_corpus_sha256": digest(consumed_corpus / "provenance.json"),
                "cases_sha256": digest(output / "cases.json"), "model_manifest_sha256": digest(candidate_dir / "candidate_manifest.json"),
                "embedding_manifest_sha256": embedding_pin,
                "code_sha256": {p.relative_to(ROOT).as_posix(): digest(p) for p in source_files},
                "environment": environment, "bootstrap_draws": 1000, "bootstrap_seed": 20261003,
                "deployment_approved": model_manifest["deployment_approved"], "legacy_threshold_provenance": "unverified",
                "no_training_or_tuning": True, "labels": "Publisher-authored synthetic edit assignments, not independently adjudicated natural labels"}
    (output / "protocol.json").write_text(json.dumps(protocol, indent=2), encoding="utf-8")
    print(json.dumps({k: protocol[k] for k in ("selected_groups", "selected_cases", "family_counts", "exclusions")}), flush=True)
    return protocol, cases


def initialize(models, model_pin, embedding, embedding_pin):
    global _SERVICE
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    import torch
    torch.set_num_threads(1)
    from src.inference import load_pipeline
    from src.core.analysis_service import AnalysisService
    clf, scaler, a, b, c = load_pipeline(models, model_pin, embedding_dir=embedding,
                                      expected_embedding_manifest_sha256=embedding_pin)
    c.model.to("cpu")
    _SERVICE = AnalysisService(mod_a=a, mod_b=b, mod_c=c, meta_clf=clf, scaler=scaler)
    _SERVICE.candidate_model = True
    _SERVICE.model_id = "candidate-" + model_pin[:16]


def analyze(row):
    from src.evaluation.external_challenge import ARMS
    if digest(row["pdf_path"]) != row["pdf_sha256"]:
        raise ValueError("Frozen PDF changed")
    started = time.perf_counter()
    base = {k: row[k] for k in ("case_id", "source_group", "family", "added_attack")}
    try:
        result = _SERVICE.analyze_pdf(row["pdf_path"])
        reasons = set(result["reason_codes"])
        text = pdf_text(row["pdf_path"])
        flags = {"full_policy": result["decision"] == "review_recommended",
                 "direct_cue_only": "direct_instruction_cue" in reasons,
                 "repetition_only": "keyword_repetition_signal" in reasons,
                 "structure_advisory_only": "pdf_structure_advisory" in reasons,
                 "legacy_model_only": result.get("model_decision"),
                 "simple_regex": bool(re.search(SIMPLE_REGEX, text, re.I)) if text is not None else None}
        status = result["status"]
        arms = {name: {"flagged": (bool(flags[name]) if flags[name] is not None else None)} for name in ARMS}
        for entry in arms.values():
            if status == "unscorable" or (status != "complete" and entry["flagged"] is False):
                entry["flagged"] = None
        return {**base, "status": status, "arms": arms,
                "reason_codes": sorted(reasons), "elapsed_ms": round((time.perf_counter() - started) * 1000, 3)}
    except Exception:
        return {**base, "status": "runtime_error", "arms": {name: {"flagged": None} for name in ARMS},
                "reason_codes": ["runtime_error"], "elapsed_ms": round((time.perf_counter() - started) * 1000, 3)}


def verify_freeze(output, protocol):
    if digest(output / "cases.json") != protocol["cases_sha256"]:
        raise ValueError("Frozen cases changed")
    if digest(output / "research_candidate/candidate_manifest.json") != protocol["model_manifest_sha256"]:
        raise ValueError("Frozen model changed")
    for name, expected in protocol["code_sha256"].items():
        if digest(ROOT / name) != expected:
            raise ValueError("Frozen code or protocol changed: " + name)


def run(output, embedding, workers=2):
    from src.evaluation.external_challenge import summarize
    protocol_bytes = (output / "protocol.json").read_bytes()
    protocol = json.loads(protocol_bytes)
    verify_freeze(output, protocol)
    cases = json.loads((output / "cases.json").read_text(encoding="utf-8"))
    receipt, rows = output / "observations.jsonl", []
    started = time.perf_counter()
    with receipt.open("x", encoding="utf-8") as stream:
        with ProcessPoolExecutor(max_workers=workers, initializer=initialize,
                                 initargs=(str(output / "research_candidate"), protocol["model_manifest_sha256"],
                                           str(embedding), protocol["embedding_manifest_sha256"])) as pool:
            for row in pool.map(analyze, cases, chunksize=1):
                rows.append(row)
                stream.write(json.dumps(row) + "\n")
                stream.flush()
                if len(rows) % 100 == 0:
                    print(json.dumps({"completed": len(rows), "total": len(cases),
                                      "elapsed_s": round(time.perf_counter() - started, 1)}), flush=True)
    verify_freeze(output, protocol)
    if (output / "protocol.json").read_bytes() != protocol_bytes:
        raise ValueError("Protocol changed during execution")
    summary = summarize(rows, protocol["bootstrap_draws"], protocol["bootstrap_seed"])
    summary.update({"protocol_sha256": digest(output / "protocol.json"), "observations_sha256": digest(receipt),
                    "elapsed_s": round(time.perf_counter() - started, 3), "workers": workers,
                    "latency_scope": "Includes shared pipeline and baseline extraction; local CPU timing, not separately measured arm latency or load acceptance"})
    with (output / "summary.json").open("x", encoding="utf-8") as stream:
        json.dump(summary, stream, indent=2)
    print(json.dumps({"completed": len(rows), "summary_sha256": digest(output / "summary.json")}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path)
    parser.add_argument("--consumed-corpus", type=Path)
    parser.add_argument("--models", type=Path)
    parser.add_argument("--embedding", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-groups", type=int, default=300)
    parser.add_argument("--run-frozen", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to((ROOT / "data/benchmarks").resolve()):
        parser.error("Raw outputs must stay in ignored data/benchmarks")
    if args.run_frozen:
        run(output, args.embedding.resolve())
    else:
        if any(p is None for p in (args.corpus, args.consumed_corpus, args.models)):
            parser.error("Freeze needs corpus, consumed-corpus and models")
        freeze(args.corpus.resolve(), output, args.models.resolve(), args.embedding.resolve(),
               args.consumed_corpus.resolve(), args.max_groups)


if __name__ == "__main__":
    main()
