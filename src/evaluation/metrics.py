"""
metrics.py — Base Evaluation Metrics & Bootstrapping
====================================================
Generates Precision, Recall, F1, and Confusion Matrices for the individual 
modules and the combined meta-classifier. Includes bootstrapping for confidence intervals.
"""

import pandas as pd
import numpy as np
import logging
from sklearn.metrics import precision_recall_fscore_support, confusion_matrix, classification_report
from sklearn.utils import resample

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def evaluate_predictions(y_true: np.ndarray, y_pred: np.ndarray, module_name: str = "Model") -> dict:
    """
    Computes standard evaluation metrics.
    """
    precision, recall, f1, _ = precision_recall_fscore_support(y_true, y_pred, average='binary')
    cm = confusion_matrix(y_true, y_pred)
    
    logger.info(f"--- {module_name} Evaluation ---")
    logger.info(f"Precision: {precision:.4f} | Recall: {recall:.4f} | F1: {f1:.4f}")
    logger.info(f"Confusion Matrix:\n{cm}")
    
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "confusion_matrix": cm.tolist()
    }

def bootstrap_f1(y_true: np.ndarray, y_pred: np.ndarray, n_iterations: int = 1000) -> tuple:
    """
    Bootstraps the F1 score to generate a 95% confidence interval.
    Critical for mitigating noise in synthetic dataset evaluations.
    """
    logger.info(f"Bootstrapping F1 score with {n_iterations} iterations...")
    f1_scores = []
    
    for _ in range(n_iterations):
        # Resample with replacement
        indices = resample(np.arange(len(y_true)))
        y_true_resampled = y_true[indices]
        y_pred_resampled = y_pred[indices]
        
        _, _, f1, _ = precision_recall_fscore_support(y_true_resampled, y_pred_resampled, average='binary', zero_division=0)
        f1_scores.append(f1)
        
    lower_bound = np.percentile(f1_scores, 2.5)
    upper_bound = np.percentile(f1_scores, 97.5)
    mean_f1 = np.mean(f1_scores)
    
    logger.info(f"Bootstrapped F1: {mean_f1:.4f} (95% CI: [{lower_bound:.4f}, {upper_bound:.4f}])")
    return mean_f1, lower_bound, upper_bound

if __name__ == "__main__":
    pass
