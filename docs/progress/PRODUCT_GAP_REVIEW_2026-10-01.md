# Product-gap response and implementation - October 1, 2026

## Review against current source

The commercial-readiness criticism is valid. Some cited behaviors refer to historical revisions rather than current public main `0a79242290802c28517e344ff1bcca9c71d65380`.

| Review concern | Current code/evidence | Remaining gap |
| --- | --- | --- |
| Silent heuristic fallback | `server.get_service`, `inference.load_pipeline` and Module C require actual artifacts; missing dependencies/artifacts return unavailable, with private startup verification. No GPT-2 path exists in the maintained app. | Approved real-bundle compatibility on the intended host remains unverified. |
| Runtime internet pulls | Server defaults to offline loading; private mode requires separately pinned local candidate and embedding manifests. Dataset/export acquisition is explicit operator tooling. | Provision and independently approve the real versioned bundle; build smoke is not an approved-model acceptance test. |
| Perfect controlled score versus legacy F1 | Historical synthetic text-marker metrics, policy 1.0 and policy 2.0 have different data, labels, rules and evaluation boundaries. Policy 2.0 used fresh source groups but the same authored attack families. These are not interchangeable or a paired improvement estimate. | Independent natural labels, new families, adversary independence, representative subgroups and near-duplicate adjudication. |
| Density/coherence false positives | Policy 2.0 uses direct instruction or sustained repetition for review triggers; density, structure and model alerts are advisory. | Demotion can sacrifice recall; it does not validate weak features or eliminate unknown false alarms. |
| Adaptive attacker | Fixed lexical diagnostics exist and record seven authored misses. Legacy proxy attacker code is not deployed-policy validation. | Independently designed, permitted adaptive tests against frozen candidates. |
| Detector as entire security architecture | No instruction-following scoring LLM is in the maintained analysis path. New closed-vocabulary review API separates detail from downstream review integration. | Verified factual extraction, downstream privilege controls and customer integration are not implemented end to end. |
| Real corpus | Explicit pinned acquisition produces real PDF layouts with unreviewed labels; controlled edits have known intervention labels. | Natural manipulation ground truth, representative prevalence and fairness evidence remain absent. |
| Operations/security | Linux CI, installed-wheel smoke, audits and container smoke passed for main after PR #5. These checks do not establish native physical-RAM containment or external security certification. | Real load/latency/cost, host security review, penetration testing, SBOM/release acceptance, alerting and agreed service levels. |

## Implemented improvements

- Added `POST /api/v1/review` to both HTTP adapters, sharing authentication, body limits, budget, worker/deadline and retry behavior. The private gateway example applies the same analysis-specific limits to it.
- Added a fixed-vocabulary projection: only supported schema/policy, enumerated statuses/decisions, bounded category counts and coverage states. It discards source text, arbitrary worker metadata, explanation strings, previews and numeric scores. Unsupported projection inputs return generic unavailable responses. No sanitizer or hiring decision is claimed.
- Kept `/analyze` and the maintained UI unchanged. No detector/module, policy, threshold, artifact or held-out evaluation changed. Existing candidate policy fingerprints are not re-signed.
- Added `src.evaluation.prevalence`: explicit supplied confusion counts/class denominators, assumed base rates/cohort size, projected PPV/NPV, expected TP/FP/TN/FN, and optional separately labeled FPR stress scenarios. It reads no resumes, fits no models, verifies no labels and estimates no deployment prevalence. Zero-FP observations are not zero population risk; stress assumptions are not confidence bounds.
- Added [integration contract](../INTEGRATION.md), updated maintained guidance, and tests for source-string exclusion, schema failure, cross-adapter denial/budget/retry parity and base-rate edge cases.

At sensitivity 0.656, FPR 0.075 and assumed prevalence 0.02, 10,000 applicants give expected TP 131.2, FP 735, TN 9065 and FN 68.8: projected precision is about 15.15%. This is a conditional arithmetic illustration, not a newly measured current result. Taking controlled 100/0/200/0 counts at face value yields optimistic PPV 1; supplying a separate FPR stress assumption of 0.0295 at the same base rate drops projected PPV to about 40.89%. The 2.95% source-group bound is not a proved deployment row FPR.

## Verification

- Final offline Windows Python 3.14 suite: **397 passed, 2 unchanged platform skips, 3 integration tests deselected**, with one existing Starlette test-client deprecation warning. New tests also exercise actual shared-service text/PDF result contracts using mocked embeddings/classifier and synthetic temporary PDFs, not a provisioned real model or accuracy benchmark.
- Scoped Bandit high-severity scan passed with zero high/medium findings and two low observations. B301 remains excluded only for intentional trusted model loading; worker IPC stays data-only.
- Private Compose shape guard, maintained local documentation links and `git diff --check` passed. Gateway route-scope regression verifies both analysis paths have the same auth, token and admission directives; this does not replace running Nginx/customer acceptance.
- Independent read-only code review identified unbounded source-count input and cross-field result consistency gaps. Source counts now total at most one billion, at most 100 prevalence scenarios are accepted, and the projection enforces current category/trigger/decision and complete-evidence invariants. Regression tests cover both fixes.
- The first focused run passed all new tests but hit one Windows socket abort in an existing malformed-header test; its unchanged ten-test transport suite passed on recheck and the full final suite passed. No skip or assertion was added to hide this observation.
- Outgoing publication guard must pass against public main before push. Hosted Linux/container CI will run on the published branch; no new hosted result is claimed in this pre-publication record.

## Regulatory and ethical acceptance

Human review labeling is not a blanket exemption from hiring/data-protection law. Applicable classifications, notices, legal basis, controller/processor obligations, audit retention, candidate appeals and bias assessment depend on actual use/jurisdiction and must be reviewed before customer processing. This implementation provides no legal compliance or fairness certification.

Primary references checked for this record: [EU AI Act Annex III employment uses](https://ai-act-service-desk.ec.europa.eu/en/ai-act/annex-3), [NYC DCWP AEDT requirements](https://home4.nyc.gov/site/dca/about/automated-employment-decision-tools.page), and [MeitY DPDP Rules publication](https://www.meity.gov.in/documents/act-and-policies/digital-personal-dataprotection-rules-2025gDOxUjMtQWa?pageTitle=Digital-Personal-Data-ProtectionRules-2025). No implementation date or jurisdictional applicability is inferred from these references alone.

The first supported pilot scope remains a human review aid in a customer's controlled intake workflow, without automatic rejection, public upload service or a validated cheating probability. See [release gates](../COMPANY_RELEASE_GATE.md).
