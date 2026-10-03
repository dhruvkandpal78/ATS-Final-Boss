"""Offline authored regression checks for Module C's current lexical rules."""
import pytest

from src.modules import module_c
from src.core.evidence import instruction_spans
from scripts.check_instruction_regressions import CASES, QUALITY_REVIEW_CASES, run_diagnostic


def test_diagnostic_uses_fixed_cases_without_initializing_model(monkeypatch):
    def forbidden_model_init(*args, **kwargs):
        raise AssertionError("instruction regression diagnostic must not load a model")

    monkeypatch.setattr(module_c, "SentenceTransformer", forbidden_model_init)
    result = run_diagnostic()

    assert result["model_inference"] is False
    assert result["label_basis"] == "fixed internally authored regression examples; not dataset labels"
    assert result["scope"] == "current Module C lexical instruction cues only"
    assert len(result["cases"]) == len(CASES)
    assert result["metrics"] == {"tp": 18, "fp": 0, "tn": 22, "fn": 0}
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


@pytest.mark.parametrize("case_id,text,attack", QUALITY_REVIEW_CASES)
def test_reviewed_qualification_scope_agrees_with_explanation_and_source(case_id, text, attack):
    scorer = object.__new__(module_c.SemanticCoherenceScorer)
    assert (scorer._injection_signal(text) > 0) == attack
    assert (scorer._injection_cue_for_sentence(text) is not None) == attack
    assert bool(instruction_spans(text, scorer)) == attack
