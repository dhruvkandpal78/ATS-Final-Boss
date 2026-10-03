# Local analysis and motion repair — 3 October 2026

## Reported failures and causes

The supplied screen recording showed the pipeline's highlighted step, progress line and visible text drifting apart. The previous implementation mapped navigation evenly across total scroll distance, ignoring the introductory cover and actual step offsets. It separately scrubbed the pan, progress and per-step line masks; the final step did not travel far enough to complete its reveal. These defects existed in the retained motion implementation and became apparent in user review. Earlier button-only checks were insufficient to establish synchronization.

Repeated localhost POST requests returned 503 while the badge claimed “Ready · model loads on first analysis.” The default model directory held unsupported legacy pickle files. Independently, Windows denied access/cleanup for Python-created directories under system temporary storage, causing requests to fail before model loading. Server liveness did not establish inference readiness.

## Changes

- A single rendered pan position now controls step selection, progress, stems, dots and text opacity/translation. The horizontal scroll style and alternating step arrangement remain. Removed independent reveal triggers and SplitText line masks.
- Navigation uses measured offsets, including the cover and responsive step widths. Measured trailing space brings the last step fully into view; the line ends at the final dot. Buttons settle immediately while ordinary scrolling retains scrub smoothing. Very short viewports (under 600 px), mobile and reduced-motion views use the static sequence. Route teardown clears motion styles.
- Added an explicit local launcher that verifies candidate/embedding manifest pins and frozen policy code, uses offline model loading, preflights temporary-directory creation/cleanup, and binds only to loopback. See [local setup](../LOCAL_DEMO.md). No fallback classifier or fabricated score was introduced.
- Replaced the misleading cold “Ready” badge with “Model not loaded · starts on analysis.” Health parsing requires explicit liveness/readiness values and distinguishes recovery and busy states. Health refreshes after analysis finishes.
- Local experimental bundles are permitted only in local mode; private startup and model loading require explicit deployment approval in addition to existing verification. Old frozen study manifests/receipts remain unchanged. The new local current-policy freeze is ignored, unapproved and has unverified legacy threshold provenance; it establishes no new accuracy or calibration result.

## Result clarity follow-up

The user observed a 100% keyword-density signal next to an insufficient-evidence decision. These answer different questions: a signal can reach its detector scale maximum while pasted text still lacks PDF coverage and a validated combined assessment. The interface previously made this unnecessarily confusing.

The first result now gives the review-policy decision, a short reason and a next action. Its three labels are **Needs review**, **No review triggers found**, and **Inconclusive**. These do not certify fraud or authenticity. Module percentages and gauges were removed; module rows state completion/support status. Model output, coverage and policy diagnostics are collapsed below the evidence. Uncalibrated model output is shown on its raw 0–1 scale, without a percentage gauge. JSON retains original diagnostic values. Detector thresholds and backend decision policy did not change.

Four copy regressions verify that a maximum numeric signal cannot promote insufficient evidence or change a no-trigger result, a zero advisory signal cannot erase a review recommendation, and unknown decisions stay inconclusive. Together with preview export tests, eight tests passed. Browser testing of fictional keyword-dense text produced Inconclusive with the density/coverage explanation; instruction-like text produced Needs review. Details were closed, no module meters remained, both themes were readable, and the mobile result had no horizontal overflow.

## Runtime and motion checks

Browser checks at 1814 × 702 exercised all seven step buttons: each selected its matching label and showed fully opaque, unclipped text. Additional 1280 × 650 and 1440 × 900 resize checks verified geometry-based navigation. Desktop themes, mobile/static fallback and analysis-route cleanup were inspected. JavaScript syntax checks passed.

The actual localhost service completed a fictional pasted-text instruction case and a separately generated fictional PDF. Both returned findings for human review; text kept its partial coverage/no combined-score behavior, and PDF displayed its experimental score with limitations. These are runtime smoke checks, not an accuracy benchmark. A separate port-8001 smoke observed cold health, HTTP 200 analysis and then model readiness. No real applicant data was used or published.

Focused backend verification passed 156 tests with four skips, followed by 18 focused runtime/ASGI tests including the added private approval gate. The final publication-tree offline regression suite passed **837 tests, with five skipped and three integration tests deselected**. Two warnings came from the existing Starlette/httpx deprecation and a deliberate duplicate-ZIP fixture. JavaScript syntax and preview export checks passed. This does not establish hosted CI, production acceptance or model accuracy. Model bundles, embeddings, user recordings, screenshots and generated PDFs remain ignored local files.
