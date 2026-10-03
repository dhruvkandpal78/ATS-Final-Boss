# Website UI redesign — 3 October 2026

## Scope

This pass refined the existing ATS Final Boss frontend in `src/app/index.html` and `src/app/assets/style.css`. It retained the existing routes, input and result IDs, sample controls, upload flow, theme switch, and responsive navigation. No backend, detector, model, scoring, or review-policy code changed as part of the redesign.

The visual system now uses charcoal and warm paper neutrals with one orange accent. The home page has a left-led editorial hero, a restrained document illustration, a clearer source-evidence preview, and a focused closing action. The analysis workspace, input tabs, PDF drop area, results, findings, source context, reading pages, and footer use sharper geometry, improved spacing and type hierarchy, visible focus states, and responsive layouts. Copy continues to describe findings as evidence for human review and does not imply a calibrated cheating probability or candidate-suitability judgment.

## Preserved animation and dependencies

The existing horizontal, scroll-driven seven-step pipeline is preserved. This redesign did not edit `src/app/assets/pipeline-timeline.js`, the pipeline section's structure, its class/ID hooks, its seven steps, or its GSAP behavior. One copy correction changes "independent" to "complementary" signals, avoiding a statistical-independence claim. The same implementation pins and scrubs on supported desktop viewports and presents a static vertical sequence for compact viewports or reduced-motion preference. Its route-change cleanup remains in place.

The locally vendored `gsap.min.js`, `ScrollTrigger.min.js`, and `SplitText.min.js` files declare GSAP **3.15.0** in their headers and link to the [GSAP Standard License](https://gsap.com/standard-license/). They are third-party code and retain GreenSock's copyright and license terms; the project's ownership notice does not supersede them. No GSAP dependency file was modified in this redesign.

## Verification

- Browser review covered dark and light home and analysis views, a 390 px mobile menu, and the compact pipeline fallback. The parent task confirmed these rendered and behaved as expected.
- The key route, upload, result, navigation, and seven pipeline-step hooks remained present in the source.
- `node --check src/app/assets/app.js`, `node --check src/app/assets/theme.js`, and `git diff --check` passed for the frontend changes.
- This visual change establishes no new performance claim. The separately executed [external challenge](../../results/reports/external-hiringaudit-20261003.md) is adverse and is now acknowledged on the methodology page.
- Final combined offline suite: 830 passed, five skipped, three integration tests deselected. Desktop pipeline step controls and route reload were checked; browser console showed no errors at the check.

The working baseline already contained uncommitted pipeline and preview-export changes before this redesign. This note documents the UI pass and does not present that earlier work as newly created here.
