# Research & Methodology

## Problem
Modern Applicant Tracking Systems (ATS) increasingly rely on Large Language Models (LLMs) and automated keyword extractors to screen candidates. This has incentivized adversarial behavior from applicants, including Keyword Stuffing, Semantic Blurring, and direct Prompt Injections (e.g., "Ignore all previous instructions").

## Threat Model
We assume a "Grey Box" attacker:
* The attacker knows the system uses keyword matching and semantic similarity (MiniLM).
* The attacker can manipulate text content and PDF byte-structure (white-text, zero-sized bounding boxes).
* The attacker can embed direct prompt injections to attack downstream LLMs.

## Dataset
We utilized a synthetic dataset of 6,555 resume samples (clean and adversarial) built using Faker and localized to represent diverse demographic profiles, ensuring we can test fairness.

## Architecture
The system operates as a Stacking Ensemble over three specialized modules:
1. **Module A (Keywords)**: Measures term density, normalizes aliases, and flags abnormally clumped keywords.
2. **Module B (Structural)**: Parses the PDF byte-layer using PyMuPDF to find zero-sized, out-of-bounds, or contextually hidden text.
3. **Module C (Semantics)**: Uses `all-MiniLM-L6-v2` to compute sliding-window semantic variance. Anomaly scores spike when a resume contains disjointed jargon.

## Evaluation & Results
All metrics (Precision, Recall, F1) are computed on a strictly held-out test set (20% split). The `run_experiments.py` script confirms that the Stacking Ensemble heavily outperforms single-module detection. 

*See `results/reports/experiments_summary.md` for full benchmark metrics.*

## Error Analysis
* **False Positives**: Highly experienced candidates with 10+ years of dense project descriptions occasionally trigger Module A.
* **False Negatives**: Subtle semantic blurring (replacing 2-3 words per sentence) currently bypasses Module C if the overall cosine similarity remains smooth.

*See `results/reports/error_analysis.md` for specific samples.*

## Adaptive Attacker & Robustness
We deployed a white-box simulation (the Adaptive Attacker endpoint) where an adversary optimizes against the meta-classifier's decision boundary.
By implementing **Moving Target Defense (MTD)**—jittering the final decision threshold randomly by ±5% at inference time—the success rate of greedy iterative attacks plummeted, proving basic robustness without requiring massive architecture changes.

## Limitations & Future Work
* PyMuPDF dictionary parsing does not catch raw PDF stream manipulation (e.g., deeply obfuscated Text Rendering Mode 3 operations).
* The semantic model (`MiniLM`) is English-only and does not handle multi-lingual resumes well.
* Future work should incorporate robust multi-lingual embeddings.
