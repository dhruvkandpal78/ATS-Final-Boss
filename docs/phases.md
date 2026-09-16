# 6-Week Prototype Build & Research Phases

## Phase 1: Data, Infrastructure, & Attack Generation (Week 1)
- **Task 1.1**: Setup Python environment, dependencies (`requirements.txt`), and ethics documentation for dual-use dataset generation.
- **Task 1.2**: Clean ~700 Kaggle resumes down to a working set of ~500 clean resumes.
- **Task 1.3**: Write adversarial injection scripts to generate ~200 stuffed resumes spanning Type A (Repetition), Type B (Hidden Text), and Type C (Irrelevant Jargon).
- **Task 1.4**: Lock a 60/20/20 train/validation/test split. *Store the test set entirely out of reach.*

## Phase 2: Statistical & Structural Modules (Week 2)
- **Task 2.1**: Build Module A (Keyword Density). Calculate statistical anomalies based on keyword frequency over text length, grounded in spam-filtering literature.
- **Task 2.2**: Build Module B (Simulated). Create simulated hidden-text fields for the bulk dataset.
- **Task 2.3**: Build Module B (Real PDFs). Convert 30-50 resumes to real PDFs. Implement PyMuPDF forensics to check for text-rendering mode 3, OCGs set to OFF, matching background colors, and font size ≤ 1pt.

## Phase 3: Semantic Coherence & Explainability (Week 3)
- **Task 3.1**: Implement `all-MiniLM-L6-v2` for semantic embeddings.
- **Task 3.2**: Build a lightweight reference corpus from the clean training resumes.
- **Task 3.3**: Implement sliding-window semantic coherence scoring to flag abrupt jargon insertions.
- **Task 3.4**: Integrate SHAP to provide word-level explainability for anomalous sections, demonstrating how statistical/explainability signals isolate mechanical insertions.

## Phase 4: LLM-Obfuscated Attacks & Meta-Classifier (Week 4)
- **Task 4.1**: Generate Type D (LLM-obfuscated) attacks using fixed, logged prompts to test sophisticated prompt injection techniques.
- **Task 4.2**: Set Module A & C thresholds using a single percentile pass on the *validation split only*.
- **Task 4.3**: Build the Combined Scoring Layer. Train a Logistic Regression meta-classifier on the validation split's heterogeneous anomaly scores (statistical, structural, semantic).

## Phase 5: Rigorous Evaluation & Fairness Audit (Week 5)
- **Task 5.1**: Execute the held-out Test evaluation: Precision, Recall, F1, Confusion Matrix (per module and ensemble).
- **Task 5.2**: Execute the Fairness Audit. Slice outputs by a lexical-diversity proxy to evaluate disparate impact risk, connecting technical outcomes to regulatory stakes (e.g., EU AI Act, Title VII).
- **Task 5.3**: Compare the ensemble system against a naive baseline (simple keyword-count).
- **Task 5.4**: Bootstrap F1 scores 1,000 times for robust confidence intervals.
- **Task 5.5**: Perform qualitative error analysis on 2-3 misclassified resumes.

## Phase 6: Adaptive Adversary Test & Documentation (Week 6)
- **Task 6.1**: Implement the Adaptive Adversary Test. Run a manual word-substitution loop on 20-30 resumes (swapping SHAP-flagged words for synonyms) to measure how the defense degrades under active evasion.
- **Task 6.2 (Optional)**: Build a small demonstration of OCR/image-based evasion (flattened PDFs) as a noted future limitation where text-extractors fail entirely.
- **Task 6.3**: Finalize the Results section, ensuring explicit acknowledgement of the synthetic dataset and lack of commercial ATS baseline.
