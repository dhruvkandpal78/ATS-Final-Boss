import os
import pandas as pd
import numpy as np
import logging
import json
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score
from sklearn.linear_model import LogisticRegression

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from src.modules.module_a import KeywordDensityDetector
from src.modules.module_c import SemanticCoherenceScorer
from src.models.meta_classifier import EnsembleMetaClassifier
from src.evaluation.evaluate import simulate_module_b_proxy, extract_features

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-7s | %(message)s')
logger = logging.getLogger(__name__)

SPLITS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "splits")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "results")
CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "configs")

def load_thresholds():
    with open(os.path.join(CONFIG_DIR, "thresholds.json"), "r") as f:
        return json.load(f)

def calc_metrics(y_true, y_pred, y_prob=None):
    metrics = {
        "Precision": precision_score(y_true, y_pred, zero_division=0),
        "Recall": recall_score(y_true, y_pred, zero_division=0),
        "F1": f1_score(y_true, y_pred, zero_division=0)
    }
    if y_prob is not None and len(np.unique(y_true)) > 1:
        if len(y_prob.shape) > 1 and y_prob.shape[1] > 1:
            y_prob = y_prob[:, 1]
        metrics["ROC-AUC"] = roc_auc_score(y_true, y_prob)
    else:
        metrics["ROC-AUC"] = 0.0
    return metrics

