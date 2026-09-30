"""Experimental, bounded comparison of PDF text traces with rendered page ink.

This is a review aid, not a detector of intent or a model feature. A flat raster
region can result from white text, occlusion, clipping, or ordinary PDF behavior.
"""

from __future__ import annotations

import math
from pathlib import Path

import fitz
import numpy as np


MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_PAGES = 20
MAX_PAGE_PIXELS = 2_000_000
MAX_TOTAL_PIXELS = 20_000_000
MAX_TRACES = 20_000
MAX_CROPS = 1_000
MAX_CROP_PIXELS = 100_000
MAX_TOTAL_CROP_PIXELS = 20_000_000
MAX_OBSERVATIONS = 200
FLAT_CONTRAST_RANGE = 24

CAPABILITIES = {"pixel_region_inspection": True, "ocr": False,
                "model_feature": False, "policy_integration": False}
LIMITATIONS = [
    "Experimental region sampling does not establish whether a person can read the text or why a region appears flat.",
    "Overlapping objects, clipping, transparency, complex optional-content groups, and font antialiasing can change the rendered result.",
    "Image-only pages are not OCRed; text omitted from PDF traces cannot be assessed.",
    "PyMuPDF materializes a page's text traces before the 20,000-trace iteration limit is applied.",
    "This standalone research check is not a process sandbox for untrusted PDFs.",
    "This check is bounded and incomplete; it makes no completeness or manipulation claim.",
]


def _result(status, observations, coverage, limitations, error=None):
    result = {"status": status, "capabilities": dict(CAPABILITIES),
              "observations": observations, "coverage": coverage,
              "limitations": list(dict.fromkeys(limitations))}
    if error is not None:
        result["error"] = error
    return result


def _has_visible_characters(trace):
    for item in trace.get("chars", ()):
        if not item:
            continue
        code = item[0]
        if isinstance(code, int) and 0 < code <= 0x10FFFF and not chr(code).isspace():
            return True
    return False


def _trace_rect(trace):
    coords = trace.get("bbox")
    if not isinstance(coords, (tuple, list)) or len(coords) != 4:
        return None
    if not all(isinstance(value, (int, float)) and math.isfinite(value) for value in coords):
        return None
    return fitz.Rect(coords)


def _pixel_box(rect, page_rect, width, height):
    clipped = rect & page_rect
    if clipped.is_empty or clipped.is_infinite:
        return None
    x0 = max(0, min(width, math.floor((clipped.x0 - page_rect.x0) * width / page_rect.width)))
    y0 = max(0, min(height, math.floor((clipped.y0 - page_rect.y0) * height / page_rect.height)))
    x1 = max(0, min(width, math.ceil((clipped.x1 - page_rect.x0) * width / page_rect.width)))
    y1 = max(0, min(height, math.ceil((clipped.y1 - page_rect.y0) * height / page_rect.height)))
    return (x0, y0, x1, y1) if x1 > x0 and y1 > y0 else None


