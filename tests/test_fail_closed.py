"""Missing model artifacts must never create a substitute detector."""
import pytest

from src.app import server
from src.inference import load_pipeline


def test_loader_missing_artifacts_fails_before_semantic_model_load(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_pipeline(tmp_path)


def test_service_missing_artifacts_does_not_cache_fallback(tmp_path, monkeypatch):
    monkeypatch.setenv("ATS_DEPLOYMENT_MODE", "local")
    monkeypatch.setattr(server, "models_directory", lambda: tmp_path)
    monkeypatch.setattr(server, "_SERVICE", None)
    with pytest.raises(FileNotFoundError):
        server.get_service()
    assert server._SERVICE is None
