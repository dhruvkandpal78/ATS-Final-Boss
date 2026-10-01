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


def validate_review_response(value):
    """Strict consumer contract; never trust arbitrary JSON from an endpoint."""
    expected = {"schema_version", "analysis_schema_version", "policy_version", "purpose", "input_mode",
                "analysis_status", "decision", "observations", "coverage",
                "automatic_rejection_allowed", "authenticity_verified"}
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError("Invalid review response fields.")
    if (value["schema_version"] != "1.0" or value["analysis_schema_version"] != "2.0" or
            value["policy_version"] != "2.0" or value["purpose"] != "human_review_assistance" or
            value["input_mode"] not in ("text", "pdf") or
            value["analysis_status"] not in ("complete", "partial", "unscorable") or
            value["decision"] not in ("no_signals_detected", "review_recommended", "insufficient_evidence") or
            value["automatic_rejection_allowed"] is not False or value["authenticity_verified"] is not False):
        raise ValueError("Unsupported review response.")
    observations = value["observations"]
    if not isinstance(observations, dict) or set(observations) != set(CATEGORIES):
        raise ValueError("Invalid review categories.")
    total = triggers = 0
    for category, counts in observations.items():
        if not isinstance(counts, dict) or set(counts) != {"count", "review_trigger_count"}:
            raise ValueError("Invalid observation fields.")
        count, trigger = counts["count"], counts["review_trigger_count"]
        if type(count) is not int or type(trigger) is not int or not 0 <= trigger <= count <= MAX_FINDINGS:
            raise ValueError("Invalid bounded observation counts.")
        if trigger != (count if category in ("direct_instruction", "keyword_repetition") else 0):
            raise ValueError("Inconsistent observation policy.")
        total += count
        triggers += trigger
    coverage = value["coverage"]
    if total > MAX_FINDINGS or bool(triggers) != (value["decision"] == "review_recommended"):
        raise ValueError("Inconsistent review decision.")
    if not isinstance(coverage, dict) or set(coverage) != {"modules", "has_limitations", "pdf_visibility"}:
        raise ValueError("Invalid review coverage.")
    if (not isinstance(coverage["modules"], dict) or set(coverage["modules"]) != {"a", "b", "c"} or
            any(status not in ("ok", "not_applicable", "unsupported", "error") for status in coverage["modules"].values()) or
            type(coverage["has_limitations"]) is not bool or
            coverage["pdf_visibility"] != ("incomplete" if value["input_mode"] == "pdf" else "not_applicable")):
        raise ValueError("Unsupported review coverage.")
    modules = coverage["modules"]
    if (value["analysis_status"] == "complete" and (value["input_mode"] != "pdf" or any(s != "ok" for s in modules.values())) or
            value["input_mode"] == "text" and (value["analysis_status"] != "partial" or modules["b"] != "not_applicable") or
            value["input_mode"] == "pdf" and modules["b"] == "not_applicable" or
            value["analysis_status"] == "unscorable" and (triggers or value["decision"] != "insufficient_evidence")):
        raise ValueError("Inconsistent analysis coverage.")
    if value["decision"] == "no_signals_detected" and (value["analysis_status"] != "complete" or
            value["input_mode"] != "pdf" or any(status != "ok" for status in coverage["modules"].values())):
        raise ValueError("Incomplete evidence cannot produce no signals.")


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
