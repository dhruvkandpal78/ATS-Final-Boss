"""Synthetic PDFs exercise the experimental raster comparison without models."""

import fitz
import pytest

from src.research import pdf_visibility


def _save_pdf(path, paint):
    with fitz.open() as document:
        page = document.new_page(width=300, height=200)
        paint(page)
        document.save(path)
    return path


def _flags(result):
    return {flag for observation in result["observations"] for flag in observation["flags"]}


def test_visible_black_text_has_raster_contrast(tmp_path):
    path = _save_pdf(tmp_path / "visible.pdf", lambda page: page.insert_text((40, 80), "Visible sample", fontsize=24))
    result = pdf_visibility.inspect_pdf_visibility(path)
    assert result["status"] == "complete"
    assert result["coverage"]["traces_examined"] >= 1
    assert result["coverage"]["regions_sampled"] >= 1
    assert "flat_rendered_region" not in _flags(result)
    assert result["capabilities"]["pixel_region_inspection"] is True
    assert result["capabilities"]["ocr"] is False
    assert "score" not in result and "probability" not in result


@pytest.mark.parametrize("paint", [
    lambda page: page.insert_text((40, 80), "White sample", fontsize=24, color=(1, 1, 1)),
    lambda page: (page.insert_text((40, 80), "Covered sample", fontsize=24),
                  page.draw_rect(fitz.Rect(30, 50, 280, 95), color=(1, 1, 1), fill=(1, 1, 1), overlay=True)),
])
def test_flat_rendered_region_is_review_observation(tmp_path, paint):
    path = _save_pdf(tmp_path / "flat.pdf", paint)
    result = pdf_visibility.inspect_pdf_visibility(path)
    assert result["status"] == "complete"
    assert "flat_rendered_region" in _flags(result)
    assert all("intent" in item["interpretation"] for item in result["observations"])


def test_traceless_page_has_partial_coverage_and_no_text_observation(tmp_path):
    path = _save_pdf(tmp_path / "traceless.pdf", lambda page: page.draw_rect(
        fitz.Rect(40, 50, 250, 130), color=(0, 0, 0), fill=(0, 0, 0)))
    result = pdf_visibility.inspect_pdf_visibility(path)
    assert result["status"] == "partial"
    assert result["coverage"]["traces_examined"] == 0
    assert result["observations"] == []
    assert any("not OCRed" in text for text in result["limitations"])
    assert any("no text traces" in text for text in result["limitations"])


def test_file_and_page_limits_are_enforced_before_rendering(tmp_path):
    oversized = tmp_path / "oversized.pdf"
    oversized.write_bytes(b"%PDF-" + b"x" * pdf_visibility.MAX_FILE_BYTES)
    assert pdf_visibility.inspect_pdf_visibility(oversized)["error"] == "PDF exceeds the 5 MiB limit."

    many_pages = tmp_path / "many-pages.pdf"
    with fitz.open() as document:
        for _ in range(pdf_visibility.MAX_PAGES + 1):
            document.new_page(width=100, height=100)
        document.save(many_pages)
    result = pdf_visibility.inspect_pdf_visibility(many_pages)
    assert result["status"] == "error"
    assert result["coverage"]["pages_rendered"] == 0


def test_render_and_crop_budgets_mark_partial_coverage(tmp_path, monkeypatch):
    path = tmp_path / "bounded.pdf"
    with fitz.open() as document:
        for _ in range(2):
            page = document.new_page(width=200, height=200)
            page.insert_text((20, 80), "Bounded sample", fontsize=18)
        document.save(path)
    monkeypatch.setattr(pdf_visibility, "MAX_PAGE_PIXELS", 100)
    monkeypatch.setattr(pdf_visibility, "MAX_TOTAL_PIXELS", 150)
    monkeypatch.setattr(pdf_visibility, "MAX_CROPS", 0)
    result = pdf_visibility.inspect_pdf_visibility(path)
    assert result["status"] == "partial"
    assert result["coverage"]["pages_rendered"] <= 1
    assert result["coverage"]["rendered_pixels"] <= 150
    assert result["coverage"]["regions_sampled"] == 0
    assert any("budget" in text for text in result["limitations"])


def test_observations_and_trace_count_are_bounded(tmp_path, monkeypatch):
    path = _save_pdf(tmp_path / "traces.pdf", lambda page: (
        page.insert_text((20, 50), "First invisible", fontsize=18, color=(1, 1, 1)),
        page.insert_text((20, 90), "Second invisible", fontsize=18, color=(1, 1, 1))))
    monkeypatch.setattr(pdf_visibility, "MAX_OBSERVATIONS", 1)
    result = pdf_visibility.inspect_pdf_visibility(path)
    assert len(result["observations"]) == 1
    assert result["coverage"]["observations_omitted"] >= 1
    monkeypatch.setattr(pdf_visibility, "MAX_TRACES", 1)
    result = pdf_visibility.inspect_pdf_visibility(path)
    assert result["status"] == "partial"
    assert len(result["observations"]) <= 1
    assert any("trace budget" in text for text in result["limitations"])
