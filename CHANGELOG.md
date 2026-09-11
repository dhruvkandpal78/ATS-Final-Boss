# ATS Final Boss - Development Journey & Iterations

This document tracks the step-by-step evolution of the ATS Final Boss project, from its initial prototype to its current rigorous, defense-in-depth architecture.

## Phase 1: The Initial Prototype
**State:** The project had a brilliant conceptual foundation—using a multi-modal ensemble (Statistical, Structural, and Semantic) to defend against LLM-era HR attacks—and featured a highly polished Scrollytelling UI.
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
