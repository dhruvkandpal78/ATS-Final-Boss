import json
import pytest
from src.evaluation.prevalence import main, prevalence_scenario


def test_low_base_rate_exposes_review_burden():
    scenario = prevalence_scenario(0.656, 0.075, 0.02)
    assert scenario["expected_counts"] == pytest.approx({"TP": 131.2, "FP": 735, "TN": 9065, "FN": 68.8})
    assert scenario["projected_precision"] == pytest.approx(131.2 / 866.2)
    assert scenario["projected_negative_predictive_value"] == pytest.approx(9065 / 9133.8)


def test_no_flags_and_no_negatives_keep_undefined_values():
    assert prevalence_scenario(0, 0, 0.02)["projected_precision"] is None
    assert prevalence_scenario(1, 1, 1)["projected_negative_predictive_value"] is None


@pytest.mark.parametrize("kwargs", [
    {"sensitivity": True}, {"sensitivity": float("nan")}, {"false_positive_rate": float("inf")},
    {"prevalence": -0.01}, {"prevalence": 1.01}, {"cohort_size": True},
    {"cohort_size": 0}, {"cohort_size": 10**9 + 1},
])
def test_invalid_assumptions_are_rejected(kwargs):
    values = dict(sensitivity=0.8, false_positive_rate=0.05, prevalence=0.02)
    values.update(kwargs)
    with pytest.raises(ValueError):
        prevalence_scenario(**values)


def test_controlled_perfection_requires_visible_assumptions_and_stress(capsys):
    main(["--tp", "100", "--fp", "0", "--tn", "200", "--fn", "0",
          "--source-kind", "controlled_edits", "--prevalence", "0.02", "--fpr-stress", "0.0295"])
    report = json.loads(capsys.readouterr().out)
    assert report["source_kind_supplied_by_operator"] == "controlled_edits"
    assert report["scenarios"][0]["projected_precision"] == 1
    assert report["stress_scenarios"][0]["projected_precision"] == pytest.approx(200 / (200 + 289.1))
    assert "not confidence bounds" in report["limitations"][2]


def test_missing_class_denominator_is_not_validated_performance():
    with pytest.raises(SystemExit) as error:
        main(["--tp", "0", "--fp", "0", "--tn", "200", "--fn", "0", "--source-kind", "controlled_edits"])
    assert error.value.code == 2


def test_oversized_source_counts_return_validation_error(capsys):
    with pytest.raises(SystemExit) as error:
        main(["--tp", str(10**1000), "--fp", "0", "--tn", "200", "--fn", "0",
              "--source-kind", "controlled_edits"])
    assert error.value.code == 2
    assert "source counts must total at most" in capsys.readouterr().err
