# Public repository cleanup - September 30, 2026

## Scope and decisions

Cleanup starts from public main `41219f463a5c15e52ed66d2dfc2d644dd677a326`. Private local history, datasets, resume PDFs, model artifacts and unrelated local UI edits are excluded.

- Removed `docs/UI_Rebuild.txt`: its decoded 1,501 lines match the Markdown specification exactly. Moved the single retained Markdown copy into `docs/archive/` and converted its UTF-16 encoding to UTF-8 without changing the decoded text, so publication tools can inspect it as Markdown.
- Removed `docs/ui/legacy-feature-map.md`: obsolete migration instructions referenced only by historical plans, with routes and removal instructions that do not describe the maintained UI.
- Removed `scripts/generate_dummy_fixtures.py`: unused generator of constant-prediction dummy pickles, with no maintained imports or callers. Tests use isolated fixtures and do not require these files.
- Removed `sample_poisoned.txt`: unreferenced root scratch example; maintained tests already cover injection examples.
- Removed `src/data_prep/llm_injector.py`: unused external API script with an unbounded request, raw provider error logging and a fixed historical model. It was not imported by the maintained runtime, scripts or tests. No supported automatic external resume transmission remains through that script.
- Replaced the duplicate dependency list in `requirements.txt` with `.[dev]`, retaining `pip install -r requirements.txt` compatibility while using `pyproject.toml` as the source of dependency declarations. The hashed Linux runtime lock and runtime dependency versions are unchanged.
- Updated `RESEARCH.md` and project rules to distinguish current detectors and controlled evidence from historical synthetic metrics, unsupported adaptive endpoints, unimplemented SHAP and unproven fairness/robustness claims.

Kept source code, maintained frontend, reproducible research/evaluation tools, CI, deployment examples, runtime lock, licenses, synthetic PDF test fixtures, dated change records, historical experiment outputs and archive provenance. The optional static preview exporter is retained because it is a supported design inspection tool and has concurrent local edits; public hosting remains cancelled.

No deployed detector features, thresholds, frozen policy code or model artifacts changed. Git history is preserved, so removed files remain retrievable at older revisions. Existing consumed evaluation results have not been rerun or used for tuning.

## Verification

- Offline Windows Python 3.14 suite: **351 passed, 2 skipped, 3 integration tests deselected**, with one existing Starlette test-client deprecation warning. The two platform skips are unchanged; no model downloads or held-out evaluation was performed.
- Pip's requirements parser accepts `.[dev]` through the compatibility file; the archived Markdown specification has identical decoded text to its previous path and uses UTF-8.
- Local links in the changed maintained Markdown files resolve; `git diff --check` passes. Historical archive references are intentionally not treated as maintained commands.
- Publication must pass `scripts/check_release_payload.py --base origin/main --head HEAD` before push. Hosted Linux and container CI will run on the published branch; no new hosted result is claimed here.

## Remaining release gates

Cleanup does not establish company readiness, calibrated cheating probability, complete PDF visibility, natural manipulation accuracy, fairness or native process containment. See [release gate](../COMPANY_RELEASE_GATE.md) and [current status](STATUS.md).
