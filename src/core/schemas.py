from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Any

@dataclass
class ModuleAData:
    score: float
    density: float
    is_flagged: bool

@dataclass
class ModuleBData:
    score: float
    is_flagged: bool
    details: Dict[str, Any]

@dataclass
class SentenceData:
    sentence: str
    heat: float
    contribution: float
    injection_cue: Optional[str] = None

@dataclass
class ModuleCData:
    score: float
    variance: float
    injection_cues: int
    is_flagged: bool
    sentences: List[SentenceData]

@dataclass
class AnalysisResult:
    timestamp: str
    input_mode: str
    features: Dict[str, float]
    model_decision: bool
    model_proba: float
    policy_decision: bool
    policy_proba: float
    module_a: ModuleAData
    module_b: ModuleBData
    module_c: ModuleCData
    schema_version: str = "1.0.0"
    policy_threshold: float = 0.5
    
    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)
