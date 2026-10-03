# Frozen Kaggle PDF stress test — October 3, 2026

Share with caveats: this is a measured controlled-edit stress test on real PDF layouts, not independent natural-world accuracy or downstream protection.

## Source and composition

Downloaded [Snehaan Bhawal Resume Dataset](https://www.kaggle.com/snehaanbhawal/resume-dataset/metadata), version 1. Publisher lists CC0; sources are scraped LiveCareer resume examples with unreviewed manipulation labels. Fresh archive contained 2,484 unique PDFs. Raw PDFs and private receipts remain excluded from Git. No document content was sent to an external model API.

Excluded 184 previously used sources (all nine earlier train/validation/holdout manifests), two normalized-text duplicates and three final rounding sources. Selection is independent of predictions. Final set: **2,295 unique sources: 1,836 unmodified (80%) and 459 injected (20%)**. Each source contributes one final document; one additional intervention page preserves the original layout. Ten fixed authored attack families are distributed 46 each, except keyword repetition (45).

## Measured dispositions

| Cohort | N | Complete review | Partial review | Complete no-signals | Insufficient | Runtime error |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Unmodified originals | 1836 | 0 | 0 | 1813 | 23 | 0 |
| Added attacks | 459 | 272 | 3 | 182 | 2 | 0 |

**Unmodified flags (false-positive proxy): 0/1,836 (0.000%).** Originals are not certified benign, so a true false-positive count/rate remains unknown.
**Complete no-signals on intended edits (controlled detector misses): 182/459 (39.651% of all injected rows).** There were 2 additional insufficient/error attack holds. Holds and partial reviews are separate dispositions; they are not silently counted as detections, clean cases or successful attacks.
These misses are relative to the intended manipulation label, not proof that a downstream screener obeyed any attack. Among complete injected analyses, 182/454 (40.088%) returned no-signals; three partial reviews and two insufficient cases are excluded from that complete-only denominator.

Unmodified insufficient/error holds: 23/1,836. Review is a human-routing signal; no hiring rejection or downstream attack prevention is measured.

## Per-family outcomes

| Authored family | N | Complete review | Partial review | Complete no-signals | Insufficient | Runtime error |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| visible_direct | 46 | 45 | 1 | 0 | 0 | 0 |
| invisible_direct | 46 | 46 | 0 | 0 | 0 | 0 |
| white_direct | 46 | 46 | 0 | 0 | 0 | 0 |
| tiny_direct | 46 | 46 | 0 | 0 | 0 | 0 |
| zero_width_direct | 46 | 45 | 1 | 0 | 0 | 0 |
| homoglyph_direct | 46 | 0 | 0 | 44 | 2 | 0 |
| base64_instruction | 46 | 0 | 0 | 46 | 0 | 0 |
| spanish_instruction | 46 | 0 | 0 | 46 | 0 | 0 |
| conditional_mimicry | 46 | 0 | 0 | 46 | 0 | 0 |
| keyword_repetition | 45 | 44 | 1 | 0 | 0 | 0 |

## Interpretation and limits

Low control flag burden does not establish comprehensive injection protection. Shared lexical patterns and fixed attack templates do not validate general recall, multilingual resistance, encoded payload resistance, scanned/OCR content or hidden-layer coverage. The conditional family requests unsupported assumptions about qualifications and probes an evasion tradeoff in the precision guard. No model parameters, policy rules or thresholds were changed after outcomes were opened. Future tuning against these cases makes this set development evidence.

The 20% attack share and uniform family mix are intentionally artificial. Byte/text deduplication and source exclusion do not establish person-level or semantic near-duplicate independence, independently adjudicated labels, fairness, real attacker behavior, realistic prevalence or customer efficacy. Row Wilson intervals in the private summary are descriptive; their independence assumption can fail through templates/site/category dependencies. A zero observed proxy does not guarantee zero deployment errors.

Complete no-signals means supported checks completed without actionable cues, not that the document is authentic or an LLM will resist it. Incomplete/unsupported analyses require hold/error handling. This run exercises the canonical PDF service through real local components, not the HTTP gateway, existing customer screener or operating-system resource containment.

## Reproducibility and verification

Code and parameters were frozen before execution. Real CPU MiniLM embeddings use local safetensors revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`. The existing local research candidate was explicitly migrated to data-only V2; old validation/approval claims were not carried forward and deployment approval remains false. Its trained parameters and thresholds were retained. Candidate development sources are excluded. The prior policy freeze is not represented as a deployment approval.

An initial unopened build was retained and superseded before execution solely to explicitly set CPU device and candidate identity. No observations existed then, and the final selection, labels, payloads, detector policy and thresholds were unchanged.

Run: two local CPU workers, 703.687 seconds wall time including startup. This is not a load/latency SLA or cost-per-customer-resume benchmark.

Independent metadata review checked exact composition, stored source/text uniqueness, prior manifest hashes and source overlap; it did not inspect raw PDFs or establish ground truth. An independent raw-receipt tally reconciled all 2,295 results and every per-family table against the summary. Harness tests cover selection, byte integrity, path containment, actual PDF intervention extraction and abstention accounting. Final offline suite: 688 passed, 5 skipped, 3 provisioned integration tests deselected; 13 focused harness checks passed. Actual pinned-model execution also verified the final initializer.

Frozen evidence digests (private raw files retained locally):

- Source archive: `b12c4ab34df707ad2cc64312c016509cad9b6c93b0baed7a6a2c7cbd6b2b7aa4`
- Final protocol: `36f3f2b117923aa0f6c94c0931e95cc7034426a006c108a191b0bc6aae12a2f8`
- Cases manifest: `da233d80b1174b92dfca10b4f830aeaf3e762aac64fec0816a5dc9f2262d2dbc`
- Observation receipt: `2bd0092595f84b283331acd3f99c3f74760125fab6ea74debb12e84ee7542682`
- Summary: `e10ed7e5ea211143ba4d699db61aa26d7026bf416e279156ed41ca5b437c1c87`
- V2 candidate manifest: `7c02d587212008a6b2314c3c4f4e24a3a0562030cab293c69f3bd4093e4b12bb`
- Embedding manifest: `d322a13d4a68f9ee3defed17d8fa1638f36bd63772748b30dae5f71e6060702e`
- Benchmark code: `e93366d41237e3e3b5721ec694441d1d6ab74afdc78abe05e5cb3c51cb6c5e7e`

Local environment: Python 3.14.6 on Windows; PyMuPDF 1.28.2, numpy 2.4.6, pandas 3.0.5, scikit-learn 1.9.0, sentence-transformers 5.7.0, torch 2.13.0. Hosted Linux release checks are separate.

See [protocol and supported commands](../../docs/research/KAGGLE_STRESS_PROTOCOL.md).
