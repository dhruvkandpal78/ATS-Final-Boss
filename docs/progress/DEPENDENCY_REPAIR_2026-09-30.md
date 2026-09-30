# HTML parser dependency repair (2026-09-30)

## Problem and change
GitHub Actions run 36705214513 stopped during Python 3.11 and 3.12 test collection: `tests/test_data_prep.py` imports `src/data_prep/cleaner.py`, whose direct BeautifulSoup import was not satisfied by the `.[dev,security]` installation.

Added `beautifulsoup4>=4.12.0` to the main `pyproject.toml` runtime dependencies and synchronized `requirements.txt`. Regenerated `requirements-runtime.lock` with Beautiful Soup 4.15.0 and Soup Sieve 2.10 and their wheel/source hashes. The existing typing-extensions 4.16.0 pin also satisfies Beautiful Soup. All 57 previously locked versions and their hash sets are retained; the resulting lock contains 59 packages. No extra workflow installation or test skipping was introduced.

## Resolution method
Used the existing uv 0.12.21 `pip compile` workflow rather than introducing a separate uv.lock:

```
uv pip compile pyproject.toml --constraint requirements-runtime.lock --python-version 3.12 --python-platform x86_64-unknown-linux-gnu --generate-hashes --emit-index-url --no-header --index-url https://pypi.org/simple --extra-index-url https://download.pytorch.org/whl/cpu --index-strategy unsafe-best-match --output-file requirements-runtime.lock
```

Resolution targeted Python 3.12 Linux. The local interpreter available for build metadata was Python 3.14; no source distributions were built for the added pure-Python parser packages. Existing hash sets were preserved after comparison to the previous lock, including Jinja2 and MarkupSafe platform hashes omitted by the resolver output. This prevents unrelated lock churn.

## Verification
- Downloaded all three parser requirements for the Python 3.12 Linux target using pip `--require-hashes --only-binary=:all:`; hash validation succeeded.
- Installed the three pinned parser requirements into an isolated environment using uv `--require-hashes`; parsing HTML entities through BeautifulSoup succeeded with versions 4.15.0 and 2.10.
- Runtime advisory audit: 59 upstream distribution versions checked, no skips and no known vulnerabilities reported.
- API/data-preparation tests: 25 passed after a transient Windows loopback interruption in an initial full run.
- Final offline suite: 259 passed, one Windows symlink skip, three cached-model integration tests deselected; one existing Starlette/httpx deprecation warning.

The Windows sandbox initially prevented access to test-created temporary directories; verification was repeated with approved local execution. Cached-model integration tests are excluded from this offline run. A complete Python 3.12 Linux/container installation of the revised full lock still requires a successful new CI run. Dependency repair does not close the documented customer gateway, model export, worker physical-memory isolation or independent accuracy/security release gates. No private PDFs, datasets or model artifacts are part of this change.
