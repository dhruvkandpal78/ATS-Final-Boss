# Private pilot hardening — September 30, 2026

## Scope and changes

Selected a proposed first segment: technical staffing agencies and midsized recruiting teams, with a single-company customer-managed deployment and human review. Added customer strategy, operations and security documentation without changing ownership rights.

The API now refuses network-wide local-mode binding and checks Host and exact Origin before processing. Private mode requires a secret-file bearer token, HTTPS origins, an independently supplied candidate manifest digest and Linux. All private routes except minimal GET liveness require authentication. A global analysis request budget and eight-connection cap bound admission; inference deadlines include IPC submission. Response headers restrict browser capabilities and inline script execution; theme initialization moved into an external asset.

Rejected small POST bodies are discarded without parsing, bounded to 8 KiB and 50 ms, to reduce Windows TCP resets on immediate authorization denial. This does not guarantee clean responses for oversized or slow rejected uploads. Gateway injection applies to every UI/asset/API request; readiness requires an authenticated warm-up before readiness-gated routing.

Candidate loading verifies the externally pinned manifest and exact artifact bytes before deserialization; legacy pickle bundles are refused in pinned deployment. Pickle remains executable trusted serialization, not safe user input. Linux worker limits and a non-root, read-only, resource-limited Compose container are provided. Response audit events contain a random request ID, canonical route, method, status and duration, omitting documents, queries, credentials and client addresses. SIGTERM closes the inference worker and waits for bounded handlers.

Added a hashed Python 3.12 Linux CPU runtime lock, dependency audit helper, static scanning and CI checks. The audit normalizes only the known Torch CPU version suffix for upstream advisory lookup and fails on skipped entries. Installed development Jupyter Server was updated from 2.20.0 to 2.21.1 after its advisory was detected; it is not a runtime dependency. Added regression tests for authentication, origin/host rejection, saturation, artifact replacement and audit handling.

## Evidence and remaining gates

The preceding implementation checkpoint passed 147 offline tests. Final verification is recorded below after the latest changes. The runtime advisory check examined 55 upstream distribution versions without skipped entries and reported no known vulnerabilities; that is not a guarantee of security. Static scanning found no high-severity findings in the scoped application; trusted pickle deserialization remains an explicit medium-severity exception.

Final local verification: 149 tests passed in 46.40 seconds, including cached-model integration tests; 146 passed in the separate offline-only run. JavaScript syntax, YAML parsing, whitespace checks and the scoped high-severity scan passed. Initial sandbox runs could not access pytest temporary directories; an approved local run with a fresh workspace test directory resolved that environment issue. A full run exposed a small-body Windows authorization-response reset, addressed by bounded discard and then rerun successfully. No personal PDFs were used. Shutdown can interrupt an in-flight analysis; graceful request draining remains an operations limitation.

Docker is unavailable on this workstation. The locked Linux environment, container build, cgroup enforcement, SIGTERM behavior on Linux and customer SSO/TLS gateway must be tested before a real pilot. Base-image digest pinning, image provenance/SBOM, OS vulnerability scanning, durable audit collection, external penetration testing and customer legal/privacy approval remain open. No production certification or public multi-tenant readiness is claimed.

The five frozen detection-policy files were not changed. No consumed holdout was reopened or tuned. Natural manipulation labels, field false-positive rates and cheating-probability calibration remain unverified.

## Publication

Personal resumes, datasets, model artifacts, secrets and unrelated projects are excluded from the source-only publication payload. GitHub publication remains pending: managed approval review rejected the earlier push; application changes cannot disable that control. No upload has occurred.
