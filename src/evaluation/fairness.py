import numpy as np
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DisparateImpactAuditor:
    """
    Evaluates algorithmic fairness by implementing the EEOC 80% (Four-Fifths) Rule,
    aligning with EU AI Act Annex III transparency requirements for high-risk employment AI.
    """
    
    def __init__(self, threshold: float = 0.80):
        """
        :param threshold: The Disparate Impact Ratio threshold (default 0.80 as per EEOC).
        """
        self.threshold = threshold

    def evaluate_fairness(self, results_df: pd.DataFrame, proxy_column: str, label_column: str, pred_column: str) -> dict:
        """
        Calculates False Positive Rates (FPR) and Selection Rates across subgroups.
        
        :param results_df: DataFrame containing the test set evaluation results.
        :param proxy_column: Column name representing the subgroup proxy (e.g., 'lexical_diversity_quartile').
        :param label_column: Ground truth column (1 = Adversarial, 0 = Clean).
        :param pred_column: Model prediction column (1 = Flagged, 0 = Passed).
        :return: Dictionary containing Disparate Impact Metrics.
        """
        subgroups = results_df[proxy_column].unique()
        metrics = {}
        
        for group in subgroups:
            group_data = results_df[results_df[proxy_column] == group]
            
            # True Positives, False Positives, True Negatives, False Negatives
            tp = len(group_data[(group_data[label_column] == 1) & (group_data[pred_column] == 1)])
            fp = len(group_data[(group_data[label_column] == 0) & (group_data[pred_column] == 1)])
            tn = len(group_data[(group_data[label_column] == 0) & (group_data[pred_column] == 0)])
            fn = len(group_data[(group_data[label_column] == 1) & (group_data[pred_column] == 0)])
            
            # Selection Rate (Passed the filter / Total Candidates in group)
            # In our context, passing the filter means being predicted as 0 (Clean).
            total_group = len(group_data)
            passed = tn + fn
            selection_rate = passed / total_group if total_group > 0 else 0
            
            # False Positive Rate (Legitimate resumes incorrectly flagged as adversarial)
            # FPR = FP / (FP + TN)
            actual_clean = fp + tn
            fpr = fp / actual_clean if actual_clean > 0 else 0
            
            metrics[group] = {
                "selection_rate": selection_rate,
                "false_positive_rate": fpr,
                "total_candidates": total_group
            }
            
        return self._calculate_eeoc_compliance(metrics)

    def _calculate_eeoc_compliance(self, metrics: dict) -> dict:
        """
        Applies the Four-Fifths Rule to the calculated subgroup selection rates.
        """
        if not metrics:
            return {"status": "error", "message": "No metrics available to calculate compliance."}
            
        # Identify the group with the highest selection rate (the advantaged group)
        highest_sr_group = max(metrics.keys(), key=lambda g: metrics[g]["selection_rate"])
        highest_sr = metrics[highest_sr_group]["selection_rate"]
        
        compliance_report = {
            "advantaged_group": highest_sr_group,
            "highest_selection_rate": highest_sr,
            "violations": [],
            "group_metrics": metrics
        }
        
        if highest_sr == 0:
            logger.warning("Highest selection rate is 0. Cannot compute Disparate Impact Ratio.")
            return compliance_report
            
        for group, data in metrics.items():
            if group == highest_sr_group:
                continue
                
            sr = data["selection_rate"]
            impact_ratio = sr / highest_sr
            data["disparate_impact_ratio"] = impact_ratio
            
            if impact_ratio < self.threshold:
                compliance_report["violations"].append({
                    "subgroup": group,
                    "impact_ratio": impact_ratio,
                    "message": f"Violation: Impact ratio {impact_ratio:.2f} is below the {self.threshold} EEOC threshold."
                })
                
        compliance_report["is_compliant"] = len(compliance_report["violations"]) == 0
        return compliance_report

if __name__ == "__main__":
    # Example usage with mock data
    mock_data = pd.DataFrame({
        "lexical_diversity_quartile": ["Q1", "Q1", "Q1", "Q4", "Q4", "Q4"],
        "is_adversarial": [0, 0, 1, 0, 0, 1],
        "is_flagged":     [1, 0, 1, 0, 0, 1] 
    })
    
    auditor = DisparateImpactAuditor()
    # report = auditor.evaluate_fairness(mock_data, "lexical_diversity_quartile", "is_adversarial", "is_flagged")
    # print(report)
