# Precision regressions and data-only candidate runtime — October 2, 2026

## What changed

Ambiguous technical phrases (system override, role markers, administrator instructions,
output directives, generic rejection and score labels) require hiring/candidate context
in the same sentence. Generic rank/ranking/eligibility words do not themselves establish
hiring context; sports ranking and benefits prose have negative controls. Applicant-directed perfect-match, highest-score and eligibility
commands have explicit cues. Generic gap/qualification-disregard phrases do not
independently trigger review; benign hiring-workflow descriptions cover this case. Quote/example exclusions and original-source evidence
remain shared. Semantic variance, density and the uncalibrated model score remain
advisory; recommendations are for human review, never automatic rejection.

This narrows known false-positive triggers while covering a known missed paraphrase.
It trades some recall for precision: context split across sentences, unfamiliar wording,
translations, encodings and technical prose containing hiring context remain limitations.

## Fixed development comparison

`python scripts/check_instruction_regressions.py` runs 13 internally authored strings
without initializing an embedding model. The same cases were evaluated against the
pre-change `origin/main` Module C at cb490d1 and the working rules:

| Rule revision | Attack cues found / 6 | Attack cues missed / 6 | Benign examples flagged / 7 |
| --- | ---: | ---: | ---: |
| cb490d1 | 3 | 3 | 4 |
| Current development patch | 6 | 0 | 0 |

These are known-specimen lexical regressions, **not independent accuracy or population
false-positive estimates**. They do not measure PDFs, downstream attack success,
fairness, scanned documents or commercial benefit. The unfavorable eight-condition
reference study is preserved; no LLM outcome has been rerun or reclassified here.

## Model boundary and compatibility

Normal CLI/HTTP inference now accepts only a manifest schema 2.0 real-PDF candidate
containing `linear_model.json`, `thresholds.json` and `model_config.json`. The bounded,
closed-schema linear JSON contains three coefficients, an intercept, class order,
scaler mean/positive scale and exact feature order. Inference checks finite inputs,
transforms and logits and preserves sklearn binary prediction/tie semantics. Verified
bytes are parsed directly without reopening or executable object deserialization.
No fallback classifier or automatic conversion is available.

V1 manifests remain readable for integrity inspection; serving V1 or an unmanifested
pickle directory fails closed. Training exports V2 and freezes the canonical policy
file set, including evidence and linear inference code. Existing frozen studies are
not edited, and copying a study bundle selects its original version's file contract.

This is a breaking provisioning change: approve a newly trained V2 or explicitly run
`python scripts/migrate_linear_candidate.py --legacy-candidate <local-v1> --output-dir <new-directory> --manifest-sha256 <independently-approved-pin> --trust-legacy-pickle`
offline on operator-trusted artifacts. Migration executes legacy pickle only in that
explicit offline tool. A matching digest does not make malicious pickle safe. It
preserves source/leakage provenance but drops old validation and policy approvals;
output is marked deployment_approved=false. Review and establish new validation and
independent pins before deployment. Never upload customer files or private artifacts.

## Verification and remaining work

Final verification on October 3: **607 offline tests passed**, five platform/link
checks skipped and three provisioned-model integration tests deselected. The scoped
high-severity Bandit scan passed with no disabled tests; git diff whitespace checks
passed. Targeted semantic/evidence/negative-control checks also passed. Tests use
synthetic engineering fixtures and authored negative/positive controls. JSON conversion does not calibrate
scores, retrain the detector or establish real model/customer compatibility.

Independent permitted labels, representative prevalence and false-positive confidence
bounds, unseen adaptive attacks, fairness, OCR/full visibility, native-memory isolation,
load/cost/latency, customer integration acceptance and incident/rollback exercises remain
open. No zero-gap, zero-false-positive or production-readiness claim is made.
