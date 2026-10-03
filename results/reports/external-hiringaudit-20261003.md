# External HiringAudit challenge — adverse result

## Measured result

The unchanged review policy flagged **100/1,000 publisher-assigned attack PDFs
(10%)**, leaving **900/1,000 unflagged after complete analysis**. It flagged
**0/100 original synthetic PDFs**. All 1,100 analyses completed; there were no
partial, insufficient or runtime-error cases. This is controlled external edit
detection, not natural-world accuracy or measured downstream attack prevention.
The 90% detection target **failed**. The below-2% control-burden target is **not
established**: even zero events in 100 independent original groups gives a
one-sided 95% upper bound of **2.95%**. Do not advertise this as zero false positives.

## Why this experiment matters

Attacks were authored by another project before this evaluation, rather than
created to match this detector's rules. Acquisition used publisher-rendered PDFs
from [HiringAudit](https://huggingface.co/datasets/PD777/HiringAudit-adversarial_cv_dataset),
pinned revision `81a0f6b1a5c3254371e6304af9dafdc533b6c9d5`; its publisher describes
fully synthetic CVs and MIT licensing. The dataset has only **100 profiles and ten
shared attack templates**, not 1,000 independent attacker behaviors. All available
groups were selected under the [pre-outcome protocol](../../docs/research/EXTERNAL_CHALLENGE_PROTOCOL.md).
No original byte/normalized-text matches to the consumed Kaggle corpus, or duplicate
original groups, were found. Person/semantic/template independence remains unverified.

The prior Kaggle recovery result concerned inspected development attacks and
cannot override this adverse generalization result. This cohort is now consumed;
subsequent fixes tested on it must be described as development replay.

## Identical-byte shadow comparisons

| Method | Attack PDFs flagged / 1,000 | Originals flagged / 100 |
| --- | ---: | ---: |
| Full review policy | 100 | 0 |
| Direct-cue evidence only | 100 | 0 |
| Sustained keyword repetition only | 0 | 0 |
| Structural advisory treated as a flag | 200 | 0 |
| Legacy experimental classifier, threshold 0.5 | 179 | 0 |
| Fixed simple English regex | 0 | 0 |

These are shadow projections of one shared pipeline, not independently optimized
deployments. The simple baseline was frozen to three phrases before outcomes; it
is deliberately limited and is not an established state-of-the-art comparator.
The classifier retains **unverified legacy threshold provenance** and uncalibrated
scores; this experiment does not repair its calibration or approve deployment.

Full versus structural-only has 100 full-only flags and 200 structural-only flags
on attacks: a net **−10 percentage points**, with different cases flagged. Full
versus classifier has zero full-only and 79 classifier-only flags: **−7.9 points**;
paired source-group bootstrap 95% interval **[−8.8, −7.0] points**. Neither comparator
created control flags in this cohort. Combining these signals after seeing results
would be a new development policy, not a result of the frozen study.

## Attack taxonomy and observed failures

| Publisher ID | Supplied family / channel / goal | Full policy flagged | Structural-only flagged |
| --- | --- | ---: | ---: |
| A1 | Direct score inflation / body / G1 | 0/100 | 0/100 |
| A2 | Hidden instruction / footer / G1 | 0/100 | 100/100 |
| A3 | Exaggerated achievements / body / G1 | 0/100 | 0/100 |
| A4 | Fabricated credentials / body / G1 | 0/100 | 0/100 |
| A5 | System override / body / G2 | 100/100 | 0/100 |
| A6 | Hidden instruction / footer / G1 | 0/100 | 100/100 |
| A7 | Metadata instruction / metadata / G1 | 0/100 | 0/100 |
| A8 | Rubric replacement / body / G2 | 0/100 | 0/100 |
| A9 | Internal-rubric disclosure request / body / G3 | 0/100 | 0/100 |
| A10 | Publisher degradation intervention / body / G4 | 0/100 | 0/100 |

Post-result inspection of one profile's publisher additions identifies hypotheses,
not an independent causal attribution: A1 uses arbitrary score thresholds and
qualification-bypass language outside the current narrow cues. A2/A6 structural
observations are present but deliberately advisory under policy 2.0. A7 is carried
in metadata rather than extracted page text. A8 replaces the rubric without the
currently recognized outcome phrasing. A9 asks for internal instructions and
weights, outside the scoring-focused cues. A10 contains a textual placeholder for
a long/noisy section; this is not verified actual resource-exhaustion success.
A3/A4 alter factual claims: truth cannot be established from document patterns
alone, so these failures must not be presented as proof that a text detector can
or should certify credentials. The 900 unflagged assignments are retained without
silently removing these threat-model mismatches from the denominator.

## Uncertainty and compute

1,000 paired bootstrap draws retain all 11 variants per source. Full-policy attack
and control intervals collapse to **[10%, 10%]** and **[0%, 0%]** because each profile
has the same family-level outcomes. These describe this fixed template mix, **not
certainty about novel attacks**. Leaving out A5 yields 0% attack flags; leaving out
another attack template yields 11.11%. Row-independent Wilson intervals are
secondary only: attack flag rate **8.29–12.02%**; control burden **0–3.70%**. None of
these covers label error, shared templates or population shift. No confirmatory
family-level significance claims are made.

Elapsed execution plus statistics: **249.169 seconds**, two CPU workers. Per-case
shared-pipeline timing: median **48.48 ms**, P95 **997.64 ms**. Startup/bootstrap are
not in the per-case timing; additional extraction for the regex is included.
These measurements are not HTTP throughput, separate-arm latency, an SLA or
customer capacity evidence. MiniLM was local and pinned; no external API received
résumé content. Runtime: Windows, Python 3.14.6; PyMuPDF 1.28.2, numpy 2.4.6,
scikit-learn 1.9.0, sentence-transformers 5.7.0, torch 2.13.0.

## Reproducibility and reporting audit

Executed runner version: public commit `f81891fcc0c0f89a6aa6f89eea2e57813cb006e8`.
The detector was unchanged from merged main `0eba3f419eeb94a4bd21158f1078ed4c24d36a72`.
The frozen local case/protocol manifests bind exact platform file bytes and local
model/embedding hashes. No data, private PDFs, candidate parameters or credentials
are published. Retrieve the pinned corpus with `scripts/acquire_hiringaudit.py`;
use a separately verified local research candidate and embedding export, then
freeze with `scripts/run_external_challenge.py` and execute `--run-frozen` once.
Obtaining the exact old local candidate is a reproducibility limitation; building
a different candidate is a new experiment and must not reuse these results.

| Receipt | SHA-256 |
| --- | --- |
| Publisher ZIP | `37ebec01c1eed28d16a71aeb4a9f884c778935092f806d65ddeb4eb5833d03b8` |
| Frozen protocol | `ddb8e8ae3927dce82724ebab9aadc33ff15101ba2777f9671aa1218a52f6b8bc` |
| Observations | `f271d24040c16106defe5ea8e0d5d5f9024883ade6dc2a5bdd8e044a410027bc` |
| Aggregate summary | `695b83f4e5a6ee7383ef20b4321872f999e1e1fb95a7dc093262388325c0dafb` |

The first launch failed at Windows worker-pipe creation before model loading or
any case analysis; its empty receipt is retained and the identical frozen run
was retried with sandbox escalation. No observations were overwritten.

A separate pre-unblinding audit found that a `complete` status with an
`insufficient_evidence` decision could be projected as a nonflag. This run has
**zero complete rows with unavailable classifier output**, so that edge case does
not change its counts. The maintained runner now preserves unknown decisions and
records the categorical decision explicitly, with regression tests. The original
receipt/summary are untouched. No corrected detector replay has been substituted.

## What can be claimed

The experiment establishes a substantial external controlled-challenge failure
and a large gap between known-attack recovery and generalization. It does **not**
establish journal-ready high accuracy, natural false-positive/false-negative
rates, calibrated probability, fairness, downstream benefit or production readiness.
Next work needs development repairs plus a separate, newly authored challenge;
independent adjudication and real permitted customer data remain necessary for
stronger claims. Publication suitability also depends on research novelty,
baselines, reproducibility and the selected journal's review.
