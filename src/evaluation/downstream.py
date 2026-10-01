"""Compare supplied paired downstream observations; never run a screener.

No resumes, models, held-out datasets or API credentials are opened. Source
labels, system execution and measurements are operator-supplied, not certified.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

import numpy as np

from src.app.http_contract import decode_json_body
from src.evaluation.statistics import binary_confusion_metrics, source_group_bootstrap, iter_source_group_bootstrap_indices

MAX_BYTES = 16 * 1024 * 1024
MAX_ROWS = 10000
SHA = re.compile(r"[0-9a-f]{64}\Z")
CODE = re.compile(r"[a-z][a-z0-9_-]{0,47}\Z")
PROTOCOL_KEYS = {"schema_version", "comparison_kind", "measurement_kind", "label_basis",
                 "dataset_sha256", "baseline_screener_sha256", "protected_screener_sha256",
                 "gate_sha256", "success_predicate_sha256", "environment_sha256",
                 "development_families", "development_source_sha256s", "adversary_relation"}
ROW_KEYS = {"document_sha256", "source_sha256", "label", "family", "is_reference",
            "review_decision", "review_status", "baseline", "protected"}
ARM_KEYS = {"document_sha256", "screener_sha256", "state", "attack_success",
            "ranking_score", "latency_ms", "cost_usd", "output_sha256"}


def _fields(value, keys):
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError("Invalid schema fields; raw document/output fields are not accepted.")


def _sha(value):
    if not isinstance(value, str) or not SHA.fullmatch(value):
        raise ValueError("Expected a lowercase SHA-256 digest.")


def _number(value, ceiling):
    if value is not None and (type(value) not in (int, float) or not 0 <= value <= ceiling or not math.isfinite(value)):
        raise ValueError("Invalid finite numeric observation.")


def _read(path):
    with Path(path).open("rb") as file:
        raw = file.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("Benchmark input exceeds 16 MiB.")
    return decode_json_body(raw, strict=True), hashlib.sha256(raw).hexdigest()


def validate_protocol(protocol):
    _fields(protocol, PROTOCOL_KEYS)
    if (protocol["schema_version"] != "1.0" or protocol["comparison_kind"] not in ("gate_only", "system_comparison") or
            protocol["measurement_kind"] not in ("measured", "simulated") or
            protocol["label_basis"] not in ("known_interventions", "natural_adjudicated") or
            protocol["adversary_relation"] not in ("same_team", "independent_team", "unknown")):
        raise ValueError("Unsupported protocol version or provenance fields.")
    for key in PROTOCOL_KEYS:
        if key.endswith("_sha256"):
            _sha(protocol[key])
    if protocol["comparison_kind"] == "gate_only" and protocol["baseline_screener_sha256"] != protocol["protected_screener_sha256"]:
        raise ValueError("Gate-only comparison requires identical declared screener fingerprints.")
    for key, maximum in (("development_families", 64), ("development_source_sha256s", MAX_ROWS)):
        values = protocol[key]
        if not isinstance(values, list) or len(values) > maximum or any(not isinstance(v, str) for v in values):
            raise ValueError("Invalid bounded development declaration.")
        if len(set(values)) != len(values):
            raise ValueError("Duplicate development declarations.")
    if any(not CODE.fullmatch(family) or family == "none" for family in protocol["development_families"]):
        raise ValueError("Invalid development family codes.")
    for value in protocol["development_source_sha256s"]:
        _sha(value)


def validate_rows(rows, protocol):
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_ROWS:
        raise ValueError("Expected between one and 10,000 paired rows.")
    documents, references = set(), set()
    development = set(protocol["development_source_sha256s"])
    for row in rows:
        _fields(row, ROW_KEYS)
        for key in ("document_sha256", "source_sha256"):
            _sha(row[key])
        if row["document_sha256"] in documents:
            raise ValueError("Duplicate document observations.")
        documents.add(row["document_sha256"])
        if row["source_sha256"] in development or row["document_sha256"] in development:
            raise ValueError("Declared development/evaluation overlap.")
        if type(row["label"]) is not int or row["label"] not in (0, 1) or type(row["is_reference"]) is not bool:
            raise ValueError("Explicit binary labels/reference roles are required.")
        family = row["family"]
        if not isinstance(family, str) or not CODE.fullmatch(family) or (family == "none" and row["label"]):
            raise ValueError("Families must be coded; attacks cannot use none.")
        if row["is_reference"]:
            if row["label"] or row["source_sha256"] in references:
                raise ValueError("At most one no-attack reference is allowed per source.")
            references.add(row["source_sha256"])
        if row["review_decision"] not in (None, "no_signals_detected", "review_recommended", "insufficient_evidence"):
            raise ValueError("Unknown review decision.")
        if row["review_status"] not in ("complete", "partial", "unscorable", "error"):
            raise ValueError("Unknown review status.")
        if (row["review_status"] == "error") != (row["review_decision"] is None):
            raise ValueError("Review errors must not invent a decision.")
        if row["review_decision"] == "no_signals_detected" and row["review_status"] != "complete":
            raise ValueError("Incomplete review cannot claim no signals.")
        for name in ("baseline", "protected"):
            arm = row[name]
            _fields(arm, ARM_KEYS)
            if arm["document_sha256"] != row["document_sha256"] or arm["screener_sha256"] != protocol[name + "_screener_sha256"]:
                raise ValueError("Mismatched document or screener in paired observation.")
            if arm["state"] not in (("completed", "error") if name == "baseline" else ("completed", "held", "error")):
                raise ValueError("Unknown or impossible arm state.")
            completed = arm["state"] == "completed"
            if completed:
                _sha(arm["output_sha256"])
            elif arm["output_sha256"] is not None or arm["ranking_score"] is not None:
                raise ValueError("Held/errors cannot contain downstream output or ranking scores.")
            if row["label"] and completed:
                if type(arm["attack_success"]) is not bool:
                    raise ValueError("Completed attacks require a graded downstream success observation.")
            elif arm["attack_success"] is not None:
                raise ValueError("Non-evaluated/benign cases cannot invent attack success observations.")
            _number(arm["ranking_score"], 1)
            _number(arm["latency_ms"], 24 * 60 * 60 * 1000)
            _number(arm["cost_usd"], 10**6)
        forward = row["review_decision"] == "no_signals_detected" and row["review_status"] == "complete"
        protected_state = row["protected"]["state"]
        if (protected_state == "completed" and not forward) or (protected_state == "held" and forward):
            raise ValueError("Protected disposition contradicts the preregistered fail-closed gate.")
        if row["review_status"] == "error" and protected_state != "error":
            raise ValueError("Unavailable review must be recorded as an error, not a successful hold.")
    if len({row["family"] for row in rows if row["label"]}) > 64:
        raise ValueError("At most 64 attack families are supported.")


def _rate(successes, total):
    return {"numerator": int(successes), "denominator": int(total), "rate": successes / total if total else None}


def _quantiles(values):
    if not values:
        return {"n": 0, "mean": None, "p50": None, "p95": None, "p99": None}
    return {"n": len(values), "mean": float(np.mean(values)),
            **{f"p{q}": float(np.percentile(values, q)) for q in (50, 95, 99)}}


def _attack_outcomes(rows):
    attacks = [row for row in rows if row["label"]]
    matched = [row for row in attacks if all(row[name]["state"] == "completed" for name in ("baseline", "protected"))]
    by_arm = {}
    for name in ("baseline", "protected"):
        completed = [row for row in attacks if row[name]["state"] == "completed"]
        by_arm[name] = {
            "success_among_completed": _rate(sum(row[name]["attack_success"] for row in completed), len(completed)),
            "completed": len(completed), "held": sum(row[name]["state"] == "held" for row in attacks),
            "errors": sum(row[name]["state"] == "error" for row in attacks),
        }
    before = sum(row["baseline"]["attack_success"] for row in matched)
    after = sum(row["protected"]["attack_success"] for row in matched)
    return {"attack_cases": len(attacks), "by_arm": by_arm,
            "matched_completed": {"cases": len(matched), "baseline_success": _rate(before, len(matched)),
                                  "protected_success": _rate(after, len(matched)),
                                  "delta_protected_minus_baseline": (after - before) / len(matched) if matched else None}}


def compare(rows, protocol, *, n_resamples=1000, seed=42):
    validate_protocol(protocol)
    validate_rows(rows, protocol)
    if type(n_resamples) is not int or not 1 <= n_resamples <= 2000 or type(seed) is not int or not 0 <= seed <= 2**32 - 1:
        raise ValueError("Invalid bounded bootstrap configuration.")
    labels = [row["label"] for row in rows]
    groups = [row["source_sha256"] for row in rows]
    evaluable = [row for row in rows if row["review_decision"] in ("review_recommended", "no_signals_detected")]
    evaluated_labels = [row["label"] for row in evaluable]
    flags = [int(row["review_decision"] == "review_recommended") for row in evaluable]
    detection = binary_confusion_metrics(evaluated_labels, flags) if evaluable else None
    if detection is not None:
        detection["source_group_bootstrap"] = source_group_bootstrap(evaluated_labels, flags,
            [row["source_sha256"] for row in evaluable], n_resamples, seed)
    outcomes = _attack_outcomes(rows)
    matched = [row for row in rows if row["label"] and all(row[n]["state"] == "completed" for n in ("baseline", "protected"))]
    paired_interval = None
    if len(set(row["source_sha256"] for row in matched)) >= 2:
        delta = np.array([int(row["protected"]["attack_success"]) - int(row["baseline"]["attack_success"]) for row in matched])
        draws = [float(np.mean(delta[index])) for index in iter_source_group_bootstrap_indices(
            [row["source_sha256"] for row in matched], n_resamples, seed)]
        paired_interval = [float(v) for v in np.percentile(draws, [2.5, 97.5])]
    outcomes["matched_completed"]["source_group_delta_interval_95pct"] = paired_interval
    outcomes["matched_completed"]["source_groups"] = len(set(row["source_sha256"] for row in matched))
    burden = {}
    for label, name in ((0, "no_added_attack" if protocol["label_basis"] == "known_interventions" else "labeled_benign"), (1, "labeled_attack")):
        subset = [row for row in rows if row["label"] == label]
        burden[name] = {"manual_holds": _rate(sum(row["protected"]["state"] == "held" for row in subset), len(subset)),
                        "review_flags": _rate(sum(row["review_decision"] == "review_recommended" for row in subset), len(subset)),
                        "protected_errors": _rate(sum(row["protected"]["state"] == "error" for row in subset), len(subset))}
    measurements = {}
    for metric in ("latency_ms", "cost_usd"):
        pairs = [row for row in rows if all(row[n][metric] is not None for n in ("baseline", "protected"))]
        measurements[metric] = {
            "by_arm": {name: _quantiles([row[name][metric] for row in rows if row[name][metric] is not None]) for name in ("baseline", "protected")},
            "paired_delta_all_dispositions": _quantiles([row["protected"][metric] - row["baseline"][metric] for row in pairs]),
            "paired_delta_both_completed": _quantiles([row["protected"][metric] - row["baseline"][metric] for row in pairs if all(row[n]["state"] == "completed" for n in ("baseline", "protected"))]),
        }
    references = {row["source_sha256"]: row for row in rows if row["is_reference"]}
    displacements = []
    for row in rows:
        reference = references.get(row["source_sha256"])
        if row["label"] and reference and all(item[name]["ranking_score"] is not None for item in (row, reference) for name in ("baseline", "protected")):
            displacements.append({name: row[name]["ranking_score"] - reference[name]["ranking_score"] for name in ("baseline", "protected")})
    family_results = {}
    known = set(protocol["development_families"])
    for family in sorted(set(row["family"] for row in rows if row["label"])):
        subset = [row for row in rows if row["family"] == family]
        family_results[family] = {"development_relation": "declared_known" if family in known else "declared_unseen",
                                  **_attack_outcomes(subset)}
    return {
        "schema_version": "1.0", "report_kind": "imported_paired_downstream_observations",
        "provenance": {key: protocol[key] for key in PROTOCOL_KEYS if key != "development_source_sha256s"},
        "inventory": {"cases": len(rows), "source_groups": len(set(groups)), "attacks": sum(labels),
                      "by_arm": {name: {state: sum(row[name]["state"] == state for row in rows) for state in ("completed", "held", "error")} for name in ("baseline", "protected")}},
        "review_detection": detection,
        "review_evaluation_coverage": {"attempted": len(rows), "evaluable": len(evaluable),
            "abstentions": sum(row["review_decision"] == "insufficient_evidence" for row in rows),
            "errors": sum(row["review_status"] == "error" for row in rows)},
        "benign_control_families": {family: {
            "cases": sum(not row["label"] and row["family"] == family for row in rows),
            "flags": sum(not row["label"] and row["family"] == family and row["review_decision"] == "review_recommended" for row in rows)}
            for family in sorted({row["family"] for row in rows if not row["label"]})},
        "downstream_attack_outcomes": outcomes, "review_burden": burden,
        "measurements": measurements, "score_displacement_from_reference": {
            name: _quantiles([value[name] for value in displacements]) for name in ("baseline", "protected")},
        "attack_families": family_results,
        "unseen_family_evidence": "present_operator_declared" if any(row["label"] and row["family"] not in known for row in rows) else "not_measured",
        "bootstrap": {"resamples": n_resamples, "seed": seed},
        "limitations": [
            "Imported labels, provenance, fingerprints, success grades, executions and measurements are operator-supplied; authenticity is not verified.",
            "Held cases are manual deferrals, not downstream model resistance; errors and unmatched completions must not be silently excluded.",
            "Matched-completed attack deltas describe the forwarded subset, not the full attack population. Score displacement is not actual ranking corruption.",
            "Known interventions do not certify naturally benign originals; declared unseen families/team independence are not independently established.",
            "Group intervals assume independent source groups and omit undefined draws; small samples and few resamples are unreliable.",
            "Latency/cost may be missing and reflect declared runs only; manual review cost, load throughput, CPU/memory, SLAs and fairness are not measured here.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", required=True)
    parser.add_argument("--protocol-sha256", required=True, help="Separately approved byte digest")
    parser.add_argument("--observations", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--bootstrap-resamples", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)
    try:
        protocol, digest = _read(args.protocol)
        _sha(args.protocol_sha256)
        if digest != args.protocol_sha256:
            raise ValueError("Protocol pin mismatch.")
        observations, observation_digest = _read(args.observations)
        _fields(observations, {"schema_version", "protocol_sha256", "dataset_sha256", "rows"})
        if observations["schema_version"] != "1.0" or observations["protocol_sha256"] != digest or observations["dataset_sha256"] != protocol.get("dataset_sha256"):
            raise ValueError("Observation protocol/dataset mismatch.")
        report = compare(observations["rows"], protocol, n_resamples=args.bootstrap_resamples, seed=args.seed)
        report["input_integrity"] = {"protocol_sha256": digest, "observation_sha256": observation_digest,
                                     "dataset_identity_is_operator_declared": True}
        # Refuse overwrite, including accidentally choosing an input path.
        with Path(args.output).open("x", encoding="utf-8") as file:
            json.dump(report, file, allow_nan=False, indent=2)
            file.write("\n")
    except (ValueError, OSError, RecursionError):
        parser.error("Invalid bounded benchmark inputs or output path; no valid report was produced.")
    print("Paired observation report written; this does not certify downstream protection.")


if __name__ == "__main__":
    main()
