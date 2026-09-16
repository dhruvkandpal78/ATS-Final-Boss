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
Additionally, an optional **LLM-Generated Adversarial Variant** (`llm_adversarial_resumes.csv`) can be dynamically created using the Anthropic API (`claude-3-5-sonnet`). This provides a secondary, highly linguistically varied adversarial source to evaluate model generalization, balancing the deterministic nature (and zero cost) of the template-based generator against the expensive but realistic LLM-generated attacks.

## Architecture
The system operates as a Stacking Ensemble over three specialized modules:
1. **Module A (Keywords)**: Measures term density, normalizes aliases, and flags abnormally clumped keywords.
2. **Module B (Structural)**: Parses the PDF byte-layer using PyMuPDF to find zero-sized, out-of-bounds, or contextually hidden text.
3. **Module C (Semantics)**: Uses `all-MiniLM-L6-v2` to compute sliding-window semantic variance. Anomaly scores spike when a resume contains disjointed jargon.

## Evaluation & Results
All metrics (Precision, Recall, F1) are computed on a strictly held-out test set (20% split). After fixing a critical normalization bug in Module A (which had been zeroing out all keyword-density scores), the pipeline achieved strong detection performance. The **Hybrid System** (Meta + Rules) achieved the best overall F1 of **0.7834** (Precision: 79.87%, Recall: 76.88%). The Stacking Ensemble (F1: 0.7752) and Logistic Regression baseline (F1: 0.7791) achieved highly comparable results, demonstrating strong linear separability of the three-module anomaly scores.

*See `results/reports/experiments_summary.md` for full benchmark metrics.*

## Error Analysis
* **False Positives**: The Hybrid System maintains strong precision (79.87%), but highly-technical legitimate resumes with dense keyword sections can occasionally be flagged by Module A's density detector.
* **False Negatives**: Type C (semantic blurring) attacks remain the hardest to detect (52.50% detection rate) because they blend context-free jargon that is semantically similar to legitimate technical language. Type B (structural) attacks are caught at 100% due to the explicit `[HIDDEN_TEXT_START]` marker in the proxy.
* **Historical Bug (Fixed)**: An earlier version had a critical normalization bug in Module A where the optimal calibrated threshold of 0.000 caused the normalizer to output 0.0 for all inputs. This was fixed by adding a proper fallback: `normalized = 1.0 if score > 0 else 0.0` when threshold equals zero.

*See `results/reports/error_analysis.md` for specific samples.*

## Adaptive Attacker & Robustness
We deployed a white-box simulation (the Adaptive Attacker endpoint) where an adversary optimizes against the meta-classifier's decision boundary.
By implementing **Moving Target Defense (MTD)**—jittering the final decision threshold randomly by ±5% at inference time—the success rate of greedy iterative attacks plummeted, proving basic robustness without requiring massive architecture changes.

## Limitations & Future Work
* PyMuPDF dictionary parsing does not catch raw PDF stream manipulation (e.g., deeply obfuscated Text Rendering Mode 3 operations).
* The semantic model (`MiniLM`) is English-only and does not handle multi-lingual resumes well.
* Future work should incorporate robust multi-lingual embeddings.

## Related Work
* **Adversarial Attacks in NLP:** General textual adversarial attacks often utilize synonym substitution or formatting tricks. Jin et al. (2020) in *Is BERT Really Robust? A Strong Baseline for Natural Language Attack on Text Classification and Entailment* (TextFooler) demonstrates how language models can be fooled by semantically preserving perturbations, akin to our Type C semantic blurring.
* **ATS Gaming & Keyword Stuffing:** Academic literature on ATS gaming is sparse, largely due to the proprietary nature of commercial ATS systems (e.g., Workday, Taleo). However, industry analyses from platforms like Jobscan (e.g., \"How to Beat the ATS\") routinely discuss white-text steganography and skill-section stuffing, motivating our Module A and B defenses.
* **Prompt Injections & LLM Defenses:** With the rise of LLM-based evaluators, direct prompt injections have become a critical threat. Perez et al. (2022) in *Ignore Previous Prompt: Attack Techniques For Language Models* and Greshake et al. (2023) in *Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection* formalize the exact Type D attacks simulated in our dataset, where context windows are hijacked by adversarial instructions.
* **PDF Steganography:** Hiding text within PDFs (Type B attacks) exploits the PDF rendering specification. Zhong et al. (2020) and various cybersecurity whitepapers on PDF malware analysis highlight the use of zero-width fonts, off-page rendering coordinates, and matching foreground/background colors (Text Rendering Mode 3) to embed hidden payloads that parsers extract but humans cannot see.
