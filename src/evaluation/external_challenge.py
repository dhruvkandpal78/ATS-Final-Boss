"""Paired descriptive summaries of a controlled external PDF challenge.

No files or detector services are opened. Added-edit labels are experimental
assignments, not verified natural attack labels. Source controls estimate review
burden on unmodified documents, not natural false-positive rate or precision.
"""
from collections import Counter
from numbers import Integral, Real

import numpy as np

from src.evaluation.statistics import (iter_source_group_bootstrap_indices,
                                       wilson_interval, zero_event_upper_bound)

ARMS = ("full_policy", "direct_cue_only", "repetition_only",
        "structure_advisory_only", "legacy_model_only", "simple_regex")
STATUSES = ("complete", "partial", "unscorable", "runtime_error")


def _validate(rows):
    rows = list(rows)
    if not rows:
        raise ValueError("at least one attempted case is required")
    seen = set()
    for row in rows:
        for field in ("case_id", "source_group", "family"):
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError(f"{field} must be a nonempty string")
        if row["case_id"] in seen:
            raise ValueError("duplicate case_id")
        seen.add(row["case_id"])
        if type(row.get("added_attack")) is not bool:
            raise ValueError("added_attack must be boolean")
        if row.get("status") not in STATUSES:
            raise ValueError("invalid case status")
        elapsed = row.get("elapsed_ms")
        if isinstance(elapsed, bool) or not isinstance(elapsed, Real) or not np.isfinite(elapsed) or elapsed < 0:
            raise ValueError("elapsed_ms must be a finite nonnegative number")
        if not isinstance(row.get("arms"), dict) or set(row["arms"]) != set(ARMS):
            raise ValueError("every case must supply exactly the registered arms")
        for arm in ARMS:
            entry = row["arms"][arm]
            if not isinstance(entry, dict) or "flagged" not in entry:
                raise ValueError("every arm requires flagged")
            flag = entry["flagged"]
            if flag is not None and type(flag) is not bool:
                raise ValueError("flagged must be boolean or None")
            if row["status"] != "complete" and flag is False:
                raise ValueError("incomplete nonflags must be unknown (None)")
            if row["status"] in ("unscorable", "runtime_error") and flag is not None:
                raise ValueError("unscorable/error arms must be unknown")
    return rows


def _ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def _stratum(rows, arm, boundary=False):
    complete = [row for row in rows if row["status"] == "complete" and row["arms"][arm]["flagged"] is not None]
    flagged = sum(row["arms"][arm]["flagged"] is True for row in complete)
    partial = sum(row["status"] == "partial" and row["arms"][arm]["flagged"] is True for row in rows)
    errors = sum(row["status"] == "runtime_error" for row in rows)
    result = {"attempts": len(rows), "complete": len(complete),
              "complete_flagged": flagged, "complete_missed": len(complete) - flagged,
              "partial_flagged": partial, "error": errors,
              "insufficient": len(rows) - len(complete) - partial - errors,
              "all_attempt_flagged_rate": _ratio(flagged + partial, len(rows)),
              "complete_only_flagged_rate": _ratio(flagged, len(complete)),
              "row_wilson_secondary": wilson_interval(flagged, len(complete))}
    if boundary:
        groups = {}
        for row in rows:
            groups.setdefault(row["source_group"], []).append(row)
        # A group is known event-free only if every control attempt completed.
        events = sum(any(r["arms"][arm]["flagged"] is True for r in group) for group in groups.values())
        fully_observed = sum(all(r["status"] == "complete" and r["arms"][arm]["flagged"] is not None
                                 for r in group) for group in groups.values())
        eligible = len(groups) > 0 and events == 0 and fully_observed == len(groups)
        result["source_group_zero_event_boundary"] = {
            "n_groups": len(groups), "groups_with_any_flag": events,
            "fully_observed_groups": fully_observed,
            "one_sided_95pct_upper": zero_event_upper_bound(len(groups)) if eligible else None,
            "assumption": "Independent source groups; all control attempts observed; source IDs do not establish person independence."}
    return result


def _arm_reports(rows):
    return {arm: {"overall": _stratum(rows, arm),
                  "added_attack": _stratum([r for r in rows if r["added_attack"]], arm),
                  "unmodified_source_control": _stratum([r for r in rows if not r["added_attack"]], arm, True)}
            for arm in ARMS}


