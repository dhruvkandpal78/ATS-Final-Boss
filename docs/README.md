# Documentation

Start with the [project README](../README.md). It describes supported commands and
current limitations. The repository is a research prototype, not a production or
accuracy certification.

## Product and implementation

| Document | Purpose |
| --- | --- |
| [Architecture](Architecture.md) | Runtime, evidence, policy and trust boundaries |
| [Integration](INTEGRATION.md) | Versioned API, SDK and downstream privileges |
| [Security](../SECURITY.md) and [Ethics](ethics.md) | Security policy and human-review limits |
| [Ownership](OWNERSHIP.md) | License and attribution context |
| [Project rules](rules.md) | Methodology and change constraints |

## Deployment and evaluation

| Document | Purpose |
| --- | --- |
| [Private pilot](PRIVATE_PILOT.md) and [release gate](COMPANY_RELEASE_GATE.md) | Provisioning and acceptance evidence |
| [Operations metrics](OPERATIONS_METRICS.md) | Authenticated telemetry and its limits |
| [Customer strategy](CUSTOMER_PILOT_STRATEGY.md) | Proposed customer and pilot scope |
| [Public preview](PUBLIC_PREVIEW.md) | Preview behavior and deployment constraints |
| [Downstream benchmark](DOWNSTREAM_BENCHMARK.md) | Paired comparison and outcome denominators |
| [Reference study](REFERENCE_STUDY.md) and [consistency](SCREENER_CONSISTENCY.md) | Reference screener identity and repeatability |
| [Kaggle protocol](research/KAGGLE_STRESS_PROTOCOL.md) | Frozen 20% intervention experiment |

## Evidence and history

[Research guide](../RESEARCH.md) distinguishes controlled edits from natural labels.
[Results index](../results/reports/README.md) separates current measured studies from
legacy proxy experiments. [Status](progress/STATUS.md), [issues](progress/ISSUES.md)
and [changelog](../CHANGELOG.md) track verified work and open gaps. Dated records in
`progress/` preserve implementation, failed experiments and validation evidence.

[Historical rationale](archive/README.md) retains the original PRD and design
rationale. Obsolete duplicate plans, assistant memory files and presentation
scripts were removed from the maintained tree; earlier revisions remain in Git.
See [cleanup inventory](progress/REPO_CLEANUP_2026-10-03.md).
