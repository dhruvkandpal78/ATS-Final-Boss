"""Closed-vocabulary projection for review integrations, never candidate scoring.

No document-derived string, arbitrary worker metadata, image or score crosses
this output boundary. This does not sanitize the original document or prove
that observations from the native worker are true.
"""
from src.app.worker_protocol import validate_analysis_result

REVIEW_ROUTE = "/api/v1/review"
REVIEW_CAPABILITIES = {"review_api_version": "1.0", "review_endpoint": REVIEW_ROUTE,
                       "review_output": "closed_vocabulary_no_source_text"}
CATEGORIES = ("direct_instruction", "keyword_repetition", "keyword_density",
              "semantic_variance", "pdf_structure")
MAX_FINDINGS = 4096


def validate_review_request(payload):
    """Disallow extra directives/URLs/options on this constrained endpoint."""
    if not isinstance(payload, dict) or set(payload) not in ({"text"}, {"filename", "b64"}):
        raise ValueError("Invalid review request fields.")


def project_review(result):
    validate_analysis_result(result)
    if result["policy_version"] != "2.0" or len(result["findings"]) > MAX_FINDINGS:
        raise ValueError("Unsupported review result.")
    observations = {category: {"count": 0, "review_trigger_count": 0} for category in CATEGORIES}
    for finding in result["findings"]:
        category, trigger = finding.get("category"), finding.get("review_trigger")
        if not isinstance(category, str) or category not in observations or type(trigger) is not bool:
            raise ValueError("Unsupported finding contract.")
        if trigger != (category in ("direct_instruction", "keyword_repetition")):
            raise ValueError("Inconsistent finding policy.")
        observations[category]["count"] += 1
        observations[category]["review_trigger_count"] += int(trigger)
    has_trigger = any(item["review_trigger_count"] for item in observations.values())
    if has_trigger != (result["decision"] == "review_recommended"):
        raise ValueError("Inconsistent review decision.")
    if result["decision"] == "no_signals_detected" and (
            result["status"] != "complete" or result["input_mode"] != "pdf" or result["score"] is None or
            any(result["modules"][key]["status"] != "ok" for key in "abc")):
        raise ValueError("Incomplete evidence cannot produce no signals.")
    return {
        "schema_version": "1.0", "analysis_schema_version": "2.0", "policy_version": "2.0",
        "purpose": "human_review_assistance", "input_mode": result["input_mode"],
        "analysis_status": result["status"], "decision": result["decision"],
        "observations": observations,
        "coverage": {
            "modules": {key: result["modules"][key]["status"] for key in ("a", "b", "c")},
            "has_limitations": bool(result["coverage"]["limitations"]),
            "pdf_visibility": "incomplete" if result["input_mode"] == "pdf" else "not_applicable",
        },
        "automatic_rejection_allowed": False, "authenticity_verified": False,
    }
