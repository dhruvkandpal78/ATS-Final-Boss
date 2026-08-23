# Project Memory & Status Tracker

## Current Status
- **Date**: Ongoing
- **Phase**: Phase 4 (Final Codebase Polish & Write-up Preparation)
- **Currently Working On**: Pipeline is complete. Preparing for final walkthrough and academic manuscript planning.

## Completed Tasks
- [x] Initial requirement ingestion from the Research Advisory Document.
- [x] Refined `PRD.md` to reflect adversarial ranking attack framing and input-level vs model-level defense distinctions.
- [x] Refined `Architecture.md` to include SHAP explainability and specific PDF forensic targets (rendering modes).
- [x] Refined `rules.md` to establish strict academic boundaries, fairness assumptions, and dual-use ethics.
- [x] Refined `phases.md` to integrate adaptive adversary testing and SHAP integration precisely into the 6-week timeline.
- [x] Created `design.md` for CLI and data visualization aesthetics.
- [x] Refined `README.md` to serve as a high-level, CV-ready project overview.
- [x] Setup `requirements.txt` with PyMuPDF, SHAP, and sentence-transformers.
- [x] Download Kaggle resume dataset via `kagglehub`.
- [x] Execute `cleaner.py` (Produced 2,476 clean baseline resumes).
- [x] Execute `injector.py` (Injected 800 adversarial resumes including Type D prompt overrides).
- [x] Execute `splitter.py` (Strict 60/20/20 train/val/test splits safely secured).
- [x] Implement Module A (Keyword Density Detector).
- [x] Implement Module B (Deep PDF Structural Forensics).
- [x] Implement Module C (Semantic Coherence Scorer with MiniLM-L6-v2 and SHAP stub).
- [x] Implement Fairness Auditor (EEOC 80% Rule).
- [x] Implement Meta-Classifier (`src/models/meta_classifier.py`).
- [x] Implement Base Metrics & Bootstrapping (`src/evaluation/metrics.py`).
- [x] Implement Visualization Curves (`src/evaluation/curves.py`).
- [x] Execute Phase 3 Evaluation (`src/evaluation/evaluate.py`).
- [x] Generate `evaluation_report.md` with final test-set metrics and Bootstrapped F1 bounds.

## Pending Tasks
- [ ] Review final outputs with user and adjust thresholds if necessary.
- [ ] Prepare final repository zip/handoff for manuscript writing.

## Active Files
- `results/evaluation_report.md`
