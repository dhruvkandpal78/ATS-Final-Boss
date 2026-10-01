import copy
import hashlib
import json

import pytest

from src.evaluation import downstream as subject


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def protocol():
    return {"schema_version": "1.0", "comparison_kind": "gate_only", "measurement_kind": "simulated",
            "label_basis": "known_interventions", "adversary_relation": "same_team",
            "dataset_sha256": digest("dataset"), "baseline_screener_sha256": digest("screener"),
            "protected_screener_sha256": digest("screener"), "gate_sha256": digest("gate"),
            "success_predicate_sha256": digest("predicate"), "environment_sha256": digest("environment"),
            "development_families": ["direct_instruction"], "development_source_sha256s": []}


def row(name, attack=False, held=False, error=False, source=None):
    state = "error" if error else "held" if held else "completed"
    def arm(arm_state, score, cost, latency):
        return {"document_sha256": digest(name), "screener_sha256": digest("screener"), "state": arm_state,
                "attack_success": bool(attack) if attack and arm_state == "completed" else None,
                "ranking_score": score if arm_state == "completed" else None,
                "latency_ms": latency, "cost_usd": cost,
                "output_sha256": digest("output") if arm_state == "completed" else None}
    return {"document_sha256": digest(name), "source_sha256": digest(source or name), "label": int(attack),
            "family": "direct_instruction" if attack else "none", "is_reference": not attack,
            "review_decision": None if error else "review_recommended" if held else "no_signals_detected",
            "review_status": "error" if error else "complete",
            "baseline": arm("completed", 0.9 if attack else 0.3, 0.01, 10),
            "protected": arm(state, 0.9 if attack else 0.3, 0.002 if held else 0.012, 2 if held else 12)}


def test_holding_every_attack_is_not_model_robustness():
    report = subject.compare([row("clean"), row("attack", attack=True, held=True)], protocol(), n_resamples=10)
    assert report["downstream_attack_outcomes"]["by_arm"]["baseline"]["success_among_completed"]["rate"] == 1
    assert report["downstream_attack_outcomes"]["by_arm"]["protected"]["success_among_completed"]["rate"] is None
    assert report["downstream_attack_outcomes"]["matched_completed"]["delta_protected_minus_baseline"] is None
    assert report["review_burden"]["labeled_attack"]["manual_holds"]["rate"] == 1
    assert report["unseen_family_evidence"] == "not_measured"


def test_benign_holds_and_failures_cannot_disappear_from_review_burden():
    report = subject.compare([row("benign_hold", held=True), row("benign_error", error=True),
                              row("attack", attack=True)], protocol(), n_resamples=10)
    burden = report["review_burden"]["no_added_attack"]
    assert burden["manual_holds"]["rate"] == 0.5
    assert burden["protected_errors"]["rate"] == 0.5
    assert report["inventory"]["by_arm"]["protected"] == {"completed": 1, "held": 1, "error": 1}


def test_abstentions_and_errors_do_not_become_negative_detections():
    error = row("error", error=True)
    abstain = row("abstain", held=True)
    abstain["family"] = "benign_confounder"
    abstain["review_decision"] = "insufficient_evidence"
    abstain["review_status"] = "partial"
    report = subject.compare([error, abstain], protocol(), n_resamples=2)
    assert report["review_detection"] is None
    assert report["review_evaluation_coverage"] == {"attempted": 2, "evaluable": 0, "abstentions": 1, "errors": 1}
    assert report["benign_control_families"]["benign_confounder"] == {"cases": 1, "flags": 0}
    assert report["provenance"]["gate_sha256"] == protocol()["gate_sha256"]


@pytest.mark.parametrize("field", ["development_families", "development_source_sha256s"])
def test_nested_development_declarations_are_rejected(field):
    p = protocol()
    p[field] = [{"unexpected": []}]
    with pytest.raises(ValueError): subject.compare([row("clean")], p, n_resamples=2)


def test_matched_delta_and_declared_unseen_family_preserve_provenance():
    rows = [row("attack1", attack=True), row("attack2", attack=True)]
    for r in rows:
        r["protected"]["attack_success"] = False
        r["family"] = "novel_family"
    report = subject.compare(rows, protocol(), n_resamples=20)
    assert report["downstream_attack_outcomes"]["matched_completed"]["delta_protected_minus_baseline"] == -1
    assert report["downstream_attack_outcomes"]["matched_completed"]["source_group_delta_interval_95pct"] == [-1, -1]
    assert report["attack_families"]["novel_family"]["development_relation"] == "declared_unseen"
    assert report["provenance"]["measurement_kind"] == "simulated"


