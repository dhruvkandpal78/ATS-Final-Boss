# ATS Final Boss

**Latest external evidence is adverse:** a frozen challenge of 1,100
publisher-rendered HiringAudit PDFs flagged **100/1,000 supplied attacks**, leaving
**900 unflagged after complete analysis**, with **0/100 original flags** and no
incomplete/errors. The control sample does not establish below-2% false-positive
burden; these are synthetic publisher assignments, not natural manipulation
labels. Earlier known-attack recovery does not establish generalization. See the
[full result, comparisons and uncertainty](results/reports/external-hiringaudit-20261003.md).

A further [targeted paraphrase review](docs/progress/PARAPHRASE_REDTEAM_2026-10-03.md) fixes 11 authored directed commands missed by the prior cues, preserving 14 benign controls and paired visible/hidden PDF routing. JSON references, URL encoding and letter-spaced words still evade the authored diagnostic; no unseen zero-error claim is made.

The [known-case replay](results/reports/kaggle-recovery-development-20261003.md) recovered all 182 previous completed misses: 454 completed and five partial attack reviews, zero completed misses. Unmodified controls remain zero flags with 23 insufficient analyses. This reuses observed attacks and does not establish independent zero error.

The [known-miss recovery record](docs/progress/CUE_RECOVERY_2026-10-03.md) adds bounded passive Base64 views, mixed-token lookalike normalization, narrow Spanish cues and explicit qualification-fabrication checks. The follow-up reuses observed cases and is a development regression, not new independent accuracy. Original results below remain historical.

The [frozen 2,295-PDF Kaggle stress test](results/reports/kaggle-stress-20pct-20261003.md)
used 1,836 unmodified resumes and 459 injected attempts (20%). It recorded zero
unmodified flags, 23 incomplete originals, 272 complete attack reviews, three partial
attack reviews, **182 complete no-signal outcomes on injected documents** and two
insufficient attack analyses. Encoded, Spanish, homoglyph and conditional-mimicry
interventions received no review. Original manipulation labels are unreviewed: zero
flags is a control-burden result, not a proven zero population false-positive rate
or comprehensive injection protection. These edits were not tested for downstream success.

The [latest pre-commit precision review](docs/progress/QUALITY_REVIEW_2026-10-03.md)
reduces known false flags on ATS engineering descriptions and qualification-dependent
workflow instructions, with paired bypass and PDF controls. Results are authored regressions; representative
real-world false-positive rates remain unverified.

Normal inference requires a verified **data-only V2 candidate**. V1 pickle bundles fail closed and need explicit offline migration or new training. See [provisioning changes and regression scope](docs/progress/PRECISION_AND_DATA_ONLY_2026-10-02.md). Real-world false-positive and recall targets remain unverified.

For a local demo using a pinned candidate and offline embedding export, see the
[local analysis setup](docs/LOCAL_DEMO.md).

A research security layer for AI hiring pipelines: document-level forensic inspection and conservative human-review gating before an existing screener. It combines keyword analysis, PDF text-trace heuristics and MiniLM coherence evidence. It does **not** determine honesty or suitability for employment, sanitize a resume, or guarantee that a downstream AI system is protected.

```text
Resume → ATS Final Boss review gate → existing screener (complete no-signals only)
                                  ↘ human review / unavailable-analysis error
```

**Current evidence:** controlled detection demonstrated; incremental downstream protection has **not** been established. The [real hosted feasibility study](docs/progress/REFERENCE_STUDY_2026-10-01.md) observed 0/16 baseline canary successes, 0/8 forwarded protected successes and eight attack holds, with 0/8 control holds. It also exposed identical-input score instability. These are small same-team synthetic observations, not natural-world accuracy or company readiness.

MiniLM measures sentence-window coherence; instruction detection is a separate conservative lexical cue check, not a general semantic prompt-injection classifier. Paraphrased, encoded, multilingual and mixed-script instructions can evade it. The [documentation map](docs/README.md) identifies current specifications and historical planning records.

