# Final Evaluation Report: Phase 3

## 1. Overview
This document summarizes the final evaluation metrics of the model-agnostic adversarial defense ensemble on the completely isolated `test.csv` dataset. The evaluation assesses the system's ability to detect Types A, B, C, and D attacks (including Keyword Stuffing, Simulated Hidden Text, Irrelevant Jargon, and LLM-obfuscated prompt injections).

## 2. Meta-Classifier Feature Importance
The Logistic Regression meta-classifier (calibrated on the validation set, best C=1.0) learned the following relative weights for each detection module:
- **Module B (Structural PyMuPDF Simulation)**: `+1.29`
- **Module A (Statistical Keyword Density)**: `+1.02`
- **Module C (Semantic Coherence / MiniLM)**: `+0.35`

*Insight*: Structural anomalies are the strongest signal for adversarial injection, followed closely by raw statistical keyword density. Semantic blurring is a softer signal but contributes to catching Type C and D attacks.

## 3. Strict Test-Set Performance
Evaluated on the strict 20% holdout split containing a mix of 496 Clean and 160 Adversarial resumes.

### Classification Metrics
- **Precision**: `0.7279`
- **Recall**: `0.6188`
- **F1-Score**: `0.6689`

### Confusion Matrix
| | Predicted Clean | Predicted Adversarial |
|---|---|---|
| **Actual Clean** | 459 (True Negatives) | 37 (False Positives) |
| **Actual Adv.** | 61 (False Negatives) | 99 (True Positives) |

*Insight*: The system prioritizes a low False Positive Rate to minimize unfair rejection of legitimate candidates (False Positives = 37 / 496 = 7.4%).

### Bootstrapped Confidence Intervals
To ensure statistical rigor in a synthetic context, the F1 score was bootstrapped over 1,000 iterations:
- **Mean Bootstrapped F1**: `0.6664`
- **95% Confidence Interval**: `[0.5993, 0.7285]`

## 4. Visualizations
The automated evaluation pipeline successfully generated the following publishable plots:
1. `results/plots/roc_curves.png`: Compares the True Positive Rate vs False Positive Rate for the Meta-Classifier against individual Modules A and C.
2. `results/plots/degradation_curve.png`: Simulates the detection capability drop-off against an Adaptive Adversary employing word substitution budgets.
