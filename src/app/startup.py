"""Synthetic startup probes exercise the actual detector and PDF paths."""
import base64
import math

WARMUP_TEXT = (
    "Synthetic system readiness verifies document processing. "
    "This harmless text exercises semantic encoding. "
    "The service should return complete text detector coverage."
)


def warmup_pdf_payload():
    import fitz
    with fitz.open() as document:
        page = document.new_page()
        page.insert_textbox(fitz.Rect(50, 50, 540, 750), WARMUP_TEXT, fontsize=12)
        encoded = base64.b64encode(document.tobytes()).decode("ascii")
    return {"filename": "synthetic-startup.pdf", "b64": encoded}


def require_warmup_result(result, *, pdf=False):
    if not isinstance(result, dict) or not isinstance(result.get("modules"), dict):
        raise ValueError("Startup probe did not return detector coverage")
    for name in ("a", "b", "c") if pdf else ("a", "c"):
        module = result["modules"].get(name, {})
        score = module.get("score")
        if (module.get("status") != "ok" or isinstance(score, bool) or
                not isinstance(score, (int, float)) or not math.isfinite(score) or not 0 <= score <= 1):
            raise ValueError("Startup detector probe failed")
    if pdf:
        score = result.get("score")
        if (result.get("status") != "complete" or isinstance(score, bool) or
                not isinstance(score, (int, float)) or not math.isfinite(score) or not 0 <= score <= 1):
            raise ValueError("Startup PDF classifier probe failed")
