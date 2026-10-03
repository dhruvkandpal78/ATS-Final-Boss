"""Acquire a pinned, synthetic HiringAudit PDF corpus for external evaluation.

The archive is data only: this script never imports or executes publisher code.
All downloads and extracted PDFs live under the ignored data/ directory.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import zipfile

import requests


ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "data" / "external" / "hiringaudit-v1"
DATASET = "PD777/HiringAudit-adversarial_cv_dataset"
REVISION = "81a0f6b1a5c3254371e6304af9dafdc533b6c9d5"
BASE_URL = f"https://huggingface.co/datasets/{DATASET}/resolve/{REVISION}"
ARCHIVE_URL = f"{BASE_URL}/cv_dataset.zip"
EXPECTED_ARCHIVE_SHA256 = "37ebec01c1eed28d16a71aeb4a9f884c778935092f806d65ddeb4eb5833d03b8"
MAX_ARCHIVE_BYTES = 550 * 1024 * 1024
MAX_ENTRIES = 30_000
MAX_UNCOMPRESSED_BYTES = 4 * 1024 * 1024 * 1024
MAX_PDF_BYTES = 20 * 1024 * 1024
MAX_METADATA_BYTES = 20 * 1024 * 1024
CHUNK = 1024 * 1024
PDF_NAME = re.compile(r"cv_(original|A\d+)\.pdf", re.IGNORECASE)
PUBLISHER_REVISION = "ea1acd703c2e5fdb69a9ed154b047a32adf467c7"
# Source: LLM-Assurance/attacks.yaml at PUBLISHER_REVISION. The generator uses
# attack_name to dispatch, while channel describes placement in the document.
PUBLISHER_ATTACKS = {
    "A1": ("prompt_injection_simple", "body", "direct", "G1"),
    "A2": ("prompt_injection_hidden", "footer", "hidden", "G1"),
    "A3": ("exaggeration", "body", "content_manipulation", "G1"),
    "A4": ("fake_credentials", "body", "falsification", "G1"),
    "A5": ("jailbreak_attempt", "body", "system_override", "G2"),
    "A6": ("prompt_injection_hidden", "footer", "hidden", "G1"),
    "A7": ("prompt_injection_metadata", "meta", "direct", "G1"),
    "A8": ("prompt_injection_simple", "body", "direct", "G2"),
    "A9": ("prompt_injection_simple", "body", "multi_step", "G3"),
    "A10": ("exaggeration", "body", "content_manipulation", "G4"),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_destination(destination: Path) -> Path:
    """Confine writes to ignored external data without traversing a reparse point."""
    external = ROOT / "data" / "external"
    root = ROOT.resolve(strict=True)
    candidate = Path(os.path.abspath(destination))
    try:
        relative = candidate.relative_to(root)
    except ValueError as error:
        raise ValueError("Destination is outside the ignored data root") from error
    if relative.parts[:2] != ("data", "external") or len(relative.parts) < 3:
        raise ValueError("Destination is outside the ignored data root")
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink() or (hasattr(current, "is_junction") and current.is_junction()):
            raise ValueError(f"Destination crosses a link or junction: {current}")
    if not candidate.resolve().is_relative_to(external.resolve()):
        raise ValueError("Destination resolves outside the ignored data root")
    return candidate


def download_archive(destination: Path = DESTINATION) -> Path:
    destination = validate_destination(destination)
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / "cv_dataset.zip"
    if archive.is_file():
        if archive.stat().st_size > MAX_ARCHIVE_BYTES:
            raise ValueError("Existing archive exceeds size limit")
        if sha256_file(archive) != EXPECTED_ARCHIVE_SHA256:
            raise ValueError("Existing archive SHA-256 differs from pinned dataset")
        return archive
    partial = destination / "cv_dataset.partial"
    partial.unlink(missing_ok=True)
    try:
        with requests.get(ARCHIVE_URL, stream=True, timeout=(20, 120)) as response:
            response.raise_for_status()
            declared = response.headers.get("content-length")
            if declared and int(declared) > MAX_ARCHIVE_BYTES:
                raise ValueError("Declared archive exceeds size limit")
            total = 0
            with partial.open("xb") as output:
                for chunk in response.iter_content(CHUNK):
                    total += len(chunk)
                    if total > MAX_ARCHIVE_BYTES:
                        raise ValueError("Archive exceeds size limit")
                    output.write(chunk)
        if sha256_file(partial) != EXPECTED_ARCHIVE_SHA256:
            raise ValueError("Downloaded archive SHA-256 differs from pinned dataset")
        partial.replace(archive)
    finally:
        partial.unlink(missing_ok=True)
    return archive


def safe_member(info: zipfile.ZipInfo) -> PurePosixPath:
    name = info.filename.replace("\\", "/")
    path = PurePosixPath(name)
    if (not name or name.startswith("/") or "//" in name or
            any(part in ("", ".", "..") for part in path.parts) or
            re.match(r"^[A-Za-z]:", name)):
        raise ValueError(f"Unsafe archive path: {info.filename!r}")
    mode = info.external_attr >> 16
    if stat.S_IFMT(mode) == stat.S_IFLNK:
        raise ValueError(f"Symlink in archive: {info.filename!r}")
    if mode and stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR):
        raise ValueError(f"Unsupported archive member: {info.filename!r}")
    return path


def bounded_json(bundle: zipfile.ZipFile, info: zipfile.ZipInfo) -> object:
    if info.file_size > MAX_METADATA_BYTES:
        raise ValueError("Metadata exceeds size limit")
    with bundle.open(info) as source:
        raw = source.read(MAX_METADATA_BYTES + 1)
    if len(raw) > MAX_METADATA_BYTES:
        raise ValueError("Metadata exceeds size limit")
    return json.loads(raw)


def inventory_archive(archive: Path, destination: Path = DESTINATION) -> dict:
    destination = validate_destination(destination)
    records: list[dict] = []
    source_metadata: object | None = None
    source_metadata_path: str | None = None
    with zipfile.ZipFile(archive) as bundle:
        entries = bundle.infolist()
        if len(entries) > MAX_ENTRIES:
            raise ValueError("Too many archive entries")
        if sum(item.file_size for item in entries) > MAX_UNCOMPRESSED_BYTES:
            raise ValueError("Archive expands beyond size limit")
        paths = [(safe_member(info), info) for info in entries]
        names = [str(path) for path, _ in paths]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate archive member names")
        metadata_entries = [(path, info) for path, info in paths
                            if path.name == "dataset_metadata.json"]
        if len(metadata_entries) != 1:
            raise ValueError("Expected exactly one dataset_metadata.json")
        metadata_path, metadata_info = metadata_entries[0]
        source_metadata = bounded_json(bundle, metadata_info)
        source_metadata_path = str(metadata_path)
        pdf_entries = [(path, info) for path, info in paths
                       if path.suffix.lower() == ".pdf"]
        output_paths = set()
        for path, _ in pdf_entries:
            if path.name.startswith("._"):
                continue  # macOS AppleDouble metadata, not a PDF document
            match = PDF_NAME.fullmatch(path.name)
            if not match:
                raise ValueError(f"Unexpected PDF filename: {path}")
            if match.group(1).upper() != "ORIGINAL" and match.group(1).upper() not in PUBLISHER_ATTACKS:
                raise ValueError(f"Unknown publisher attack ID: {path}")
            relative = Path("pdfs") / path.parent.name / path.name
            if relative in output_paths:
                raise ValueError(f"PDF extraction path collision: {relative}")
            output_paths.add(relative)
        for path, info in pdf_entries:
            if path.name.startswith("._"):
                continue
            match = PDF_NAME.fullmatch(path.name)
            assert match is not None  # validated above
            if info.file_size > MAX_PDF_BYTES:
                raise ValueError(f"PDF exceeds size limit: {path}")
            digest = hashlib.sha256()
            relative = Path("pdfs") / path.parent.name / path.name
            target = destination / relative
            validate_destination(target.parent)
            target.parent.mkdir(parents=True, exist_ok=True)
            validate_destination(target.parent)
            temporary = target.with_suffix(".partial")
            temporary.unlink(missing_ok=True)
            try:
                with bundle.open(info) as source, temporary.open("xb") as output:
                    prefix = source.read(5)
                    if prefix != b"%PDF-":
                        raise ValueError(f"Invalid PDF signature: {path}")
                    output.write(prefix)
                    digest.update(prefix)
                    total = len(prefix)
                    while chunk := source.read(CHUNK):
                        total += len(chunk)
                        if total > MAX_PDF_BYTES:
                            raise ValueError(f"PDF exceeds size limit: {path}")
                        digest.update(chunk)
                        output.write(chunk)
                temporary.replace(target)
            finally:
                temporary.unlink(missing_ok=True)
            attack_id = match.group(1).upper()
            records.append({
                "source_group": path.parent.name,
                "archive_path": str(path),
                "pdf_path": relative.as_posix(),
                "sha256": digest.hexdigest(),
                "size_bytes": info.file_size,
                "variant": "original" if attack_id == "ORIGINAL" else "attack",
                "attack_id": None if attack_id == "ORIGINAL" else attack_id,
                "label_basis": "publisher_filename",
            })
    if not isinstance(source_metadata, list):
        raise ValueError("Publisher dataset metadata has unexpected structure")
    return {"records": records, "source_metadata": source_metadata,
            "source_metadata_path": source_metadata_path}


def acquire(destination: Path = DESTINATION) -> dict:
    archive = download_archive(destination)
    inventory = inventory_archive(archive, destination)
    metadata = inventory.pop("source_metadata")
    records = inventory["records"]
    by_group = {row.get("id"): row for row in metadata if isinstance(row, dict)}
    if len(by_group) != len(metadata):
        raise ValueError("Publisher metadata has duplicate or invalid source groups")
    for record in records:
        source = by_group.get(record["source_group"], {})
        attacks = source.get("attacks", []) if isinstance(source, dict) else []
        attack = next((item for item in attacks
                       if isinstance(item, dict) and item.get("attack_id") == record["attack_id"]), None)
        if record["variant"] == "attack":
            record["publisher_attack_path"] = attack.get("attack_pdf_path") if attack else None
            taxonomy = PUBLISHER_ATTACKS.get(record["attack_id"])
            record["attack_family"] = taxonomy[0] if taxonomy else None
            record["channel"] = taxonomy[1] if taxonomy else None
            record["style"] = taxonomy[2] if taxonomy else None
            record["goal"] = taxonomy[3] if taxonomy else None
        else:
            record["publisher_original_path"] = source.get("pdf_path") if isinstance(source, dict) else None
            record["attack_family"] = None
            record["channel"] = None
            record["style"] = None
            record["goal"] = None
        publisher_path = record.get("publisher_attack_path") or record.get("publisher_original_path")
        if not publisher_path or record["archive_path"] != f"cv_dataset/{publisher_path}":
            raise ValueError(f"PDF does not match publisher lineage: {record['archive_path']}")
    if len({row["archive_path"] for row in records}) != len(records):
        raise ValueError("Duplicate PDF archive paths")
    expected = set()
    for group, source in by_group.items():
        expected.add((group, source.get("pdf_path")))
        for attack in source.get("attacks", []):
            if not isinstance(attack, dict) or attack.get("attack_id") not in PUBLISHER_ATTACKS:
                raise ValueError(f"Unknown publisher attack metadata in {group}")
            expected.add((group, attack.get("attack_pdf_path")))
    actual = {(row["source_group"], row.get("publisher_attack_path") or row.get("publisher_original_path"))
              for row in records}
    if len(expected) != len(records) or actual != expected:
        raise ValueError("PDF inventory differs from publisher metadata")
    result = {
        "schema_version": 1,
        "dataset": DATASET,
        "revision": REVISION,
        "source_url": f"https://huggingface.co/datasets/{DATASET}",
        "archive_url": ARCHIVE_URL,
        "archive_sha256": sha256_file(archive),
        "archive_size_bytes": archive.stat().st_size,
        "publisher_repo": "https://github.com/clonerex7777/LLM-Assurance",
        "publisher_revision": PUBLISHER_REVISION,
        "publisher_license_url": f"https://github.com/clonerex7777/LLM-Assurance/blob/{PUBLISHER_REVISION}/LICENSE",
        "attack_taxonomy_url": f"https://github.com/clonerex7777/LLM-Assurance/blob/{PUBLISHER_REVISION}/attacks.yaml",
        "publisher_license": "MIT",
        "dataset_card_license": "mit",
        "synthetic": True,
        "pdf_origin": "publisher_rendered_original_and_attack_pdfs",
        "source_metadata_path": inventory["source_metadata_path"],
        "source_group_count": len({row["source_group"] for row in records}),
        "pdf_count": len(records),
        "records": records,
    }
    output = destination / "provenance.json"
    temporary = destination / "provenance.partial"
    temporary.unlink(missing_ok=True)
    with temporary.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, indent=2, ensure_ascii=False))
    temporary.replace(output)
    print(json.dumps({key: value for key, value in result.items() if key != "records"}, indent=2))
    return result


if __name__ == "__main__":
    acquire()
