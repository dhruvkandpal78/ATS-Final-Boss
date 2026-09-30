# Baseline Inventory
## Enhancement audit: 2026-09-26
- Actual source commit: `a0c2982dfdf2358c39b415c237eb4338eeb98de3`.
- Windows; local venv Python 3.14.6, pytest 9.1.1; Node 24.17.0.
- Existing untracked work preserved: plan, review/UI docs, `PROJECTS FOR CV/`, `run_all.ps1`, and `web/` distribution.
- Source invariants reproduced by inspection: service ignores scaler and selects probability column 0; API eagerly loads models and bypasses service; rule overrides rewrite probabilities; text proxy presented as PDF evidence; CLI JSON imports absent schema classes.
- Baseline command: `venv/Scripts/python.exe -m pytest tests/test_data_prep.py tests/test_module_b.py -q` with offline model flags. Exit 1: 4 passed, 1 environment error (default pytest temp directory access denied). Subsequent checks use a workspace-local temporary directory.
- Prior completion claims below are historical, not verified acceptance evidence. B01 provisioning and full browser baseline remain incomplete; improvements will be reported with actual evidence and explicit gaps.

## Historical inventory
- Commit: 78e121764f0e729c4001d537dcc691907fdcbeb1
- OS: Windows
- Python: 3.14.6
- Node: v24.17.0
- Working tree status: Dirty (untracked plan files and run scripts)
- Directory inventory: standard ATS-Final-Boss structure.

## Tests
- Run with pytest. See test output in logs.
