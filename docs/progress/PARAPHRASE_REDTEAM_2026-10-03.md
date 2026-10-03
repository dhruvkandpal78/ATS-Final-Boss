# Targeted paraphrase red-team continuation - October 3, 2026

## Reproducible misses

A lighter-model read-only review proposed fictional attack/benign pairs. Root
independently exercised the cue detector from preceding public revision 9b1582a,
without initializing embeddings or contacting any API. The frozen old module is
kept in ignored local test storage; public vectors are in
`tests/test_paraphrase_controls.py`. The final expanded set contains 11 directed
commands and 14 paired legitimate descriptions/workflows/examples.

| Authored development set | Prior cues | Revised cues |
| --- | ---: | ---: |
| Directed commands detected / 11 | 0 | 11 |
| Benign examples flagged / 14 | 0 | 0 |

The set was designed to expose misses and then used for repairs. It is not a
random sample, new accuracy holdout, independent labeling study or population rate.

## Changes and evidence

Expanded applicant-directed commands for first/number-one rank, shortlist top
placement, first-choice selection, own match rating100 and explicit immediate
hiring. Added narrowly phrased qualification fabrication and outcome-reuse commands
that include a bypass, plus an applicant-directed hire/full-marks instruction.
These are lexical rules, not new learned model capabilities. Generic schema labels,
numeric achievements and quoted training examples remain non-actionable.

Read-only review found two plausible legitimate qualification gates:
`following completion of ... checks` and `subject to verification of ... qualifications`.
Bounded qualification matching now preserves those controls, while paired explicit
bypass and fabricated-qualification assertions still recommend review. Detection,
explanation and original-source spans agree for every new positive/negative string.
Visible and white-on-white generated PDFs exercise all 25 strings (50 PDF routes),
using real PDF extraction/forensics and deterministic semantic/classifier fixtures.
These PDF fixtures do not test real embedding accuracy or downstream screener behavior.

No thresholds, learned coefficients, API response contract or generic technical
markers changed. Policy-source hashes continue to fail closed for old freezes;
existing approvals must not be silently carried forward. No Kaggle PDFs were rerun
or retuned in this continuation. The earlier original and known-case replay reports
retain their original evidence scope and counts.

## Remaining authored misses

The following independent probe strings still have zero cues in both revisions:
- Referencing values from example JSON across sentences to request an outcome.
- URL-percent-encoded instructions.
- Letter-spaced instruction words.

The fixed adaptive diagnostic is now version1.2: rank-first and immediate-hire
probes are covered, but Hindi and split-sentence wording remain missed. No claim
of zero unseen false negatives is made. Arbitrary encodings, languages and semantic
references require further evidence; blindly concatenating or decoding all resume
content risks legitimate false positives. Full OCR, independent labels, natural
attack behavior and downstream value remain open.

## Validation

Final focused string/source/paired PDF/adaptive checks: 164 passed. Scoped
high-severity Bandit and whitespace checks passed. Full offline result is recorded
below after final verification. Raw resumes, private history, credentials and model
weights remain excluded from publication.

Final full offline suite: **793 passed, five skipped, three provisioned-model integration tests deselected** (one Starlette/httpx deprecation warning). Earlier 781-pass run preceded the final qualification/bypass additions and is superseded for this revision. Previous PR14 hosted CI passed for 9b1582a; the new revision requires fresh hosted checks.
