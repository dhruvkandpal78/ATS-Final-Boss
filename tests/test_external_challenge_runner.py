"""Unknown service decisions must survive benchmark projection unchanged."""
from types import SimpleNamespace

import pytest

from scripts import run_external_challenge as runner


def observe(monkeypatch, result):
    monkeypatch.setattr(runner, "digest", lambda path: "pinned")
    monkeypatch.setattr(runner, "pdf_text", lambda path: "Ordinary resume text")
    monkeypatch.setattr(runner, "_SERVICE", SimpleNamespace(analyze_pdf=lambda path: result))
    return runner.analyze({"case_id": "1", "source_group": "g1", "family": "A1",
                           "added_attack": True, "pdf_path": "unused", "pdf_sha256": "pinned"})


def test_complete_but_insufficient_decision_is_not_a_miss(monkeypatch):
    row = observe(monkeypatch, {"status": "complete", "decision": "insufficient_evidence",
                               "reason_codes": [], "model_decision": None})
    assert row["status"] == "complete"
    assert row["decision"] == "insufficient_evidence"
    assert row["arms"]["full_policy"]["flagged"] is None
    from src.evaluation.external_challenge import summarize
    report = summarize([row], n_resamples=2)["arms"]["full_policy"]["added_attack"]
    assert report["complete_missed"] == 0
    assert report["insufficient"] == 1


def test_partial_cue_is_not_complete_detection(monkeypatch):
    row = observe(monkeypatch, {"status": "partial", "decision": "review_recommended",
                               "reason_codes": ["direct_instruction_cue"], "model_decision": None})
    assert row["arms"]["full_policy"]["flagged"] is True
    assert row["arms"]["simple_regex"]["flagged"] is None


def test_unknown_service_decision_is_error_not_clean(monkeypatch):
    row = observe(monkeypatch, {"status": "complete", "decision": "cleanish", "reason_codes": []})
    assert row["status"] == "runtime_error"
    assert all(arm["flagged"] is None for arm in row["arms"].values())


def test_frozen_pdf_change_aborts_instead_of_becoming_a_miss(monkeypatch):
    monkeypatch.setattr(runner, "digest", lambda path: "changed")
    with pytest.raises(ValueError, match="Frozen PDF changed"):
        runner.analyze({"pdf_path": "unused", "pdf_sha256": "pinned"})
