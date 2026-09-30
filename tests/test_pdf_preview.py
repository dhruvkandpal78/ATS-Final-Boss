import base64

import fitz
import pytest

from src.core.pdf_preview import build_evidence_previews


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_bounded_preview_with_transformed_source_region(tmp_path, rotation):
    path = tmp_path / "sample.pdf"
    with fitz.open() as doc:
        page = doc.new_page(width=600, height=800)
        page.insert_text((72, 72), "Synthetic evidence")
        page.set_rotation(rotation)
        doc.save(path)
    findings = [{"id": "b1", "anchor": {"page_index": 0, "bbox": [72, 60, 180, 80]}}]
    result = build_evidence_previews(path, findings)
    assert len(result) == 1
    preview = result[0]
    assert max(preview["width"], preview["height"]) <= 900
    assert base64.b64decode(preview["image_url"].split(",")[1]).startswith(b"\x89PNG")
    region = preview["regions"][0]["box"]
    assert all(0 <= value <= 100 for value in region)
    assert region[2] > 0 and region[3] > 0
    assert build_evidence_previews(path, []) == []
