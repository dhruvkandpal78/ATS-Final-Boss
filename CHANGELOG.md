# ATS Final Boss - Development Journey & Iterations

## 2026-09-30: resolve main/publication merge conflicts

Merged current main into the enhanced publication branch, preserving the shared runtime, deterministic API suite and byte-identical synthetic PDF fixtures. Retained the main ReportLab requirements addition. Details and verification: [merge resolution record](docs/progress/MERGE_RESOLUTION_2026-09-30.md).

## 2026-09-30: regular CI installation and patched build tools

Changed CI to a regular project install with metadata verification and a setuptools fixed-version floor. Removed the editable audit exclusion while preserving strict lock checks. The actual preceding failure was vulnerable runner setuptools; Python 3.12 and container jobs passed. See [CI installation repair](docs/progress/CI_INSTALL_REPAIR_2026-09-30.md).

## 2026-09-30: declare the HTML parser runtime dependency

Declared `beautifulsoup4>=4.12.0` in project runtime dependencies and the legacy requirements list. Regenerated the Linux CPU hash lock with Beautiful Soup 4.15.0 and Soup Sieve 2.10, preserving all previous runtime versions and hashes. This fixes CI test collection through `src/data_prep/cleaner.py` without an ad hoc workflow install. Validation and limits: [dependency repair record](docs/progress/DEPENDENCY_REPAIR_2026-09-30.md).

## 2026-09-30: architecture verification and failure recovery

Conducted an architecture verification phase targeting documented deployment gaps. Documented operational blockers (Linux container isolation, customer gateway, pinned export verification) for Windows environments. Improved worker failure recovery and operational monitoring in `src/app/server.py` by adding explicit worker exit-code tracking and structured JSON logging for timeout events. See [architecture verification record](docs/progress/ARCHITECTURE_VERIFICATION_2026-09-30.md).

## 2026-09-30: embedding integrity and meaningful readiness

Added an independently pinned embedding-export contract and offline freeze tool, local immutable-export loading, semantic/PDF startup coverage checks, shutdown-aware readiness, private diagnostic suppression, stricter header/content-type validation and a read-only Git publication guard. Documented the shared-container physical-memory limitation. Personal files and existing detector policy remain unchanged. See [integrity/startup record](docs/progress/INTEGRITY_STARTUP_2026-09-30.md).

## 2026-09-30: production-compatible adapter and lifecycle architecture

Added a Uvicorn/Starlette private adapter, shared HTTP security headers, fail-closed model warm-up before serving, coordinated worker shutdown and spawn-failure cleanup. Added a TLS/SSO gateway template, deployment-security mutation checks, image-build/smoke CI, and reusable denominator-aware statistics. Full local suite: 218 passed; live loopback adapter smoke passed. Detection policy and consumed holdouts remain unchanged. Exact Linux/container/gateway validation remains open. See [architecture hardening record](docs/progress/ARCHITECTURE_HARDENING_2026-09-30.md).

## 2026-09-30: private-company pilot security foundation

Added guarded local/private deployment modes, Host/Origin checks, secret-file authentication, externally pinned model verification, bounded connections/request admission, content-free response audit events and Linux resource-limit/container configuration. Added a hashed Linux CPU runtime lock, advisory/static checks, CI and security/operations/customer-strategy documentation. The proposed first customer is a technical staffing agency or midsized recruiting team. This is a pilot foundation; Docker, customer SSO/TLS, exact Linux runtime and independent security validation remain release gates. Personal resumes remain excluded from publication. See [hardening record](docs/progress/PRIVATE_PILOT_HARDENING_2026-09-30.md).

## 2026-09-30: architecture record and source-only publication

Replaced the outdated architecture plan with the implemented runtime, policy/score separation, evidence and frozen PDF research workflow. Added publication exclusions for personal PDFs/projects and a [GitHub handoff record](docs/progress/GITHUB_PUBLICATION_2026-09-30.md). The reviewed publication branch removes personal resume paths from its current tree without merging unrelated local history; older GitHub history remains unchanged.

## 2026-09-30: precision-focused policy 2.0

Changed standalone structural, keyword-density and experimental-model alarms to advisory evidence. Review now requires a direct instruction cue or sustained skill repetition; removed three ambiguous phrase cues and clarified findings in the UI. Froze policy code hashes and evaluated once on 100 fresh source groups: 0/200 no-added-attack PDFs flagged, 100/100 controlled attacks detected. The group-level false-positive upper bound is 2.95%; natural attack accuracy and cheating probability remain unvalidated. See [precision policy record](docs/progress/PRECISION_POLICY_2026-09-30.md) for the exact methods, tradeoffs, hashes and checks.

