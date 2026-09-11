# ATS Final Boss - Evaluation Experiments

## Phase 9: Benchmark Experiment
| Model | Precision | Recall | F1 Score | ROC-AUC |
|-------|-----------|--------|----------|---------|
| Module A (Keywords) | 0.2400 | 0.0375 | 0.0649 | 0.7417 |
| Module B (PDF/Text Proxy) | 1.0000 | 0.2500 | 0.4000 | 0.6250 |
| Module C (Semantics) | 0.4800 | 0.1500 | 0.2286 | 0.5860 |
| Simple Fusion (OR) | 0.5888 | 0.3937 | 0.4719 | 0.0000 |
| Stacking Ensemble | 0.9600 | 0.3000 | 0.4571 | 0.8311 |

## Phase 10: Ablation Study
| Features | Precision | Recall | F1 Score | ROC-AUC |
|----------|-----------|--------|----------|---------|
| LR (A: Keywords Only) | 0.3913 | 0.2812 | 0.3273 | 0.7417 |
| LR (A + B: Keywords + Forensics) | 1.0000 | 0.2500 | 0.4000 | 0.7949 |
| LR (A + C: Keywords + Semantics) | 0.3115 | 0.4750 | 0.3762 | 0.5994 |
| LR (A + B + C: Full Proxy Features) | 0.5794 | 0.3875 | 0.4644 | 0.7114 |

## Phase 11: Attack-Type Evaluation
| Attack Type | Total Samples | Detection Rate (Recall) |
|-------------|---------------|-------------------------|
| TYPE_D | 40 | 15.00% |
| TYPE_B | 40 | 100.00% |
| TYPE_C | 40 | 5.00% |
| TYPE_A | 40 | 0.00% |
