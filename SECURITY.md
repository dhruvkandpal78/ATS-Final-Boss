# Security policy

ATS Final Boss is a research prototype. The private-pilot setup is intended for one staffing agency or midsized recruiting organization behind that organization's TLS and SSO gateway. It is a human-review aid, not an automated hiring decision system. No security certification, complete vulnerability absence, or production availability guarantee is claimed.

## Reporting a vulnerability

Do not include candidate documents, credentials, or personal data in a report. If GitHub private vulnerability reporting is enabled for the repository, use it. Otherwise contact the maintainer through the repository owner's profile and ask for a private reporting route before sharing exploit details. Allow a reasonable coordinated-disclosure window; do not publish an exploit while a fix is being prepared.

## Trust boundary

The API accepts untrusted text and PDF documents. Native inference worker IPC uses bounded JSON bytes, not pickle deserialization, with request-correlated reply envelopes and whole-frame read deadlines. This prevents executable message deserialization across the child boundary; shared-container physical-memory isolation remains unresolved. Model pickle files are executable serialization and must only be provisioned from a reviewed, access-controlled source. The candidate manifest hash supplied to the service must be pinned in the customer deployment configuration, outside the model volume. A hash detects a changed bundle relative to that pin; it does not prove who created the artifact. Never accept model files from users or the browser.

Private embedding loading requires a separate independently pinned manifest for an approved safetensors export, including model identity, declared upstream revision and the exact bounded file set. It rejects code/pickle formats and symlinks, and loads that local export rather than a mutable model-name cache alias. The export must remain immutable during runtime; integrity checks do not attest publisher identity or prevent a trusted host operator from changing the mount later.

The container listens on its private network interface. It has no host-published port; customer gateway traffic should be the only path to it. The trusted gateway terminates TLS, performs SSO, authorizes users, injects the API bearer token server-to-server, and applies request quotas. Never put the token in browser code, HTML, local storage, a query string, or a client-visible response.

## Current controls and limits

The maintained API has bounded request sizes, PDF page and text limits, one-at-a-time analysis, an inference deadline, temporary upload cleanup, generic error responses and security response headers. The pilot container runs as a non-root user, drops Linux capabilities, uses a read-only root filesystem, a bounded private temporary filesystem, CPU/memory/PID limits and a read-only model mount.

The private image uses a single-process Uvicorn/Starlette adapter with authentication before processing, bounded upload time/size, startup artifact verification and synthetic model warm-up. HTTP adapters share their browser security-header and strict request-header contract. Worker shutdown stops new admission and coordinates process/pipe cleanup. The gateway template requires a customer SSO authorizer; neither its configuration nor the offline Compose validator proves that a deployed network is secure. Hosted CI has passed isolated image build/smoke checks; these do not load a real approved model or demonstrate containment under attack.

These controls do not replace customer network controls, host patching, backups, access reviews, monitoring, incident response, or legal/privacy review. `requirements-runtime.lock` pins and hashes the Linux Python 3.12 CPU runtime; the exact container build and operating-system packages still require release verification. CI audits known dependency advisories and performs a scoped static scan, but neither proves the absence of vulnerabilities. Response audit events omit content, credentials and client addresses; durable access-controlled collection remains the operator's responsibility. Tenant isolation, high availability and an externally verified artifact signing chain are not implemented.

## Before a private pilot

Follow [the private-pilot operations guide](docs/PRIVATE_PILOT.md) and complete [the customer release evidence checklist](docs/COMPANY_RELEASE_GATE.md). The organization must approve its data-use purpose and retention period, confirm rights to the code and model/data artifacts, name an incident owner, verify the gateway controls, and validate backup/deletion procedures. Resume findings can include document-derived information; export, access, and deletion must follow the customer's approved handling policy.