Copyright © 2026 Dhruv Kandpal. New original enhancements have reserved-rights terms; previously MIT-licensed material and third-party rights are preserved. See [LICENSE](LICENSE), [legacy MIT notice](LICENSE-MIT-LEGACY.txt), and [ownership policy](docs/OWNERSHIP.md). This is a mixed-rights research project, not an unrestricted open-source release of the new additions.

## For an evaluation partner

The proposed first partner is a recruiting or hiring-software team with an IT
owner and control of its downstream screener integration. This is a demand
hypothesis, not a named customer or validated market. A recruiter who cannot
change their ATS pipeline is not assumed to have an integration path.

| Buyer requirement | Current evidence |
|---|---|
| Recall above 90% and false-positive rate below 2% on representative real resumes | **Unverified.** Historical F1/recall/FPR and controlled-edit results are not current field-performance claims. |
| Human review rather than automatic rejection | Implemented review/error routing; findings do not authorize hiring decisions. Customer workflow acceptance is still required. |
| Deployable review API and integration | Versioned REST endpoint, strict server-side SDK and private deployment templates exist. No installed ATS connector or accepted customer gateway is claimed. |
| Named pilot and buyer value | No named pilot evidence is established. The measured local development study showed no incremental score-attack protection before its regression fix. |
| General injection resistance | Lexical checks have known evasions. MiniLM coherence and the experimental meta-classifier are not a validated learned injection defense. |

The next proof is a frozen comparison against a partner's actual screener with
independently reviewed, permitted documents, realistic base-rate reporting and
added review burden. See [the proposed pilot](docs/CUSTOMER_PILOT_STRATEGY.md).
No named customers, traction, pricing validation or production guarantees are
implied by the demo or test count.

## Run locally

Operators can inspect bounded, content-free runtime counters and latency histograms through the [metrics endpoints](docs/OPERATIONS_METRICS.md). Customer monitoring and load acceptance remain separate.

The subsequent [local score/rank development study](docs/progress/REVIEW_ROUTING_STUDY_2026-10-01.md) qualified stable reference routing but found **no added protection**: six of eight authored attack conditions crossed the numeric score threshold without review in both arms. A narrow explicit self-score-command regression fix followed; its downstream benefit and population false-positive rate have not been measured. The original failed protocols and unfavorable results remain preserved.

For a buyer or integration review, start with the [review API and SDK](docs/INTEGRATION.md), [paired downstream evaluation procedure](docs/DOWNSTREAM_BENCHMARK.md), and [customer release gates](docs/COMPANY_RELEASE_GATE.md). The comparison harness imports supplied observations; the separate opt-in reference runners use actual hosted or pinned local models with fictional PDFs. Neither establishes real-world downstream improvement.

Before processing real customer resumes, complete [the single-customer release evidence checklist](docs/COMPANY_RELEASE_GATE.md). It records currently untested operational gates and the supported pilot scope; this repository is not certified company-ready.

Python 3.11 or newer is required. For the proposed single-company customer pilot, see [private deployment](docs/PRIVATE_PILOT.md), [security policy](SECURITY.md), and [customer strategy](docs/CUSTOMER_PILOT_STRATEGY.md). This deployment foundation still requires a verified Linux build and customer gateway integration before real resume processing.

```powershell
python -m pip install -e ".[dev]"
python scripts/doctor.py
python src/app/server.py
```

Open http://127.0.0.1:8000. The interface has a light theme inspired by the supplied white/lavender reference and a persistent charcoal/orange dark theme. The maintained frontend is `src/app/index.html` and `src/app/assets/`; no frontend build step is required.

The private deployment image uses `python -m src.app.asgi`, a single-process Uvicorn/Starlette adapter with bounded inference, admission controls and private startup warm-up. The standard-library server above remains the lightweight local demo. Run `python scripts/check_private_deployment.py` before reviewing a private Compose deployment. The gateway example delegates identity verification to the customer's SSO authorizer; it is not an installed SSO integration.

