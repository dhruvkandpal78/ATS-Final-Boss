# CI installation and build-tool repair (2026-09-30)

## Verified cause
GitHub run 36707154747 at 332b915 passed the Python 3.12 test/security job and container smoke job. Python 3.11 failed its installed dependency audit because setuptools 79.0.1 carried PYSEC-2026-3447. The editable project message was a separate skip notice, not the vulnerability causing exit 1. Python 3.11 never reached the locked audits; Python 3.12 completed both.

The [reviewed advisory](https://github.com/advisories/GHSA-h35f-9h28-mq5c) lists setuptools 83.0.0 as fixed.

## Changes
- Replace the editable CI install with regular `pip install ".[dev,security]"`.
- Upgrade CI setuptools to >=83.0.0 alongside pip; require the same floor for isolated builds in pyproject.toml.
- Explicitly verify installed project metadata is non-editable and setuptools meets the floor.
- Remove the old `--skip-editable` audit option. No ignore list, advisory suppression, continue-on-error behavior or relaxed runtime-lock completeness check is added.

## Validation and limits
Built a wheel with local setuptools 84.0.0 and installed it without dependencies into the isolated parser test environment. Its direct_url metadata is non-editable and version assertions pass. An audit of that environment without skip/ignore arguments found no known vulnerabilities in its third-party packages. Runtime-audit unit test: one passed. Workflow YAML parses and its embedded Python verification compiles.

This packaging smoke used Windows Python 3.14 with --no-build-isolation and --no-deps to avoid installing the heavy Linux runtime locally. It does not establish full Python 3.11/3.12 installation; the updated hosted CI must pass.

A regular wheel does not make unpublished application code discoverable in PyPI advisory services. The local audit JSON explicitly reports ats-final-boss 0.2.0 as unavailable on PyPI. This is not an independent vulnerability assessment of application code. The separate strict lock audit still requires all 59 upstream runtime versions without skips; Bandit and tests inspect application code. No runtime lock versions, private PDFs, datasets or model artifacts change.
