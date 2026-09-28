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
from sklearn.metrics import f1_score

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
def extract_features(df: pd.DataFrame, mod_a: KeywordDensityDetector, mod_c: SemanticCoherenceScorer) -> pd.DataFrame:
    """
    Extract historical synthetic-research features with reused detector objects.

    The B value is an explicit marker proxy, not PDF evidence. Keep this path
    separate from the deployed AnalysisService, which correctly reports B as
    not applicable for text and never fills in a synthetic structural score.
    """
    logger.info("Extracting synthetic research features for %d samples...", len(df))
    rows = []
    for text in tqdm(df['text'], total=len(df), desc="Extracting"):
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Research feature extraction requires nonempty text")
        a_result = mod_a.predict(text)
        c_result = mod_c.predict(text)
        rows.append({
            "Module_A_Score": float(a_result["anomaly_score"]),
            "Module_B_Score": simulate_module_b_proxy(text),
            "Module_C_Score": float(c_result["anomaly_score"]),
            "Injection_Cues": int(c_result.get("injection_cues", 0)),
        })
    return pd.DataFrame(rows, columns=["Module_A_Score", "Module_B_Score", "Module_C_Score", "Injection_Cues"])


RESEARCH_MODEL_FEATURES = ["Module_A_Score", "Module_B_Score", "Module_C_Score"]


def research_policy_predictions(features: pd.DataFrame, meta_clf) -> np.ndarray:
    """Policy decisions for synthetic research features, separate from deployment."""
    model_predictions = np.asarray(meta_clf.predict(features[RESEARCH_MODEL_FEATURES]), dtype=int)
    rules = (features["Injection_Cues"].to_numpy() > 0) | (
        features["Module_B_Score"].to_numpy() >= 0.9
    )
    return (model_predictions.astype(bool) | rules).astype(int)


def validation_degradation_curve(df_val: pd.DataFrame, mod_a, mod_c, meta_clf,
                                 budgets=(0, 10, 20, 30, 40, 50), sample_size=30,
                                 seed=42):
    """Score a fixed validation subset at each mutation budget.

    This is a synthetic research stress test, not a deployed PDF benchmark.
    It must never select examples or a budget using the test split.
    """
    required = {"text", "attack_type", "is_adversarial"}
    if not required.issubset(df_val.columns):
        raise ValueError("Validation curve requires text, attack_type, and is_adversarial")
    attacked = df_val[df_val["attack_type"].isin(["TYPE_A", "TYPE_D"])]
    clean = df_val[df_val["is_adversarial"] == 0]
    if attacked.empty or clean.empty:
        raise ValueError("Validation curve needs both text-based attacks and clean controls")
    attacked = attacked.sample(min(sample_size, len(attacked)), random_state=seed)
    clean = clean.sample(min(sample_size, len(clean)), random_state=seed)
    clean_features = extract_features(clean, mod_a, mod_c)
    clean_predictions = research_policy_predictions(clean_features, meta_clf)
    labels = np.concatenate([np.ones(len(attacked), dtype=int), np.zeros(len(clean), dtype=int)])
    values = []
    for budget in budgets:
        if not 0 <= budget <= 100:
            raise ValueError("Mutation budgets must be percentages between 0 and 100")
        texts = []
        for row_index, text in enumerate(attacked["text"]):
            words = text.split()
            count = min(len(words), int(len(words) * budget / 100))
            if count:
                rng = random.Random(seed + budget * 1009 + row_index)
                for word_index in rng.sample(range(len(words)), count):
                    words[word_index] = "experience"
            texts.append(" ".join(words))
        attack_features = extract_features(pd.DataFrame({"text": texts}), mod_a, mod_c)
        attack_predictions = research_policy_predictions(attack_features, meta_clf)
        predictions = np.concatenate([attack_predictions, clean_predictions])
        values.append(float(f1_score(labels, predictions, zero_division=0)))
    return {"budgets": list(budgets), "f1": values,
            "n_adversarial": len(attacked), "n_clean": len(clean),
            "source_split": "validation", "input_mode": "synthetic_text_proxy"}

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
    for i, row in X_test.reset_index(drop=True).iterrows():
        if row['Injection_Cues'] > 0 or row['Module_B_Score'] >= 0.9:
            y_pred_policy[i] = 1
            
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
    
    # 7. Synthetic validation stress test. The final test split is never used
    # for selecting the mutation budget or building this curve.
    logger.info("Running synthetic degradation study on a fixed validation subset...")
    try:
        degradation = validation_degradation_curve(df_val, mod_a, mod_c, meta_clf)
    except ValueError as exc:
        logger.warning("Validation degradation study unavailable: %s", exc)
    else:
        plot_degradation_curve(degradation["budgets"], degradation["f1"],
                               os.path.join(RESULTS_DIR, "plots", "degradation_curve.png"))
    
    logger.info("=" * 60)
    logger.info("EVALUATION COMPLETE. ALL PLOTS SAVED TO /results/plots/")
    logger.info("=" * 60)

if __name__ == "__main__":
    run_evaluation()