def run_experiments():
    logger.info("Loading splits...")
    df_val = pd.read_csv(os.path.join(SPLITS_DIR, "val.csv"))
    df_test = pd.read_csv(os.path.join(SPLITS_DIR, "test.csv"))
    
    logger.info("Initializing modules...")
    mod_a = KeywordDensityDetector()
    mod_c = SemanticCoherenceScorer(model_name='all-MiniLM-L6-v2', window_size=2)
    
    thresh = load_thresholds()
    mod_a.threshold = thresh["mod_a_threshold"]
    mod_c.variance_threshold = thresh["mod_c_variance_threshold"]
    
    logger.info("Extracting features for Validation set (for ablation training)...")
    X_val = extract_features(df_val, mod_a, mod_c)
    y_val = df_val['is_adversarial'].values
    
    logger.info("Extracting features for Test set...")
    X_test = extract_features(df_test, mod_a, mod_c)
    y_test = df_test['is_adversarial'].values
    
    logger.info("Running Benchmark Experiment...")
    # 1. Single Modules (using calibrated thresholds as decision boundaries)
    y_pred_A = (X_test['Module_A_Score'] > mod_a.threshold).astype(int)
    y_pred_B = (X_test['Module_B_Score'] > 0.5).astype(int)
    y_pred_C = (X_test['Module_C_Score'] > mod_c.variance_threshold).astype(int)
    
    # 2. Simple Fusion (Logical OR)
    y_pred_fusion = ((y_pred_A == 1) | (y_pred_B == 1) | (y_pred_C == 1)).astype(int)
    
    # 3. Full Ensemble
    meta_clf = EnsembleMetaClassifier()
    meta_clf.load_model(os.path.join(RESULTS_DIR, "models"))
    y_pred_meta = meta_clf.predict(X_test)
    y_prob_meta = meta_clf.predict_proba(X_test)
    
    benchmark_results = {
        "Module A (Keywords)": calc_metrics(y_test, y_pred_A, X_test['Module_A_Score'].values),
        "Module B (Forensics)": calc_metrics(y_test, y_pred_B, X_test['Module_B_Score'].values),
        "Module C (Semantics)": calc_metrics(y_test, y_pred_C, X_test['Module_C_Score'].values),
        "Simple Fusion (OR)": calc_metrics(y_test, y_pred_fusion),
        "Stacking Ensemble": calc_metrics(y_test, y_pred_meta, y_prob_meta)
    }
    
    logger.info("Running Ablation Experiment...")
    def train_eval_ablation(features):
        clf = LogisticRegression(class_weight='balanced')
        clf.fit(X_val[features], y_val)
        preds = clf.predict(X_test[features])
        probs = clf.predict_proba(X_test[features])[:, 1]
        return calc_metrics(y_test, preds, probs)
        
    ablation_results = {
        "A (Keywords Only)": train_eval_ablation(['Module_A_Score']),
        "A + B (Keywords + Forensics)": train_eval_ablation(['Module_A_Score', 'Module_B_Score']),
        "A + C (Keywords + Semantics)": train_eval_ablation(['Module_A_Score', 'Module_C_Score']),
        "A + B + C (Full Ensemble)": benchmark_results["Stacking Ensemble"] # Just reuse the full model
    }
    
    logger.info("Running Attack-Type Evaluation...")
    attack_results = []
    # Only evaluate on positive cases
    adv_test = df_test[df_test['is_adversarial'] == 1].copy()
    adv_X = X_test.loc[adv_test.index]
    adv_preds = meta_clf.predict(adv_X)
    adv_test['prediction'] = adv_preds
    
    for attack_type in adv_test['attack_type'].unique():
        subset = adv_test[adv_test['attack_type'] == attack_type]
        recall = subset['prediction'].sum() / len(subset)
        attack_results.append({
            "Attack Type": attack_type,
            "Total Samples": len(subset),
            "Detection Rate (Recall)": recall
        })
        
    # Generate Error Analysis Sample
    logger.info("Generating Error Analysis Sample...")
    df_test['prediction'] = y_pred_meta
    fps = df_test[(df_test['is_adversarial'] == 0) & (df_test['prediction'] == 1)]
    fns = df_test[(df_test['is_adversarial'] == 1) & (df_test['prediction'] == 0)]
    
    error_report = f"# Error Analysis Sample\n\n## False Positives (Clean resumes flagged as adversarial)\nTotal: {len(fps)}\n\n"
    for idx, row in fps.head(5).iterrows():
        error_report += f"**Sample ID:** {idx}\n**Text Snippet:** {row['text'][:200]}...\n\n"
        
    error_report += f"## False Negatives (Adversarial resumes that bypassed detection)\nTotal: {len(fns)}\n\n"
    for idx, row in fns.head(5).iterrows():
        error_report += f"**Sample ID:** {idx}\n**Attack Type:** {row['attack_type']}\n**Text Snippet:** {row['text'][:200]}...\n\n"
    
    os.makedirs(os.path.join(RESULTS_DIR, "reports"), exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "reports", "error_analysis.md"), "w") as f:
        f.write(error_report)
        
    # Generate the Markdown Report
    logger.info("Saving Experiments Report...")
    report = "# ATS Final Boss - Evaluation Experiments\n\n"
    
    report += "## Phase 9: Benchmark Experiment\n"
    report += "| Model | Precision | Recall | F1 Score | ROC-AUC |\n"
    report += "|-------|-----------|--------|----------|---------|\n"
    for k, v in benchmark_results.items():
        report += f"| {k} | {v['Precision']:.4f} | {v['Recall']:.4f} | {v['F1']:.4f} | {v['ROC-AUC']:.4f} |\n"
        
    report += "\n## Phase 10: Ablation Study\n"
    report += "| Features | Precision | Recall | F1 Score | ROC-AUC |\n"
    report += "|----------|-----------|--------|----------|---------|\n"
    for k, v in ablation_results.items():
        report += f"| {k} | {v['Precision']:.4f} | {v['Recall']:.4f} | {v['F1']:.4f} | {v['ROC-AUC']:.4f} |\n"
        
    report += "\n## Phase 11: Attack-Type Evaluation\n"
    report += "| Attack Type | Total Samples | Detection Rate (Recall) |\n"
    report += "|-------------|---------------|-------------------------|\n"
    for res in attack_results:
        report += f"| {res['Attack Type']} | {res['Total Samples']} | {res['Detection Rate (Recall)']:.2%} |\n"
        
    with open(os.path.join(RESULTS_DIR, "reports", "experiments_summary.md"), "w") as f:
        f.write(report)
        
    logger.info("DONE! Reports saved to results/reports/")

if __name__ == "__main__":
    run_experiments()
