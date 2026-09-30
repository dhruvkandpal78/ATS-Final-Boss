# Current system architecture

Updated September 30, 2026. This describes the maintained implementation; older plans and experimental reports are historical.

## Runtime and trust boundaries

ATS Final Boss is an input-level resume inspection tool. It reports evidence and coverage before a downstream screening decision. It does not verify claims, determine hiring suitability or establish a probability of dishonesty.

```mermaid
flowchart TD
    UI[Maintained browser UI: src/app] --> Gateway[Customer TLS and SSO gateway: private deployment]
    Gateway --> API[Uvicorn and Starlette adapter]
    Demo[Loopback demo UI] --> Local[Standard-library local adapter]
    Local --> Worker
    API --> Worker[Isolated inference worker and deadline]
    CLI[CLI adapter] --> Service[Shared AnalysisService]
    Worker --> Service
    Service --> Extract[Bounded PDF extraction or submitted text]
    Extract --> A[Keyword density and repetition]
    Extract --> B[PDF trace heuristics: PDF only]
    Extract --> C[MiniLM coherence and instruction cues]
    A --> Evidence[Source findings and explicit coverage]
    B --> Evidence
    C --> Evidence
    A --> Model[Experimental classifier: complete PDF features only]
    B --> Model
    C --> Model
    Evidence --> Policy[Policy 2.0: instruction or sustained repetition]
    Model --> Advisory[Separate uncalibrated score]
    Policy --> Result[Versioned result and review decision]
    Advisory --> Result
    Evidence --> Result
```

The CLI and HTTP worker use `src/core/analysis_service.py`; adapters do not invent PDF structural scores for plain text. The API bounds uploads, rejects concurrent analysis, uses an isolated worker with a deadline and cleans temporary files. PDF parsing is limited to 20 pages and 100,000 extracted characters. Unsupported, encrypted, scanned-only, incomplete and failed analyses expose coverage limitations. OCR is not implemented.

Uploaded documents are untrusted data. Candidate weights are trusted local artifacts, never uploaded documents. Candidate bundles are hash-checked before pickle deserialization; hashes detect accidental changes, not replacement of both artifacts and manifests by an attacker.

Private mode additionally requires an independently pinned manifest digest, verifies policy hashes, and deserializes the exact verified bytes. It requires Linux resource limits and an authenticated customer gateway. Host/Origin guards, bearer authentication, connection limits and a global request budget apply before analysis. Local mode refuses network-wide binding. The proposed container is non-root, read-only and resource-limited; Docker execution and customer SSO/TLS integration remain unverified. See [private pilot guide](PRIVATE_PILOT.md).

`src/app/asgi.py` is the maintained private HTTP adapter. Uvicorn runs one server process with a concurrency cap; the application limits body size and total upload time before passing validated payloads to the shared isolated worker. Private startup validates pinned artifacts and performs a synthetic warm-up before accepting traffic, eliminating the earlier readiness/warm-up routing cycle. Static UI and API requests require gateway-injected authentication. Lifespan shutdown stops worker admission and coordinates cleanup; model work stays outside the HTTP process.

The worker owns its process and pipe under a request lock. A stop event cancels active work during bounded polling and prevents new requests; shutdown no longer closes a pipe concurrently with a request. Spawn failures clean up both endpoints. The deployment validator rejects weakened Compose controls, while CI adds a data-free image build and smoke test. These are testable architecture controls, not proof of runtime isolation or external security certification.

Private embedding exports have their own independently pinned integrity contract and are loaded from a reviewed local safetensors directory. Startup exercises multi-sentence semantic encoding and a synthetic PDF, then checks detector statuses and classifier coverage before serving. Readiness respects stop admission, and private child diagnostics cannot bypass redacted parent response logs. Shared container memory remains a containment limitation; the worker virtual-address limit must not be interpreted as a physical-RAM bound.

## Evidence, policy and score

