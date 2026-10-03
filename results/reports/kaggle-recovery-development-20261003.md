# Known-case recovery replay - October 3, 2026

This is a measured development regression after inspecting the original failures. It is not a fresh holdout, independent accuracy, or downstream attack prevention. The [original result](kaggle-stress-20pct-20261003.md) remains unchanged.

## Exact-input replay

All 2,295 original case records, PDF identities, labels and assignments match byte-for-byte. The 1,836 unmodified originals remain unreviewed. Linear coefficients, thresholds and offline embedding bytes are unchanged; a new unapproved candidate freezes the recovery policy. No external model API or retraining was used.

| Cohort | N | Complete review | Partial review | Complete no-signals | Insufficient | Runtime error |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Unmodified originals | 1836 | 0 | 0 | 1813 | 23 | 0 |
| Added attacks | 459 | 454 | 5 | 0 | 0 | 0 |

## Per-family replay

| Family | N | Complete review | Partial review | Complete no-signals | Insufficient | Runtime error |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| visible_direct | 46 | 45 | 1 | 0 | 0 | 0 |
| invisible_direct | 46 | 46 | 0 | 0 | 0 | 0 |
| white_direct | 46 | 46 | 0 | 0 | 0 | 0 |
| tiny_direct | 46 | 46 | 0 | 0 | 0 | 0 |
| zero_width_direct | 46 | 45 | 1 | 0 | 0 | 0 |
| homoglyph_direct | 46 | 44 | 2 | 0 | 0 | 0 |
| base64_instruction | 46 | 46 | 0 | 0 | 0 | 0 |
| spanish_instruction | 46 | 46 | 0 | 0 | 0 | 0 |
| conditional_mimicry | 46 | 46 | 0 | 0 | 0 | 0 |
| keyword_repetition | 45 | 44 | 1 | 0 | 0 | 0 |

## Previous misses

Transitions for the 182 previously complete no-signal injected cases:
- 182: complete/no_signals_detected -> complete/review_recommended.

## Verification and limits

718 offline tests passed; five skipped, three provisioned-model integration tests excluded. The final focused recovery/PDF set passed 101 checks. Scoped high-severity Bandit and whitespace checks passed. Independent code review caught fixture/apply precedence and paired tests verify its repair. An earlier four-worker partial replay was stopped and explicitly marked non-final before correcting that issue; its receipts remain local.

Known-case successes can reflect shared authored templates. Zero unmodified review flags would establish only control burden on unreviewed originals, not zero true false positives. Partial/insufficient analyses remain incomplete, not clean or proven detections. Hindi, broad paraphrases, arbitrary encodings, scanned PDFs, natural attacks, fairness, customer deployment and downstream efficacy remain unverified.

## Local receipt identity

- cases.json: `da233d80b1174b92dfca10b4f830aeaf3e762aac64fec0816a5dc9f2262d2dbc`
- protocol.json: `6afdf27dc440b648b342ef53cad3f9f8de0a27a328955d197ae2f0c3e53bfbe7`
- observations.jsonl: `9f5aa6a79bac91cec241c889a6b3732bf0f45532aa6a689f64789b2570a718ac`
- summary.json: `24c471b22880c20a992b506be8475f41995bc11580f41079e6988c64380c99f4`
- Research candidate manifest: `0f50aceabf27b83bbe3946c52b9514b1c3bf4c7d683a868728237295d35a1352`
- Runtime: 746.606 seconds, 2 CPU workers; this is an offline run, not capacity/SLA evidence.

A separate read-only agent reconciled all 2,295 unique indices, identical case bytes, family/label assignments, per-family outcomes, previous-miss transitions and receipt digests against the public report, with no discrepancies. No resume contents were read for that reconciliation. The publication branch tree matched the tested development tree; the offline release-payload guard passed.
