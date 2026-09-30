# Controlled PDF benchmark on public resume layouts

This record is for the project team and the research-paper collaborator. The benchmark tests whether the **current review policy** detects edits added by a controlled script to public resume PDFs. It does not estimate the prevalence of cheating or establish accuracy on naturally occurring manipulation.

## Source and protocol

- Source: [Snehaan Bhawal's Resume Dataset, Kaggle version 1](https://www.kaggle.com/datasets/snehaanbhawal/resume-dataset), listed CC0 by its publisher. Download archive SHA-256: `b12c4ab34df707ad2cc64312c016509cad9b6c93b0baed7a6a2c7cbd6b2b7aa4`.
- `scripts/build_controlled_pdf_benchmark.py` selected 48 unique source PDFs in a deterministic hash order, subject to size, page and extractable-text bounds. It kept each source and its variants in one partition: 24 training, 12 validation and 12 holdout sources. The generated corpus contains 144 PDFs.
- Every source contributed an unchanged PDF (label 0), a hidden benign note as a structural confounder (label 0), and one of four known edits (label 1): invisible instruction, white instruction, visible instruction, or keyword repetition. Thus labels mean **known added attack**, not verified honesty of the original PDF.
- Candidate training used real PDF detector features and clean-validation P95 thresholds. The legacy synthetic text proxy and global deployed artifacts were not used. Candidate bundle: `results/candidates/pdf-20260930T081435Z-065f2381/` (local, ignored); the manifest freezes source and artifact hashes.
- Holdout was evaluated once with `--final-evaluation`, after candidate creation. Receipt SHA-256 for the holdout manifest: `234fd671bbd0ca2c7639894d7a3b6eb472774270f31aaa542ef0832718189217`. The receipt prevents another local run for this candidate. No post-holdout threshold or policy change was made.

## Results of the frozen current review policy

Validation (36 PDF rows): model F1 0.880, ROC-AUC 0.958; policy precision 0.462, recall 1.000, F1 0.632. These are development estimates.

Holdout (36 PDF rows, 12 source groups): TP 12, FP 13, TN 11, FN 0. Policy precision **0.480**, recall **1.000**, F1 **0.649**, and false-positive rate on no-added-attack rows **0.542**. The separate uncalibrated model score had ROC-AUC **0.993**. All 12 benign structural confounders were flagged; 1 of 12 unchanged originals was flagged. All 12 known injected variants were flagged (3 in each of four families).

Source-group bootstrap, 1,000 draws: F1 95% interval [0.615, 0.667]; false-positive-rate interval [0.500, 0.625]. These intervals capture sampling variation over only 12 source groups, not label uncertainty or deployment shift. The frozen generated report is at `results/reports/kaggle-controlled-v1-holdout.md` locally; its SHA-256 is `796ca2431dfde19c8447fca63b75c22ca0a2cd58873887d0d5b0b43ab7585c7b`.

## Interpretation and next gate

The structural rule catches intentionally hidden text but also treats a hidden benign note as needing review. This is the dominant measured false-positive failure. These PDFs preserve real resume layouts, but the edits and labels are synthetic. Source originals were not manually adjudicated for pre-existing manipulation, and the selection excludes scanned or unsupported PDFs. The observed recall does not predict performance on natural attacks or new attack families. The model score is uncalibrated and must not be described as a probability of cheating.

The next scientific step is a new development cycle focused on distinguishing malicious instructions from benign structural oddities using **training and validation only**, plus independent human review of a representative untouched corpus. A new untouched benchmark would be required for the changed policy. Do not reuse this consumed holdout to choose a rule or report a post-tuning result.

## Engineering verification and publication

Focused regression checks passed: 5 tests covering source-disjoint benchmark generation, confusion counts and confounder reporting, source-group intervals, validation-only studies, and candidate training safeguards. The initial restricted run could not access its Windows temporary directory; the approved rerun passed. These tests used synthetic fixtures and did not reopen the consumed research holdout. Git whitespace checks passed.

Local candidate bundles are ignored because they contain source hashes and machine-specific paths; only code, documentation, tests and the aggregate report belong in this change. GitHub publication is pending: automatic approval review rejected the push because the local branch's older history includes personal resume PDFs and differs from the remote history. The team should publish reviewed source changes through a clean branch based on the remote repository, without exporting that local history. The aggregate report and this record should accompany the code so the paper preserves the measured false-positive limitation.
