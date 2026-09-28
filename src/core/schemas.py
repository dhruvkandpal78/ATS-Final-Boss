"""The versioned, JSON-compatible result contract shared by all adapters."""

from typing import Any, Dict, List, Literal, Optional, TypedDict


Decision = Literal["no_signals_detected", "review_recommended", "insufficient_evidence"]
ModuleStatus = Literal["ok", "not_applicable", "unsupported", "error"]


class Anchor(TypedDict):
    page_index: Optional[int]
    char_start: Optional[int]
    char_end: Optional[int]
    bbox: Optional[List[float]]


class Finding(TypedDict):
    id: str
    detector: str
    category: str
    severity: str
    explanation_method: str
    explanation: str
    anchor: Anchor
    uncertainty: str


class ModuleResult(TypedDict, total=False):
    name: str
    sub: str
    desc: str
    status: ModuleStatus
    score: Optional[float]
    reason: Optional[str]
    evidence_ids: List[str]
    capabilities: Dict[str, bool]


class CoverageInfo(TypedDict):
    pages_total: Optional[int]
    pages_analyzed: Optional[int]
    limitations: List[str]


class AnalysisResult(TypedDict, total=False):
    schema_version: Literal["2.0"]
    analysis_id: str
    created_at: str
    status: Literal["complete", "partial", "unscorable"]
    input_mode: Literal["text", "pdf"]
    model: Dict[str, Any]
    policy_version: str
    score: Optional[float]
    score_kind: Literal["model_score", "calibrated_probability", "unavailable"]
    decision: Decision
    reason_codes: List[str]
    coverage: CoverageInfo
    modules: Dict[str, ModuleResult]
    findings: List[Finding]
    timings_ms: Dict[str, float]
