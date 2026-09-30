# Project Rules, Boundaries, & Methodology

## 1. What to Use (Methodologies & Libraries)
- **Pre-trained Models**: Use `sentence-transformers/all-MiniLM-L6-v2` entirely off-the-shelf to measure semantic coherence.
- **Explainability**: Findings and source anchors locate observations. SHAP attribution is unimplemented; do not present highlights as causal explanations.
- **PDF Extraction**: Use `PyMuPDF` and `pdfplumber` strictly for structural forensics. Go beyond simple 'white text' heuristics and check for text-rendering mode 3 and Optical Content Groups (OCGs) set to OFF.
- **Ensemble Learning**: Use `scikit-learn` Logistic Regression as a lightweight meta-classifier to combine heterogeneous anomaly scores.
- **Thresholding**: Use P95 of clean validation examples, calculated only on the source-disjoint validation split. Require both labeled classes for validation diagnostics. Reject zero/nonfinite thresholds instead of substituting arbitrary constants. Detection-threshold calibration does not establish probability calibration.

## 2. What to Avoid (Anti-Patterns & Scope Limits)
- **NO Model-Level Defenses**: Do not attempt to fine-tune the MiniLM models, the downstream ATS screener, or implement adversarial training. This project's novelty is explicitly positioned as an **input-level, model-agnostic pre-filter**.
- **NO Test Set Leakage**: Do not use the Test split for threshold calibration, hyperparameter tuning, or preliminary checks. The Test set is touched exactly *once* at the very end of Phase 5.
- **NO Proprietary ATS Baselines**: Acknowledge the lack of access to commercial ATS tools as a formal limitation. Baseline against an open-source standard.

## 3. Generative AI & Attack Simulation
- **Adversarial Ranking Attacks**: Treat keyword stuffing explicitly as an adversarial ranking attack (manipulating a document's retrieval rank), not just a classification error.
- **Attack Generation**: The maintained generators create controlled, scripted edits. No external LLM injector is supported. Any future external generation workflow requires explicit data-use permission and recorded model revision, prompt, parameters and provenance; generated attacks do not establish natural attack performance.
- **Dual-Use Ethics**: The dataset generation scripts are dual-use (they create adversarial attacks). Maintain ethical disclosure norms when documenting this process.

## 4. Evaluation Rigor & Error Handling
- **Fairness Assumptions**: The fairness audit uses lexical diversity proxies based on adjacent domains (e.g., AI-text detection bias). State explicitly that this is testing a hypothesis on whether known failure modes transfer to this detector type.
- **Confidence Intervals**: Report confidence intervals (bootstrap the test set ~1,000 times) instead of single point estimates to mitigate the noise inherent in a 400-500 sample synthetic dataset.
- **Robustness**: Report unavailable or incomplete PDF coverage explicitly. Missing evidence does not prove manipulation or cleanliness.
