# Embedding integrity, startup coverage and publication safety

## Changes

Private deployment now requires a second independent digest for the exported embedding model, in addition to the candidate classifier bundle. The offline export freezer records model identity, a reviewed upstream revision and hashes for every allowed file. Verification bounds file count, depth and bytes, rejects custom code/pickle weight formats/symlinks/path traversal, detects added or changed files and checks identity before local embedding loading. Exported safetensors weights must be reviewed and mounted read-only; hashes establish approved-byte integrity, not publisher identity or model quality. No real embedding export was generated or evaluated in this pass.

Startup now exercises multi-sentence semantic encoding and a synthetic PDF, checks detector coverage and the combined PDF score, and rejects HTTP-success results containing failed detectors. Readiness turns off when worker shutdown begins. Private child stdout/stderr and Python logging are silenced so library/native diagnostics cannot bypass the parent's content-free response events. Host/Origin control characters are rejected explicitly; ASGI rejects ambiguous content types and handles deeply nested JSON as invalid input, with parsing outside its event-loop handler.

Added an offline Git-range publication guard. It checks outgoing commits as well as the final diff, permits removal of pre-existing personal PDFs, rejects newly introduced private/data/model paths and symlinks, and scans bounded changed text blobs for known credential formats without echoing matched content. Aggregate reports are allowed; unknown/unscannable files require review. This is narrow hygiene validation, not proof of absence of all personal information or secrets.

## Verification and limits

Focused integrity/security suite: 66 passed, one symlink test skipped because the Windows host could not create links. Additional startup/log-boundary checks and the complete suite are verified below after integration. Existing detector policy files and consumed holdouts remain unchanged.

Final full suite: 262 passed, one Windows symlink test skipped, one existing Starlette/httpx compatibility warning, in 79.18 seconds. The initial full run exposed a test expectation difference: this Python build accepts deeply nested JSON before rejecting its non-object request shape (422), while other builds may reject decoder depth (400); both remain client errors and never reach inference. The test was corrected and the full suite rerun. Private child diagnostic suppression was tested in a real synthetic subprocess. Scoped high-severity scanning, deployment validation, whitespace checks and publication guard on the preceding clean branch passed. No actual private Linux/embedding deployment or new accuracy experiment was performed.

The Linux virtual-address limit is not a physical-RAM limit. The 3 GiB container memory budget covers parent and worker together; the 16 GiB worker virtual-address ceiling accommodates library mappings and does not prevent a fast allocation from exhausting the shared cgroup. Worker-specific physical isolation or a tested containment design remains an open production gate. Docker/WSL are unavailable locally, and the actual private gateway, pinned real embedding export, Linux image and external security review remain unverified. Do not claim this iteration makes the application foolproof or production-certified.

## Handoff

The user requested a prompt for Antigravity to complete verification and publish to GitHub. The source-only branch is `codex/publish-research-repair`, based on `origin/upgrade/paper-and-signal`, in `.test-tmp/github-publication`. Do not push the unrelated working branch or private local history. Keep personal PDFs/data/weights/secrets/recordings out of publication and preserve local copies. Prior managed push denials were not bypassed through another tool.
