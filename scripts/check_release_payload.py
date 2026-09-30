"""Offline publication guard for a proposed Git range.

Usage: python scripts/check_release_payload.py --base origin/main --head HEAD [--repo .]

The checker is read-only: it does not fetch, stage, commit, rewrite, or push. It
checks changed path names (including paths introduced and later removed in
outgoing commits), rejects symlinks and prohibited payloads without opening
their contents, then scans only changed small text blobs for a few credential
patterns. Passing is a narrow hygiene check, not a release/security approval.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
import sys
from typing import Sequence

MAX_SCAN_BYTES = 1024 * 1024
TEXT_SUFFIXES = {
    ".cfg", ".conf", ".css", ".dockerignore", ".env.example", ".html", ".ini",
    ".js", ".json", ".lock", ".md", ".ps1", ".py", ".rst", ".sh", ".sql",
    ".svg", ".toml", ".ts", ".tsx", ".txt", ".xml", ".yaml", ".yml",
}
TEXT_NAMES = {"dockerfile", "makefile", "license", "license.md", ".gitignore", ".dockerignore", ".env.example"}
PERSONAL_DIRS = {"projects for cv", "personal", "private", "secrets"}
PROHIBITED_SUFFIXES = {".pdf", ".pkl", ".pickle", ".webm", ".pem", ".key", ".token"}
SECRET_NAME = re.compile(r"(?:^|[._-])(secret|secrets|token|tokens|credential|credentials|private|privatekey|pem|key|id_rsa|id_ed25519)(?:$|[._-])", re.I)
PRIVATE_KEY = re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")
GITHUB_TOKEN = re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b")
OPENAI_TOKEN = re.compile(rb"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")


@dataclass(frozen=True)
class Change:
    status: str
    old_path: str | None
    new_path: str


class GitError(RuntimeError):
    pass


def git(repo: Path, *args: str, check: bool = True) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=False,
    )
    if check and result.returncode:
        message = result.stderr.decode("utf-8", "replace").strip()
        raise GitError(message or f"git command failed: {args[0]}")
    return result.stdout


def parse_name_status_z(output: bytes) -> list[Change]:
    fields = output.split(b"\0")
    if fields and fields[-1] == b"":
        fields.pop()
    changes: list[Change] = []
    i = 0
    while i < len(fields):
        status = fields[i].decode("ascii", "replace")
        i += 1
        kind = status[:1]
        if kind in {"R", "C"}:
            if i + 1 >= len(fields):
                raise GitError("malformed rename/copy metadata from git")
            old_path = fields[i].decode("utf-8", "surrogateescape")
            new_path = fields[i + 1].decode("utf-8", "surrogateescape")
            i += 2
        else:
            if i >= len(fields):
                raise GitError("malformed changed-path metadata from git")
            old_path = None
            new_path = fields[i].decode("utf-8", "surrogateescape")
            i += 1
        changes.append(Change(status, old_path, new_path))
    return changes


def is_prohibited_path(path: str) -> str | None:
    normalized = path.replace("\\", "/").strip("/")
    parts = [part.casefold() for part in normalized.split("/") if part]
    if any(part in PERSONAL_DIRS for part in parts):
        return "personal directory"
    if any(part == "data" for part in parts):
        return "data directory"
    if parts and parts[0] == "results" and not (len(parts) > 2 and parts[1] == "reports" and Path(parts[-1]).suffix in {".md", ".json"}):
        return "results directory"
    name = parts[-1] if parts else ""
    if name == ".env" or name.startswith(".env.") and name != ".env.example":
        return "environment/secret file"
    if Path(name).suffix.casefold() in PROHIBITED_SUFFIXES:
        return "prohibited binary/secret file type"
    if SECRET_NAME.search(name) and Path(name).suffix not in {".py", ".md", ".rst", ".html", ".js", ".ts", ".tsx"}:
        return "secret-like filename"
    return None


def _changed_names_for_commit(repo: Path, commit: str) -> list[Change]:
    output = git(repo, "diff-tree", "--root", "--no-commit-id", "--name-status", "--diff-filter=AMRC",
                 "-r", "-m", "-z", "--find-renames", commit)
    return parse_name_status_z(output)


def _changed_range(repo: Path, base: str, head: str) -> list[Change]:
    output = git(repo, "diff", "--name-status", "--diff-filter=AMRC", "-z", "--find-renames", base, head)
    return parse_name_status_z(output)


def _mode_for_path(repo: Path, head: str, path: str) -> tuple[str | None, str | None]:
    # `--` safely delimits a pathspec. The output is metadata only; no blob is read.
    output = git(repo, "ls-tree", "-r", "-z", head, "--", path)
    for record in output.split(b"\0"):
        if not record:
            continue
        metadata, found_path = record.split(b"\t", 1)
        if found_path.decode("utf-8", "surrogateescape") == path:
            mode, object_type, object_id = metadata.decode("ascii").split(" ", 2)
            return mode, object_id
    return None, None


def _is_scannable_text(path: str) -> bool:
    name = path.rsplit("/", 1)[-1].casefold()
    return name in TEXT_NAMES or Path(name).suffix.casefold() in TEXT_SUFFIXES


def _scan_blob(repo: Path, object_id: str, path: str) -> str | None:
    size_text = git(repo, "cat-file", "-s", object_id).decode("ascii", "replace").strip()
    try:
        size = int(size_text)
    except ValueError:
        return f"unverified blob size in {path}"
    if size < 0 or size > MAX_SCAN_BYTES:
        return f"text scan size bound exceeded in {path}"
    content = git(repo, "cat-file", "blob", object_id)
    if b"\0" in content:
        return f"non-text content in declared text file: {path}"
    for label, pattern in (("private key", PRIVATE_KEY), ("GitHub token", GITHUB_TOKEN), ("OpenAI token", OPENAI_TOKEN)):
        if pattern.search(content):
            # Never include matched text, surrounding context, or blob contents.
            return f"credential pattern ({label}) in {path}"
    return None


def validate_range(repo: Path, base: str, head: str = "HEAD") -> list[str]:
    repo = repo.resolve()
    git(repo, "rev-parse", "--show-toplevel")
    base_oid = git(repo, "rev-parse", "--verify", f"{base}^{{commit}}").decode().strip()
    head_oid = git(repo, "rev-parse", "--verify", f"{head}^{{commit}}").decode().strip()
    git(repo, "merge-base", "--is-ancestor", base_oid, head_oid)

    final_changes = _changed_range(repo, base_oid, head_oid)
    violations: list[str] = []

    # Inspect every outgoing commit's changed names so an artifact added and
    # deleted before HEAD is still rejected, while pre-existing base history is
    # not reclassified as newly published content.
    commit_ids = git(repo, "rev-list", "--reverse", f"{base_oid}..{head_oid}").decode().splitlines()
    scanned: set[tuple[str, str]] = set()
    for commit in commit_ids:
        for change in _changed_names_for_commit(repo, commit):
            paths = [change.new_path]
            if change.old_path is not None:
                paths.append(change.old_path)
            for path in paths:
                reason = is_prohibited_path(path)
                if reason:
                    violations.append(f"prohibited outgoing path ({reason}): {path}")
            reason = is_prohibited_path(change.new_path)
            if reason:
                continue
            mode, object_id = _mode_for_path(repo, commit, change.new_path)
            if mode == "120000":
                violations.append(f"symlink is not allowed in outgoing history: {change.new_path}")
                continue
            scan_key = (object_id or "", change.new_path)
            if not object_id or scan_key in scanned:
                continue
            if not _is_scannable_text(change.new_path):
                violations.append(f"unreviewed file type in outgoing history: {change.new_path}")
                continue
            scanned.add(scan_key)
            finding = _scan_blob(repo, object_id, change.new_path)
            if finding:
                violations.append(finding)

    for change in final_changes:
        path = change.new_path
        reason = is_prohibited_path(path)
        if reason:
            violations.append(f"prohibited changed path ({reason}): {path}")
            continue
        mode, object_id = _mode_for_path(repo, head_oid, path)
        if mode == "120000":
            violations.append(f"symlink is not allowed in release payload: {path}")
            continue
        scan_key = (object_id or "", path)
        if not object_id or not _is_scannable_text(path) or scan_key in scanned:
            continue
        scanned.add(scan_key)
        finding = _scan_blob(repo, object_id, path)
        if finding:
            violations.append(finding)
    return violations


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="Base commit or remote ref (for example origin/main)")
    parser.add_argument("--head", default="HEAD", help="Proposed release head (default: HEAD)")
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="Git repository path (default: current directory)")
    args = parser.parse_args(argv)
    try:
        violations = validate_range(args.repo, args.base, args.head)
    except (GitError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if violations:
        for violation in violations:
            print(f"FAIL: {violation}", file=sys.stderr)
        return 1
    print("PASS: no prohibited paths, symlinks, or recognized credentials in scanned release text files.")
    print("This offline check does not fetch refs, inspect ignored/untracked files, or prove publication safety.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
