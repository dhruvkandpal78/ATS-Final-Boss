# Pre-commit precision quality review — October 3, 2026

## Scope and confirmed improvement

The preceding 704385f precision change was already committed when the request to
check improvements before committing arrived. This follow-up was reviewed and
implemented before its own commit. It does not rewrite that revision's evidence.

The review exposed six additional legitimate procedural controls: rejecting only
after identity checks, eligibility after criteria are met, a perfect match only when
qualifications are present, hiring after reference checks clear, ranking when the
interview score is highest and assigning scores to someone who meets rubric criteria.
Those condition-dependent instructions were still flagged by directed-outcome cues.

Outcome cues now inspect bounded positive qualification conditions in their own
clause. They do not independently recommend review when that condition governs the
outcome and no explicit bypass is present. Explicit disregard/bypass language takes
precedence over the condition, including hybrid strings containing both. Strong
instruction-override cues keep their existing semantics. Score allocation cannot
use an unfamiliar descriptive prefix to suppress an explicit bypass.

Instruction overrides and outcome patterns are explicitly grouped; positional pattern
slices were removed. Text/PDF fixture groups are named rather than selected by a
magic index. Detection, sentence explanation and original-source evidence use the
same context function. No model parameters, thresholds or response schema changed.
Existing policy hashes require explicit review, never automatic pin rewriting.

## Development evidence

Diagnostic version 1.2 includes the original 26 internally authored probes plus six
qualification/bypass pairs and two condition-plus-bypass hybrids, for 40 strings.
The same cases are compared with frozen preceding code 704385f. The comparison is
known development regression evidence, not a natural-world accuracy estimate:

| Cue rules | Benign flags / 22 | Directed attack cues / 18 |
| --- | ---: | ---: |
| 704385f | 6 | 18 |
| Working revision | 0 | 18 |

The newly reviewed groups also check consistency of detection, sentence explanation
and original-source spans. Generated PDFs exercise visible and white-on-white versions
of the new pairs alongside ATS engineering controls, using deterministic test semantic
and classifier fixtures. Paired render variants are not independent resumes. The
original 26-case and earlier unfavorable downstream studies remain historical evidence.

Focused checks before grouping cleanup: **142 passed**, two provisioned-model tests
excluded. Final offline suite: **675 passed, 5 skipped, 3 integration tests deselected**.
High-severity Bandit scan and `git diff --check` passed. The preceding 704385f
hosted PR CI completed successfully; this follow-up requires its own hosted checks.

## Limits and tradeoffs

The qualification phrases are internally authored labels, not independently reviewed
candidate ground truth. Resume instructions remain untrusted. An attacker can phrase
a harmful command like a legitimate conditional workflow; absence of explicit bypass
words is not proof of benign intent. Long, remote or unrecognized conditions, other
languages, encodings and unseen wording remain coverage gaps. Quote and example
exclusions likewise do not constitute an injection security boundary.

Zero flags in these development controls is not a zero population false-positive
rate. Independent permitted labels, realistic prevalence, fairness, unseen attacks,
measured downstream effects, full OCR/visibility, customer deployment and physical
resource containment remain unverified. Unsupported inputs remain insufficient
evidence. Human review and downstream privilege separation remain necessary.