def inspect_pdf_visibility(pdf_path):
    """Return bounded, content-free visibility observations for one local PDF."""
    coverage = {"pages_total": None, "pages_rendered": 0, "traces_examined": 0,
                "regions_sampled": 0, "rendered_pixels": 0, "sampled_pixels": 0,
                "observations_omitted": 0}
    observations = []
    limitations = list(LIMITATIONS)
    try:
        if Path(pdf_path).stat().st_size > MAX_FILE_BYTES:
            return _result("error", [], coverage, limitations, "PDF exceeds the 5 MiB limit.")
        with fitz.open(pdf_path) as document:
            coverage["pages_total"] = len(document)
            if document.needs_pass:
                return _result("error", [], coverage, limitations, "Encrypted PDF is unsupported.")
            if not 0 < len(document) <= MAX_PAGES:
                return _result("error", [], coverage, limitations, "PDF page count is outside the supported limit.")

            def observe(page_index, rect, flags, contrast_range=None):
                item = {"page_index": page_index, "bbox": [round(value, 2) for value in rect],
                        "flags": flags, "interpretation": "Review the original PDF; this is not evidence of intent."}
                if contrast_range is not None:
                    item["rendered_contrast_range"] = contrast_range
                if len(observations) < MAX_OBSERVATIONS:
                    observations.append(item)
                else:
                    coverage["observations_omitted"] += 1

            truncated = False
            incomplete = False
            for page_index, page in enumerate(document):
                if page.rotation != 0:
                    limitations.append("Rotated pages were skipped because text and raster coordinates may differ.")
                    incomplete = True
                    continue
                page_rect = page.rect
                if not all(math.isfinite(value) for value in page_rect) or page_rect.width <= 0 or page_rect.height <= 0:
                    limitations.append("Pages with invalid dimensions were skipped.")
                    incomplete = True
                    continue
                scale = min(2.0, math.sqrt((MAX_PAGE_PIXELS * 0.95) / (page_rect.width * page_rect.height)))
                estimated = math.ceil(page_rect.width * scale) * math.ceil(page_rect.height * scale)
                if estimated > MAX_PAGE_PIXELS or coverage["rendered_pixels"] + estimated > MAX_TOTAL_PIXELS:
                    limitations.append("Rendering stopped at the page or total pixel budget.")
                    truncated = True
                    break
                pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), colorspace=fitz.csGRAY, alpha=False)
                pixels = pixmap.width * pixmap.height
                if pixels > MAX_PAGE_PIXELS or coverage["rendered_pixels"] + pixels > MAX_TOTAL_PIXELS:
                    limitations.append("Rendering stopped at the page or total pixel budget.")
                    truncated = True
                    break
                raster = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(pixmap.height, pixmap.stride)[:, :pixmap.width]
                coverage["pages_rendered"] += 1
                coverage["rendered_pixels"] += pixels

                traces = page.get_texttrace()
                if not traces:
                    limitations.append("A page had no text traces; OCR and text visibility comparison were unavailable.")
                    incomplete = True
                for trace in traces:
                    if coverage["traces_examined"] >= MAX_TRACES:
                        limitations.append("Text trace inspection stopped at the trace budget.")
                        truncated = True
                        break
                    coverage["traces_examined"] += 1
                    if not _has_visible_characters(trace):
                        continue
                    rect = _trace_rect(trace)
                    if rect is None:
                        limitations.append("Text traces with invalid bounding boxes were skipped.")
                        incomplete = True
                        continue
                    flags = []
                    if rect.width * rect.height <= 0.01:
                        flags.append("zero_area_text_trace")
                    if (rect.x1 <= page_rect.x0 or rect.y1 <= page_rect.y0 or
                            rect.x0 >= page_rect.x1 or rect.y0 >= page_rect.y1):
                        flags.append("off_page_text_trace")
                    if isinstance(trace.get("size"), (int, float)) and trace["size"] <= 1.5:
                        flags.append("tiny_text_trace")
                    if trace.get("type") == 3 or trace.get("opacity") == 0:
                        flags.append("invisible_text_trace")
                    if "off_page_text_trace" in flags or "zero_area_text_trace" in flags:
                        observe(page_index, rect, flags)
                        continue
                    box = _pixel_box(rect, page_rect, pixmap.width, pixmap.height)
                    if box is None:
                        if flags:
                            observe(page_index, rect, flags)
                        continue
                    x0, y0, x1, y1 = box
                    crop_pixels = (x1 - x0) * (y1 - y0)
                    if (crop_pixels > MAX_CROP_PIXELS or coverage["regions_sampled"] >= MAX_CROPS or
                            coverage["sampled_pixels"] + crop_pixels > MAX_TOTAL_CROP_PIXELS):
                        limitations.append("Some text regions were skipped at the crop budget.")
                        incomplete = True
                        if flags:
                            observe(page_index, rect, flags)
                        continue
                    crop = raster[y0:y1, x0:x1]
                    contrast_range = int(crop.max()) - int(crop.min())
                    coverage["regions_sampled"] += 1
                    coverage["sampled_pixels"] += crop_pixels
                    if contrast_range <= FLAT_CONTRAST_RANGE:
                        flags.append("flat_rendered_region")
                    if flags:
                        observe(page_index, rect, flags, contrast_range)
                if truncated:
                    break
        status = "partial" if (truncated or incomplete or coverage["observations_omitted"] or
                               coverage["pages_rendered"] < coverage["pages_total"]) else "complete"
        return _result(status, observations, coverage, limitations)
    except Exception:
        return _result("error", [], coverage, limitations, "PDF visibility inspection could not complete.")
