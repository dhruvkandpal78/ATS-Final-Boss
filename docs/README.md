# Documentation map

October 3 precision continuation: generic technical cues no longer independently
recommend review, even in hiring prose; score/outcome commands require an applicant
target. Authored text and visible/white-on-white PDF controls pass. Population false
positives and unseen recall remain unverified. See [change and tradeoffs](progress/APPLICANT_INTENT_PRECISION_2026-10-03.md).

The [precision and data-only record](progress/PRECISION_AND_DATA_ONLY_2026-10-02.md) documents authored cue improvements and the breaking V2 provisioning change. Runtime never loads pickle; explicit offline migration does not establish accuracy or deployment approval.

The [candidate artifact record](progress/CANDIDATE_BOUNDS_2026-10-02.md) documents
bounded integrity/loading, strict manifest parsing, link rejection and the
evidence-source policy-pin migration without implying safe pickle or deployment
approval.

The [cue-context record](progress/CUE_CONTEXT_2026-10-01.md) documents consistent
instruction explanations and shared sentence indexing with limited local timing
evidence; it adds no downstream efficacy claim.

The [review-routing study](progress/REVIEW_ROUTING_STUDY_2026-10-01.md) separates
the reference screener's baseline review requests from detector-added holds,
preserving the original failed protocol and conditional efficacy limits.

The [pinned local reference record](progress/PINNED_LOCAL_REFERENCE_2026-10-01.md) documents model-file integrity, actual local controls and the model-review qualification failure separately from hosted fingerprints and detector decisions.

[Screener consistency](SCREENER_CONSISTENCY.md) defines the clean-repeat stop rules and separate score, eligibility and four-candidate ranking endpoints required before an interpretable reference efficacy experiment.

The [consistency execution record](progress/CONSISTENCY_AND_RANKING_2026-10-01.md) reports actual clean repeat results and the failed backend-identity condition; its attack phase was not run.

The opt-in [reference screener study](REFERENCE_STUDY.md) runs fictional PDFs through an actual hosted model. Its [dated execution record](progress/REFERENCE_STUDY_2026-10-01.md) distinguishes descriptive findings from independent customer evidence.

[Runtime metrics](OPERATIONS_METRICS.md) describes authenticated telemetry, collection limits and customer monitoring responsibilities.

The [paired downstream harness](DOWNSTREAM_BENCHMARK.md) defines comparison inputs and denominators; [mentor implementation record](progress/MENTOR_REVIEW_IMPLEMENTATION_2026-10-01.md) lists what is implemented and what still requires real evidence.

Start with the root [README](../README.md). The current maintained system is documented in [Architecture](Architecture.md), [Security](../SECURITY.md), and [Ethics](ethics.md). Deployment instructions are in [Private pilot](PRIVATE_PILOT.md), and customer acceptance evidence belongs in [Company release gate](COMPANY_RELEASE_GATE.md).

The versioned review API and downstream privilege boundaries are documented in [Integration](INTEGRATION.md). The [product-gap response](progress/PRODUCT_GAP_REVIEW_2026-10-01.md) distinguishes current implementation from stale review claims and still-open commercial/scientific requirements.

[CHANGELOG](../CHANGELOG.md) summarizes shipped work. [Status](progress/STATUS.md) and [Issue ledger](progress/ISSUES.md) distinguish tested implementation from unresolved operational and accuracy gates. Detailed dated records under progress preserve evidence and research reproducibility; they are not separate product specifications.

Historical planning and review records are preserved under [archive](archive/README.md). Statements in those files do not override the current README, architecture, security policy or frozen evaluation records. Duplicate specifications and obsolete migration scaffolding have been removed; the retained rebuild specification is historical. Local assistant launch configuration and generated frontend bundles are excluded from the maintained publication tree.

The downloaded public corpus contains real PDF layouts with unreviewed manipulation labels. Acquire it with the pinned, bounded [dataset script](../scripts/acquire_resume_dataset.py). Synthetic injection and paired edits are separate controlled experiments. Neither corpus download nor controlled-attack accuracy establishes natural manipulation accuracy or a cheating probability. See [Precision policy evidence](progress/PRECISION_POLICY_2026-09-30.md).
