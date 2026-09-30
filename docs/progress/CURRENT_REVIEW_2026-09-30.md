# Current-code response to the external architecture review

The supplied review explicitly relied on README and older PR snippets, not current source. This record distinguishes current implementation from unresolved scientific and operational gaps; it is not a response claiming all criticism is fixed.

| Concern | Current source and change | Remaining evidence |
|---|---|---|
| Silent model fallback | Removed during earlier merge resolution; get_service and load_pipeline require actual artifacts, and private startup verifies pins and warms the real pipeline. Added explicit missing-artifact tests proving no fallback service is cached. | CI synthetic adapters/image smoke do not replace a customer-approved real-model deployment test. No tiny model is presented as real validation. |
| Circular controlled evaluation | Public PDFs provide real layouts, but inserted attacks are authored controlled variants. Prior frozen source-group result remains unchanged: 0/200 no-added-attack observations, not population zero. | Independent natural manipulation labels, reviewer agreement, representative subgroup coverage and near-duplicate adjudication still required. No new holdout tuning or invented labels. |
| Lexical injection evasion | README explicitly separates MiniLM coherence from lexical instruction cues. Added reproducible lexical-only adaptive diagnostics without initializing models: direct/fullwidth/zero-width cues detected, seven authored paraphrase/Unicode/multilingual/encoded/split probes missed. | A replacement classifier requires approved independent labels, measured benign performance, versioned candidate artifacts and fresh evaluation. Broadening current rules silently would invalidate the frozen policy and could raise false positives. |
| Hidden-text coverage | Current Module B already checks invisible trace mode, opacity, tiny fonts, wholly off-page traces, zero-area boxes, background color and partial OCG data. UI now prominently identifies unsupported pixel/layer visibility even when supported trace checks finish. Added separate experimental raster-region inspection to compare extracted trace regions with actual rendered contrast. | OCR/text discrepancy, metadata semantics, complete clipping/layer reasoning and adaptive PDF coverage remain incomplete. Flat pixels are observations, not manipulation proof. New experiment is not integrated into the frozen model/policy. |
| Calibration and three-feature model | Existing loader applies the saved scaler before classification; evaluation tools report precision/recall and group intervals. Scores remain explicitly uncalibrated. | Three-feature logistic regression is a baseline, not an established superiority claim. Reliability diagrams, calibration on independent labels, class/subgroup evaluation and deployment-domain validation remain open. |
| Documentation and history | Added docs/README.md as the map of current canonical specifications; marked old planning documents historical. Changelog and dated evidence remain available to the research teammate. Historical dashboard labels its proxy scores and uses local font fallbacks. | Existing public commit history is preserved. No force-push, history rewrite or deletion of research evidence. Development launch configuration is not runtime architecture. |

## Reproduction

`python scripts/check_adaptive_cues.py` prints only fixed synthetic case identifiers and diagnostic results. It is lexical-only and does not estimate full-system attack success, probability, fairness or population accuracy.

`src.research.pdf_visibility.inspect_pdf_visibility(path)` is an experimental local inspection function. It samples bounded rendered grayscale regions associated with PDF traces and emits coordinates/flags without extracted content. It does not alter API decisions or scores. Native PDF work must receive resource/process isolation before any public input path uses it.

## Publication scope

The free static website export is an interface preview: no backend, uploads or fabricated analysis. Hugging Face currently requires a paid plan to create Docker compute Spaces; Static Spaces remain free. See [preview guide](../PUBLIC_PREVIEW.md) and official [hosting rules](https://huggingface.co/docs/hub/en/spaces-overview), checked September 30, 2026.

Local test results and hosted CI evidence for this patch are recorded in [the implementation record](COMPANY_HTTP_HARDENING_2026-09-30.md). Customer launch is governed by [the release checklist](../COMPANY_RELEASE_GATE.md).