The server starts without loading models. The first analysis loads trusted local `results/models/meta_classifier.pkl`, `results/models/scaler.pkl`, detector configuration, and cached MiniLM weights. Downloads are disabled by default. Missing dependencies produce an actionable 503 response, not a fabricated result. The diagnostic checks installed packages, model files and embedding config cache without downloading or evaluating data; a successful diagnostic does not certify artifact provenance or full runtime compatibility.

CLI uses the same analysis service:

```powershell
python src/inference.py path/to/resume.pdf --json
python src/inference.py path/to/resume.txt
```

Integrations can use `POST /api/v1/review` for a fixed-vocabulary, data-minimized review result without source text, explanation strings, previews or scores. It uses the same bounded worker and fail-closed availability handling. It does not reconstruct/sanitize a resume or make a hiring decision. See [request/response and downstream separation](docs/INTEGRATION.md).

## Interpreting results

The checked-in keyword threshold is currently zero. This invalid calibration is now reported by `scripts/doctor.py`; keyword and combined scores are withheld until a positive threshold is established using source-disjoint validation data. Available semantic and PDF evidence still runs. Do not substitute an arbitrary threshold to enable a percentage display.

- **Review recommended:** an instruction cue or sustained skill-repetition rule requires human inspection. Density, structural anomalies and experimental model scores remain advisory.
- **Insufficient evidence:** the available input or coverage cannot support a complete analysis.
- **No signals detected:** no configured signal triggered in the completed analysis; this is not a guarantee.
- Model scores and review policy are separate. Rule triggers never increase the displayed numeric score.
- Plain text has no PDF structural evidence and no validated combined model score. Individual text checks still run.
- PDF scores from existing artifacts are **experimental and uncalibrated**: historical training used synthetic structural markers, not an independently validated real-PDF corpus. Incomplete semantic/PDF coverage suppresses the combined score.

Findings expose detector, category, uncertainty and available source anchors. Text instruction cues support exact-span highlighting; PDF findings support bounded rendered previews and trace-region overlays. OCR, complete visibility reasoning, and causal/SHAP explanations remain unimplemented. Highlights locate observations and do not prove intent.

## Local processing limits

The local server binds to loopback by default. It accepts JSON text or a base64 PDF (`POST /analyze`), with limits of 5 MiB raw PDF, 7 MiB encoded request, 20 PDF pages, and 100,000 input characters. Semantic scoring is limited to 20,000 characters with explicit partial coverage. One isolated model worker runs at a time; saturation returns 429, and a 90-second deadline terminates and resets the worker. Repeated attempted worker crashes, timeouts or internal failures trigger a 5-to-60-second capped recovery delay with Retry-After guidance; cooldown requests do not initiate another analysis attempt. Successful validated replies reset recovery. Temporary uploads are deleted on normal completion, errors, and worker timeout. Browser cancellation stops waiting; server work ends on completion or deadline.

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

Use `python -m src.evaluation.prevalence --help` to report supplied confusion counts at explicitly assumed deployment base rates. It calculates aggregate review burden and precision/NPV scenarios, not candidate probabilities or independent validation. Zero observed false positives must not be presented as zero population risk.

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

## Installed runtime

A regular `pip install .` includes the maintained HTML/assets, default JSON configs and both public license notices. `python -m src.app.asgi` serves the local UI from outside the checkout. Model artifacts remain operator-provisioned: set `ATS_MODELS_DIR` to the approved bundle directory for both the API and CLI. Missing artifacts do not produce a replacement model score. Private mode still requires the independent candidate/embedding pins and deployment controls in [the private pilot guide](docs/PRIVATE_PILOT.md).

CI runs `scripts/check_installed_runtime.py` outside the checkout to verify the installed HTTP resources, configuration and lifecycle without model downloads. See [portable runtime verification](docs/progress/PORTABLE_RUNTIME_2026-09-30.md).
