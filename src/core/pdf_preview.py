"""Bounded, in-memory PDF evidence previews; no upload is retained."""
import base64
import math

import fitz


def build_evidence_previews(path, findings):
    previews = []
    used = 0
    with fitz.open(path) as document:
        pages = sorted({f.get("anchor", {}).get("page_index") for f in findings
                        if type(f.get("anchor", {}).get("page_index")) is int})[:3]
        for index in pages:
            if not 0 <= index < len(document):
                continue
            page = document[index]
            scale = min(1.5, 900 / max(page.rect.width, page.rect.height))
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            raw = pix.tobytes("png")
            if used + len(raw) > 2 * 1024 * 1024:
                break
            used += len(raw)
            regions = []
            for finding in findings:
                anchor = finding.get("anchor", {})
                box = anchor.get("bbox")
                if anchor.get("page_index") != index or not isinstance(box, list) or len(box) != 4:
                    continue
                if not all(isinstance(x, (int, float)) and math.isfinite(x) for x in box):
                    continue
                rectangle = fitz.Rect(box) * page.rotation_matrix
                rectangle &= page.rect
                if rectangle.is_empty or rectangle.is_infinite:
                    continue
                regions.append({"finding_id": finding["id"], "box": [
                    rectangle.x0 / page.rect.width * 100, rectangle.y0 / page.rect.height * 100,
                    rectangle.width / page.rect.width * 100, rectangle.height / page.rect.height * 100]})
            previews.append({"page_index": index, "width": pix.width, "height": pix.height,
                             "image_url": "data:image/png;base64," + base64.b64encode(raw).decode("ascii"),
                             "regions": regions})
    return previews
