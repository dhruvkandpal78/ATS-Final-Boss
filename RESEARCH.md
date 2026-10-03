# Research and methodology

This project inspects document-manipulation signals for human review. It does not establish a candidate's intent, honesty or suitability. Current runtime details are in [Architecture](docs/Architecture.md); the [release gate](docs/COMPANY_RELEASE_GATE.md) lists the evidence still required before customer use.

## Detector scope

- Module A measures keyword density and repetition. Dense technical skills alone are advisory under policy 2.0.
- Module B examines PDF text traces and structural attributes. Full pixel visibility, clipping/occlusion, complex optional-content behavior and OCR comparison remain incomplete. The rendered-region inspector in `src/research/pdf_visibility.py` is experimental and is not a deployed model feature.
- Module C uses cached, off-the-shelf MiniLM embeddings for sentence-window coherence. Screening instructions are detected by separate conservative lexical cues, which can miss paraphrases, encoding, multilingual and mixed-script text.
- The meta-classifier combines standardized features. Its score is experimental, not a calibrated cheating probability. Invalid keyword calibration and incomplete required coverage suppress the combined score.

Rules and model scores are separate. The deployed review policy does not jitter thresholds, and the lab/adaptive endpoints are unavailable. Evidence highlights locate observations; they are not SHAP attributions or proof of intent.

## Data and evaluation

The [external HiringAudit challenge](results/reports/external-hiringaudit-20261003.md)
is a frozen test of independently authored synthetic interventions on 100 source
groups. Full policy flags 100/1,000 attack assignments, leaving 900 complete
unflagged outcomes; originals receive 0/100 flags. This demonstrates substantial
controlled-challenge failure, not high accuracy. The templates are shared, the
legacy classifier thresholds remain unverified, natural labels are absent, and
the 100-control zero-event bound is 2.95%. The cohort is now consumed for development.

Historical synthetic text-marker aggregate reports are retained in [the results index](results/reports/README.md). Unmaintained plots and per-row exports were removed from the current tree; their prior revision is recorded in the cleanup inventory. They are historical outputs, not current accuracy claims or real-PDF hidden-text validation. The removed external API injector was not part of the maintained pipeline or supported evaluation; its existence never established generalization, human ground truth or permission to transmit resumes.

The [dataset acquisition script](scripts/acquire_resume_dataset.py) retrieves a pinned public PDF corpus with hashes into ignored local storage. These are real layouts with unreviewed manipulation labels. Public availability does not establish natural attack ground truth or permission for every subsequent use.

Controlled benchmarks pair no-added-attack documents with known scripted edits, grouping all variants of each source in one partition. [Policy 2.0's frozen evaluation](docs/progress/PRECISION_POLICY_2026-09-30.md) observed 0/200 no-added-attack false positives and detected 100/100 scripted attacks across 100 holdout source groups. The group-level one-sided 95% upper false-positive bound is 2.95%. These results do not establish zero population false positives, natural attack accuracy or subgroup fairness. The earlier benchmark failures remain recorded in [the controlled benchmark record](docs/progress/CONTROLLED_PDF_BENCHMARK_2026-09-30.md).

Train and validation manifests must retain source lineage. Calibration uses only source-disjoint validation data; zero/nonfinite thresholds stop candidate generation. Freeze configuration, policy code and artifact hashes before a one-time final evaluation. Do not tune against an already consumed holdout. Supported candidate/evaluation commands are in [README](README.md).

## Robustness and remaining evidence

`scripts/check_adaptive_cues.py` runs fixed lexical diagnostic probes without model downloads. Seven authored misses were recorded in [the review response](docs/progress/CURRENT_REVIEW_2026-09-30.md). This small diagnostic is not a representative adaptive attack benchmark or an empirical robustness guarantee.

Natural manipulation labels, independent adjudication, near-duplicate review, subgroup evaluation, source-disjoint probability calibration, complete PDF visibility and customer deployment/security acceptance remain open. Preserve confidence intervals, sample definitions, split provenance and per-attack outcomes when reporting future evaluations. Synthetic demographic fields or lexical diversity proxies do not establish fairness.

Consult [Ethics](docs/ethics.md), [project rules](docs/rules.md), [current status](docs/progress/STATUS.md) and [the issue ledger](docs/progress/ISSUES.md). Historical plans in `docs/archive/` preserve context and do not override these maintained records.
