# Research results

## Controlled PDF evidence

- [Frozen 2,295-PDF stress test](kaggle-stress-20pct-20261003.md): original adverse
  result, including 182 completed misses and unreviewed original labels.
- [Exact-case recovery replay](kaggle-recovery-development-20261003.md): development
  replay after observing those misses; not a fresh holdout or population accuracy.
- [Controlled V1 holdout](kaggle-controlled-v1-holdout.md) and
  [controlled V2 holdout](kaggle-controlled-v2-holdout.md): earlier related studies.
- [Paraphrase development record](../../docs/progress/PARAPHRASE_REDTEAM_2026-10-03.md):
  authored commands, benign controls and explicitly remaining misses.

## Legacy synthetic proxy evidence

[Experiment summary](experiments_summary.md), [holdout comparison](holdout_comparison.md)
and [aggregate error analysis](error_analysis.md) preserve earlier reported results.
They used previous code or synthetic text/proxy signals and do not describe the
current PDF service. Removed runners cannot reproduce them from the current tree.
No new validation or independent accuracy is implied by retaining these records.

Obsolete generated plots, per-row result JSON, unsupported architecture diagram and
empty stale-report placeholder were removed; their prior Git revision is documented
in the [cleanup inventory](../../docs/progress/REPO_CLEANUP_2026-10-03.md). Resume excerpts
and sample identifiers are not needed in the maintained aggregate error report.
