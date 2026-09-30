# Application architecture hardening

The user clarified that the application should support the research methodology and that this work should enhance architecture rather than draft a paper. No manuscript was created. Research-protocol draft files created during the initial interpretation were removed before staging.

## Implemented changes

- Added a Uvicorn/Starlette HTTP adapter for the private image, using the existing shared inference worker and security settings. It preserves the maintained UI/API behavior, bounds upload size/time, validates requests before inference, uses generic errors and redacted response events, and avoids trusting forwarded identity headers.
- Private startup verifies the independent model pin and frozen policy, then warms the worker with synthetic text before accepting traffic. Liveness/readiness are distinct; missing or invalid dependencies fail startup instead of admitting a deceptively ready service.
- Worker shutdown now stops admission, cancels active work through bounded polling and coordinates process/pipe cleanup under the request lock. Worker spawn failure closes both endpoints and allows recovery.
- Added a customer gateway template with TLS, SSO authorization delegation, upload/connection/rate limits and backend-token injection from a protected include. No SSO account or identity service is fabricated or deployed.
- Added an offline deployment validator and mutation tests for public ports, external secondary networks, capability additions, root identity, host devices/socket mounts, writable model mounts, invalid resource budgets and secret wiring.
- Updated the hashed Linux CPU runtime lock and CI with deployment validation plus an isolated data-free Docker image build/smoke job. Docker is unavailable locally; CI execution and exact Linux installation remain unverified.
- Consolidated binary metric validation into a reusable statistics module, including explicit denominators and undefined cases, Wilson intervals, exact zero-event bounds and seeded source-group resampling. Only synthetic tests were run; completed reports and consumed holdouts were not changed or reopened.

## Verification and limits

Final checks are recorded after integration below. The updated lock's 57 upstream distribution versions were audited without skipped entries or known advisories; the installed environment audit also reported no known vulnerabilities. Advisory scans do not establish absence of vulnerabilities.

Final integration: 218 tests passed in 39.24 seconds, including cached-model checks. The Starlette test client emitted one compatibility deprecation warning for its existing httpx backend; the test run passed. A real hidden loopback ASGI process passed startup, liveness, maintained UI/security-header and invalid-input rejection checks without loading models or reading PDFs. Scoped high-severity static scanning, offline deployment validation and whitespace checks passed. Both adapters now share the response-header contract. Windows sandbox temporary-folder restrictions required approved local test execution. Linux private-mode lifecycle tests use synthetic injected dependencies; they do not substitute for a real container test.

These changes do not alter the frozen detector policy or establish improved detection accuracy. Customer SSO/TLS integration, exact container/resource-limit verification, artifact/embedding provenance, external penetration testing, privacy/license decisions and independent field validation remain release gates. The gateway template and static Compose validation do not prove an effective deployed network boundary. No company-ready certification or IEEE acceptance is claimed.

## Git handoff

Commit code, architecture, tests and change records together so the research teammate can trace implementation changes. Exclude personal PDFs, datasets, model artifacts, secrets, unrelated projects and private local history. Publication uses the existing clean remote-based branch; no force push or history rewrite is authorized.
