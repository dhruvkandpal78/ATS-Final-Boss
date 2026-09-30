"""Git publication guard tests use isolated temporary repositories and fake data."""
from __future__ import annotations

import subprocess
from pathlib import Path
import tempfile

import pytest

from scripts.check_release_payload import validate_range


@pytest.fixture
def synthetic_root():
    # Keep fake Git trees in the authorized workspace; the host temp directory
    # may be unavailable in the restricted Windows test runner.
    project_root = Path(__file__).resolve().parents[1]
    test_root = project_root / ".test-tmp"
    test_root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="release-payload-", dir=test_root) as path:
        yield Path(path)


def git(repo: Path, *args: str, input_bytes: bytes | None = None) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], input=input_bytes,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if result.returncode:
        pytest.fail(result.stderr.decode("utf-8", "replace"))
    return result.stdout.decode("utf-8", "replace").strip()


def make_repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "Synthetic Test")
    git(repo, "config", "user.email", "synthetic@example.invalid")
    (repo / "README.md").write_text("synthetic fixture\n", encoding="utf-8")
    git(repo, "add", "README.md")
    git(repo, "commit", "-qm", "base")
    return repo, git(repo, "rev-parse", "HEAD")


def commit_all(repo: Path, message: str) -> None:
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", message)


def test_clean_text_change_passes(synthetic_root):
    repo, base = make_repo(synthetic_root)
    (repo / "docs" ).mkdir()
    (repo / "docs" / "notes.md").write_text("ordinary documentation\n", encoding="utf-8")
    commit_all(repo, "docs")
    assert validate_range(repo, base) == []


@pytest.mark.parametrize("path", [
    "resume.pdf", "models.pkl", "data/synthetic.csv", "results/output.json",
    "results/candidates/model.bin", "PROJECTS FOR CV/sample.txt", "capture.webm",
    ".env", ".env.production", "secrets/api.conf", "private-key.pem",
])
def test_prohibited_paths_are_rejected_without_opening_content(synthetic_root, path):
    repo, base = make_repo(synthetic_root)
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"-----BEGIN " + b"PRIVATE KEY----- synthetic placeholder")
    commit_all(repo, "synthetic restricted path")
    violations = validate_range(repo, base)
    assert any(path in item for item in violations)
    assert not any("credential pattern" in item for item in violations)


def test_deleted_personal_pdf_from_base_is_allowed(synthetic_root):
    repo = synthetic_root / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "Synthetic Test")
    git(repo, "config", "user.email", "synthetic@example.invalid")
    (repo / "resume.pdf").write_bytes(b"fake fixture bytes")
    (repo / "README.md").write_text("synthetic fixture\n", encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "base with pre-existing personal sample")
    base = git(repo, "rev-parse", "HEAD")
    (repo / "resume.pdf").unlink()
    commit_all(repo, "remove pre-existing sample")
    assert validate_range(repo, base) == []


def test_add_then_remove_prohibited_blob_still_fails_outgoing_history(synthetic_root):
    repo, base = make_repo(synthetic_root)
    (repo / "data").mkdir()
    (repo / "data" / "transient.txt").write_text("synthetic only", encoding="utf-8")
    commit_all(repo, "add prohibited synthetic path")
    (repo / "data" / "transient.txt").unlink()
    (repo / "data").rmdir()
    commit_all(repo, "remove transient file")
    assert any("outgoing path" in item and "data/transient.txt" in item for item in validate_range(repo, base))


def test_secret_added_then_removed_is_scanned_without_echoing_secret(synthetic_root):
    repo, base = make_repo(synthetic_root)
    secret = "ghp_" + "A" * 36
    (repo / "notes.md").write_text(f"synthetic placeholder {secret}\n", encoding="utf-8")
    commit_all(repo, "synthetic token mistake")
    (repo / "notes.md").unlink()
    commit_all(repo, "remove token mistake")
    violations = validate_range(repo, base)
    assert any("GitHub token" in item for item in violations)
    assert all(secret not in item for item in violations)


def test_symlink_git_mode_is_rejected(synthetic_root):
    repo, base = make_repo(synthetic_root)
    target_blob = git(repo, "hash-object", "-w", "--stdin", input_bytes=b"synthetic-target")
    git(repo, "update-index", "--add", "--cacheinfo", f"120000,{target_blob},link.txt")
    git(repo, "commit", "-qm", "synthetic symlink")
    assert any("symlink" in item and "link.txt" in item for item in validate_range(repo, base))


@pytest.mark.parametrize("payload,expected", [
    (b"-----BEGIN " + b"OPENSSH PRIVATE KEY-----\nsynthetic\n", "private key"),
    (b"ghp_" + b"B" * 40, "GitHub token"),
    (b"sk-proj-" + b"C" * 40, "OpenAI token"),
])
def test_credential_patterns_are_reported_without_content(synthetic_root, payload, expected):
    repo, base = make_repo(synthetic_root)
    (repo / "config.md").write_bytes(b"placeholder\n" + payload)
    commit_all(repo, "synthetic credential pattern")
    violations = validate_range(repo, base)
    assert any(expected in item for item in violations)
    assert all(payload.decode("utf-8", "replace") not in item for item in violations)
