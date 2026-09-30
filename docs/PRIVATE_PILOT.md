# Private pilot operations guide

This guide targets one technical staffing agency or midsized recruiting team running a single-organization private deployment. It assumes an existing customer-managed TLS and SSO gateway. The application is a human-review aid for document-integrity signals; it must not make or determine candidate ranking, eligibility, or hiring decisions.

The package is a deployment starting point. It does not establish that the service is secure for a particular customer, legally compliant, industry-certified, or free of vulnerabilities. A customer security and privacy review remains a launch gate.

## Deployment shape

Run the service as a private container behind the customer's gateway. The Compose file intentionally publishes no host port and places the service on an internal-only network. Connect the gateway to that private network using the customer's approved network design. The gateway must terminate TLS, authenticate users with customer SSO, authorize access, inject the API bearer token only on its server-to-server request, and enforce upload/rate limits. The browser must never receive or persist that token.

The gateway's allowed host and exact HTTPS origin must match `ATS_ALLOWED_HOSTS` and `ATS_ALLOWED_ORIGINS`. The API expects the gateway to supply the configured bearer token. Keep the service unreachable from public interfaces and do not set up a direct public ingress.

The gateway must inject the backend token for every authenticated UI, asset and API request; direct browser navigation to the private backend will be denied. The ASGI service verifies pinned artifacts and performs a synthetic model warm-up during private startup, before accepting traffic. Failed verification or warm-up fails startup; `/health/ready` checks that the warmed worker is still alive. The standard-library demo remains lazy and is not the private image entry point.

## Provisioning

1. Review the source revision, license/ownership terms, third-party notices, dependency audit, and customer-approved purpose before building. Commercial or internal reuse rights must be confirmed with the rights holder; the repository's current mixed rights notice may require written permission for new additions.
2. Run `python scripts/check_private_deployment.py`, then build the image from a reviewed source checkout. `.dockerignore` excludes datasets, results, model pickles, PDFs, local environment files and personal project files from the build context. Do not add customer data or model artifacts to the image. The image runs the single-process ASGI adapter; the standard-library adapter is for local demos.
3. Provision a validated candidate bundle and embedding-model cache in an access-controlled directory outside this checkout. Verify the bundle using the project's candidate validation workflow, review its origin, then record the exact SHA-256 of `candidate_manifest.json` through an independent trusted channel. The Compose configuration mounts that directory read-only at `/models` and requires the externally pinned manifest hash. Hashes alone do not attest publisher identity.
4. Create a high-entropy API token in the gateway's secret manager and place the same token in a root/operations-only file on the host. Set `ATS_API_TOKEN_FILE` to that absolute path. Compose mounts it at `/run/secrets/ats_api_token`; do not put the token in `.env`, command arguments, browser state, source control, support tickets, or logs.
5. Supply deployment values in the operator's protected environment or an access-controlled, non-versioned Compose env file: `ATS_MODELS_PATH` (absolute provisioned directory), `ATS_CANDIDATE_MANIFEST_SHA256`, `ATS_ALLOWED_HOSTS` (the exact DNS host, without scheme), and `ATS_ALLOWED_ORIGINS` (the exact HTTPS origin, including port if nonstandard). The application also requires `ATS_DEPLOYMENT_MODE=private` and a readable token file. No public host port is configured.
6. Review resource capacity before start. The sample container limit is 3 GiB memory, 2 CPUs, 128 PIDs and 128 MiB temporary storage; a model may need a larger measured memory budget. Change limits only after a controlled load test using synthetic documents. Do not run production resumes through an unvalidated test plan.
7. Start using the Compose file and verify `/health/live` from the gateway's private network. This intentionally unauthenticated endpoint returns only liveness, while Host/Origin guards still apply. Confirm SSO-required behavior, allowed Host/Origin checks, gateway token injection, response headers, model hash pinning, 429 handling, and that no route is reachable from an external network. Warm up with an authorized synthetic request, then verify authenticated `/health/ready`; readiness is not proof of detection quality. Native Windows private mode is rejected; use a supported Linux container.

The Python 3.12 Linux CPU runtime is pinned with hashes in `requirements-runtime.lock`; the Dockerfile requires those hashes. The base image tag is not yet digest-pinned. Build from a recorded image digest and source revision, archive the generated SBOM and vulnerability scan results, and rebuild regularly for security updates. Docker build, Linux runtime limits and gateway integration have not been verified on this Windows workstation. The pilot owner must test and approve the exact image; signed image provenance is not yet provided.

## Data handling and operations

Before receiving real resumes, the customer must document the permitted use, user population, data categories, retention period, deletion path, access roles, and support process. The service processes submitted content on the server; result findings may quote or otherwise reveal content-derived details even though source text is omitted from JSON export. Restrict result access to authorized recruiters and reviewers, and avoid storing request/response bodies in gateway, proxy, APM, crash, or support logs.

The API removes temporary uploaded PDF files after normal completion and worker termination. This does not cover host snapshots, swap, filesystem backups, operator copies, gateway logs, or customer exports. The service does not currently provide durable audit events, tenant separation, or automated retention enforcement. The pilot owner must test host-level deletion and backup expiry and keep an access-controlled operational record without candidate content.

Assign named owners for service operation, security incident intake, customer privacy escalation, and model/artifact approval. On suspected exposure, stop external access at the gateway, revoke/rotate the gateway token, preserve only approved non-content evidence, assess affected data and notify the customer's designated privacy/security owners under their process. Rebuild from a reviewed source and newly pinned artifact set before restoring access. Do not silently reuse a compromised token or model bundle.

Monitor container health, restart loops, resource use, 429/5xx counts and gateway authentication denials. Do not enable payload logging to make monitoring easier. Establish a tested maintenance window and rollback to the prior reviewed image digest and artifact manifest. Updates must rerun tests, dependency scanning and customer acceptance checks.

## Readiness gates

The pilot remains blocked until all of the following have named owners and recorded evidence:

- Rights holder confirms the organization's permission to use and modify the relevant project material; customer confirms rights and terms for model weights, code, and data.
- Customer security approves the threat model, gateway integration, network exposure, access controls, vulnerability response, host patching, secrets rotation, backups, and incident procedure.
- Customer privacy/legal teams approve the intended use, candidate notice/consent position where required, retention, deletion, data residency, processor terms, and impact assessment obligations.
- Artifact owner validates the model bundle, embedding weights, provenance, pinned digest and compatibility; service owner tests the exact image on the supported host.
- Recruiting operations train reviewers to treat each result as a document signal requiring human judgment. No automated rejection, ranking penalty, or statement about a person's honesty may be based on the score or signal alone.
- Customer accepts current empirical limits: the deployed legacy PDF model is experimental and uncalibrated; natural manipulation performance, broad population fairness and production-scale reliability have not been established. Controlled synthetic/edited-document results do not establish field performance.

Do not describe the product as certified, fully secure, free of vulnerabilities, or validated for automated employment decisions. Reassess scope and controls before adding organizations, public SaaS access, third-party model calls, or automated downstream hiring actions.
