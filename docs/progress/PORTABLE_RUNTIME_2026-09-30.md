# Portable installed runtime (2026-09-30)

## Problem and change
CI installed a regular wheel but ran tests in the source checkout. The wheel omitted the maintained HTML, CSS/JavaScript and default JSON configs, so installations outside the repository could serve a missing frontend and fail legacy configuration lookup. Notice routes assumed LICENSE files were at the source root even though setuptools stores them under distribution metadata.

Package explicit UI assets and the existing configs directory; declare both existing license files. Resolve public notices through the installed distribution when checkout notices are unavailable. Both adapters return a bounded unavailable response if notices are missing. Preserve source-checkout paths and all license terms.

Use one models_directory helper for CLI, API worker and private ASGI preflight: ATS_MODELS_DIR is honored, ~ expands consistently, blank values fail rather than silently selecting the current directory. Model weights remain external; a wheel does not include or validate approved artifacts. The existing checkout results/models default is preserved and may be absent in an installed environment.

## Meaningful installed-wheel verification
Added scripts/check_installed_runtime.py to both Python CI entries. It runs from a temporary directory outside the checkout, rejects checkout imports and editable metadata, verifies packaged JSON/public notices, starts an actual Uvicorn ASGI server on loopback, and checks UI, all three maintained assets, license routes, liveness, security headers and graceful shutdown. It verifies no model worker process started. No real resumes or model downloads are used.

Windows local validation built a regular wheel using setuptools 84.0.0, installed it without dependencies to an isolated target and supplied already-provisioned runtime dependencies. Imported application/config paths were checked against the forbidden source checkout. The live installed-wheel smoke passed. Archive inventory included all required public assets/configs and excluded PDF/model/credential artifacts. This is not a clean Linux full-dependency installation; hosted CI supplies that separate check.

## Results
- Full offline suite: 262 passed, one Windows symlink skip, three cached-model integration tests deselected. One existing Starlette/httpx warning.
- Initial focused API/ASGI/resource checks: 35 passed. After peer review aligned private preflight and added tilde/blank coverage: 14 relevant checks passed.
- CI YAML parse, offline Compose shape validation and scoped Bandit high-severity check passed (existing trusted-pickle B301 exception retained).
- The five frozen detector/service/policy files are unchanged. No holdout, calibration, score or threshold changes; no independent accuracy claim is added.

The previous source-only publication is now merged as PR #2; both Python jobs and container smoke passed for that merge. Customer gateway testing, real pinned embedding compatibility, independent natural manipulation labels, external security review and worker-specific physical-memory containment remain open. Hosted checks for this enhancement are pending publication.
