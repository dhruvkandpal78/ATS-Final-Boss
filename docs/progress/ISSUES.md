# Issue Ledger

- [x] Opt-in real hosted reference-screener execution added using 24 fictional PDFs, fixed same-team interventions and private paired observations; see [study record](REFERENCE_STUDY_2026-10-01.md).
- [ ] Independent customer-screener benefit, natural ground truth, immutable end-to-end model identity, fairness and representative load remain unestablished. Small synthetic reference outcomes do not close these gates.

- [x] Fixed-cardinality, content-free analysis HTTP counters/histograms and authenticated JSON/Prometheus metrics implemented in both maintained adapters; counters reset on restart.
- [ ] Customer collector, alert delivery/thresholds, gateway/pre-dispatch telemetry and representative load/resource acceptance remain unverified; see [runtime metrics](../OPERATIONS_METRICS.md).

- [x] Maintained adapters share strict body-header validation; malformed deeply nested JSON is a client error. Worker crash events exclude exception messages.
- [x] Historical Streamlit font imports removed and proxy-score limitations visibly identified.
- [ ] Customer-specific release evidence checklist must be completed; static scan results do not waive deployed security, memory or accuracy validation.

- [x] Regular wheel packages UI/configs/notices; live installed-runtime check now runs outside the checkout in CI.

- [x] Private HTTP adapter uses Uvicorn/Starlette, bounded requests and fail-closed startup warm-up.
- [x] Worker stop admission, cancellation and spawn-failure cleanup coordinated under lifecycle lock.
- [x] Deployment configuration weakening is detected by mutation-tested offline checks; this does not verify runtime isolation.

- [x] Local network binding, Host/Origin validation and private-route authentication implemented with regression coverage.
- [x] Private model loading requires independently pinned manifest and verified artifact bytes; executable pickle remains trusted-only.
- [x] Locked Linux CPU installation and non-root/offline container smoke verified by hosted CI; this smoke does not load a real approved model or establish containment under attack.
- [ ] Real model/resource stress containment, customer gateway integration and external penetration testing still require release evidence.
- [x] Reviewed source-only publication merged in PR #2; all Python/container CI checks passed. No new personal PDFs were included. Older public Git history is not erased.

Updated 2026-09-30. Evidence: [enhancement record](ENHANCEMENT_2026-09-26.md), [research repair](RESEARCH_REPAIR_2026-09-30.md), and [controlled PDF benchmark](CONTROLLED_PDF_BENCHMARK_2026-09-30.md). Checked items mean the named implementation defect is addressed, not that every research release gate is complete.

- [x] **F01** Inference preprocessing differs: one shared CLI/API service; scaling and positive-class regression tests (B02-B03).
- [x] **F02** Rules alter probability: policy and numeric score separated and tested (B02-B03).
- [x] **F03** Text markers presented as PDF evidence: proxy experiments isolated; text B unavailable; PDF score explicitly experimental (B02-B03/B04-B10).
- [ ] **F04** Related variants cross splits: code now retains lineage and group-splits; old data regeneration and near-duplicate audit remain pending (B04-B10).
- [ ] **F05** Published metrics disagree: old reports marked historical. Policy 1.0 had 54.2% false positives on its controlled sample. Policy 2.0 separates advisory anomalies from review triggers and recorded 0/200 false positives on a fresh controlled source sample (100 groups; upper group-level bound 2.95%). Independent naturally occurring manipulation labels, broader benign coverage and probability calibration remain pending. See [precision policy record](PRECISION_POLICY_2026-09-30.md).
- [ ] **F06** Structural coverage: additional trace checks and honest limitations implemented; complete OCG/occlusion/OCR support remains open.
- [x] **F07** Keyword normalization: token-aware aliases, whitespace positions and regression tests implemented.
- [ ] **F08** Explanation fidelity: exact source spans and bounded PDF page/region previews are implemented; causal explanations, OCR and full occlusion reasoning remain open.
- [x] **F09** Misleading demos: unavailable endpoints and UI state replace unsupported success claims.
- [ ] **F10** Startup/artifact coupling: lazy startup and offline deterministic tests implemented; complete reproducible provisioning remains open.
- [ ] **F11** Processing bounds: one isolated worker, deadlines and upload/page/trace bounds implemented and tested; OS memory limits and production isolation remain open.
- [x] **F12** UI hierarchy: rebuilt and browser-checked light/dark responsive interface; full automated accessibility/performance audit remains separate.
