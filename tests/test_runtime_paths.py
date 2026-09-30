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
