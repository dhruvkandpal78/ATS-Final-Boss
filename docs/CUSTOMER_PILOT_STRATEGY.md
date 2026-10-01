# First customer pilot

Start with a technical staffing agency, hiring-software builder or midsized
recruiting team that has an IT owner, an SSO gateway and control of a downstream
screener integration point. This is a proposed starting segment, not a
validated market ranking. A team limited to an unchanged third-party ATS is
not assumed to be able to install this layer. Verify pipeline ownership and
permitted access before proposing a trial. The initial scope is one private
organization, not a public multi-tenant service.

The buyer is the recruiting operations lead together with the security/IT owner. The use case is identifying inspectable document-integrity evidence before downstream screening. The product does not verify experience, rank candidates or establish cheating probability.

Use a single-company private Linux deployment, customer-controlled TLS/SSO, offline models and human review. Begin acceptance testing with synthetic documents. Real resumes require approved purpose, access, retention and deletion rules, artifact rights, and a verified deployment.

Measure reviewer-confirmed false alarms, missed known controlled edits, processing failures, latency and reviewer time. Record denominators and uncertainty; do not extrapolate the controlled 0/200 false-positive result into a field guarantee. Agree pilot acceptance criteria with the customer before collecting outcomes, and keep any new evaluation independent of the consumed research holdout.

The generic [review API and SDK](INTEGRATION.md) exist; native ATS connectors
and customer authorization are still roadmap/acceptance items. Do not promise
Workday, Greenhouse, Lever or Ashby installation from the generic REST contract.
Validate demand before adding public SaaS, tenant isolation or automatic actions.

## Evidence required to change the buyer verdict

Treat the supplied buyer target—recall above 90% and false-positive rate
below 2% on representative real resumes—as an **unmet proposed acceptance
criterion**, not an achieved metric. Agree a frozen operating point, sample
size, source/person independence checks, ground-truth review/disagreement
process and uncertainty requirements before evaluation. Public resume downloads
have unreviewed manipulation labels and cannot establish these targets alone.
Keep synthetic edits, natural suspected manipulation and legitimate unusual
formatting/scans in distinct reported strata. Include failures and abstentions.

Run the existing screener and screener-plus-gate comparison on the same approved
cases. Report attack success, false alarms, completion/holds/errors, additional
legitimate reviews, reviewer minutes, latency and actual cost. Preserve failed
results, including the [local score study](progress/REVIEW_ROUTING_STUDY_2026-10-01.md).
Independently grade outcomes; held cases are not proven downstream resistance.
Human review is a use restriction, not a claim that all legal or fairness risk
is removed. The release gates remain required before processing real candidates.

Identify a named sponsor, integration owner and reviewers; confirm willingness
to run the evaluation and the problem/cost they want reduced. No current named
pilot, customer permission, validated pricing, traction or defensible market
advantage is established. Price/SLA commitments need measured deployment cost
and demand evidence first.

A learned injection classifier would require permitted training data, labels,
frozen independent evaluation and ongoing drift/attack testing. More models do
not close those evidence gaps. Compare any such classifier with the conservative
baseline at the agreed false-positive constraint before changing the gate.
