# ATS Final Boss - Evaluation Experiments

## Phase 9: Benchmark Experiment
| Model | Precision | Recall | F1 Score | ROC-AUC |
|-------|-----------|--------|----------|---------|
| Module A (Keywords) | 0.4852 | 0.5125 | 0.4985 | 0.7417 |
| Module B (Forensics) | 1.0000 | 0.2500 | 0.4000 | 0.6250 |
| Module C (Semantics) | 0.2473 | 1.0000 | 0.3965 | 0.5863 |
| Simple Fusion (OR) | 0.2469 | 1.0000 | 0.3960 | 0.0000 |
| Stacking Ensemble | 0.9600 | 0.3000 | 0.4571 | 0.8314 |

## Phase 10: Ablation Study
| Features | Precision | Recall | F1 Score | ROC-AUC |
|----------|-----------|--------|----------|---------|
| A (Keywords Only) | 0.3913 | 0.2812 | 0.3273 | 0.7417 |
| A + B (Keywords + Forensics) | 1.0000 | 0.2500 | 0.4000 | 0.7949 |
| A + C (Keywords + Semantics) | 0.3102 | 0.4750 | 0.3753 | 0.5996 |
| A + B + C (Full Ensemble) | 0.9600 | 0.3000 | 0.4571 | 0.8314 |

## Phase 11: Attack-Type Evaluation
| Attack Type | Total Samples | Detection Rate (Recall) |
|-------------|---------------|-------------------------|
| TYPE_D | 40 | 15.00% |
| TYPE_B | 40 | 100.00% |
| TYPE_C | 40 | 5.00% |
| TYPE_A | 40 | 0.00% |
