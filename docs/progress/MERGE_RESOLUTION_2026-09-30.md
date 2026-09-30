# Merge main into enhanced publication branch (2026-09-30)

## Conflict resolution
PR #2 reported conflicts after main merged the older startup fallback PR #1. Merged main a7a2d06 into codex/publish-research-repair without rewriting either branch history.

- src/app/server.py: retained the enhanced shared AnalysisService/isolated-worker implementation. The earlier fallback assigns arbitrary weighted probabilities and sentence-length proxies when artifacts are absent; importing it would contradict current missing-coverage reporting and private startup verification.
- tests/test_api.py: retained the enhanced deterministic HTTP, validation, coverage, privacy and cleanup tests. The older test expects global eager model variables that no longer exist in this architecture. Private startup failure cases are covered in tests/test_asgi.py.
- tests/fixtures/normal.pdf, tiny_text.pdf and white_on_white.pdf: retained the publication branch versions exactly. These pre-existing synthetic fixtures acquire no new bytes relative to the published branch.
- requirements.txt: retained main reportlab>=4.0.0 addition and existing Beautiful Soup declaration. ReportLab was already declared in the project dev extra. No duplicate Beautiful Soup entry is introduced.

## Verification
No unresolved index entries remain; git diff --cached --check passes. Relative to the pre-merge publication branch, the runtime, API tests and PDF fixtures are unchanged. Personal PROJECTS FOR CV PDFs and results/standalone_pdfs remain absent from the publication tree. Before pushing, inspect newly reachable Git blobs against both known remote tips so reused, already-published fixtures are distinguished from new upload content.

Full offline suite: 259 passed, one Windows symlink skip, three cached-model integration tests deselected; one existing Starlette/httpx deprecation warning. The previous CI installation implementation 672dd85 passed all three hosted jobs in run 36708469548; that does not replace verification of this merge. Updated PR mergeability and merge-commit CI must be checked after publication. No main-branch merge or production-readiness certification is performed here.