## 2026-09-30: controlled PDF benchmark and paper record

Built a deterministic source-disjoint PDF benchmark from 48 public resume layouts and paired controlled variants. Trained an isolated candidate and ran its frozen policy once on 12 reserved source groups. Holdout detected 12/12 known inserted attacks but flagged 13/24 no-added-attack rows, including every benign structural confounder. Added per-family counts, false-positive rate and source-group intervals to the evaluator. This is a controlled edit benchmark, not natural-manipulation accuracy. See [the benchmark record](docs/progress/CONTROLLED_PDF_BENCHMARK_2026-09-30.md).

## 2026-09-30: calibration, PDF research workflow and inspectable evidence

Implemented clean-validation percentile calibration, isolated real-PDF candidate training, hash-verified bundles, guarded final evaluation, exact text anchors, evidence filtering and bounded PDF previews. Acquired 2,484 public Kaggle PDFs with unreviewed labels and provenance. Full offline suite: 116 passed; synthetic candidate training/reload passed. Real-world accuracy and calibrated probability remain unverified. See [detailed repair record](docs/progress/RESEARCH_REPAIR_2026-09-30.md).

## 2026-09-29: invalid-calibration safety

Prevented zero keyword thresholds from producing misleading maximum signals. Invalid keyword calibration now yields explicit missing coverage and no combined percentage, while available evidence remains reviewable. Added threshold diagnostics and regression coverage. See [follow-up record](docs/progress/ENHANCEMENT_2026-09-29.md).

## 2026-09-26 to 2026-09-28: correctness, runtime, interface and ownership

- Unified CLI/API analysis, fixed scaling and class-probability selection, separated policy from score, and made missing/partial coverage explicit.
- Fixed keyword alias boundaries, scoped injection exceptions, improved PDF trace heuristics and bounded explanation work.
- Preserved source lineage for group-disjoint dataset splitting; separated historical proxy experiments from real-PDF evaluation; moved mutation studies to validation only.
- Removed per-row model loading and failing nested-CV diagnostics; made optional XGBoost explicit and default worker counts bounded.
- Added lazy isolated inference, request validation, concurrency rejection, a hard deadline, temporary-file cleanup and safe error responses.
- Rebuilt the maintained frontend with the user's light/dark references, a persistent theme toggle, responsive input/results, coverage and evidence, export and honest unavailable lab states.
- Added ownership/reuse notices and an in-app policy page. New reserved-rights additions do not revoke earlier MIT permissions; the prior license is preserved.
- Full implementation suite: 73 passed, including cached-model integration and synthetic PDF checks. No held-out dataset used and no improved accuracy percentage claimed.

Exact changes, commands, screenshots, remaining limitations and package records: [enhancement record](docs/progress/ENHANCEMENT_2026-09-26.md). Earlier entries below are historical, not current release certification.

This document tracks the step-by-step evolution of the ATS Final Boss project, from its initial prototype to its current rigorous, defense-in-depth architecture.

## Phase 1: The Initial Prototype
**State:** The project had a brilliant conceptual foundationâ€”using a multi-modal ensemble (Statistical, Structural, and Semantic) to defend against LLM-era HR attacksâ€”and featured a highly polished Scrollytelling UI.
**Issues Identified:**
* The ML evaluation was poorly structured.
* The ablation study compared incompatible models (Stacking Ensemble vs individual modules).
* Module A (Keyword Stuffing) had a normalization bug leading to 0% recall on text attacks.
* Module C (Prompt Injections) relied on brittle exact-string matches (e.g., "ignore previous instructions") that were easily bypassed.
* The API server silently swallowed errors (returning HTTP 200 for everything).
* The repository contained 500MB+ of unrelated zip files and personal CVs.
**Reason for Iteration:** The project was conceptually strong but technically fragile. In a strict capstone evaluation, the fabricated/flawed ML metrics and vulnerable detection logic would result in failure. We needed to transition from a "good prototype" to a "credible, scientifically sound defense system."

---

