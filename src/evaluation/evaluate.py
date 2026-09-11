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

def _init_worker():
    global _worker_mod_a, _worker_mod_c
    from src.modules.module_a import KeywordDensityDetector
    from src.modules.module_c import SemanticCoherenceScorer
    _worker_mod_a = KeywordDensityDetector()
    _worker_mod_c = SemanticCoherenceScorer(model_name='all-MiniLM-L6-v2', window_size=2)

def _process_row(args):
    idx, text, mod_a_thresh, mod_c_thresh = args
    global _worker_mod_a, _worker_mod_c
    
    _worker_mod_a.threshold = mod_a_thresh
    _worker_mod_c.variance_threshold = mod_c_thresh
    
    a_res = _worker_mod_a.predict(text)
    b_score = simulate_module_b_proxy(text)
    c_res = _worker_mod_c.predict(text)
    
    return {
        "Module_A_Score": a_res['anomaly_score'],
        "Module_B_Score": b_score,
        "Module_C_Score": c_res['anomaly_score'],
        "Injection_Cues": c_res.get('injection_cues', 0)
    }

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
    logger.info("Processing Validation Set...")
    X_val = extract_features(df_val, mod_a, mod_c)
    y_val = df_val['is_adversarial'].values
    
    logger.info("Processing Test Set...")
    X_test = extract_features(df_test, mod_a, mod_c)
    y_test = df_test['is_adversarial'].values
    
    # 5. Train Meta-Classifier
    logger.info("--- META-CLASSIFIER TRAINING PHASE ---")
    meta_clf = EnsembleMetaClassifier()
    meta_clf.train(X_val, y_val)
    meta_clf.save_model(os.path.join(RESULTS_DIR, "models"))
    
    # 6. Evaluate on Test Set
    logger.info("--- FINAL TEST SET EVALUATION ---")
    y_pred = meta_clf.predict(X_test)
    y_proba_meta = meta_clf.predict_proba(X_test)
    
    # Standard metrics
    metrics = evaluate_predictions(y_test, y_pred, module_name="Meta-Classifier")
    
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
            a_sc = mod_a.predict(mutated_text)['anomaly_score']
            b_sc = simulate_module_b_proxy(mutated_text)
            c_sc = mod_c.predict(mutated_text)['anomaly_score']
            
            feat = pd.DataFrame([{"Module_A_Score": a_sc, "Module_B_Score": b_sc, "Module_C_Score": c_sc}])
            is_attack = meta_clf.predict(feat)[0]
            
            y_true_budg.append(1) # We know these are adversarial
            y_pred_budg.append(int(is_attack))
            
        # Add some clean samples to compute real F1 at this budget
        clean_test = df_test[df_test['is_adversarial'] == 0]
        n_clean = min(30, len(clean_test))
        clean_sub = clean_test.sample(n_clean, random_state=42)
        
        for idx, row in clean_sub.iterrows():
            y_true_budg.append(0)
            
            a_sc = mod_a.predict(row['text'])['anomaly_score']
            b_sc = simulate_module_b_proxy(row['text'])
            c_sc = mod_c.predict(row['text'])['anomaly_score']
            
            feat = pd.DataFrame([{"Module_A_Score": a_sc, "Module_B_Score": b_sc, "Module_C_Score": c_sc}])
            is_attack = meta_clf.predict(feat)[0]
            
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
