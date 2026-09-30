"""Offline integrity contract for an explicitly exported embedding model tree.

The independent manifest digest must come from a trusted operator channel. Matching
it proves local byte integrity, not publisher identity or scientific suitability.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import stat


MANIFEST_NAME = "embedding_manifest.json"
MAX_MANIFEST_BYTES = 256 * 1024
MAX_FILES = 512
MAX_FILE_BYTES = 1024 * 1024 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024 * 1024
MAX_DIRECTORIES = 512
MAX_DEPTH = 16
ALLOWED_SUFFIXES = {
    ".json", ".txt", ".md", ".yaml", ".yml", ".model", ".vocab",
    ".tiktoken", ".safetensors",
}
DENIED_SUFFIXES = {".py", ".pyc", ".pkl", ".pickle", ".pt", ".pth", ".bin"}
SHA256_RE = re.compile(r"[0-9a-fA-F]{64}\Z")
REVISION_RE = re.compile(r"[0-9a-fA-F]{40}\Z")


def _checked_relative(name: object) -> PurePosixPath:
    if not isinstance(name, str) or not name or "\\" in name or "\x00" in name:
        raise ValueError("Embedding file path must be canonical relative POSIX syntax")
    path = PurePosixPath(name)
    if (path.is_absolute() or PureWindowsPath(name).drive or
            any(part in {"", ".", ".."} for part in name.split("/"))):
        raise ValueError("Embedding file path is absolute or contains traversal")
    suffix = path.suffix.lower()
    if suffix in DENIED_SUFFIXES or suffix not in ALLOWED_SUFFIXES:
        raise ValueError("Embedding export contains prohibited code or weight format")
    return path


def _check_root(directory: Path) -> Path:
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("Embedding directory must be an existing non-symlink directory")
    return directory.resolve()


def _scan(directory: Path) -> dict[str, Path]:
    """Enumerate only the named export, without following symlinks."""
    files: dict[str, Path] = {}
    total = 0
    directories = 0
    stack = [(directory, "", 0)]
    while stack:
        folder, prefix, depth = stack.pop()
        directories += 1
        if directories > MAX_DIRECTORIES or depth > MAX_DEPTH:
            raise ValueError("Embedding export exceeds directory bounds")
        with os.scandir(folder) as entries:
            for entry in entries:
                if entry.is_symlink():
                    raise ValueError("Embedding export contains a symlink")
                name = f"{prefix}{entry.name}"
                if entry.is_dir(follow_symlinks=False):
                    stack.append((Path(entry.path), name + "/", depth + 1))
                    continue
                if not entry.is_file(follow_symlinks=False):
                    raise ValueError("Embedding export contains a non-regular file")
                if name == MANIFEST_NAME:
                    continue
                _checked_relative(name)
                size = entry.stat(follow_symlinks=False).st_size
                if size > MAX_FILE_BYTES:
                    raise ValueError("Embedding export contains a file above the size bound")
                total += size
                files[name] = Path(entry.path)
                if len(files) > MAX_FILES or total > MAX_TOTAL_BYTES:
                    raise ValueError("Embedding export exceeds file count or total size bounds")
    if not {"config.json", "modules.json"}.issubset(files):
        raise ValueError("Embedding export requires config.json and modules.json")
    if not any(name.endswith(".safetensors") for name in files):
        raise ValueError("Embedding export requires at least one safetensors file")
    return files


def _read_bounded(path: Path, limit: int) -> bytes:
    if path.is_symlink():
        raise ValueError("Embedding export contains a symlink")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(path, flags), "rb") as handle:
        size = os.fstat(handle.fileno())
        if not stat.S_ISREG(size.st_mode) or size.st_size > limit:
            raise ValueError("Embedding file is not regular or exceeds its size bound")
        content = handle.read(limit + 1)
        if len(content) > limit or len(content) != size.st_size:
            raise ValueError("Embedding file changed or exceeded its size bound")
        return content


def _hash_file(path: Path) -> str:
    if path.is_symlink():
        raise ValueError("Embedding export contains a symlink")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(path, flags), "rb") as handle:
        before = os.fstat(handle.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_FILE_BYTES:
            raise ValueError("Embedding file is not regular or exceeds its size bound")
        digest = hashlib.sha256()
        seen = 0
        while chunk := handle.read(1024 * 1024):
            seen += len(chunk)
            if seen > MAX_FILE_BYTES:
                raise ValueError("Embedding file exceeded its size bound during hashing")
            digest.update(chunk)
        if seen != before.st_size:
            raise ValueError("Embedding file changed during hashing")
        return digest.hexdigest()


def _validate_identity(model_id: object, upstream_revision: object) -> None:
    if not isinstance(model_id, str) or not model_id.strip() or len(model_id) > 256:
        raise ValueError("model_id must be a nonempty bounded string")
    if not isinstance(upstream_revision, str) or not REVISION_RE.fullmatch(upstream_revision):
        raise ValueError("upstream_revision must be a 40-digit commit hash")


def freeze_embedding(directory: Path | str, model_id: str, upstream_revision: str) -> str:
    """Create a manifest exclusively for an operator-approved local export.

    Returns the manifest SHA-256 digest to pin through an independent channel.
    """
    _validate_identity(model_id, upstream_revision)
    root = _check_root(Path(directory))
    if (root / MANIFEST_NAME).exists() or (root / MANIFEST_NAME).is_symlink():
        raise ValueError("Embedding manifest already exists; export to a new directory")
    files = _scan(root)
    hashes = {name: _hash_file(path) for name, path in sorted(files.items())}
    manifest = {
        "schema_version": "1.0", "model_id": model_id,
        "upstream_revision": upstream_revision.lower(), "files": hashes,
    }
    raw = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode("utf-8")
    if len(raw) > MAX_MANIFEST_BYTES:
        raise ValueError("Embedding manifest exceeds its size bound")
    with (root / MANIFEST_NAME).open("xb") as handle:
        handle.write(raw)
    return hashlib.sha256(raw).hexdigest()


def verify_embedding(directory: Path | str, expected_manifest_sha256: str,
                     expected_model_id: str | None = None) -> dict:
    """Verify the independently pinned manifest and exact bounded export tree."""
    if not isinstance(expected_manifest_sha256, str) or not SHA256_RE.fullmatch(expected_manifest_sha256):
        raise ValueError("An external 64-digit embedding manifest SHA-256 pin is required")
    root = _check_root(Path(directory))
    raw = _read_bounded(root / MANIFEST_NAME, MAX_MANIFEST_BYTES)
    actual = hashlib.sha256(raw).hexdigest()
    if not hmac.compare_digest(actual, expected_manifest_sha256.lower()):
        raise ValueError("Embedding manifest does not match the independent trust pin")
    try:
        manifest = json.loads(raw)
    except (UnicodeError, ValueError):
        raise ValueError("Embedding manifest is not valid JSON") from None
    if not isinstance(manifest, dict) or set(manifest) != {"schema_version", "model_id", "upstream_revision", "files"}:
        raise ValueError("Embedding manifest has an invalid schema")
    if manifest["schema_version"] != "1.0":
        raise ValueError("Embedding manifest schema version is unsupported")
    _validate_identity(manifest["model_id"], manifest["upstream_revision"])
    if expected_model_id is not None and manifest["model_id"] != expected_model_id:
        raise ValueError("Embedding model ID does not match the expected identity")
    hashes = manifest["files"]
    if not isinstance(hashes, dict) or not hashes or len(hashes) > MAX_FILES:
        raise ValueError("Embedding file hashes must be a bounded nonempty object")
    for name, digest in hashes.items():
        _checked_relative(name)
        if name == MANIFEST_NAME or not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            raise ValueError("Embedding manifest contains an invalid file hash")
    files = _scan(root)
    if set(files) != set(hashes):
        raise ValueError("Embedding export file set does not match the manifest")
    for name, path in files.items():
        if not hmac.compare_digest(_hash_file(path), hashes[name].lower()):
            raise ValueError("Embedding export file integrity mismatch: " + name)
    return manifest
