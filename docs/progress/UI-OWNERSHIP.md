# UI and ownership implementation record

Status: delivered locally; verification continued 2026-09-28. Baseline: a0c2982dfdf2358c39b415c237eb4338eeb98de3.

Changed: src/app/index.html, src/app/assets/style.css, src/app/assets/app.js, frontend/license routes in server.py, LICENSE, LICENSE-MIT-LEGACY.txt, docs/OWNERSHIP.md, README.md.

The user supplied a white/lavender/pink light reference and a charcoal/orange dark reference. These supersede the earlier ivory/emerald appearance requirement. The new interface has a persistent, accessible theme control; responsive landing, analysis, methodology, unavailable lab and ownership views; explicit synthetic samples; input validation; cancellable client waiting; separate model score, policy reasons, coverage and evidence; JSON export and print summary. Source text stays in browser memory and is omitted from the export. No fabricated benchmark cards or demonstration outcomes are shown.

Architecture decision: maintain small vanilla HTML/CSS/JS sources because the repository's web directory contained only historical distribution/dependency files, with no maintainable package/source project. The existing stdlib server can serve this directly without adding a build pipeline or UI dependencies. This deviates from the older proposed React migration and keeps the delivered frontend inspectable. Existing untracked web files are preserved and not served.

Browser evidence: both desktop themes inspected at 1440x1000, mobile layout and real synthetic analysis checked at 390px; subagent also checked 320px. Theme persistence verified on reload. See evidence/light-desktop.png and evidence/dark-desktop.png. Full accessibility certification, automated contrast and Lighthouse performance scores are not claimed.

Ownership: existing license identified Dhruv Kandpal and granted MIT permissions. Its exact prior notice is preserved as LICENSE-MIT-LEGACY.txt. The replacement notice reserves rights only for new legally protectable original additions after the baseline, preserving prior MIT, third-party, statutory and platform rights. A footer and /ownership page link both notices. No automatic fines, guaranteed enforcement, registration, or technical copy-prevention claim is made. No remote visibility or publication change was performed. Legal review before enforcement remains necessary.

Checks: node --check src/app/assets/app.js; git diff --check; HTTP license-route and legacy-notice preservation checks. See the aggregate verification record for results.

## 2026-09-28: active analysis-navigation contrast fix

The top-right Analyze a resume button inherited the active-page link color, overriding its contrasting button text: dark ink on a dark button in light mode and orange text on an orange button in dark mode. Restricted active-page text-color rules to navigation links that are not buttons. The active button retains its normal white-on-charcoal or dark-on-orange color pair, including hover; aria-current remains intact. Changed src/app/assets/style.css only for behavior. Verification uses browser inspection of the analysis route in both themes; no backend behavior changed.

Browser verification passed for both themes on /analyze: the active navigation button now shows white text on charcoal in light mode and dark text on orange in dark mode. Screenshots: evidence/analysis-contrast-light.png and evidence/analysis-contrast-dark.png. Keyboard theme switching was also verified.

## 2026-09-28: percentage signal bars

User requested a percentage bar for manipulation likelihood. Added a combined score meter when the API supplies a finite 0–1 score, plus individual detector percentage meters. Existing uncalibrated output is explicitly labeled a manipulation signal score, not odds of cheating. A probability label is used only when both score_kind is calibrated_probability and model.calibrated is true. Null/invalid scores hide the combined meter and explain why unavailable evidence is not 0% risk. Module signals are never averaged to invent probability. Meters have accessible names/value descriptions and theme-specific colours. Files: src/app/index.html, src/app/assets/app.js, src/app/assets/style.css. No model, threshold, policy or API changes.

Next product improvements, in priority order: independently calibrated text/PDF models with reliability evaluation; a PDF evidence viewer with real page/region anchors; a frozen challenge set with benign skill-heavy/short/OCR controls and manipulation families. These remain planned, not completed features or measured accuracy gains.

## 2026-09-29: findings navigation and coverage guidance

The result view now shows complete, partial and unscorable coverage states explicitly. Missing combined scores offer mode-specific inspection guidance; uncalibrated percentage meters retain their experimental labeling. Detector and severity filters appear only when a result has enough variation to narrow its findings. A live count and zero-match message make the filtered view clear; JSON export still includes every returned finding.

For pasted text, a finding gets a “View in text” action only when the API supplies a valid half-open Unicode code-point span inside the unchanged submitted text. The browser converts those offsets safely for display, highlights exactly that span, and offers Clear selection. Findings without spans remain document-level observations. PDF findings with a valid page index expose the returned page number and, when present, the exact numeric page-space box as text. The interface does not render the original PDF, guess a rectangle, or imply that OCR or a PDF evidence viewer is complete. Clear session and New analysis remove submitted text and source context from the page.

Files: src/app/index.html, src/app/assets/app.js and src/app/assets/style.css. No model, detector, threshold or policy logic changed.
