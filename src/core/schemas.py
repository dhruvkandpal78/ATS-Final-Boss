from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class Finding:
    id: str
    detector: str
    category: str
    severity: str
    explanation: str

@dataclass
class ModuleResult:
    status: str
    score: float
    reason: Optional[str] = None
    findings: List[Finding] = field(default_factory=list)

@dataclass
class CoverageInfo:
    pages_total: int
    pages_analyzed: int
    limitations: List[str] = field(default_factory=list)

@dataclass
class ModelInfo:
    id: str
    calibrated: bool

@dataclass
class TimingInfo:
    total: int

@dataclass
class AnalysisResult:
    state: str
    schema_version: str
    analysis_id: str
    created_at: str
    status: str
    input_mode: str
    model: ModelInfo
    policy_version: str
    decision: str
    reason_codes: List[str]
    coverage: CoverageInfo
    score: float
    score_kind: str
    modules: Dict[str, ModuleResult]
    findings: List[Finding]
    timings_ms: TimingInfo
