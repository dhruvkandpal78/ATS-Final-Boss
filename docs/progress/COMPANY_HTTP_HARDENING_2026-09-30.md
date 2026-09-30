# Company pilot HTTP hardening and release evidence

## Scope

Continues the merged portable-runtime release from public main 494b64e. This is a single-company private-pilot foundation, not a claim of general commercial readiness or complete vulnerability absence.

## Changes

- Share strict body-header validation across ASGI and local HTTP: reject transfer encoding even when empty, require one decimal Content-Length within the encoded-body limit, and exactly one JSON Content-Type. Preserve authorization before processing.
- Accept UTF-8 JSON with an explicit 64-level nesting bound in both adapters, independent of Python parser recursion behavior. Return deeper or malformed bodies as 400. Bounded draining of small rejected local bodies preserves error delivery on Windows. Inference limits stay unchanged.
- Worker crash events retain only exception class and process exit code, never the raw exception message. This is preventive logging hardening, not a demonstrated document-disclosure vulnerability.
- Remove Google Fonts requests from the historical Streamlit dashboard and visibly label its proxy scores as historical and uncalibrated. Streamlit itself is not the supported private entry point or covered by the maintained HTTP guards.
- Add parser and actual adapter rejection tests with synthetic data and no model downloads.
- Add a customer release evidence checklist covering deployed identity/network controls, exact artifact/image identity, startup, memory containment, privacy, load/recovery, human use, and incident/rollback ownership. All customer acceptance gates remain untested until evidence is attached.
- Follow-up user review: added fail-closed artifact tests, lexical adaptive diagnostics, separate experimental raster-region inspection, visible PDF capability limits, and a current documentation map. Older planning documents are marked historical rather than removed; detailed response is in [current review](CURRENT_REVIEW_2026-09-30.md).
- Added an allowlisted free static-site exporter. The preview has no analysis backend and disables document input; it does not expose private runtime routes or copy PDFs/model artifacts. Hugging Face publication is awaiting the owner's account/session.

## Security assessment before this patch

Codex Security scan 19dae95a-4f94-4d51-920e-6ab802f8bbd2 reviewed all 11 src/app files at c0444159cd76b483b497ef79c2a35ed97e7b8782. Independent baseline, architecture and focused reviews plus parent source validation found no demonstrated boundary-crossing vulnerability. Scope was static app review; deployment templates were supporting context. This result does not certify the patch, the deployed gateway, detector internals, or absence of vulnerabilities.

The managed report and canonical coverage are retained in the local Codex Security workbench. Reported tool usage was 4,014,039 total tokens across three tracked threads, including 3,713,408 cached input tokens; this is the tool's accounting, not a cost estimate.

## Validation

Initial HTTP full offline run: 297 passed, one Windows symlink skip, three integration tests deselected, one Starlette/httpx deprecation warning. Subsequent additive review checks initially passed 13 focused tests. Final combined offline verification: 310 passed, one Windows symlink skip, three integration tests deselected and one Starlette/httpx deprecation warning. High-severity Bandit scan (including the experimental module) passed with the existing trusted-pickle B301 exception; two low-severity observations remain. Node syntax checks for maintained/preview scripts and offline Compose shape validation passed. Static export built from the explicit allowlist. Hosted CI is pending and must not be inferred from local success.

## Remaining release gates

Worker and HTTP parent still share the container physical memory budget. RLIMIT_AS constrains virtual address space and does not provide independent physical-RAM isolation. Real native OOM/hang containment, a customer gateway/SSO deployment, approved model compatibility, durable privacy-safe monitoring and external security validation remain open. The controlled benchmark is unchanged; zero observed sample false positives does not establish population zero, and model scores are not calibrated cheating probabilities.

No detector policy or frozen holdout changes, new model/data artifacts, personal PDFs or secret values are part of this patch.
