# Shared cue context and explanation consistency — October 1, 2026

## Problem and change

The detector already checked all matches of an instruction pattern, but its
sentence explanation helper checked only the first. A quoted benign example
followed by an actionable command could therefore be flagged without the
corresponding explanation cue. The helper now checks subsequent matches using
the same local-context exclusions as detection.

For dense quoted/example text, each match also rescanned the document prefix
to find its clause. Detection, sentence explanations and source-span evidence
now each build one normalized-document sentence-boundary index per invocation
and use binary search to locate the relevant clause. Evidence retains exact
source offsets, the 20-span output cap and abstention for unmappable Unicode
composition. Simple injected test detectors retain their existing interface.

Patterns, review decisions, score thresholds, normalization and local
quote/example exclusions are unchanged. This does not broaden paraphrase,
encoding or multilingual detection, remove quote-based evasions, implement OCR,
or establish downstream protection. Source hashes change and approved policy
pins require explicit review; do not silently re-sign earlier artifacts.

## Verification and local scan measurement

Focused tests cover later actionable matches after quoted examples, sentence
boundaries across punctuation/newlines, dense examples sharing one index,
Unicode-backed source anchors, benign technical language and PDF routing.
The focused suite passed **55 tests**, with two provisioned-model cases
deselected. Full offline suite: **533 passed**, two platform skips and three
provisioned-model integration cases deselected. Scoped high-severity Bandit
and whitespace checks passed. Hosted checks for preceding PR #11 revision
`c121f8004cdba5cc7f063029a442279608c631bf` passed on Python 3.11/3.12 and its
container smoke test; these do not verify the new patch until its CI completes.

A synthetic 72,024-character input contains 2,000 local example sentences and
one final actionable self-score command. Three alternating before/after calls
in one Python process each returned one distinct actionable pattern. The
preceding code is taken from revision
`c121f8004cdba5cc7f063029a442279608c631bf`; source hashes and raw timing receipts
remain private under ignored `.test-tmp/cue-context-20261001`.

The initial comparison observed median cue-scan times of **3,604.8 ms before**
and **65.9 ms after**. Offline regression processes were running concurrently;
these timings are descriptive and confounded by host load. They exclude
imports, embeddings, PDF extraction, HTTP and downstream scoring. They are
not an SLA, representative latency, capacity or universal complexity claim.
Long clauses, regex evaluation and Unicode mapping still consume work; the
existing service input bounds and worker deadlines remain necessary.

## Research and publication scope

The previous score-attack results and failed qualification runs remain intact.
This patch fixes explanation consistency and a computational hot path, not
the missing commercial efficacy evidence. Customer model approval, independent
attacks/benign labels, fairness, OCR, load and release acceptance remain open.
Only code, tests, documentation and reviewed synthetic timing aggregates
publish; no PDFs, candidate text, credentials, model files or private history.

## Buyer-review alignment

The supplied review was based on the README rather than code. Updated the
README and existing pilot strategy to expose current API/SDK and human-review
capabilities beside unmet accuracy, named-pilot, pricing and general injection
resistance requirements. Historical F1/recall/FPR values remain historical.
The proposed partner must control its screener integration, not merely use an
unchanged third-party ATS. Above 90% recall/below 2% false positives are requested
targets, not measured results. No learned injection-defense claim is added.
The owner confirmed no current customer-screener/reviewer access; customer
evidence gates therefore stay open. Code and synthetic tests cannot create
ground truth, a pilot customer, traction or legal/fairness acceptance.
