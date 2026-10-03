"""Safety and manifest-contract tests for the external HiringAudit acquisition."""

import importlib.util
import json
from pathlib import Path
import zipfile

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "acquire_hiringaudit.py"
SPEC = importlib.util.spec_from_file_location("acquire_hiringaudit", SCRIPT)
assert SPEC and SPEC.loader
acquire_hiringaudit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(acquire_hiringaudit)


@pytest.fixture
def external_root(tmp_path, monkeypatch):
    monkeypatch.setattr(acquire_hiringaudit, "ROOT", tmp_path)
    root = tmp_path / "data" / "external"
    root.mkdir(parents=True)
    return root


def write_archive(path, metadata=None, extra=None):
    metadata = metadata if metadata is not None else [{
        "id": "group1", "pdf_path": "group1/cv_original.pdf",
        "attacks": [{"attack_id": "A2", "attack_pdf_path": "group1/cv_A2.pdf"}],
    }]
    with zipfile.ZipFile(path, "w") as bundle:
        bundle.writestr("cv_dataset/dataset_metadata.json", json.dumps(metadata))
        bundle.writestr("cv_dataset/group1/cv_original.pdf", b"%PDF-1.4\noriginal")
        bundle.writestr("cv_dataset/group1/cv_A2.pdf", b"%PDF-1.4\nattack")
        for name, content in extra or []:
            bundle.writestr(name, content)


def test_manifest_preserves_source_lineage_and_taxonomy(external_root, monkeypatch):
    destination = external_root / "dataset"
    destination.mkdir()
    archive = destination / "cv_dataset.zip"
    write_archive(archive)
    monkeypatch.setattr(acquire_hiringaudit, "download_archive", lambda _: archive)
    manifest = acquire_hiringaudit.acquire(destination)
    assert manifest["revision"] == acquire_hiringaudit.REVISION
    assert manifest["source_group_count"] == 1
    assert manifest["pdf_count"] == 2
    by_id = {row["attack_id"]: row for row in manifest["records"]}
    assert by_id[None]["variant"] == "original"
    assert by_id["A2"]["variant"] == "attack"
    assert by_id["A2"]["attack_family"] == "prompt_injection_hidden"
    assert by_id["A2"]["channel"] == "footer"
    assert by_id["A2"]["publisher_attack_path"] == "group1/cv_A2.pdf"
    for row in manifest["records"]:
        pdf = destination / row["pdf_path"]
        assert pdf.is_file()
        assert acquire_hiringaudit.sha256_file(pdf) == row["sha256"]


@pytest.mark.parametrize("path", ["../escape.pdf", "/escape.pdf", "C:/escape.pdf", "a\\..\\escape.pdf"])
def test_rejects_unsafe_archive_paths(external_root, path):
    archive = external_root / "input.zip"
    write_archive(archive, extra=[(path, b"%PDF-1.4\n")])
    with pytest.raises(ValueError, match="Unsafe archive path"):
        acquire_hiringaudit.inventory_archive(archive, external_root / "output")


def test_rejects_invalid_pdf_before_manifest(external_root):
    archive = external_root / "input.zip"
    write_archive(archive, extra=[("cv_dataset/group2/cv_original.pdf", b"not a PDF")])
    with pytest.raises(ValueError, match="Invalid PDF signature"):
        acquire_hiringaudit.inventory_archive(archive, external_root / "output")


def test_rejects_archive_expansion_limit(external_root, monkeypatch):
    archive = external_root / "input.zip"
    write_archive(archive)
    monkeypatch.setattr(acquire_hiringaudit, "MAX_UNCOMPRESSED_BYTES", 10)
    with pytest.raises(ValueError, match="expands beyond size limit"):
        acquire_hiringaudit.inventory_archive(archive, external_root / "output")


def test_rejects_wrong_cached_archive_hash(external_root):
    destination = external_root / "dataset"
    destination.mkdir()
    write_archive(destination / "cv_dataset.zip")
    with pytest.raises(ValueError, match="SHA-256 differs"):
        acquire_hiringaudit.download_archive(destination)


def test_rejects_wrong_new_archive_hash_and_removes_partial(external_root, monkeypatch):
    class Response:
        headers = {"content-length": "4"}

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def raise_for_status(self):
            pass

        def iter_content(self, _):
            yield b"bad!"

    monkeypatch.setattr(acquire_hiringaudit.requests, "get", lambda *_, **__: Response())
    destination = external_root / "dataset"
    with pytest.raises(ValueError, match="SHA-256 differs"):
        acquire_hiringaudit.download_archive(destination)
    assert not (destination / "cv_dataset.partial").exists()
    assert not (destination / "cv_dataset.zip").exists()


@pytest.mark.parametrize("extra, message", [
    ([("cv_dataset/group1/cv_A2.pdf", b"%PDF-1.4\n")], "Duplicate archive member names"),
    ([("other/group1/cv_A2.pdf", b"%PDF-1.4\n")], "PDF extraction path collision"),
    ([("cv_dataset/group1/cv_A11.pdf", b"%PDF-1.4\n")], "Unknown publisher attack ID"),
])
def test_rejects_ambiguous_or_unknown_pdf_members(external_root, extra, message):
    archive = external_root / "input.zip"
    write_archive(archive, extra=extra)
    with pytest.raises(ValueError, match=message):
        acquire_hiringaudit.inventory_archive(archive, external_root / "output")


def test_rejects_destination_outside_ignored_data(tmp_path, external_root):
    with pytest.raises(ValueError, match="outside the ignored data root"):
        acquire_hiringaudit.validate_destination(tmp_path / "other" / "dataset")


def test_rejects_linked_destination_parent(external_root, monkeypatch):
    destination = external_root / "linked" / "dataset"
    original = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda path: path == external_root / "linked" or original(path))
    with pytest.raises(ValueError, match="crosses a link or junction"):
        acquire_hiringaudit.validate_destination(destination)
