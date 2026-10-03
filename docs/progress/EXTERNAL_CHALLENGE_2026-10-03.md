# External challenge implementation and validation

The user requested stronger journal-level experimentation. Added a pinned data-only
HiringAudit importer, pre-outcome protocol, frozen runner and paired grouped
statistics. Kept current detector weights, thresholds and policy unchanged.
Raw corpus and receipts remain ignored; the maintained publication includes code,
aggregate [adverse findings](../../results/reports/external-hiringaudit-20261003.md)
and limitations. No model training, new classifier, natural labels or independent
human review is invented.

The external run covered 100 groups and 1,100 original/variant PDFs. It found
100/1,000 supplied attacks flagged and 900 complete unflagged, with 0/100 original
flags and no incomplete/errors. The 90% target failed; below-2% burden is not
established. Externally authored templates materially broadened the test and
exposed the earlier controlled recovery's generalization limit. This dataset is
now explicitly consumed for development.

Separate review caught an unknown-decision projection edge case. No complete
row in this run had unavailable classifier output; its frozen receipt remains
unchanged. The maintained runner fixes that projection, records the categorical
decision, and adds regressions. Executed source remains at commit `f81891f` for
audit; future current-code runs produce different receipts and must have new
identities. Acquisition tests cover ZIP hash pins, traversal, links, duplicate
outputs, unknown assignments and publisher lineage. Grouping tests cover unequal
clusters, paired draws, incomplete outcomes and boundary intervals.

Verification before the reporting fix: **826 offline tests passed**, five skipped,
three integration deselected. After the reporting fix: **41 focused tests passed**.
Final offline verification: **830 passed**, five skipped, three integration
deselected in 91.21 seconds. Python compilation and JavaScript syntax checks pass.
Existing
Starlette/httpx deprecation remains; duplicate-ZIP rejection deliberately creates
a warning in its test fixture. UI changes and retained third-party animation terms
are documented in [the UI record](UI_REDESIGN_2026-10-03.md).
