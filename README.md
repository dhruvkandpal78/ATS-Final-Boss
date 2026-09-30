# ATS Final Boss

A local research tool for inspecting resume-manipulation signals. It combines keyword analysis, PDF text-trace heuristics, and MiniLM semantic analysis, and presents evidence for human review. It does **not** determine honesty or suitability for employment.

Copyright © 2026 Dhruv Kandpal. New original enhancements have reserved-rights terms; previously MIT-licensed material and third-party rights are preserved. See [LICENSE](LICENSE), [legacy MIT notice](LICENSE-MIT-LEGACY.txt), and [ownership policy](docs/OWNERSHIP.md). This is a mixed-rights research project, not an unrestricted open-source release of the new additions.

## Run locally

Python 3.11 or newer is required. For the proposed single-company customer pilot, see [private deployment](docs/PRIVATE_PILOT.md), [security policy](SECURITY.md), and [customer strategy](docs/CUSTOMER_PILOT_STRATEGY.md). This deployment foundation still requires a verified Linux build and customer gateway integration before real resume processing.

```powershell
python -m pip install -e ".[dev]"
python scripts/doctor.py
python src/app/server.py
```

Open http://127.0.0.1:8000. The interface has a light theme inspired by the supplied white/lavender reference and a persistent charcoal/orange dark theme. The maintained frontend is `src/app/index.html` and `src/app/assets/`; no frontend build step is required. Existing `web/dist` files are historical and are not served.

The server starts without loading models. The first analysis loads trusted local `results/models/meta_classifier.pkl`, `results/models/scaler.pkl`, detector configuration, and cached MiniLM weights. Downloads are disabled by default. Missing dependencies produce an actionable 503 response, not a fabricated result. The diagnostic checks installed packages, model files and embedding config cache without downloading or evaluating data; a successful diagnostic does not certify artifact provenance or full runtime compatibility.

CLI uses the same analysis service:

```powershell
python src/inference.py path/to/resume.pdf --json
python src/inference.py path/to/resume.txt
```

## Interpreting results

The checked-in keyword threshold is currently zero. This invalid calibration is now reported by `scripts/doctor.py`; keyword and combined scores are withheld until a positive threshold is established using source-disjoint validation data. Available semantic and PDF evidence still runs. Do not substitute an arbitrary threshold to enable a percentage display.

- **Review recommended:** one or more configured rules or model signals need human inspection.
- **Insufficient evidence:** the available input or coverage cannot support a complete analysis.
- **No signals detected:** no configured signal triggered in the completed analysis; this is not a guarantee.
- Model scores and review policy are separate. Rule triggers never increase the displayed numeric score.
- Plain text has no PDF structural evidence and no validated combined model score. Individual text checks still run.
- PDF scores from existing artifacts are **experimental and uncalibrated**: historical training used synthetic structural markers, not an independently validated real-PDF corpus. Incomplete semantic/PDF coverage suppresses the combined score.

Findings expose detector, category, uncertainty and available source anchors. Text instruction cues support exact-span highlighting; PDF findings support bounded rendered previews and trace-region overlays. OCR, complete visibility reasoning, and causal/SHAP explanations remain unimplemented. Highlights locate observations and do not prove intent.

## Local processing limits

The local server binds to loopback by default. It accepts JSON text or a base64 PDF (`POST /analyze`), with limits of 5 MiB raw PDF, 7 MiB encoded request, 20 PDF pages, and 100,000 input characters. Semantic scoring is limited to 20,000 characters with explicit partial coverage. One isolated model worker runs at a time; saturation returns 429, and a 90-second deadline terminates and resets the worker. Temporary uploads are deleted on normal completion, errors, and worker timeout. Browser cancellation stops waiting; server work ends on completion or deadline.

Only the theme preference persists in browser storage. The frontend does not store resume history. JSON export omits submitted source text; findings may still contain document-derived information. Lab demonstrations are explicitly unavailable until validated. The stdlib server is a local demo, not a public production deployment.

## Validation

```powershell
python -m pytest tests/ -m "not integration"
# Requires local research artifacts and cached model weights:
$env:HF_HUB_OFFLINE="1"
$env:TRANSFORMERS_OFFLINE="1"
python -m pytest tests/
node --check src/app/assets/app.js
```

CI runs deterministic tests without model downloads. Generated PDF fixtures use temporary directories, not tracked files. See [the enhancement record](docs/progress/ENHANCEMENT_2026-09-26.md) for exact commands, results, browser evidence and unresolved release gates.

## Research status

Old F1/AUC values in `results/` and historical change entries are retained as historical research outputs, **not current release performance claims**. Keyword normalization, injection-cue handling, structural interpretation and source grouping have changed. A fresh training/validation cycle and independent PDF-ground-truth benchmark are needed before publishing accuracy claims. No held-out dataset was used for the September 26 enhancement verification.

New generated data retains `source_id`; the splitter keeps every source and its variants in one partition. Old CSVs without lineage fail closed and must be regenerated. Group-based row ratios are approximate; attack and category proportions need inspection. Research text-marker feature extraction is explicitly separate from deployed PDF analysis. Adaptive mutation studies use validation data only. The deployed holdout evaluator requires an explicit CSV with `source_id,pdf_path,is_adversarial`:

```powershell
python -m src.evaluation.evaluate_holdout --pdf-holdout path/to/pdf_holdout.csv --models-dir path/to/frozen-candidate --final-evaluation
```

Run final evaluation only after freezing models and thresholds. See [project rules](docs/rules.md), [issue ledger](docs/progress/ISSUES.md), and [change history](CHANGELOG.md).

## Reproducible PDF candidate workflow

`python scripts/acquire_resume_dataset.py` downloads pinned Kaggle resume PDFs into ignored `data/external/`, with hashes and unreviewed labels. Public availability does not establish manipulation ground truth. Review labels before training; all variants of a source belong in the same split.

Provide separate train and validation CSVs with `source_id,pdf_path,is_adversarial` (0 or 1). Paths are relative to their CSV. Then run:

```powershell
python -m src.evaluation.train_pdf_candidate --train-manifest path/to/train.csv --validation-manifest path/to/validation.csv
```

Candidates are saved separately in `results/candidates/`, with thresholds, weights, scaler and a hashed manifest. The deployed model is not replaced automatically. Thresholds use P95 of clean validation scores; degenerate calibration stops the run. The final evaluator requires source IDs, checks development overlap and records a one-time local access receipt. Failed final runs require investigation, not repeated tuning on the same holdout.

For engineering verification only, `python scripts/generate_pdf_smoke.py` generates synthetic PDF fixtures. These are not suitable for real-world accuracy claims. See [September 30 repair record](docs/progress/RESEARCH_REPAIR_2026-09-30.md) for verified results and open research gates.

A [controlled PDF benchmark](docs/progress/CONTROLLED_PDF_BENCHMARK_2026-09-30.md) now measures edits inserted into 48 public resume layouts. Its first frozen holdout found every inserted attack but also flagged every benign structural confounder. These are results for known edits, not validated performance on natural cheating or a calibrated probability. The policy has not been tuned on the consumed holdout.

[Policy 2.0](docs/progress/PRECISION_POLICY_2026-09-30.md) keeps structure, density and experimental model alerts advisory; direct screening instructions or sustained keyword repetition trigger review. On a fresh, once-evaluated source holdout it flagged 0/200 no-added-attack PDFs and detected 100/100 scripted attacks. The group-level 95% upper bound for false-positive risk is 2.95%; natural attack performance remains unverified. Candidates now freeze policy code hashes alongside model artifacts before final evaluation.
