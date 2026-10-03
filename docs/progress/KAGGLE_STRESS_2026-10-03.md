# Large controlled Kaggle execution — October 3, 2026

## Request and scope

Downloaded a large real-PDF Kaggle corpus and tested the actual current PDF pipeline
with exactly 20% deliberately injected attempts. This measures response to known
edits and unmodified control burden; originals have unknown natural manipulation
labels. No threshold, detector or model tuning followed the measured outcomes.

Fresh version-1 download of Snehaan Bhawal's Resume Dataset contained 2,484 unique
PDFs; its archive hash matches the previous pinned acquisition. All nine earlier
development/holdout CSVs were excluded (184 sources), alongside two normalized-text
duplicates and three sources to keep exact 20% assignment. Final: **2,295 unique
sources, 1,836 unmodified and 459 injected**. Each original contributes one final case.

## What changed

- Added `scripts/run_kaggle_stress.py`: deterministic selection/assignment, source
  byte integrity and containment for both selected/excluded records, extraction
  checks for every inserted PDF payload, exclusive protocol/receipt creation,
  pinned V2 candidate and offline safetensors embedding loading, explicit CPU
  execution, privacy-minimized observations and pre/post execution code checks.
- Added ten fixed intervention families, including oblique variants deliberately
  capable of exposing lexical evasion. Attack-page generation preserves original
  layouts; artificial family balance and supplement pages remain generator limits.
- Added meaningful harness checks for exclusions, changed bytes, traversal,
  successful PDF intervention extraction and correct separation of abstentions.
- Added a maintained protocol, aggregate result and updated README, architecture,
  status, issue ledger and changelog. Raw PDFs, identifiers, per-case receipts,
  weights and machine-specific manifests remain ignored local material.

Existing local research parameters were explicitly migrated to V2 data-only JSON;
source provenance was retained, old validation/approval claims were discarded and
deployment approval remains false. Actual MiniLM CPU inference used a local pinned
safetensors export. No document content was sent to an external model API.

An initial unopened build was superseded only to explicitly record CPU execution
and candidate identity. Its frozen output/disposition remains locally preserved.
There were no observations then. Final selection, labels, payloads, detector rules
and thresholds were unchanged, and the final code was frozen before measurement.

## Measured outcome

| Cohort | Complete review | Partial review | Complete no-signals | Insufficient | Runtime error |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1,836 unmodified originals | 0 | 0 | 1,813 | 23 | 0 |
| 459 injected attempts | 272 | 3 | 182 | 2 | 0 |

The 182 complete no-signals are detector misses **against the intended edit label**,
not demonstrated successful downstream attacks. Base64, Spanish and conditional
mimicry each produced 46 complete no-signals. Homoglyphs produced 44 complete
no-signals and two insufficient cases. Direct/hidden/zero-width/repetition families
received reviews, including three partial analyses requiring continued hold handling.

Zero original flags is a false-positive proxy, not verified population accuracy;
23 insufficient originals are separate operational burden. The artificial 20%
attack share and authored templates are not natural prevalence/behavior. Person-level
and semantic near-duplicate independence, fair performance, scanned/OCR coverage,
independent labels, unseen families and downstream/customer benefit remain open.

## Verification

- **688 offline tests passed**, five skipped, three provisioned integration tests
  deselected; final run included the CPU/candidate initializer clarification.
- **13 focused harness checks passed**; real Unicode font/PDF extraction checks
  separately passed for the two Unicode intervention types.
- Actual pinned-model corpus run completed every case, with no runtime errors,
  in 703.687 seconds on two local CPU workers. This is not an HTTP load test or SLA.
- Separate metadata review verified exact composition, stored uniqueness, nine
  exclusion manifest hashes, zero previous source/model-development overlap and
  frozen code/model bytes. It did not establish clean ground truth from PDF contents.
- Independent receipt reconciliation verified all 2,295 indices, case assignments,
  cohort partitions, ten family tables and evidence digests. A second reviewer
  independently confirmed the same raw-receipt counts.

See [the full measured result and digests](../../results/reports/kaggle-stress-20pct-20261003.md)
and [reproduction protocol](../research/KAGGLE_STRESS_PROTOCOL.md). Hosted CI and
production artifact acceptance remain separate; this result grants no deployment approval.
