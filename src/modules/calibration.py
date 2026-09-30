"""Validation-only threshold helpers shared by anomaly-scoring modules."""

import numpy as np
import pandas as pd


VALIDATION_PERCENTILE = 95


def clean_validation_threshold(scores, labels, module_name: str) -> float:
    """Return the clean-validation P95, rejecting unusable or degenerate input."""
    values = np.asarray(scores, dtype=float)
    targets = np.asarray(labels)
    if values.ndim != 1 or targets.ndim != 1 or len(values) != len(targets) or len(values) == 0:
        raise ValueError(f"{module_name} calibration requires non-empty aligned score and label arrays.")
    if pd.isna(targets).any() or not np.isin(targets, [0, 1]).all():
        raise ValueError(f"{module_name} validation labels must contain only binary values 0 and 1.")
    if set(np.unique(targets).tolist()) != {0, 1}:
        raise ValueError(f"{module_name} validation data must contain both clean and adversarial samples.")
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError(f"{module_name} validation scores must be finite and non-negative.")

    clean_scores = values[targets == 0]
    if clean_scores.size == 0:
        raise ValueError(f"{module_name} calibration requires clean validation samples.")
    threshold = float(np.percentile(clean_scores, VALIDATION_PERCENTILE))
    if not np.isfinite(threshold) or threshold <= 0:
        raise ValueError(
            f"{module_name} clean-validation P{VALIDATION_PERCENTILE} threshold is not positive; "
            "collect informative validation samples before calibration."
        )
    return threshold