def _paired(rows):
    result = {}
    for arm in ARMS[1:]:
        eligible = [r for r in rows if r["status"] == "complete"
                    and r["arms"][arm]["flagged"] is not None
                    and r["arms"]["full_policy"]["flagged"] is not None]
        strata = {}
        for name, subset in (("all_completed", eligible),
                             ("added_attack", [r for r in eligible if r["added_attack"]]),
                             ("control", [r for r in eligible if not r["added_attack"]])):
            gains = sum(r["arms"]["full_policy"]["flagged"] and not r["arms"][arm]["flagged"] for r in subset)
            losses = sum(not r["arms"]["full_policy"]["flagged"] and r["arms"][arm]["flagged"] for r in subset)
            strata[name] = {"n_paired": len(subset), "full_only_flagged": gains,
                            "comparator_only_flagged": losses,
                            "net_flag_rate_difference": _ratio(gains - losses, len(subset))}
        result[arm] = strata
    return result


def summarize(rows, n_resamples=1000, seed=20261003):
    """Summarize supplied cases, with paired source-group percentile intervals.

    Incomplete unknowns stay in all-attempt denominators. Complete-only summaries
    exclude unknown arms, explicitly reporting insufficient coverage. Partial
    flags are observable flags, but never enter completed paired comparisons.
    """
    rows = _validate(rows)
    if isinstance(n_resamples, bool) or not isinstance(n_resamples, Integral) or n_resamples < 1:
        raise ValueError("n_resamples must be a positive integer")
    if isinstance(seed, bool) or not isinstance(seed, Integral) or seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    groups = [r["source_group"] for r in rows]
    n_groups = len(set(groups))
    samples = {}
    for arm in ARMS:
        for stratum in ("added_attack", "unmodified_source_control"):
            for metric in ("all_attempt_flagged_rate", "complete_only_flagged_rate"):
                samples[("arms", arm, stratum, metric)] = []
    for arm in ARMS[1:]:
        for stratum in ("all_completed", "added_attack", "control"):
            samples[("paired_vs_full", arm, stratum, "net_flag_rate_difference")] = []
    for indices in iter_source_group_bootstrap_indices(groups, n_resamples, seed):
        subset = [rows[int(index)] for index in indices]
        reports = {"arms": _arm_reports(subset), "paired_vs_full": _paired(subset)}
        for key, values in samples.items():
            section, arm, stratum, metric = key
            value = reports[section][arm][stratum][metric]
            if value is not None:
                values.append(value)
    bootstrap = {"arms": {}, "paired_vs_full": {}, "n_resamples": int(n_resamples),
                 "seed": int(seed), "n_source_groups": n_groups,
                 "method": "paired source-group percentile bootstrap; 95% intervals; row-weighted",
                 "assumptions": "Source groups sampled together across arms, preserving all variants. Independent source groups assumed; person independence unverified. Undefined draws omitted per metric. Degenerate zero-event intervals do not prove zero risk."}
    for (section, arm, stratum, metric), values in samples.items():
        bootstrap[section].setdefault(arm, {}).setdefault(stratum, {})[metric] = {
            "interval": [float(v) for v in np.percentile(values, [2.5, 97.5])] if values and n_groups >= 2 else None,
            "valid_draws": len(values), "undefined_draws": int(n_resamples) - len(values)}
    families = sorted({r["family"] for r in rows})
    return {"n_attempts": len(rows), "n_source_groups": n_groups,
            "status_counts": {status: Counter(r["status"] for r in rows)[status] for status in STATUSES},
            "arms": _arm_reports(rows), "paired_vs_full": _paired(rows),
            "families": {family: _arm_reports([r for r in rows if r["family"] == family]) for family in families},
            "leave_one_family_out": {family: {"arms": _arm_reports([r for r in rows if r["family"] != family]),
                                               "paired_vs_full": _paired([r for r in rows if r["family"] != family])}
                                     for family in families},
            "bootstrap": bootstrap,
            "interpretation": "Controlled added-edit detection and unmodified-source review-burden proxy. These labels do not establish natural attack recall, false-positive rate, precision, fairness, or hiring outcomes. Row Wilson intervals are secondary independence-based descriptions."}
