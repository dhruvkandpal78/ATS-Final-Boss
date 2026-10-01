"""Offline contract checks for the opt-in synthetic-only study runner."""
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("reference_study", Path(__file__).parents[1] / "scripts/run_reference_study.py")
study = importlib.util.module_from_spec(spec)
spec.loader.exec_module(study)


@pytest.mark.parametrize("value", [
    {"score": True, "needs_review": False, "audit_marker": ""},
    {"score": 101, "needs_review": False, "audit_marker": ""},
    {"score": 5, "needs_review": "false", "audit_marker": ""},
    {"score": 5, "needs_review": False, "audit_marker": "x" * 129},
    {"score": 5, "needs_review": False, "audit_marker": "", "extra": 0},
])
def test_invalid_model_outputs_fail_closed(value):
    with pytest.raises(ValueError):
        study.validate_output(value)


class Response:
    def __init__(self, code, raw):
        self.status_code, self.raw = code, raw

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def iter_content(self, size):
        yield self.raw


class Session:
    def __init__(self, response):
        self.response, self.headers, self.calls = response, {}, []

    def post(self, endpoint, **kwargs):
        self.calls.append((endpoint, kwargs))
        return self.response


def client(monkeypatch, tmp_path, response):
    import requests
    session = Session(response)
    monkeypatch.setattr(requests, "Session", lambda: session)
    monkeypatch.setattr(study.time, "sleep", lambda _: None)
    return study.Screener("fictional-test-credential", tmp_path), session


def test_provider_limit_stops_without_retry(monkeypatch, tmp_path):
    runner, session = client(monkeypatch, tmp_path, Response(429, b""))
    assert runner.run("fictional")[2] == "http_429"
    assert runner.run("fictional")[2] == "budget_or_provider_stop"
    assert len(session.calls) == 1
    assert session.calls[0][0] == study.ENDPOINT
    assert session.calls[0][1]["allow_redirects"] is False


@pytest.mark.parametrize("response", [
    Response(200, b"x" * 65537),
    Response(200, b'{"usage":{"total_tokens":12},"model":"other","choices":[{"finish_reason":"stop"}]}'),
    Response(200, b'{"usage":{"total_tokens":12},"model":"openai/gpt-oss-120b","choices":[{"finish_reason":"length"}]}'),
])
def test_bad_responses_do_not_become_completions(monkeypatch, tmp_path, response):
    runner, _ = client(monkeypatch, tmp_path, response)
    result, _, error = runner.run("fictional")
    assert result is None and error is not None
    assert not list(tmp_path.iterdir())


def test_success_preserves_provenance_without_credential(monkeypatch, tmp_path):
    output = {"score": 45, "needs_review": False, "audit_marker": ""}
    response = Response(200, json.dumps({"usage": {"total_tokens": 12}, "model": study.MODEL,
        "system_fingerprint": "provider-fingerprint", "choices": [{"finish_reason": "stop",
        "message": {"content": json.dumps(output)}}]}).encode())
    runner, _ = client(monkeypatch, tmp_path, response)
    assert runner.run("fictional")[0] == output
    saved = (tmp_path / "response-001.json").read_text()
    assert "provider-fingerprint" in saved and "fictional-test-credential" not in saved


def test_request_budget_stops_before_network(monkeypatch, tmp_path):
    runner, session = client(monkeypatch, tmp_path, Response(200, b""))
    runner.calls = 48
    assert runner.run("fictional")[0] is None
    assert not session.calls


def test_token_reservation_stops_before_network(monkeypatch, tmp_path):
    runner, session = client(monkeypatch, tmp_path, Response(200, b""))
    runner.tokens = 70001
    assert runner.run("fictional")[0] is None
    assert not session.calls


def test_each_family_order_is_counterbalanced():
    for family in range(len(study.VARIANTS)):
        first = [study.arm_order(group * len(study.VARIANTS) + family)[0] for group in range(4)]
        assert first.count("baseline") == first.count("protected") == 2


def test_key_outside_ignored_directory_is_rejected(monkeypatch, tmp_path):
    monkeypatch.setattr(study, "ROOT", tmp_path / "checkout")
    path = tmp_path / "key.txt"
    path.write_text("gsk_fictionalcredential12345")
    with pytest.raises(ValueError):
        study.read_key(path)


def test_provider_fingerprint_variation_is_preserved(monkeypatch, tmp_path):
    response = Response(200, json.dumps({"system_fingerprint": "new-fingerprint"}).encode())
    runner, session = client(monkeypatch, tmp_path, response)
    runner.fingerprint, runner.fingerprint_seen = "old-fingerprint", True
    assert runner.run("fictional")[0] is None
    assert runner.fingerprints == {"new-fingerprint"}
    assert runner.fingerprint == "new-fingerprint"
    assert len(session.calls) == 1


def test_study_manifest_does_not_reapprove_original(tmp_path):
    from src.core.artifacts import FILES, FEATURE_ORDER, verify_candidate, verify_policy
    source = tmp_path / "original"
    source.mkdir()
    hashes = {}
    for name in FILES:
        raw = ("test-only-" + name).encode()
        (source / name).write_bytes(raw)
        hashes[name] = study.digest(raw)
    manifest = {"schema_version": "1.0", "kind": "real_pdf_candidate", "input_mode": "pdf",
        "feature_order": FEATURE_ORDER, "artifacts": hashes, "validation_metrics": {"old": 1},
        "policy": {"version": "stale"}}
    original_bytes = json.dumps(manifest).encode()
    (source / "candidate_manifest.json").write_bytes(original_bytes)
    output = tmp_path / "study"
    study.freeze_study_bundle(source, output)
    assert (source / "candidate_manifest.json").read_bytes() == original_bytes
    assert (output / "original-candidate" / "candidate_manifest.json").read_bytes() == original_bytes
    current = json.loads((output / "study_manifest.json").read_text())
    verify_policy(current)
    assert current["kind"] == "synthetic_reference_study"
    assert current["study_lineage"]["deployment_approved"] is False
    assert "validation_metrics" not in current
    with pytest.raises(FileNotFoundError):
        verify_candidate(output)
    with pytest.raises(ValueError):
        verify_policy(manifest)
