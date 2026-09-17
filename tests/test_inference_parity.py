import pytest
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.core.analysis_service import AnalysisService

def test_inference_parity():
    service = AnalysisService("results/models")
    
    text = "John Doe is a great software engineer."
    
    # 1. API simulate
    res_api = service.analyze_text(text, b_score=0.0)
    
    # 2. Assert values
    assert 'policy_proba' in res_api
    assert 'model_proba' in res_api
    assert res_api['policy_proba'] >= 0.0
