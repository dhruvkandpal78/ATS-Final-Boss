# Applicant-directed instruction precision — October 3, 2026

## Problem and change

Same-sentence hiring context still unlocked generic lexical patterns in legitimate
ATS/security engineering descriptions. Ordinary API-format guidance, role-marker
logging, an emergency override feature, test fixture output and valid-schema request
handling were flagged when a candidate/screening term appeared nearby.

Removed those generic patterns as standalone actionable cues. Role markers,
system/admin labels, `match score: 100`, generic return/print/output guidance and
`hire immediately` no longer independently recommend review. Retained explicit
instruction overrides and applicant-directed scoring, rank, eligibility, rejection
and hiring commands. Highest-score commands must name a candidate/applicant/resume/
application target; output-decision instructions require an explicit eligibility
target and a local imperative/directive prefix, so ordinary rubric descriptions are
excluded. Bare `disregard previous` now requires an instruction/rule/guidance noun.
Shared Unicode normalization, quote/example exclusions and exact-source evidence
remain in place. Density, structure and experimental model scores remain advisory.

This is a precision tradeoff: vague role-only or generic instructions, omitted or
remote targets, unknown paraphrases, encoding and other languages can escape these
rules. A lack of cues does not certify authenticity or safe downstream processing.
No threshold, model parameter, cheating-probability or automatic-rejection change.
Frozen policy hashes change; existing approved bundles require explicit review.

## Fixed authored comparison

Diagnostic version 1.1 (`python scripts/check_instruction_regressions.py`) contains
26 fixed same-team probes: 16 benign descriptions/examples and 10 directed attacks.
The identical cases were evaluated against preceding implementation cf4f2ac and the
working patch, without initializing an embedding model:

| Cue rules | Benign flags / 16 | Attack cues detected / 10 | Missed / 10 |
| --- | ---: | ---: | ---: |
| cf4f2ac | 9 | 9 | 1 |
| Current patch | 0 | 10 | 0 |

The set includes two additional legitimate rubric descriptions discovered by
read-only review. These are development regressions selected around known rule failures. Labels were
authored internally, not independently adjudicated. Counts are not estimates of
natural-world accuracy, prevalence, probability, fairness or downstream attack success.
The earlier 13-case and unfavorable downstream study records remain unchanged.

## PDF and source-path verification

Nine new benign strings and four candidate-directed attacks also pass through
actual generated PDFs in both visible and white-on-white text: **18 benign controls
produce no review recommendation; 8 directed-attack controls recommend review**.
They verify extraction and policy routing, with deterministic semantic/test-model
fixtures and a deliberately high advisory model score. They do not test real learned
accuracy or establish full visual/OCR visibility. Two render variants of one string
are paired controls, not independent real resumes.

Focused detector/evidence/policy suite: **100 passed**, two provisioned-model tests
excluded. Final offline suite: **633 passed**, five platform/link skips and three provisioned-model
integration tests deselected. Scoped high-severity Bandit and whitespace checks passed. These checks do not establish real embedding
compatibility or customer deployment acceptance.

## Open evidence requirements

Independently labeled permitted resumes, representative unusual layouts and languages,
source/person/near-duplicate separation, adaptive unseen attacks, confidence bounds,
calibration, fairness and measured customer workload remain unresolved. Unsupported
or incomplete analyses must remain insufficient evidence, not be counted as clean.
Natural ground truth and a customer screener are not available in this project.
Zero observed flags here does not imply zero population false positives. Privacy,
containment, deployment and release-acceptance gates are unchanged.
