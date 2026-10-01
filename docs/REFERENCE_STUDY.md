# Opt-in reference screener feasibility study

`scripts/run_reference_study.py` executes an actual hosted reference screener on
24 newly generated fictional PDFs: four profiles, each with clean, benign
security-training note, direct instruction, white-on-white instruction,
paraphrased instruction and base64 instruction variants. These are authored
interventions, not natural manipulation labels or an independent red team.
No arbitrary document input or configurable remote endpoint is accepted.

The baseline and forwarded protected arm use the same Groq `openai/gpt-oss-120b`
model ID, prompt, strict JSON schema, temperature and output limit. The gate is
the sole arm difference. Protected forwarding requires a complete
`no_signals_detected` review; other decisions hold, and unavailable reviews stay
errors. Pair order alternates. Calls are single attempts, without redirects,
automatic retries, tools, model substitution or account upgrade. A non-200
response stops further API calls; request and token budgets are bounded.

Before calls, the runner writes dataset, prompt/schema, success predicate,
environment/runner fingerprint and protocol. Success means the **final structured
audit marker equals a fixed injected canary**, not an LLM self-assessment,
reasoning text or a high fit score. Score displacement is descriptive, not
cohort ranking corruption. Held baseline successes are review deferrals, never
proved prevention. Four source groups do not justify inferential intervals;
the study report suppresses them. Results are single-run exploratory because
a hosted alias does not pin immutable weights or guarantee determinism. Backend
fingerprint variation is allowed, retained and reported; it prevents a claim
that both arms used one frozen backend configuration. Future runs counterbalance
each family's pair order across source groups.

## Research configuration and privacy

The operator supplies trusted local artifacts, never uploaded pickles. The
original candidate is verified and copied unchanged, including its manifest.
A separate `synthetic_reference_study` manifest records original lineage,
unchanged weights/threshold hashes and current policy source hashes. It removes
any inherited validation claim and explicitly records no deployment approval.
It is a new research combination, not a repair/re-signing of the original
candidate, and does not qualify as a production candidate bundle. No consumed
holdout, threshold, policy source or production startup verifier is changed.

Keep the key outside Git and never paste it into chat. Generated documents,
original artifacts, downstream responses and observation files stay in ignored
`.test-tmp/`. Responses may contain hostile output; treat them as inert data.
Only these fictional documents are sent to Groq. Do not extend this permission
to candidate data. Enable provider Zero Data Retention where available and
verify the account's actual free allowances before larger runs. This runner
does not verify account billing or retention settings, so cost is recorded as
unknown rather than claiming zero total operating cost.

```powershell
python scripts/run_reference_study.py --key-file .test-tmp/groq-api-key.txt --candidate results/candidates/TRUSTED_LOCAL_CANDIDATE --output .test-tmp/FRESH_STUDY_DIRECTORY
```

The API key is read internally, not placed on the command line. The output
directory must be new and inside the checkout's `.test-tmp`. Cache the trusted
embedding beforehand: model loading is offline and missing artifacts fail.
Latency excludes pacing and startup/warmup, includes gate analysis in the
protected arm, and measures local analysis plus API response validation. It
does not measure deployed HTTP service capacity, manual processing or an SLA.

This reference experiment is **not an existing customer's screener**, production
acceptance, independent efficacy, fairness evidence, calibrated cheating
probability or proof of commercial value. Preserve unfavorable outcomes and
use a fresh preregistered study for later design changes.

Provider references: [structured outputs](https://console.groq.com/docs/structured-outputs),
[rate limits](https://console.groq.com/docs/rate-limits),
[data controls](https://console.groq.com/docs/your-data).
