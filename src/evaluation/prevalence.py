"""Illustrative base-rate transport, not validation or candidate probabilities.

This module reads no documents and fits no model. Transporting sensitivity and
false-positive rates to another population is an assumption, not an observation.
"""
import argparse
import json
import math

MAX_SOURCE_ROWS = 10**9


def _rate(value, name):
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError(f"{name} must be a finite rate between zero and one")
    return float(value)


def prevalence_scenario(sensitivity, false_positive_rate, prevalence, cohort_size=10000):
    sensitivity = _rate(sensitivity, "sensitivity")
    false_positive_rate = _rate(false_positive_rate, "false_positive_rate")
    prevalence = _rate(prevalence, "prevalence")
    if type(cohort_size) is not int or not 1 <= cohort_size <= 10**9:
        raise ValueError("cohort_size must be an integer from 1 to 1,000,000,000")
    attacks = cohort_size * prevalence
    negatives = cohort_size * (1 - prevalence)
    tp, fp = attacks * sensitivity, negatives * false_positive_rate
    fn, tn = attacks * (1 - sensitivity), negatives * (1 - false_positive_rate)
    return {
        "assumed_prevalence": prevalence, "cohort_size": cohort_size,
        "assumed_sensitivity": sensitivity, "assumed_false_positive_rate": false_positive_rate,
        "expected_counts": {"TP": tp, "FP": fp, "TN": tn, "FN": fn},
        "expected_flagged": tp + fp,
        "projected_precision": tp / (tp + fp) if tp + fp else None,
        "projected_negative_predictive_value": tn / (tn + fn) if tn + fn else None,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("tp", "fp", "tn", "fn"):
        parser.add_argument(f"--{name}", type=int, required=True)
    parser.add_argument("--source-kind", required=True,
                        choices=("legacy_synthetic", "controlled_edits", "natural_labeled"))
    parser.add_argument("--prevalence", type=float, nargs="+", default=[0.001, 0.01, 0.02, 0.05])
    parser.add_argument("--cohort-size", type=int, default=10000)
    parser.add_argument("--fpr-stress", type=float, help="Separate assumed FPR for uncertainty/shift stress scenarios")
    args = parser.parse_args(argv)
    counts = {key.upper(): getattr(args, key) for key in ("tp", "fp", "tn", "fn")}
    try:
        if any(value < 0 for value in counts.values()):
            raise ValueError("confusion counts must be nonnegative")
        if sum(counts.values()) > MAX_SOURCE_ROWS:
            raise ValueError("source counts must total at most 1,000,000,000")
        if len(args.prevalence) > 100:
            raise ValueError("at most 100 prevalence scenarios are supported")
        positives, negatives = args.tp + args.fn, args.fp + args.tn
        if not positives or not negatives:
            raise ValueError("both labeled class denominators must be positive")
        sensitivity, fpr = args.tp / positives, args.fp / negatives
        scenarios = [prevalence_scenario(sensitivity, fpr, rate, args.cohort_size) for rate in args.prevalence]
        stress = ([prevalence_scenario(sensitivity, args.fpr_stress, rate, args.cohort_size)
                   for rate in args.prevalence] if args.fpr_stress is not None else [])
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps({
        "schema_version": "1.0", "report_kind": "illustrative_prevalence_transport",
        "source_kind_supplied_by_operator": args.source_kind, "source_counts": counts,
        "source_denominators": {"positives": positives, "negatives": negatives},
        "source_observed_precision": args.tp / (args.tp + args.fp) if args.tp + args.fp else None,
        "scenarios": scenarios, "stress_scenarios": stress,
        "limitations": [
            "Prevalence is assumed, not estimated. Source labels and independence are not verified here.",
            "Transport assumes unchanged sensitivity and false-positive rate; dataset shift may invalidate it.",
            "Zero observed false positives is not zero population risk; stress inputs are assumptions, not confidence bounds.",
            "These aggregate projections are not per-candidate cheating probabilities or proof of natural attack performance.",
        ],
    }, allow_nan=False, indent=2))


if __name__ == "__main__":
    main()
