"""
evaluate.py — Phase 3: End-to-End Evaluation Runner
===================================================
Orchestrates the entire evaluation pipeline:
    1. Loads train/val/test splits.
    2. Calibrates Modules A and C on the VAL set.
    3. Generates anomaly scores for Modules A, B, and C on all splits.
    4. Trains the Meta-Classifier on the VAL set scores.
    5. Evaluates the Meta-Classifier strictly on the TEST set.
    6. Generates metrics, ROC-AUC plots, and the Adversarial Degradation plot.
"""

import pandas as pd
import numpy as np
import os
import logging
import random
from tqdm import tqdm
import sys

# Add src to path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from src.modules.module_a import KeywordDensityDetector
from src.modules.module_c import SemanticCoherenceScorer
from src.models.meta_classifier import EnsembleMetaClassifier
from src.evaluation.metrics import evaluate_predictions, bootstrap_f1
from src.evaluation.curves import plot_roc_curves, plot_degradation_curve

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-7s | %(message)s')
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SPLITS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "splits")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "results")

# ---------------------------------------------------------------------------
# Module B Simulator (For CSV Data)
# ---------------------------------------------------------------------------
def simulate_module_b_proxy(text: str) -> float:
    """
    PROXY ONLY: detects the synthetic Type-B marker used at data-generation
    time ([HIDDEN_TEXT_START]...[HIDDEN_TEXT_END]). Does NOT measure real PDF
    structural forensics. See module_b.py / PDFForensicsDetector for the real
    detector, which is evaluated separately in eval_module_b_standalone.py.
    """
    if not isinstance(text, str):
        return 0.0
    if "[HIDDEN_TEXT_START]" in text:
        return 1.0
    return 0.0

# ---------------------------------------------------------------------------
# Feature Extraction Runner
# ---------------------------------------------------------------------------
# Global variables for worker processes
_worker_mod_a = None
_worker_mod_c = None

_worker_analysis_service = None

def _init_worker():
    global _worker_analysis_service
    from src.modules.module_a import KeywordDensityDetector
    from src.modules.module_c import SemanticCoherenceScorer
    from src.core.analysis_service import AnalysisService
    mod_a = KeywordDensityDetector()
    mod_c = SemanticCoherenceScorer(model_name='all-MiniLM-L6-v2', window_size=2)
    _worker_analysis_service = AnalysisService(mod_a=mod_a, mod_b=None, mod_c=mod_c)

def _process_row(args):
    idx, text, mod_a_thresh, mod_c_thresh = args
    global _worker_analysis_service
    
    _worker_analysis_service.mod_a.threshold = mod_a_thresh
    _worker_analysis_service.mod_c.variance_threshold = mod_c_thresh
    
    b_score = simulate_module_b_proxy(text)
    res = _worker_analysis_service.analyze_text(text, b_score)
    
    features = res['features']
    features['Injection_Cues'] = res['injection_cues']
    return features

def extract_features(df: pd.DataFrame, mod_a: KeywordDensityDetector, mod_c: SemanticCoherenceScorer) -> pd.DataFrame:
    """
    Extracts module anomaly scores in parallel to serve as features for the meta-classifier.
    """
    import concurrent.futures
    import multiprocessing
    
    logger.info(f"Extracting features for {len(df)} samples using {multiprocessing.cpu_count()} cores...")
    
    args_list = [(idx, row['text'], mod_a.threshold, mod_c.variance_threshold) for idx, row in df.iterrows()]
    
    with concurrent.futures.ProcessPoolExecutor(initializer=_init_worker) as executor:
        results = list(tqdm(executor.map(_process_row, args_list), total=len(df), desc="Extracting"))
        
    return pd.DataFrame(results)

