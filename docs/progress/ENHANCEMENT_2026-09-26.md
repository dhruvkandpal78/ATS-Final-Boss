# Enhancement verification record

Date: 2026-09-26. Baseline commit: `a0c2982dfdf2358c39b415c237eb4338eeb98de3`.

Continuation verified 2026-09-28: ownership/licence routes and policy links completed; `venv/Scripts/python.exe -m pytest tests/test_api.py --basetemp=.test-tmp/api-ownership-final -q` passed **21 tests in 4.03s**, exit 0. JavaScript syntax and diff checks passed again. The preserved legacy MIT notice was compared against `git show HEAD:LICENSE` and matches. The earlier 73-test full-suite result remains the latest full run; only policy/static-route and documentation changes followed it.

The ownership view was also verified in the browser on September 28; [ownership screenshot](evidence/ownership.png). The loopback preview was restarted at http://127.0.0.1:8018. Temporary viewport override was reset before handoff.

## Objective and working boundaries

Improve logic, output accuracy, performance and UI/UX while preserving existing work and recording changes. User supplied light white/lavender and dark charcoal/orange visual references and requested a persistent theme switch. A later request added explicit ownership/reuse terms. Work remained local: no push, deployment, data regeneration, final holdout evaluation or legal filing.

Sol subagents handled inference and frontend; Luna handled the detector audit and bounded classifier work. Root integrated API isolation, data lineage, additional detector fixes, test infrastructure, browser checks and documentation. Relevant installed Taste/frontend and computer-use capabilities were used. Unrelated document/spreadsheet/site deployment plugins were not added to the runtime; no additional plugin was required.

## Baseline findings

- Shared inference ignored its scaler and selected class-0 probability; API had a second path and changed probability after rule triggers.
- CLI JSON depended on schema classes that did not exist.
- Plain text markers were presented as PDF evidence.
- API eagerly loaded models, lacked typed validation and allowed unbounded expensive demos.
- Source identifiers were lost on poisoned variants, allowing related resumes across dataset splits.
- Keyword aliases rewrote substrings and positional indexing counted only spaces.
- A benign phrase anywhere disabled all instruction cues.
- PDF layer checks called an unavailable API; grayscale white text and zero-opacity spans were missed.
- Feature extraction constructed an embedding model for every row in multiprocessing workers.
- Small-dataset training failed in an extra nested CV run and selected XGBoost based on installation rather than explicit choice.
- Progress docs said release complete without acceptance evidence.

## Delivered packages

- [B02-B03 shared inference](B02-B03.md): one service, scale once, class-aware score, typed coverage and neutral decisions.
- [B04-B10 detector and evaluation changes](B04-B10.md): source lineage, token/cue/PDF fixes, explicit research proxy path, bounded explanation, validation-only degradation study.
- [B01-B11-B13 runtime and checks](B01-B11-B13.md): diagnostics, lazy isolated worker, limits, deadlines, privacy, API tests and CI separation.
- [UI and ownership changes](UI-OWNERSHIP.md): two themes, evidence-led workspace, honest unavailable states, maintained static source, rights-policy transition.

## Verification evidence

- Full suite, local venv Python 3.14.6, downloads disabled: `$env:HF_HUB_OFFLINE='1'; $env:TRANSFORMERS_OFFLINE='1'; venv/Scripts/python.exe -m pytest tests/ --basetemp=.test-tmp/full-final -q` → **73 passed in 25.75s**, exit 0. Includes cached model loading/integration and generated PDFs; no held-out files used.
- Initial broader run exposed 5 failures with 47 passing (extraction contract, nested CV, stale PDF test API). These were fixed; assertions were not simply discarded. The wrapper's documented 1D probability test was corrected while service tests explicitly check raw estimator class-column selection.
- `node --check src/app/assets/app.js` → exit 0.
- `venv/Scripts/python.exe -m compileall -q src scripts` → exit 0.
- `git diff --check` → exit 0 (Windows line-ending notices only).
- `venv/Scripts/python.exe scripts/doctor.py --json` → exit 0; packages, two saved artifacts/config hashes and embedding config cache found. This is not a signed artifact check.
- API-focused validation initially 19 passed, later includes timeout cleanup and static path traversal tests in the full suite.
- Real HTTP synthetic injection request completed through the isolated local worker: review recommended, text module B not applicable, combined score null, separate instruction/density findings.
- Browser: real sample selection and /analyze result at 390px; dark result has no horizontal overflow. Theme persisted on reload. Light/dark desktop inspected at 1440×1000; subagent also checked 320px.
- Screenshots: [light desktop](evidence/light-desktop.png), [dark desktop](evidence/dark-desktop.png). Browser screenshots are visual evidence, not automated contrast/Lighthouse certification.

Sandbox note: Python 3.14 pytest temporary-directory permissions and multiprocessing were blocked in the restricted runner. Approved local escalated test/preview runs resolved the environmental errors. No dependency downloads were performed for verification.

## Acceptance boundaries and remaining risks

- Implementation regression checks pass; **new precision/recall/F1 or improved accuracy percentages are not established**. Changed features require retraining/calibration on training/validation and an independent real-PDF final benchmark.
- Existing saved model was trained with synthetic structural proxy scores. UI labels numeric PDF output experimental and suppresses it for unavailable/partial evidence; text has no combined score.
- Group splitting implementation is verified on synthetic controls, but existing data was not regenerated. Source IDs alone do not establish near-duplicate independence between different originals.
- PDF analysis uses heuristics. OCR, clipping/occlusion, full optional-content semantics and visual evidence overlays remain incomplete. Document-level findings are not causal explanations.
- Local process isolation bounds elapsed work and concurrency; it is not an OS memory sandbox or production reverse proxy. JSON/base64 transport remains instead of the specification's proposed multipart endpoint.
- Dependencies have supported ranges, not a complete frozen cross-platform lock. No clean-room install or full model/data provenance certification was performed.
- Manual responsive/theme checks passed; exhaustive keyboard/screen-reader review, contrast automation, reduced-motion emulation and Core Web Vitals measurement remain open.
- Rights policy applies only to new protectable original material held by the named owner. It does not revoke prior MIT grants or third-party/platform/statutory rights. Lawyer review is needed before enforcement; no legal outcome is guaranteed.

Next research action: version/freeze features and artifacts, regenerate source-grouped training/validation data, validate benign and adversarial controls, and then touch a final independent holdout once. Do not treat the old Phase/U10 completion note as current status.
