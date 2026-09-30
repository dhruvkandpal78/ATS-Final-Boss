# Architecture Verification (2026-09-30)

During the current architectural review phase, we validated the pre-publication baseline and successfully ran local verification tests. However, several advanced operational deployment controls remain blocked due to the lack of appropriate local environments.

## Status of Targeted Operational Gaps

1. **Verify the exact locked Linux/container build and runtime controls.**
   - **Blocker**: The exact locked Linux container build and controls cannot be verified on this Windows workstation without an active Docker/Linux environment.
   - **Status**: Deferred until a staging server or compatible Linux runner is available. The offline deployment shape tests (`scripts/check_private_deployment.py`) verify the presence of Compose security guardrails.

2. **Test the real customer TLS/SSO gateway and secret handling.**
   - **Blocker**: The customer TLS/SSO gateway and private network environment are unavailable locally.
   - **Status**: Deferred until customer-specific staging integrations. The backend continues to enforce Host/Origin requirements locally.

3. **Verify an approved, independently pinned embedding export.**
   - **Blocker**: A provisioned, approved export model is not present on this local workstation.
   - **Status**: The infrastructure handles pinning offline via `ATS_EMBEDDING_MANIFEST_SHA256` but empirical verification is deferred.

4. **Address worker-specific physical-memory containment.**
   - **Blocker**: The existing virtual-address limitation (`RLIMIT_AS`) acts as a memory bounds, but true physical-memory isolation requires Linux cgroups, which are configured at the container level (`mem_limit` in Compose). Enforcing a secondary cgroup natively in Python for the worker process alone is not supported here.
   - **Status**: We rely on the container limits. Fast allocations in the worker could theoretically exhaust the container cgroup and impact the parent ASGI server. Acknowledged as an operational constraint.

5. **Improve failure recovery, monitoring, deployment reproducibility and operational testing.**
   - **Action Taken**: We improved monitoring and operational visibility in `src/app/server.py` by adding structured JSON logs for `worker_busy_timeout`, `worker_execution_timeout`, and `worker_crash` (recording exact `exitcode`). This directly aids in monitoring worker lifecycle anomalies and diagnosing failures.

## Next Steps
We will continue working independently on application features while tracking these documented blockers. Future test environments will unlock these deployment verifications.
