# Publication cleanup - October 3, 2026

## Scope

Removed 14 obsolete or unused tracked files (1,088,429 bytes) from the maintained publication tree. No Git history was rewritten. The prior snapshot is public commit `21d1fa2676d2cad16aeda05ce81a578e27090d3b`; dated records continue to describe their original revisions. Existing licenses, runtime/API/SDK, security controls, tests, synthetic PDF fixtures, controlled benchmark reports and unfavorable results are retained.

## Removed inventory

| Path | Reason |
| --- | --- |
| `src/app/dashboard.py` | Unused Streamlit proxy experiment; not a supported server, not referenced by maintained imports, dependency undeclared. |
| `src/utils/json_encoder.py` | Unused encoder; no maintained imports or callers. |
| `docs/ATS-Final-Boss_Capstone-Review-2_Slide-Deck.md` | Presentation/co-presenter script with outdated claims; not a product or reproducible research artifact. |
| `docs/archive/ATS_Final_Boss_Antigravity_Plan.md` | Duplicate UI proposal or obsolete assistant/design/schedule scaffolding; original PRD and rationale remain. |
| `docs/archive/ATS_Final_Boss_Review_and_UI_Rebuild.md` | Duplicate UI proposal or obsolete assistant/design/schedule scaffolding; original PRD and rationale remain. |
| `docs/archive/design.md` | Duplicate UI proposal or obsolete assistant/design/schedule scaffolding; original PRD and rationale remain. |
| `docs/archive/memory.md` | Duplicate UI proposal or obsolete assistant/design/schedule scaffolding; original PRD and rationale remain. |
| `docs/archive/phases.md` | Duplicate UI proposal or obsolete assistant/design/schedule scaffolding; original PRD and rationale remain. |
| `results/system_architecture_diagram.md` | Obsolete diagram claims implemented SHAP, calibrated probability and authenticity decisions; current architecture is canonical. |
| `results/reports/archive/evaluation_report_v1_stale.md` | Empty stale-report placeholder linking to an incorrect relative path. |
| `results/results.json` | Legacy generated per-row proxy export; preserve aggregate confusion counts in error_analysis.md. |
| `results/plots/roc_curves.png` | Unmaintained historical generated plot; not used by runtime or supported frontend. |
| `results/plots/degradation_curve.png` | Unmaintained historical generated plot; not used by runtime or supported frontend. |
| `results/plots/adaptive_attacker_curve.png` | Unmaintained historical generated plot; not used by runtime or supported frontend. |

## Documentation and publication hygiene

Replaced the accumulated documentation preamble with a concise current-specification index and a separate results index. Marked retained legacy proxy summaries explicitly historical; kept all original metric tables. Aggregate error analysis preserves TN467, FP29, FN42 and TP118 while removing sample IDs and resume excerpts. This minimizes the current tree and does not purge content from earlier published history.

Generated research outputs are ignored except reviewed reports. Local video captures, recording scripts and the separate timeline prototype are excluded from publication. Existing personal PDFs, ignored model/data caches and unrelated uncommitted frontend work are not cleanup targets.

## Verification

Tracked-file search found no caller for the removed dashboard or encoder. New current documentation links are checked separately from historical prose. Full offline checks and publication payload validation are recorded below after completion. No classifier parameters, cue policy, model freezes or response schemas changed.

Final offline suite: **793 passed, five skipped, three provisioned-model integration tests deselected** (one existing Starlette/httpx deprecation warning). All37 local links in the refreshed documentation/results/cleanup indexes resolve. Whitespace checks passed. A separate read-only audit found no maintained caller for either removed Python file and confirmed that runtime entry points, licenses, tests and measured benchmark reports remain. The publication payload guard is required before push.