- Module A computes token-aware skill density and concentration. Module C uses off-the-shelf MiniLM sentence-window coherence plus normalized, locally contextual instruction patterns. Positive P95 thresholds come only from source-disjoint clean validation examples; invalid/zero thresholds disable the affected score.
- Module B uses PyMuPDF text traces for invisible rendering, tiny fonts, off-page/degenerate boxes, optional-content layers and heuristic background matches. It does not fully resolve clipping, occlusion, OCR or pixel visibility. Disabled optional-content groups mark coverage partial.
- Policy 2.0 recommends review for direct instruction cues or sustained skill repetition. Structural anomalies, density, semantic variance and experimental classifier predictions remain advisory. The stricter gate reduces false alarms but can miss subtler attacks. Findings expose `review_trigger` and uncertainty.
- The classifier consumes A/B/C features in a fixed order, scales once and selects class 1 explicitly. Its output is uncalibrated and separate from the review decision. Plain text or incomplete PDF evidence cannot produce a combined score. A review rule never rewrites the numeric score.
- Result schema 2.0 exposes status, policy version, model identity, decision, reason codes, coverage, modules, findings and timings. Missing evidence yields `insufficient_evidence`; absence of a review trigger does not establish authenticity.

Exact text anchors use original Unicode code-point offsets and abstain on ambiguous normalization mappings. PDF findings retain page/trace regions. On-demand previews render at most three finding pages, 900 pixels per side and 2 MiB total PNG data. Preview highlights locate traces, not intent. Images and submitted source text are excluded from the exported analysis JSON. Full causal explanations and complete PDF visibility remain open work.

## Research workflow

`scripts/acquire_resume_dataset.py` stores version-pinned public PDFs with provenance and unreviewed labels under ignored `data/`. Public availability does not establish manipulation labels. Controlled variants are generated separately and grouped with their source; their labels mean known added attacks, not verified absence of pre-existing manipulation.

`src/evaluation/train_pdf_candidate.py` requires explicitly labeled, source-disjoint training/validation manifests and rejects byte-identical overlap. It uses actual PDF detector features, train-only scaling and LogisticRegression. Candidate output is isolated from deployed artifacts and includes thresholds, artifact hashes, source hashes, dependency versions, policy version and detector/service code hashes.

`src/evaluation/evaluate_holdout.py` verifies the frozen policy before label access, checks development overlap and records a one-time access receipt. Failed access consumes the local receipt too. Reports distinguish policy confusion counts from model ROC-AUC, and include family counts, source-group bootstrap intervals and a group-level false-positive upper bound. These local guards do not constitute a tamper-proof global test registry.

The legacy synthetic structural-proxy experiment path uses training/validation only and cannot substitute for deployed PDF evidence. Global deployed thresholds/models are not overwritten by candidate training. The saved global zero keyword threshold remains unavailable until valid calibration is supplied.

## Maintained files and measured limits

- Runtime/UI: `src/app/`, `src/core/`, `src/inference.py`, `src/modules/`.
- Research: `src/evaluation/`, `src/data_prep/`, `scripts/`.
- Contracts/regressions: `tests/`, `configs/`, `.github/workflows/ci.yml`.
- Team records: `CHANGELOG.md`, `docs/progress/`, aggregate `results/reports/`.

The maintained frontend is the vanilla application in `src/app/`; the older `web/dist/` build is historical. Light/dark themes, evidence filters, source highlighting and explicit advisory labels are implemented.

Policy 1.0's first controlled holdout had 13/24 no-added-attack false positives. Policy 2.0's fresh holdout had 0/200 such false positives and detected 100/100 scripted attacks across 100 source groups. Samples differ, so this is not a paired improvement estimate. Natural labels, near-duplicate/person-level independence, new attack families and calibrated probabilities remain unverified. See [precision research record](progress/PRECISION_POLICY_2026-09-30.md).

Personal resumes, downloaded datasets, local candidate weights and unrelated personal projects are excluded from new publication changes. Synthetic test fixtures remain part of the test suite. Existing GitHub history may still contain PDFs published in earlier commits; removing current tracked paths does not rewrite that history.

## Installed package resource contract

Regular wheels include src/app/index.html, maintained CSS/JavaScript assets, the existing configs JSON package and unchanged license notices in dist-info/licenses. Adapters resolve the same resources in checkouts and installed packages; public notice names are allowlisted. A shared runtime path helper resolves ATS_MODELS_DIR for CLI, worker and private startup without changing candidate integrity or detector policy. CI launches the installed ASGI service outside the checkout and asserts no model process is spawned by the static smoke. This verifies packaging and lifecycle, not approved-model compatibility or physical-memory containment.
