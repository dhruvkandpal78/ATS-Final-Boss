import pytest
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.inference import load_pipeline

def test_pipeline_loading():
    # Just verify that the pipeline can load without crashing
    models_dir = os.path.join(os.path.dirname(__file__), "..", "results", "models")
    if os.path.exists(models_dir):
        META_CLF, SCALER, MOD_A, MOD_B, MOD_C = load_pipeline(models_dir)
        assert META_CLF is not None
        assert MOD_A is not None
        assert MOD_B is not None
        assert MOD_C is not None
        # Verify configs were loaded
        assert MOD_A.threshold is not None
        assert MOD_C.variance_threshold is not None
