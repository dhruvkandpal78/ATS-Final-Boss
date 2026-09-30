"""Audit locked distributions and fail on skipped advisories.

PyTorch CPU wheels use +cpu versions on a separate index; advisory databases
track the base upstream release. This audit normalizes only that known variant
and never installs the normalized requirements. Binary/vendor audits remain
separate release gates.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile


def advisory_requirements(lock):
    requirements = []
    for line in lock.splitlines():
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+-]+)\s*(?:\\)?", line.strip())
        if not match:
            continue
        name, version = match.groups()
        if "+" in version:
            if name.lower() != "torch" or not version.endswith("+cpu"):
                raise ValueError("Unreviewed local-version distribution in runtime lock")
            version = version[:-4]
        requirements.append(f"{name}=={version}")
    if not requirements:
        raise ValueError("No pinned distributions found in runtime lock")
    return requirements


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", default="requirements-runtime.lock")
    parser.add_argument("--output", default="runtime-audit.json")
    parser.add_argument("--cache-dir", default=".test-tmp/audit-cache")
    parser.add_argument("--verify-installed", action="store_true")
    args = parser.parse_args()
    requirements = advisory_requirements(Path(args.lock).read_text())
    if args.verify_installed:
        from importlib.metadata import version
        for requirement in requirements:
            name, expected = requirement.split("==", 1)
            if name.lower() == "torch":
                expected += "+cpu"
            if version(name) != expected:
                print("Installed runtime differs from release lock: " + name, file=sys.stderr)
                return 1
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ats-advisory-") as directory:
        path = Path(directory) / "advisories.txt"
        path.write_text("\n".join(requirements) + "\n")
        result = subprocess.run([sys.executable, "-m", "pip_audit", "--disable-pip", "--no-deps",
            "--progress-spinner", "off", "--cache-dir", args.cache_dir,
            "-r", str(path), "-f", "json", "-o", str(output)], check=False)
    if result.returncode != 0:
        return result.returncode
    record = json.loads(output.read_text())
    if any(row.get("skip_reason") for row in record.get("dependencies", [])):
        print("Runtime audit incomplete: at least one distribution was skipped", file=sys.stderr)
        return 1
    if len(record.get("dependencies", [])) != len(requirements):
        print("Runtime audit incomplete: dependency count mismatch", file=sys.stderr)
        return 1
    print(f"Audited {len(requirements)} upstream distribution versions; no skipped entries.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
