# External challenge protocol — October 3, 2026

This protocol is specified before inspecting detector outcomes. It evaluates the
current input-review policy, not hiring suitability, authenticity, calibrated
cheating probability, downstream attack success or deployment approval.

## Frozen question and cohort

Does the unchanged detector flag independently authored, controlled PDF edits
from HiringAudit, and what additional review burden appears on that publisher's
unmodified synthetic originals? Acquisition is pinned to Hugging Face revision
`81a0f6b1a5c3254371e6304af9dafdc533b6c9d5` of
[PD777/HiringAudit-adversarial_cv_dataset](https://huggingface.co/datasets/PD777/HiringAudit-adversarial_cv_dataset).
The publisher states that the data are synthetic; its MIT license and generation
provenance are recorded by acquisition. Publisher attack assignments are retained
as supplied, rather than upgraded to independent human intent labels.

Select up to 300 source groups in SHA-256 order of
`external-challenge-20261003-v1:<source_group>`, retaining each original and every
supplied attack PDF within the selected group. Exact original-byte and normalized
original-text duplicates are excluded at group level before scoring. Originals
are screened against every original PDF in the previously consumed Kaggle corpus;
matching groups are excluded. Exclusions and their denominators are recorded.
Semantic/person identity and shared generator/template independence remain
unverified. Do not exclude missing-extraction, malformed, oversized or unsupported
attack-channel cases to make performance look better: retain attempted outcomes.
If publisher metadata cannot establish a case assignment, stop the freeze.

The primary study is paired across variants and methods, not an assumed 20%
attack-prevalence population sample. The previous 20% Kaggle study remains an
adverse development result. No apparent prevalence-dependent precision from this
new challenge is advertised as customer precision.

## Frozen methods

Run real local pinned MiniLM and the existing data-only classifier. Preserve
coefficients and thresholds; threshold provenance remains `legacy_unverified`.
A new manifest binds those same parameters to current policy bytes, explicitly
unapproved. No training, threshold selection or detector changes use this cohort.

Compare on identical PDF bytes: full review policy; direct-cue-only;
repetition-only; structural-advisory-only; legacy classifier at 0.5; a fixed
English regex baseline (`ignore previous instructions`, `rank me`, `score to 100`).
Individual-signal comparisons are shadow decisions from the same full pipeline,
not performance/cost claims for separately optimized services. Unsupported or
incomplete coverage cannot become a clean prediction in any arm. Partial positive
evidence is recorded separately from complete detection.

## Outcomes, uncertainty and reporting

Primary: complete flagged/missed added-edit cases, complete control review burden,
and all-attempt completion/partial/insufficient/error counts. Report every attack
family separately, including security goals beyond score inflation. Held cases
do not prove attack prevention. Use 1,000 paired source-group bootstrap draws
(seed 20261003) retaining all related variants. Report paired gains/losses and
full-minus-comparator flag-rate deltas; a positive control delta means extra burden.
Row Wilson intervals are secondary. Zero-event bootstrap intervals can collapse;
also show the independent-group exact one-sided bound and its assumptions when
all controls are observed. Leave-one-family-out estimates are sensitivity checks,
not evidence of unseen-family learning or confirmatory multiple testing.

Descriptive challenge targets: lower 95% source-bootstrap bound of complete
added-edit flag rate at least 90%, and upper uncertainty bound of control review
burden below 2%, with no hidden incomplete-case exclusions. These are study targets,
not launch gates or established natural-world sensitivity/specificity. Record
failed targets. No post-result tuning or cherry-picked rerun replaces this receipt.

Freeze case hashes, acquisition manifest, all runtime/evaluation Python source,
keyword assets, model/embedding manifests, environment and this protocol before
opening an exclusive observation receipt. Verify them again after execution.
No remote LLM receives résumé content. Raw data and observations remain ignored;
publish aggregate results, hashes, code and limitations only. Any interrupted run
is retained and explicitly disclosed; do not silently resume or overwrite it.

## Evidence still required beyond this study

Independent blinded adjudication; natural candidate/attack cohorts; broader
multilingual/OCR coverage; realistic downstream screener outcomes; calibration;
fairness and deployment evidence remain separate requirements. External authorship
reduces shared attack-author bias but does not remove synthetic generator bias,
template correlation, label uncertainty or selection effects. This protocol can
support a bounded research claim; it does not guarantee journal acceptance.
