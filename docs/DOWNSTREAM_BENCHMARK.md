# Paired downstream evaluation

This import-only harness compares supplied observations from an existing screener against the same screener behind a frozen review gate. It does not run models, open resumes, contact APIs or certify submitted measurements. A separate opt-in [reference study runner](REFERENCE_STUDY.md) executes a small hosted screener experiment using fictional PDFs; that is distinct from independent customer evidence.

## Procedure

Before attributing score/rank changes to the gate, qualify the screener on
repeated clean inputs, arm consistency and predefined cohort stability. The
opt-in [consistency-first study](SCREENER_CONSISTENCY.md) freezes these checks
and stops before attack evaluation if they fail. Do not retrofit a canary-only
experiment into evidence about hiring score/rank manipulation.

Before evaluation, independently approve and preserve protocol bytes, dataset manifest, screener configuration (model revisions, prompts, decoding settings and seeds), gate revision, success predicate and environment manifest. Hash each with SHA-256. Define grading criteria before inspecting outcomes and retain blinded grading records privately. Use permitted evaluation source groups excluded from development; group original and modified documents together. Independent attacker/reviewer declarations must reflect actual independent work.

Run both arms on identical document bytes. Only complete no-signals reviews forward in the protected arm; other decisions hold for humans, while unavailable reviews remain errors. Record errors and output digests instead of silently dropping failed runs. Include gate overhead in protected latency/cost and use identical measurement boundaries. Never mix simulated and measured runs in one import.

Keep inputs, customer outputs and generated reports in ignored `.test-tmp/` or approved private storage. Even digests can be linkable personal data. Do not publish them by default.

```powershell
python -m src.evaluation.downstream --protocol .test-tmp/protocol.json --protocol-sha256 APPROVED_SHA256 --observations .test-tmp/observations.json --output .test-tmp/comparison.json
```

Output must be new. Limits: 16 MiB per JSON input, 10,000 rows, 64 attack families and 2,000 bootstrap draws. Duplicate JSON keys, nonfinite numbers, duplicate documents, declared development overlap and inconsistent pairs are rejected.

## Closed schema 1.0

Objects accept exactly the fields below. Digests are lowercase 64-character SHA-256; family codes match `[a-z][a-z0-9_-]{0,47}`. Optional numeric observations use null when missing.

Protocol fields: `schema_version` (1.0), `comparison_kind` (gate_only/system_comparison), `measurement_kind` (measured/simulated), `label_basis` (known_interventions/natural_adjudicated), `adversary_relation` (same_team/independent_team/unknown); `dataset_sha256`, `baseline_screener_sha256`, `protected_screener_sha256`, `gate_sha256`, `success_predicate_sha256`, `environment_sha256`; unique lists `development_families` (max64) and `development_source_sha256s` (max10000). Gate-only requires identical screener fingerprints; different systems cannot isolate gate effect. Empty development declarations do not establish independence.

Observations envelope: `schema_version` (1.0), `protocol_sha256` matching the approved byte pin, `dataset_sha256` matching protocol, and `rows`.

Row fields: `document_sha256`, `source_sha256`, `label` (integer 0/1), `family`, `is_reference` (boolean), `review_decision`, `review_status`, `baseline`, `protected`. Label0 means no added attack for authored interventions, not certified naturally benign. Negative control families may be named separately; attacks cannot use `none`. At most one label0 reference per source. Review decisions: no_signals_detected/review_recommended/insufficient_evidence, or null iff status error. Status: complete/partial/unscorable/error; incomplete reviews cannot claim no signals.

Arm fields: `document_sha256`, `screener_sha256`, `state`, `attack_success`, `ranking_score`, `latency_ms`, `cost_usd`, `output_sha256`. Identities must match row/protocol. Baseline state: completed/error; protected: completed/held/error. Completed attacks require boolean success; other cases require null. Completed outputs require a digest; held/error output and score must be null. Optional score [0,1], latency [0,86400000]ms and cost [0,1000000]USD must be finite.

## Interpretation

Detection metrics include only recommendation/no-signals decisions, with attempted/evaluable/abstention/error counts beside them. Operational burden includes all attempts. Per-arm attack success uses completed denominators; matched-completed deltas and source-group intervals describe the forwarded subset. Held attacks are deferrals, not model resistance; zero completions yields null success rate. Source-group intervals assume independent groups and row-weight outcomes; small samples remain unreliable.

Reports retain configuration digests and declared provenance, known/unseen family outcomes, benign-control flags and missing measurement counts. Score displacement relative to originals is not rank drift. Actual ranking/top-k effects, human-review resolution/cost, fairness, throughput, memory containment, adaptive independent attacks and module ablation remain acceptance requirements. Operator labels, execution, authenticity and independence are not verified by this tool.
