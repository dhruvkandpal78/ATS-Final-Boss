# Final Evaluation Report: Advanced Stacking Ensemble

## 1. Overview
This document summarizes the final evaluation metrics of the model-agnostic adversarial defense ensemble on the completely isolated `test.csv` dataset. The system evaluates the ability to detect Types A, B, C, and D attacks (including Keyword Stuffing, Simulated Hidden Text, Irrelevant Jargon, and LLM-obfuscated prompt injections).

To maximize precision, the Meta-Classifier was upgraded from a basic Logistic Regression to a **Stacking Ensemble** (Random Forest + Logistic Regression with 5-fold internal Cross-Validation). 

## 2. Meta-Classifier Feature Importance
The Random Forest base estimator within the Stacking Classifier learned the following relative importance weights for each detection module:
- **Module A (Statistical Keyword Density)**: `57.25%`
- **Module C (Semantic Coherence / MiniLM)**: `23.84%`
- **Module B (Structural PyMuPDF Simulation)**: `18.91%`

*Insight*: The ensemble relies heavily on statistical keyword density as the primary baseline, heavily penalizing resumes with stuffed keywords. Semantic coherence serves as a strong secondary signal for catching anomalous context transitions (like prompt injections), while structural anomalies act as a definitive, albeit less frequent, trigger.

## 3. Strict Test-Set Performance
Evaluated on the strict 20% holdout split containing a mix of 496 Clean and 160 Adversarial resumes.

### Classification Metrics
- **Precision**: `0.8710`
- **Recall**: `0.5062`
- **F1-Score**: `0.6403`

### Confusion Matrix
| | Predicted Clean | Predicted Adversarial |
|---|---|---|
| **Actual Clean** | 484 (True Negatives) | 12 (False Positives) |
| **Actual Adv.** | 79 (False Negatives) | 81 (True Positives) |

*Insight*: The upgraded Stacking Ensemble prioritizes an **ultra-low False Positive Rate** (12 out of 496 = 2.4%). This is incredibly important for a real-world ATS system, ensuring that legitimate candidates are rarely unfairly rejected by the AI shield. Precision jumped significantly to `87.1%`, meaning when the system flags an attack, it is almost certainly correct.

### Bootstrapped Confidence Intervals
To ensure statistical rigor in a synthetic context, the F1 score was bootstrapped over 1,000 iterations:
- **Mean Bootstrapped F1**: `0.6400`
- **95% Confidence Interval**: `[0.5669, 0.7092]`

## 4. Visualizations
The automated evaluation pipeline successfully generated the following publishable plots:
1. `results/plots/roc_curves.png`: Compares the True Positive Rate vs False Positive Rate for the Meta-Classifier against individual Modules A and C.
2. `results/plots/degradation_curve.png`: Simulates the detection capability drop-off against an Adaptive Adversary employing word substitution budgets.

## 5. Standalone Module B Evaluation (Real PDFs)
Because the main evaluation uses a CSV dataset, Module B's main metrics are based on a synthetic text marker proxy. To validate its true forensic capabilities, a standalone evaluation was run on 100 generated PDFs (50 Clean, 50 with hidden text using 1pt white font).

- **Precision**: `1.0000`
- **Recall**: `1.0000`
- **F1-Score**: `1.0000`
- **False Positives**: `0 / 50`
- **False Negatives**: `0 / 50`
