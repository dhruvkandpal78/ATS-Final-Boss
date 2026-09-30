# Research and evidence repair — September 29–30, 2026

## Delivered changes

- Module A and C share clean-validation P95 calibration. Empty, invalid, single-class, nonfinite and nonpositive results are rejected; F1 calibration is explicitly unsupported. No epsilon or invented saved threshold is substituted.
- Shared analysis reports missing calibration and preserves independent instruction-cue findings even when semantic scoring is unavailable.
- The legacy proxy runner now uses train/validation only, requires disjoint source IDs, and writes isolated research outputs. It cannot overwrite deployed models or global thresholds.
- `src/evaluation/train_pdf_candidate.py` trains LogisticRegression from actual deployed PDF detector features. It requires explicit labels, source-disjoint manifests and no identical PDF bytes across splits. Partial extraction fails closed. Candidate weights, scaler, thresholds and configuration are frozen with hashes, source provenance and dependency versions.
- Candidate loading verifies bundle hashes and feature order before deserializing trusted local weights. These checks detect accidental changes; they are not signatures or protection against an attacker replacing both files and manifest.
- Final holdout CLI requires an explicit candidate and `--final-evaluation`, checks development overlap, refuses existing reports, and records first access before opening labels. A failed evaluation also consumes that candidate's local receipt. This is a local guard, not a tamper-proof global test registry.
- Instruction findings expose exact half-open Unicode code-point spans in original submitted text. Ambiguous normalization mappings abstain; spans are capped at 20. UI supports source highlighting and detector/severity filters.
- PDF evidence previews show up to three finding pages, at most 900 pixels per side and 2 MiB PNG data in total, with transformed/clipped trace regions. Rendering is on demand for API results, not training. Preview images are omitted from JSON export and not persisted by the app.

## Public data acquisition

Downloaded version 1 of [Snehaan Bhawal's Resume Dataset](https://www.kaggle.com/datasets/snehaanbhawal/resume-dataset). Kaggle's public metadata lists CC0 and PDF/string formats. The archive yielded 2,484 unique PDFs. Archive SHA-256: `b12c4ab34df707ad2cc64312c016509cad9b6c93b0baed7a6a2c7cbd6b2b7aa4`.

Local acquisition: `data/external/kaggle-resume-v1/`; per-file hashes and source identifiers are in `provenance.json`. Every manipulation label remains null/unreviewed. Files are content-addressed and kept under ignored data/, and archive paths are never trusted for extraction. Dataset content is not executed or treated as instructions. Existing raw resumes may originate from the same corpus; downloading again does not create an independent benchmark.

Also investigated [CrackedPDFs](https://huggingface.co/datasets/volkthienpreecha/crackedpdfs): its publisher describes MIT-licensed synthetic matched benign, confounder and injected PDFs. It is a useful future structural challenge set, not authentic observed resume manipulation. Its final split was not downloaded/evaluated. [HiringAudit](https://huggingface.co/datasets/PD777/HiringAudit-adversarial_cv_dataset) is explicitly synthetic and stores CV Markdown, so it was not substituted for real PDF evidence. The minimally documented d4rk3r raw PDF corpus was not selected over the versioned Kaggle source.

## Verification

- Full offline suite: 116 passed in 29.85 seconds.
- Focused final evaluation, preview, candidate and artifact contract checks after the last edits: 8 passed in 55.25 seconds. `node --check` and `git diff --check` passed; Git reported only line-ending conversion warnings.
- Generated 16 synthetic engineering PDFs across 8 source groups; candidate training completed with cached MiniLM. Positive P95 thresholds were produced without using any held-out dataset.
- Reloaded candidate `.test-tmp/pdf-candidates/pdf-20260929T183347Z-78d3265b` through the deployed loader: complete synthetic PDF analysis, uncalibrated score, review decision and one rendered evidence preview. This is an engineering smoke test, not an accuracy benchmark; the template-derived candidate was not deployed.
- JavaScript syntax check passed. A live browser run on the synthetic instruction sample displayed the calibration limitation, a direct-instruction finding, and an exact highlighted `Ignore previous instructions` span (characters 76–104). The PDF preview was verified through the deployed service and rotated-page tests; a browser screenshot/PDF interaction could not be saved because automatic approval review reported exhausted workspace credits. No visual PDF-browser verification is claimed.

## Still unresolved scientifically

The downloaded corpus lacks verified manipulation labels. Human-reviewed labels, near-duplicate auditing beyond byte hashes, a representative reserved benchmark, probability calibration and uncertainty evaluation are still required before a credible real-world accuracy/probability claim. Existing deployed zero keyword threshold remains disabled rather than replaced by synthetic smoke thresholds. OCR, full PDF occlusion reasoning, causal explanations and public-production hosting remain outside the delivered implementation. No claim that every originally identified research limitation is solved.
