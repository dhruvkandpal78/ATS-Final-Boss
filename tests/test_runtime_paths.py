from pathlib import Path, PurePosixPath
from types import SimpleNamespace

import pytest

from src.core import runtime_paths


def test_packaged_notice_uses_distribution_metadata(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime_paths, "ROOT", tmp_path / "outside")
    notice = tmp_path / "notice.txt"
    notice.write_text("Original notice", encoding="utf-8")
    dist = SimpleNamespace(files=[PurePosixPath("ats_final_boss-0.2.0.dist-info/licenses/LICENSE")],
                           locate_file=lambda entry: notice)
    monkeypatch.setattr(runtime_paths, "distribution", lambda name: dist)
    assert runtime_paths.notice_path("LICENSE").read_text() == "Original notice"
    with pytest.raises(ValueError, match="Unknown public notice"):
        runtime_paths.notice_path("../../credentials")


def test_missing_notice_does_not_select_unrelated_file(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime_paths, "ROOT", tmp_path)
    dist = SimpleNamespace(files=[PurePosixPath("unrelated/LICENSE")])
    monkeypatch.setattr(runtime_paths, "distribution", lambda name: dist)
    with pytest.raises(FileNotFoundError, match="Public notice is unavailable"):
        runtime_paths.notice_path("LICENSE")


def test_operator_model_directory_is_shared_with_cli(tmp_path, monkeypatch):
    from src import inference
    from src.core import analysis_service
    monkeypatch.setenv("ATS_MODELS_DIR", str(tmp_path / "approved"))
    seen = []
    service = SimpleNamespace(analyze_text=lambda text: {"text": text})
    def load(directory):
        seen.append(directory)
        return service
    monkeypatch.setattr(analysis_service, "AnalysisService", load)
    source = tmp_path / "synthetic.txt"
    source.write_text("Synthetic test input", encoding="utf-8")
    assert inference.analyze_file(str(source)) == {"text": "Synthetic test input"}
    assert seen == [str(tmp_path / "approved")]
    monkeypatch.setenv("ATS_MODELS_DIR", "~/approved")
    assert runtime_paths.models_directory() == Path.home() / "approved"
    monkeypatch.setenv("ATS_MODELS_DIR", " ")
    with pytest.raises(ValueError, match="ATS_MODELS_DIR"):
        runtime_paths.models_directory()


def test_local_pinned_bundle_requires_both_pins_and_current_policy(tmp_path, monkeypatch):
    from src.app import server
    from src.core import artifacts, analysis_service
    from src import inference

    monkeypatch.setattr(server, "_SERVICE", None)
    monkeypatch.setenv("ATS_DEPLOYMENT_MODE", "local")
    monkeypatch.setenv("ATS_MODELS_DIR", str(tmp_path))
    monkeypatch.setenv("ATS_CANDIDATE_MANIFEST_SHA256", "a" * 64)
    monkeypatch.delenv("ATS_EMBEDDING_MANIFEST_SHA256", raising=False)
    with pytest.raises(ValueError, match="both candidate and embedding"):
        server.get_service()

    monkeypatch.setenv("ATS_EMBEDDING_MANIFEST_SHA256", "b" * 64)
    monkeypatch.setenv("ATS_EMBEDDING_DIR", str(tmp_path / "embedding"))
    calls = []
    monkeypatch.setattr(artifacts, "verify_candidate", lambda directory, pin: calls.append((directory, pin)) or {})
    monkeypatch.setattr(artifacts, "verify_policy", lambda manifest: calls.append("policy"))
    monkeypatch.setattr(inference, "load_pipeline", lambda *args, **kwargs: calls.append(kwargs) or (1, 2, 3, 4, 5))
    monkeypatch.setattr(analysis_service, "AnalysisService", lambda **kwargs: SimpleNamespace(**kwargs))
    service = server.get_service()
    assert service.candidate_model is True
    assert service.model_id == "candidate-" + "a" * 16
    assert calls[1] == "policy"
    assert calls[2]["expected_manifest_sha256"] == "a" * 64
    assert calls[2]["expected_embedding_manifest_sha256"] == "b" * 64
    monkeypatch.setattr(server, "_SERVICE", None)


def test_private_candidate_rejects_unapproved_research_freeze():
    from src.core.artifacts import require_deployment_approval
    with pytest.raises(ValueError, match="explicitly approved"):
        require_deployment_approval({"deployment_approved": False})
    with pytest.raises(ValueError, match="explicitly approved"):
        require_deployment_approval({})
    require_deployment_approval({"deployment_approved": True})
