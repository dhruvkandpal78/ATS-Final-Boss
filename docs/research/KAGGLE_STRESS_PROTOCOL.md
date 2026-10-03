# Large Kaggle controlled PDF stress protocol

`scripts/run_kaggle_stress.py` evaluates the actual PDF analysis service with
offline model inference. It never trains or tunes thresholds. The default selects
all eligible previously unused byte/text-unique sources, rounded down to a multiple
of five, and modifies exactly one fifth. Each source contributes one final document.
Controls remain original PDFs; attacks append one verified intervention page.

The corpus is [Snehaan Bhawal's Resume Dataset](https://www.kaggle.com/datasets/snehaanbhawal/resume-dataset),
version 1, listed by its publisher as CC0. It contains scraped resume examples,
not independently labeled manipulation cases. Source originals can contain PII;
keep downloads, generated PDFs, manifests and observations in ignored local data
directories. This runner sends no document content to external model APIs.

## Freeze before execution

1. Acquire the pinned corpus with `python scripts/acquire_resume_dataset.py`.
2. Supply an explicitly reviewed data-only V2 candidate and an offline safetensors
   embedding export. The candidate must match the current policy. A migration
   does not confer deployment approval or carry forward old accuracy claims.
3. Pass every previous development/holdout CSV with `--exclude-manifest`.
   Candidate train/validation sources are also excluded automatically. Archive
   identity, every selected PDF, normalized text and excluded CSVs are hashed.
4. Build with `--build-only` before opening outcomes. Source selection and 20%
   assignment are deterministic and independent of detector predictions. A local
   Unicode font is required for Unicode interventions; its bytes are recorded.
5. Run the frozen output with `--run-frozen`. Repeating into the same observations
   file is refused, including after partial failure. Preserve any failed receipt.

Example (paths identify local reviewed resources):

```powershell
python scripts/run_kaggle_stress.py --corpus data/external/kaggle-resume-v1 --output data/benchmarks/kaggle-stress-frozen --models PATH_TO_V2_CANDIDATE --embedding PATH_TO_OFFLINE_EXPORT --exclude-manifest PATH_TO_PREVIOUS_TRAIN_CSV --exclude-manifest PATH_TO_PREVIOUS_VALIDATION_CSV --exclude-manifest PATH_TO_PREVIOUS_HOLDOUT_CSV --unicode-font PATH_TO_LOCAL_UNICODE_FONT --build-only
python scripts/run_kaggle_stress.py --corpus data/external/kaggle-resume-v1 --output data/benchmarks/kaggle-stress-frozen --models PATH_TO_V2_CANDIDATE --embedding PATH_TO_OFFLINE_EXPORT --workers 2 --run-frozen
```

The fixed families cover visible/invisible/white/tiny direct instructions,
zero-width and Cyrillic homoglyph text, Base64, Spanish, conditional mimicry and
sustained skill repetition. All payloads must fit and survive PDF extraction.
These are internally authored interventions, not a natural or independent attacker.
Their uniform family weights are a stress scenario, not deployment prevalence.
The conditional family requests unsupported assumptions about qualifications; it
tests malicious use of apparently conditional wording, not a legitimate procedure.

## Interpret counts carefully

The final summary partitions every source into complete review, partial review,
complete no-signals, insufficient evidence or runtime error. No silently dropped
cases and no conversion of abstention to clean/detected labels are allowed.

- On added attacks, complete no-signals is a measured detector miss. A review is
  a flag, not proof of successful prevention in a downstream screener.
- Flags on unmodified originals are a **false-positive proxy** and review burden;
  their natural benign status has not been independently established.
- Partial review and insufficient/error outcomes are separate operational holds,
  not proof of detector accuracy or successful attacker manipulation.
- Row Wilson intervals are descriptive and do not address shared attack templates,
  site/category dependencies, uncertain labels or deployment shift. Byte/text
  deduplication does not establish person or semantic near-duplicate independence.

Local worker execution uses real embeddings and detectors, but it is neither an
HTTP/customer integration experiment nor physical resource containment acceptance.
Time measurements do not establish a deployed throughput/latency SLA. Natural-world
accuracy, fairness, calibrated cheating probability and downstream benefit remain
separate validation requirements. Keep this protocol frozen after execution;
subsequent improvements require a new, explicitly identified development experiment.