# ---------------------------------------------------------------------------
# Main Evaluation Pipeline
# ---------------------------------------------------------------------------
def run_evaluation():
    logger.info("=" * 60)
    logger.info("PHASE 3: END-TO-END EVALUATION")
    logger.info("=" * 60)
    
    # 1. Load Splits
    logger.info("Loading dataset splits...")
    df_train = pd.read_csv(os.path.join(SPLITS_DIR, "train.csv"))
    df_val = pd.read_csv(os.path.join(SPLITS_DIR, "val.csv"))
    df_test = pd.read_csv(os.path.join(SPLITS_DIR, "test.csv"))
    
    # 2. Initialize Modules
    logger.info("Initializing detection modules...")
    mod_a = KeywordDensityDetector()
    mod_c = SemanticCoherenceScorer(model_name='all-MiniLM-L6-v2', window_size=2)
    
    # 3. Calibrate on Validation Set
    logger.info("--- CALIBRATION PHASE ---")
    mod_a.calibrate(df_val, objective='f1')
    mod_c.calibrate(df_val, objective='f1')
    
    # Save calibrated thresholds to config
    import json
    config_dir = os.path.join(os.path.dirname(__file__), "..", "..", "configs")
    os.makedirs(config_dir, exist_ok=True)
    with open(os.path.join(config_dir, "thresholds.json"), "w") as f:
        json.dump({
            "mod_a_threshold": float(mod_a.threshold),
            "mod_c_variance_threshold": float(mod_c.variance_threshold)
        }, f, indent=4)
    logger.info("Saved calibrated thresholds to configs/thresholds.json")
    
    # 4. Extract Features
    logger.info("--- FEATURE EXTRACTION PHASE ---")
    logger.info("Processing Training Set...")
    X_train = extract_features(df_train, mod_a, mod_c)
    y_train = df_train['is_adversarial'].values
    
    logger.info("Processing Test Set...")
    X_test = extract_features(df_test, mod_a, mod_c)
    y_test = df_test['is_adversarial'].values
    
    # 5. Train Meta-Classifier
    logger.info("--- META-CLASSIFIER TRAINING PHASE ---")
    meta_clf = EnsembleMetaClassifier()
    # We only pass the required ML features to train()
    ml_features = ['Module_A_Score', 'Module_B_Score', 'Module_C_Score']
    meta_clf.train(X_train[ml_features], y_train)
    meta_clf.save_model(os.path.join(RESULTS_DIR, "models"))
    
    # 6. Evaluate on Test Set
    logger.info("--- FINAL TEST SET EVALUATION ---")
    y_pred = meta_clf.predict(X_test[ml_features])
    y_proba_meta = meta_clf.predict_proba(X_test[ml_features])
    
    # Standard metrics
    metrics = evaluate_predictions(y_test, y_pred, module_name="Meta-Classifier")
    
    # Calculate policy rules for test set
    y_pred_policy = y_pred.copy()
    y_proba_policy = y_proba_meta.copy()
    for i, row in X_test.reset_index(drop=True).iterrows():
        if row['Injection_Cues'] > 0 or row['Module_B_Score'] >= 0.9:
            y_pred_policy[i] = 1
            y_proba_policy[i] = max(y_proba_policy[i], 0.95)
            
    # Calculate confusion matrix for policy
    from sklearn.metrics import confusion_matrix
    cm = confusion_matrix(y_test, y_pred_policy)
    
    # Dump results.json
    per_sample = []
    for i in range(len(y_test)):
        per_sample.append({
            "index": i,
            "split": "test",
            "true_label": int(y_test[i]),
            "module_a_score": float(X_test['Module_A_Score'].iloc[i]),
            "module_b_score": float(X_test['Module_B_Score'].iloc[i]),
            "module_c_score": float(X_test['Module_C_Score'].iloc[i]),
            "injection_cues": int(X_test['Injection_Cues'].iloc[i]),
            "model_probability": float(y_proba_meta[i]),
            "policy_probability": float(y_proba_policy[i]),
            "model_decision": bool(y_pred[i]),
            "policy_decision": bool(y_pred_policy[i])
        })
        
    results_out = {
        "confusion_matrix": {
            "tn": int(cm[0][0]) if cm.shape == (2,2) else 0,
            "fp": int(cm[0][1]) if cm.shape == (2,2) else 0,
            "fn": int(cm[1][0]) if cm.shape == (2,2) else 0,
            "tp": int(cm[1][1]) if cm.shape == (2,2) else 0
        },
        "samples": per_sample
    }
    
    import json
    with open(os.path.join(RESULTS_DIR, "results.json"), "w") as f:
        json.dump(results_out, f, indent=2)
        
    logger.info("Saved ML evaluation artifact to results/results.json")
    
    # Bootstrapped F1 for rigor
    bootstrap_f1(y_test, y_pred, n_iterations=1000)
    
    # Generate ROC curves for comparison (Module A, C vs Meta)
    # We use raw extracted scores as probabilities for individual modules for the ROC curve
    proba_dict = {
        'Module A': X_test['Module_A_Score'].values,
        'Module C': X_test['Module_C_Score'].values,
        'Meta-Classifier': y_proba_meta
    }
    plot_roc_curves(y_test, proba_dict, os.path.join(RESULTS_DIR, "plots", "roc_curves.png"))
    
    # 7. Adaptive Adversary Degradation (Real Eval)
    logger.info("Running Adaptive Adversary Degradation (subsampled to 30 for runtime)...")
    sub_pcts = [0, 10, 20, 30, 40, 50]
    acc_drops = []
    
    # Take a subset of Type-A and Type-D (the text-based attacks)
    adv_test = df_test[df_test['attack_type'].isin(['TYPE_A', 'TYPE_D'])]
    n_samples = min(30, len(adv_test))
    subset_df = adv_test.sample(n_samples, random_state=42)
    
    from src.core.analysis_service import AnalysisService
    temp_service = AnalysisService(mod_a=mod_a, mod_b=None, mod_c=mod_c, meta_clf=meta_clf, scaler=None)
    
    for budget in sub_pcts:
        if budget == 0:
            acc_drops.append(metrics['f1'])
            continue
            
        y_true_budg = []
        y_pred_budg = []
        
        for idx, row in subset_df.iterrows():
            text = row['text']
            words = text.split()
            n_replace = int(len(words) * (budget / 100.0))
            
            # Simple substitution attack: replace keywords with harmless generic words
            # to evade density detection, while trying to keep semantics.
            # We simulate this by replacing random words with generic tokens.
            if n_replace > 0:
                replace_indices = random.sample(range(len(words)), min(n_replace, len(words)))
                for i in replace_indices:
                    words[i] = "experience" # generic benign word
            
            mutated_text = " ".join(words)
            # Re-score
            b_sc = simulate_module_b_proxy(mutated_text)
            res = temp_service.analyze_text(mutated_text, b_score=b_sc)
            
            is_attack = res['policy_decision']
            
            y_true_budg.append(1) # We know these are adversarial
            y_pred_budg.append(int(is_attack))
            
        # Add some clean samples to compute real F1 at this budget
        clean_test = df_test[df_test['is_adversarial'] == 0]
        n_clean = min(30, len(clean_test))
        clean_sub = clean_test.sample(n_clean, random_state=42)
        
        for idx, row in clean_sub.iterrows():
            y_true_budg.append(0)
            
            b_sc = simulate_module_b_proxy(row['text'])
            res = temp_service.analyze_text(row['text'], b_score=b_sc)
            is_attack = res['policy_decision']
            
            y_pred_budg.append(int(is_attack))
            
        # Calc F1
        tp = sum(1 for yt, yp in zip(y_true_budg, y_pred_budg) if yt == 1 and yp == 1)
        fp = sum(1 for yt, yp in zip(y_true_budg, y_pred_budg) if yt == 0 and yp == 1)
        fn = sum(1 for yt, yp in zip(y_true_budg, y_pred_budg) if yt == 1 and yp == 0)
        
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1_budg = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
        
        acc_drops.append(f1_budg)
        
    plot_degradation_curve(sub_pcts, acc_drops, os.path.join(RESULTS_DIR, "plots", "degradation_curve.png"))
    
    logger.info("=" * 60)
    logger.info("EVALUATION COMPLETE. ALL PLOTS SAVED TO /results/plots/")
    logger.info("=" * 60)

if __name__ == "__main__":
    run_evaluation()
