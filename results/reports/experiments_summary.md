# ATS Final Boss - Evaluation Experiments

## Phase 9: Benchmark Experiment
| Model | Precision | Recall | F1 Score | ROC-AUC |
|-------|-----------|--------|----------|---------|
| Module A (Keywords) | 0.0000 | 0.0000 | 0.0000 | 0.5000 |
| Module B (PDF/Text Proxy) | 1.0000 | 0.2500 | 0.4000 | 0.6250 |
| Module C (Semantics) | 0.2570 | 0.8625 | 0.3960 | 0.6059 |
| Simple Fusion (OR) | 0.2692 | 0.9187 | 0.4164 | 0.0000 |
| Logistic Regression (A+B+C) | 0.4478 | 0.5625 | 0.4986 | 0.7115 |
| Stacking Ensemble (ML-Only) | 1.0000 | 0.2500 | 0.4000 | 0.7104 |
| Hybrid System (Meta + Rules) | 0.9500 | 0.3563 | 0.5182 | 0.7338 |

## Phase 10: Ablation Study
| Features | Precision | Recall | F1 Score | ROC-AUC |
|----------|-----------|--------|----------|---------|
| LR (A: Keywords Only) | 0.0000 | 0.0000 | 0.0000 | 0.5000 |
| LR (A + B: Keywords + Forensics) | 1.0000 | 0.2500 | 0.4000 | 0.6250 |
| LR (A + C: Keywords + Semantics) | 0.2953 | 0.5500 | 0.3843 | 0.6059 |
| LR (A + B + C: Full Proxy Features) | 0.4478 | 0.5625 | 0.4986 | 0.7115 |

## Phase 11: Attack-Type Evaluation
| Attack Type | Total Samples | Detection Rate (Recall) |
|-------------|---------------|-------------------------|
| TYPE_D | 40 | 42.50% |
| TYPE_B | 40 | 100.00% |
| TYPE_C | 40 | 0.00% |
| TYPE_A | 40 | 0.00% |
