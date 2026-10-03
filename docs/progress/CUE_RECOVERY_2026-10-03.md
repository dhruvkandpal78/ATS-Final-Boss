# Known-miss recovery: October 3, 2026

## Failure analysis

The immutable [original stress result](../../results/reports/kaggle-stress-20pct-20261003.md)
contains 182 complete misses: 46 Base64, 46 Spanish, 44 mixed-script lookalikes
and 46 conditional mimicry. Two further mixed-script documents were insufficient,
not complete misses. Original text was checked without passive decoding or visual
lookalike normalization; Spanish overrides were outside the English patterns.
The qualification-condition exemption also suppressed an outcome command followed
by a request to pretend missing qualifications were present. MiniLM coherence and
keyword density are advisory and correctly did not override this policy.

## Implementation

- Add passive, single-layer strict UTF-8 Base64 views: at most 32 candidate blocks,
  2,048 encoded characters per block and 100,000 source characters. No execution,
  external fetches or recursive decoding. PDF line wrapping is supported only
  with a nearby encoding/directive marker.
- Fold a limited set of Cyrillic/Greek visual substitutes in mixed Latin tokens;
  preserve words consisting entirely of Cyrillic/Greek characters.
- Recognize a narrow Spanish override/targeted-score vocabulary. This is bounded
  lexical coverage, not a multilingual learned classifier.
- Preserve qualification-dependent benign workflow language unless a nearby explicit
  assertion asks to fabricate/pretend qualification satisfaction. Quoted assertions
  and unrelated later instructions retain local context handling.
- Keep encoded test fixtures descriptive, including PDF line wrapping; explicit
  decode/apply commands are not covered by that new fixture-label exemption.
- Share recovered matching for signals, explanation cues and source spans. Encoded
  evidence points to the original encoded carrier, never fabricated decoded offsets.
  Ambiguous normalization offsets abstain.
- Freeze the recovery utility in candidate policy hashes. Old policy pin sets fail
  closed. The replay uses a new unapproved research candidate with identical linear
  parameters, thresholds and embedding bytes; prior approval is not inherited.

## Evaluation discipline

The replay uses the exact original 2,295 PDFs and assignments after inspecting their
outcomes. It is a known-case development regression, not a new holdout. Original
receipts, PDFs and unfavorable published counts remain intact. No models were
retrained and thresholds were not lowered. Raw PDFs, per-case receipts and models
remain ignored/local. Complete misses, partial review and insufficient evidence
remain separate. Unmodified originals lack verified clean labels, so control flags
cannot establish a true population false-positive rate. Downstream attack success,
natural manipulation, fairness and independent recall remain unverified.

The fixed adaptive diagnostic moves to version 1.1: Base64, Spanish and mixed-script
probes now recover; rank/hire paraphrases, Hindi and split-sentence wording remain
missed. The old diagnostic records remain historical evidence.

Validation and full replay outcomes are recorded in the accompanying recovery report.

## Measured replay and validation

The [exact-input development replay](../../results/reports/kaggle-recovery-development-20261003.md) recovered all 182 previous complete misses as complete review recommendations. Across 459 interventions: 454 complete reviews, five partial reviews, zero complete no-signals and zero insufficient/error cases. Unmodified originals remain zero review flags, 1,813 complete no-signals and 23 insufficient. This known-set result does not establish independent accuracy. Full offline verification: 718 passed, five skipped, three integration tests deselected; final focused checks: 101 passed. Scoped high-severity Bandit and whitespace checks passed.

A separate read-only agent reconciled all 2,295 unique indices, identical case bytes, family/label assignments, per-family outcomes, previous-miss transitions and receipt digests against the public report, with no discrepancies. No resume contents were read for that reconciliation. The publication branch tree matched the tested development tree; the offline release-payload guard passed.