def test_missing_measurements_are_not_zero_latency_or_cost():
    r = row("clean")
    r["protected"]["cost_usd"] = r["protected"]["latency_ms"] = None
    report = subject.compare([r], protocol(), n_resamples=2)
    assert report["measurements"]["cost_usd"]["paired_delta_all_dispositions"]["n"] == 0
    assert report["measurements"]["latency_ms"]["by_arm"]["protected"]["mean"] is None


def test_score_displacement_requires_completed_attack_and_control_in_both_arms():
    control, attack = row("control", source="source"), row("attack", attack=True, source="source")
    report = subject.compare([control, attack], protocol(), n_resamples=2)
    assert report["score_displacement_from_reference"]["baseline"]["mean"] == pytest.approx(0.6)
    attack["protected"] = row("attack", attack=True, held=True, source="source")["protected"]
    attack["review_decision"] = "review_recommended"
    report = subject.compare([control, attack], protocol(), n_resamples=2)
    assert report["score_displacement_from_reference"]["protected"]["n"] == 0


@pytest.mark.parametrize("mutation", ["duplicate", "hash", "model", "label_bool", "huge_number", "nan",
                                      "raw_text", "forward_flag", "error_grade", "reference", "family", "unknown_state"])
def test_invalid_or_misleading_pairs_fail_closed(mutation):
    r, p = row("case"), protocol()
    rows = [r]
    if mutation == "duplicate": rows.append(copy.deepcopy(r))
    if mutation == "hash": r["protected"]["document_sha256"] = digest("different")
    if mutation == "model": r["protected"]["screener_sha256"] = digest("different")
    if mutation == "label_bool": r["label"] = False
    if mutation == "huge_number": r["protected"]["latency_ms"] = 10**1000
    if mutation == "nan": r["protected"]["cost_usd"] = float("nan")
    if mutation == "raw_text": r["resume_text"] = "PRIVATE_CANARY"
    if mutation == "forward_flag": r["review_decision"] = "review_recommended"
    if mutation == "error_grade": r["baseline"]["state"] = "error"
    if mutation == "reference": rows.append(row("another", source="case"))
    if mutation == "family": r["family"] = "raw text is not a code"
    if mutation == "unknown_state": r["protected"]["state"] = "ignored"
    with pytest.raises(ValueError):
        subject.compare(rows, p, n_resamples=2)


def test_protocol_comparison_and_development_overlap_are_checked():
    p = protocol()
    p["protected_screener_sha256"] = digest("different")
    with pytest.raises(ValueError): subject.compare([row("case")], p, n_resamples=2)
    p = protocol()
    p["development_source_sha256s"] = [digest("case")]
    with pytest.raises(ValueError): subject.compare([row("case")], p, n_resamples=2)


def test_cli_pins_inputs_refuses_overwrite_and_exports_no_document_ids(tmp_path):
    p = tmp_path / "protocol.json"
    p.write_text(json.dumps(protocol()), encoding="utf-8")
    pin = hashlib.sha256(p.read_bytes()).hexdigest()
    packet = {"schema_version": "1.0", "protocol_sha256": pin, "dataset_sha256": protocol()["dataset_sha256"],
              "rows": [row("case")]}
    observations = tmp_path / "observations.json"
    observations.write_text(json.dumps(packet), encoding="utf-8")
    output = tmp_path / "report.json"
    args = ["--protocol", str(p), "--protocol-sha256", pin, "--observations", str(observations),
            "--output", str(output), "--bootstrap-resamples", "2"]
    subject.main(args)
    report = output.read_text()
    assert digest("case") not in report
    with pytest.raises(SystemExit): subject.main(args)
    args[3] = digest("wrong_pin")
    with pytest.raises(SystemExit): subject.main(args)


@pytest.mark.parametrize("content", [b'{"x":1,"x":2}', b'{"x":NaN}', b"[" * 65 + b"]" * 65])
def test_strict_bounded_import_rejects_ambiguous_json(tmp_path, content):
    path = tmp_path / "bad.json"
    path.write_bytes(content)
    with pytest.raises(ValueError): subject._read(path)
