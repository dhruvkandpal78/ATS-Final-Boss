"""Selection and abstention accounting for the local controlled stress protocol."""
import fitz
import pytest

from scripts.run_kaggle_stress import (FAMILIES, checked_source, digest, inject, select_sources,
                                      summarize, text_fingerprint)


def source(tmp_path, index, text):
    path = tmp_path / f"source-{index}.pdf"
    with fitz.open() as doc:
        page = doc.new_page()
        page.insert_text((40, 70), text)
        doc.save(path)
    sha = digest(path)
    return {"source_id": f"source:{sha}", "sha256": sha, "pdf_path": path.name}


def test_selection_removes_exposed_and_text_duplicates_before_twenty_percent_rounding(tmp_path):
    records = [source(tmp_path, i, f"Fictional resume {i} for independent selection.") for i in range(14)]
    records.append(source(tmp_path, 20, "Fictional resume 3 for independent selection."))
    selected, exclusions = select_sources(records, tmp_path, {records[0]["source_id"]},
                                         {text_fingerprint("Fictional resume 1 for independent selection.")})
    assert len(selected) == 10
    assert len({r[0]["source_id"] for r in selected}) == 10
    assert len({r[2] for r in selected}) == 10
    assert exclusions["previously_exposed_source"] == 1
    assert exclusions["text_duplicate_of_exposed_source"] == 1
    assert exclusions["duplicate_normalized_text"] == 1
    assert exclusions["exact_twenty_percent_rounding"] == 2
    assert len(selected) // 5 / len(selected) == 0.2


def test_selection_rejects_changed_source_instead_of_using_stale_provenance(tmp_path):
    record = source(tmp_path, 0, "Fictional resume.")
    (tmp_path / record["pdf_path"]).write_bytes(b"%PDF-mutated")
    with pytest.raises(ValueError, match="integrity"):
        select_sources([record], tmp_path, set(), set())


def test_excluded_source_reader_also_rejects_corpus_traversal(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    record = source(tmp_path, 0, "Fictional record outside the declared corpus.")
    record["pdf_path"] = "../" + record["pdf_path"]
    with pytest.raises(ValueError, match="escapes"):
        checked_source(corpus, record)


@pytest.mark.parametrize("family", [f for f in FAMILIES if f not in {"zero_width_direct", "homoglyph_direct"}])
def test_interventions_survive_actual_pdf_extraction(tmp_path, family):
    record = source(tmp_path, 0, "Fictional applicant with ordinary work history.")
    target = tmp_path / "attack.pdf"
    inject(tmp_path / record["pdf_path"], target, family, None)
    with fitz.open(target) as doc:
        assert len(doc) == 2
        assert doc[0].get_text().startswith("Fictional applicant")
        assert doc[1].get_text().strip()


def test_unicode_intervention_requires_real_font_instead_of_silent_replacement(tmp_path):
    record = source(tmp_path, 0, "Fictional applicant.")
    with pytest.raises(ValueError, match="Unicode font"):
        inject(tmp_path / record["pdf_path"], tmp_path / "attack.pdf", "homoglyph_direct", None)


def test_abstentions_are_not_counted_as_detections_or_misses():
    observations = []
    outcomes = [("complete", "review_recommended"), ("partial", "review_recommended"),
                ("complete", "no_signals_detected"), ("partial", "insufficient_evidence"),
                ("runtime_error", "insufficient_evidence")]
    for attack in (False, True):
        for status, decision in outcomes:
            observations.append({"added_attack": attack, "family": "visible_direct" if attack else "unmodified_source",
                                 "status": status, "decision": decision})
    groups = summarize(observations)["groups"]
    for group in (groups["ALL_ATTACKS"], groups["ALL_UNMODIFIED"]):
        assert group["n"] == 5
        assert group["review_complete"] == group["review_partial"] == group["no_signals_complete"] == 1
        assert group["insufficient_evidence"] == group["runtime_error"] == 1
        assert group["review_rate"] == 0.4
    assert groups["white_direct"]["review_rate"] is None
    assert groups["white_direct"]["review_rate_row_wilson_95pct"] is None