## Phase 2: Evaluation Rigor & Truthfulness
**Changes Made:**
1. **Repository Clean-up:** Surgically removed `PROJECTS FOR CV/` and legacy `.zip` archives from the git history to keep the repository focused and under GitHub's push limits.
2. **Evaluation Script (`run_experiments.py`):** Created a unified, repeatable pipeline to test the dataset. 
3. **Apples-to-Apples Ablation:** Corrected the methodology so the ablation study now trains a balanced `LogisticRegression` for every feature combination (`A`, `A+B`, `A+C`, `A+B+C`), moving the Stacking Ensemble to a separate benchmark.
4. **Honest Reporting:** Updated the README and benchmark outputs to clearly separate the text-based "Module B Proxy" from the actual PDF Forensics detector, ensuring no fabricated claims were made about ML performance.
**Reason for Iteration:** Evaluators and professors check methodology first. If the ablation study is comparing apples to oranges, or if metrics are manually typed in a README rather than generated from a script, the project loses all academic credibility.

---

## Phase 3: Module Hardening
**Changes Made:**
1. **Module A (Keyword Normalization Fix):** Discovered and fixed a critical thresholding bug. The evaluation script was incorrectly comparing normalized probability outputs (0.0 - 1.0) against raw frequency thresholds, causing all Type A attacks to slip through. It now correctly uses a 0.5 decision boundary.
2. **Module C (Regex Prompt Injections):** Scrapped the exact-match string arrays. Replaced them with robust `re` pattern matching (`INJECTION_PATTERNS`) to catch obfuscations, spacing tricks, and variations (e.g., `r"ignore\s+(all\s+)?previous\s+instructions?"`).
**Reason for Iteration:** A defense system that fails to block attacks is useless. Module A was failing entirely due to a math bug, and Module C was trivial to bypass by just adding a space. We iterated to ensure the modules actually do what they claim to do.

---

## Phase 4: Infrastructure, Security & Testing
**Changes Made:**
1. **Real PDF Forensics Testing:** Used `reportlab` to dynamically generate real malicious PDFs during testing (a normal PDF, a PDF with tiny hidden fonts, and a white-on-white text PDF). Added tests to ensure PyMuPDF (`fitz`) correctly flagged them.
2. **API Hardening (`server.py`):** Updated the local HTTP server to enforce a 5MB payload limit and return proper standard HTTP error codes (`400 Bad Request`, `413 Payload Too Large`, `422 Unprocessable Entity`, `500 Internal Server Error`) instead of burying failures in HTTP 200 responses.
3. **End-to-End Testing:** Created `tests/test_api.py` to ensure the simulated Stacking Ensemble outputs expected verdicts for clean text, keyword-stuffed text, and prompt-injected payloads. Fixed API assertions to correctly test the length-normalized keyword scoring.
4. **Multiprocessing Pipeline:** Rewrote `evaluate.py` to use `concurrent.futures.ProcessPoolExecutor`, drastically reducing the CPU time required to extract `SentenceTransformer` embeddings across the dataset.
**Reason for Iteration:** Stability and proof. To prove that Module B (PDF Forensics) works, we needed automated tests generating malicious PDFs. To prove the API is robust against bad payloads, we needed HTTP constraints. Multiprocessing was added to make iterative testing feasible without waiting an hour for feature extraction.

---

## Phase 5: Final Metrics Validation (Current)
**State:** Running the optimized, multi-core `run_experiments.py` script to generate pristine, unfabricated metrics. The final results will reflect the true performance of the hardened architecture.
**Reason for Iteration:** The final step to complete the capstone lifecycle: running the true, hardened pipeline against the dataset and documenting the final, scientifically generated results into the `results/` folder and `README.md`.

## Phase 6: E2E Methodology and Calibration Hardening (Current)
**Changes Made:**
1. **Objective-Based Calibration:** Replaced the arbitrary 95th-percentile threshold configuration with a validation-set F1-maximization search for both Module A and Module C. The system now optimizes for defense utility rather than statistical percentiles.
2. **Module A Math Fix:** Fixed a major bug where multi-word keywords added 0-index positions, which artificially deflated the positional variance (concentration) metric. Module A now maps keywords to true positional indices via regex word boundary matching.
3. **Dataset Realism:** Improved the data injector to add commas, bulk formatting, and single-keyword repetition to Type A. Added diverse prompt injection payloads to Type D.
4. **Hybrid System Evaluation:** Modified the testing scripts and meta-classifier architecture to formally decouple ML-only predictions from Hybrid (ML + Rules) predictions, clarifying exactly which layer stops prompt injections.
5. **Ablation Transparency:** Added a standard LogisticRegression(A+B+C) baseline to the main benchmark to explicitly prove whether the Stacking Ensemble is justified over a simpler model.
**Reason for Iteration:** Statistical rigor. Thresholds chosen without a defined objective are academically indefensible. Furthermore, the math error in Module A actively hindered detection of multi-word skill stuffing. By validating the ML vs Hybrid approach, we provide full transparency into how prompt injections are actually caught in a production environment.
