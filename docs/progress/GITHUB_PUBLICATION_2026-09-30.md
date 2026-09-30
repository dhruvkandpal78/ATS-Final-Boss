# Source-only GitHub publication

The user authorized publishing all reviewed project architecture/code changes, tests and change records while excluding personal resume PDFs. Publication is prepared on `codex/publish-research-repair`, based on the existing remote `upgrade/paper-and-signal` branch. The unrelated local history is not merged or pushed.

The publication includes the current runtime/UI, calibration and PDF-candidate workflow, inspectable evidence, precision policy 2.0, regression tests, aggregate benchmark reports and complete research notes. `docs/Architecture.md` now describes the actual implementation and its open limits. Commit descriptions preserve methods, measurements, tests and limitations for the research-paper collaborator.

The remote branch already tracked personal resume PDFs under `PROJECTS FOR CV/` and resume samples under `results/standalone_pdfs/`. Those directories are removed from the publication branch's current tree. GitHub's existing historical objects are not erased; no force push or history rewrite is performed. Three checked-in PDFs under `tests/fixtures/` contain synthetic example text and are retained for regression tests.

New ignore rules exclude PDFs by default except synthetic test fixtures, personal project folders, downloaded data and local candidate bundles. Local personal files, recordings and unrelated utility scripts are not staged. The outgoing commit must add or modify no personal PDFs, dataset files, model bundles or unrelated personal-project files. Verification includes review of the publication diff and outgoing history, secret-pattern checks, the offline regression suite, JavaScript syntax and whitespace checks.

The earlier automatic approval rejection applied to pushing the unrelated local branch containing private history. This publication uses the user's clarified scope and a reviewed outgoing commit based on existing GitHub history. Publication status and final commit/PR references will be recorded after GitHub confirms the write.

## Verified publication payload

- 49 added/modified project files; no added/modified PDFs, datasets, candidate bundles or model weights.
- 103 already-tracked personal/sample resume PDF paths and four unrelated personal-project paths removed from the branch tree. Only the three unchanged synthetic test PDFs remain tracked.
- Exact publication checkout: 131 offline tests passed in 45.79 seconds. The initial checkout test run failed fixture setup because its temporary parent did not exist; rerunning with an existing parent passed.
- Credential-pattern scan found no private key, GitHub token or OpenAI key patterns in the reviewed code/docs/config/test paths. JavaScript syntax and staged whitespace checks passed.

## Publication status

### Additional private-pilot payload

The clean branch now also contains security commit `20744fb` (local working branch equivalent `3eceaf8`) after initial publication commit `6479c3c`. It adds authentication, Host/Origin guards, independently pinned artifacts, bounded admission, privacy-safe events, container/CI configuration, a hashed runtime lock, tests and the corresponding architecture/change/operations records. The complete outgoing tree currently has 67 added/modified source/config/test/report/documentation files, no added/modified PDFs or model/data bundles, and the previously recorded removals. The latest full local suite passed 149 tests. This is not a verified production deployment; remaining gates are recorded in the hardening document. No further push was attempted after the approval denial.

The prepared branch is committed locally but **not pushed**. Automatic approval review rejected the September 30 push to the public repository `https://github.com/dhruvkandpal78/ATS-Final-Boss`, requiring explicit approval of that exact destination and the complete reviewed payload after the earlier rejection. No alternate upload method was attempted. The pending payload is the 49 reviewed project files above plus removal of the existing personal/sample PDF and unrelated-project paths; no private local history, new PDFs, data or model bundles are included. Target branch: `codex/publish-research-repair`. Main and the existing upgrade branch are unchanged.
