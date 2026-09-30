# Precision-focused review policy 2.0

## Problem and implemented change

The first controlled benchmark reported a 54.2% false-positive rate because policy 1.0 automatically recommended review for hidden text, high keyword density or a positive experimental classifier prediction. Hidden benign notes and ordinary technical resumes can meet those conditions. Clean-validation P95 thresholds are useful anomaly indicators, but cannot establish near-zero false positives for an OR-combined review rule.

Policy 2.0 recommends review for direct screening instruction cues or sustained, contiguous skill-keyword repetition. Structural oddities, keyword density, semantic variance and positive experimental model predictions remain available as advisory evidence. They do not independently recommend review. The score remains unchanged and uncalibrated. Missing extraction/coverage still yields insufficient evidence rather than clearance. Disabled optional-content groups still mark coverage partial.

The repetition gate requires at least eight exact copies, at least 32 tokens, and at least half the repeated sequence's tokens to be skill terms; it examines sequences of at most 12 tokens. Alias, Unicode compatibility and invisible-control normalization are applied. These fixed engineering limits favor precision and will miss shorter, dispersed or varied stuffing. They were fixed before opening the new holdout.

Removed standalone `top match`, `as an AI` and `new instructions` cue patterns because ordinary retrieval/research/project descriptions can contain them. Remaining direct cue patterns still use local quote/example handling. Other ambiguous cues and paraphrased attacks need future independent study. This is evidence triage, not a determination of honesty.

Each finding now exposes `review_trigger`. The interface labels findings as advisory or supporting review and says “No actionable manipulation evidence detected” when the precision gate does not fire, while keeping advisory findings visible. Compatibility decision enum values are preserved; policy version is now `2.0`. Reasons distinguish repetition and direct instruction triggers from density, structure and experimental model advisories.

## Fresh benchmark and freeze

The Kaggle version-1 corpus and controlled edit recipes are the same source/protocol as [the earlier benchmark](CONTROLLED_PDF_BENCHMARK_2026-09-30.md). This new cycle skips the first 48 eligible sources in the deterministic hash order, excluding every source from the consumed earlier benchmark without reopening its held-out labels or PDFs. It selects 136 new sources: 24 training, 12 validation and 100 holdout groups, totaling 408 PDFs. Each group contributes an unchanged original, hidden benign note and known added attack. Labels describe **known added attacks**, not independently verified honesty of the originals. Four attack families are scripted and balanced; this is a new source holdout for known attack recipes, not an unseen-attack-family test.

The initial relative-output generation exposed invalid manifest paths before training; the builder now resolves paths absolutely. That unused directory was not evaluated. The corrected corpus is `data/benchmarks/kaggle-controlled-v2-fixed/` (ignored).

Candidate: `results/candidates/pdf-20260930T083903Z-3048f4c0/` (ignored, not deployed). Validation policy precision/recall/F1 were all 1.000 over 36 rows; model F1 was 0.800, recall 0.667 and ROC-AUC 0.955. Candidate manifests now freeze policy version and hashes of the service, review gate and all three detectors. The final evaluator rejects changed or incomplete policy code hashes before opening labels. Final evaluation receipts still prevent another local run for a consumed candidate. The helper refactor and tests after evaluation did not change the frozen decision code.

The candidate was frozen before a single final run on 300 PDFs from 100 untouched source groups. No post-holdout policy/threshold tuning was performed. Aggregate report: [kaggle-controlled-v2-holdout.md](../../results/reports/kaggle-controlled-v2-holdout.md).

- TP 100, FP 0, TN 200, FN 0; observed review-policy precision, recall and F1: 1.000.
- No-added-attack false-positive rate: **0/200 (0% observed)**. Unchanged originals: 0/100 flagged; benign structural confounders: 0/100 flagged.
- Each attack family: 25/25 flagged (invisible instruction, white instruction, visible instruction and keyword repetition).
- Separate uncalibrated model ROC-AUC: 0.8854; model score is not the review policy or a cheating probability.
- Source groups with any false-positive variant: 0/100. Exact one-sided 95% upper bound on that group-level rate: **2.95%**, assuming independent groups. Paired variants are correlated; they must not be treated as 200 independent sources. Degenerate bootstrap intervals at zero do not prove zero population risk.

Candidate-manifest SHA-256: `5fcff261cb33255a69979797020ccccc1d2b337f1a13c928bafc7af3f859dab6`.
Protocol SHA-256: `eb94e9ca573175e0cdaf61f9b043af14e5746fc67f085bac4e3841f88c66052b`.
Holdout-manifest SHA-256: `16bda11e42fdc18334889287a8641477f4157456a75588c63174e2f715ad0c65`.
Report SHA-256: `1109fc41af40c15fdc546a2bf7a2a156409370977a095e79c8166923d159f509`.

## Validation and limits for the research paper

43 focused tests passed, and the final complete offline suite passed **131 tests**, including policy freeze integrity and nonzero uncertainty bounds at zero observed false positives. Tests pair benign hidden notes and skill-heavy text with actionable instruction/repetition attacks, and verify that a 99% experimental model score cannot independently trigger review. JavaScript syntax and Git whitespace checks passed. Visual browser verification was not performed in this cycle.

This is a substantial improvement on a fresh controlled source sample. The samples, partitions and policy versions differ from the earlier evaluation, so the percentages are not a paired comparison. Groups are distinct source PDF bytes; person-level independence and near-duplicate semantic overlap were not audited. No claim of zero real-world false positives, general attack recall or calibrated probability is supported. New attack wording, complex PDF visibility, scanned PDFs, natural manipulation labels and broader benign resume populations remain release gates. The next policy revision requires new untouched evaluation data; this holdout is now consumed.

GitHub publication remains pending because automatic approval review blocked exporting older local history containing personal resume PDFs. Source changes, tests and aggregate research records are committed locally without the datasets or candidate bundles.
