"""Offline authored regression checks for Module C's current lexical rules."""
from src.modules import module_c
from scripts.check_instruction_regressions import CASES, run_diagnostic


def test_diagnostic_uses_fixed_cases_without_initializing_model(monkeypatch):
    def forbidden_model_init(*args, **kwargs):
        raise AssertionError("instruction regression diagnostic must not load a model")

    monkeypatch.setattr(module_c, "SentenceTransformer", forbidden_model_init)
    result = run_diagnostic()

    assert result["model_inference"] is False
    assert result["label_basis"] == "fixed internally authored regression examples; not dataset labels"
    assert result["scope"] == "current Module C lexical instruction cues only"
    assert len(result["cases"]) == len(CASES)
    assert result["metrics"] == {"tp": 10, "fp": 0, "tn": 16, "fn": 0}
    assert all(set(case) == {
        "case_id", "expected_instruction", "observed_cue_count", "detected", "outcome"
    } for case in result["cases"])
    assert any(case["case_id"] == "perfect_match_score_override" and case["outcome"] == "tp"
               for case in result["cases"])


def test_diagnostic_disclaims_population_or_probability_claims():
    result = run_diagnostic()

    assert any("not independent accuracy evidence" in item for item in result["limitations"])
    assert any("population false-positive rates" in item for item in result["limitations"])
    assert any("probability" in item for item in result["limitations"])
