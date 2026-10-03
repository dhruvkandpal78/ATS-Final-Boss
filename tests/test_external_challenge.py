"""Challenge reporting checks using fabricated assignments, without PDFs."""
import copy
import math

import pytest

from src.evaluation.external_challenge import ARMS, summarize


def row(case, source="a", family="edit", attack=True, status="complete", full=True, comparator=False):
    return {"case_id": case, "source_group": source, "family": family,
            "added_attack": attack, "status": status, "elapsed_ms": 2.5,
            "arms": {arm: {"flagged": full if arm == "full_policy" else comparator} for arm in ARMS}}


def test_partial_flags_unknown_complete_and_errors_keep_attempt_denominators():
    cases = [row("observed"), row("partial", status="partial", full=True, comparator=None),
             row("unknown", full=None, comparator=None),
             row("error", status="runtime_error", full=None, comparator=None)]
    result = summarize(cases, n_resamples=10)
    full = result["arms"]["full_policy"]["added_attack"]
    assert full["attempts"] == 4
    assert full["complete"] == full["complete_flagged"] == 1
    assert full["complete_missed"] == 0
    assert full["partial_flagged"] == full["insufficient"] == full["error"] == 1
    assert full["all_attempt_flagged_rate"] == .5
    assert full["complete_only_flagged_rate"] == 1
    paired = result["paired_vs_full"]["simple_regex"]["added_attack"]
    assert paired["n_paired"] == paired["full_only_flagged"] == 1


def test_paired_comparison_uses_same_completed_rows_and_separates_controls():
    cases = [row("gain", source="a"), row("loss", source="b", full=False, comparator=True),
             row("control", source="c", attack=False), row("unknown", source="d", full=True, comparator=None)]
    result = summarize(cases, n_resamples=20)
    paired = result["paired_vs_full"]["direct_cue_only"]
    assert paired["added_attack"] == {"n_paired": 2, "full_only_flagged": 1,
                                       "comparator_only_flagged": 1, "net_flag_rate_difference": 0}
    assert paired["control"]["net_flag_rate_difference"] == 1
    assert paired["all_completed"]["n_paired"] == 3
    assert paired["all_completed"]["net_flag_rate_difference"] == pytest.approx(1 / 3)


def test_unequal_cluster_resampling_and_arm_pairing_are_preserved():
    # One source has one success, the other has nine misses. Cluster resampling
    # produces exactly all-success, mixed, or all-miss samples; row resampling
    # would produce a narrow interval around 0.1 instead of [0, 1].
    cases = [row("success", source="small", full=True, comparator=True)]
    cases += [row(f"miss{i}", source="large", full=False, comparator=False) for i in range(9)]
    result = summarize(cases, n_resamples=100, seed=7)
    assert result == summarize(cases, n_resamples=100, seed=7)
    interval = result["bootstrap"]["arms"]["full_policy"]["added_attack"]["complete_only_flagged_rate"]
    assert interval["interval"] == [0, 1]
    assert interval["valid_draws"] == 100
    delta = result["bootstrap"]["paired_vs_full"]["simple_regex"]["added_attack"]["net_flag_rate_difference"]
    assert delta["interval"] == [0, 0]  # Identical arms remain identical in every draw.
    assert delta["undefined_draws"] == 0


def test_zero_event_boundary_counts_sources_instead_of_variants():
    cases = [row(f"c{i}", source="a" if i < 5 else "b", attack=False, full=False, comparator=False)
             for i in range(6)]
    report = summarize(cases, n_resamples=10)
    controls = report["arms"]["full_policy"]["unmodified_source_control"]
    boundary = controls["source_group_zero_event_boundary"]
    assert boundary["n_groups"] == boundary["fully_observed_groups"] == 2
    assert boundary["one_sided_95pct_upper"] == pytest.approx(1 - math.sqrt(.05))
    assert controls["row_wilson_secondary"][1] < boundary["one_sided_95pct_upper"]
    cases.append(row("partial", source="b", attack=False, status="partial", full=None, comparator=None))
    uncertain = summarize(cases, n_resamples=10)["arms"]["full_policy"]["unmodified_source_control"]
    assert uncertain["source_group_zero_event_boundary"]["one_sided_95pct_upper"] is None


def test_family_exclusion_changes_composition_without_tuning():
    report = summarize([row("hit", family="visible"), row("miss", source="b", family="obfuscated", full=False)], n_resamples=10)
    assert report["families"]["visible"]["full_policy"]["added_attack"]["complete_only_flagged_rate"] == 1
    assert report["leave_one_family_out"]["visible"]["arms"]["full_policy"]["added_attack"]["complete_only_flagged_rate"] == 0
    assert report["leave_one_family_out"]["obfuscated"]["arms"]["full_policy"]["added_attack"]["complete_only_flagged_rate"] == 1


def test_missing_class_draws_are_reported_without_zero_substitution():
    report = summarize([row("edit"), row("control", source="b", attack=False, full=False)], n_resamples=100)
    metric = report["bootstrap"]["paired_vs_full"]["simple_regex"]["added_attack"]["net_flag_rate_difference"]
    assert 0 < metric["undefined_draws"] < 100
    assert metric["valid_draws"] + metric["undefined_draws"] == 100
    assert metric["interval"] == [1, 1]


@pytest.mark.parametrize("field,value", [("case_id", ""), ("source_group", None),
    ("family", " "), ("added_attack", 1), ("status", "clean"),
    ("elapsed_ms", math.inf), ("elapsed_ms", math.nan), ("elapsed_ms", -1)])
def test_invalid_records_are_rejected(field, value):
    case = row("case")
    case[field] = value
    with pytest.raises(ValueError):
        summarize([case], n_resamples=10)


def test_duplicate_cases_and_missing_arms_fail_closed():
    case = row("duplicate")
    with pytest.raises(ValueError, match="duplicate"):
        summarize([case, copy.deepcopy(case)], n_resamples=10)
    del case["arms"]["simple_regex"]
    with pytest.raises(ValueError):
        summarize([case], n_resamples=10)


@pytest.mark.parametrize("status,full,comparator", [("partial", True, False),
    ("runtime_error", True, None), ("unscorable", None, True), ("complete", 1, False)])
def test_incomplete_nonflags_and_invalid_flags_are_rejected(status, full, comparator):
    with pytest.raises(ValueError):
        summarize([row("bad", status=status, full=full, comparator=comparator)], n_resamples=10)
