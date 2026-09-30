"""Historical synthetic text-proxy research runner.

This path is intentionally isolated from deployed PDF artifacts and never opens
the held-out test split. Its Module B marker is not physical PDF evidence.
"""

import pandas as pd
import numpy as np
import os
import logging
import random
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from tqdm import tqdm
import sys
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score

# Add src to path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from src.modules.module_a import KeywordDensityDetector
from src.modules.module_c import SemanticCoherenceScorer
from src.models.meta_classifier import EnsembleMetaClassifier
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
def validate_proxy_splits(df_train: pd.DataFrame, df_val: pd.DataFrame) -> None:
    """Require explicit source lineage and two classes without touching test data."""
    for name, frame in (("train", df_train), ("validation", df_val)):
        required = {"source_id", "text", "is_adversarial"}
        if frame.empty or not required.issubset(frame.columns):
            raise ValueError(f"{name} proxy split needs source_id, text and is_adversarial")
        if frame["source_id"].isna().any() or not frame["source_id"].astype(str).str.strip().all():
            raise ValueError(f"{name} proxy split has missing source lineage")
        if set(frame["is_adversarial"]) != {0, 1}:
            raise ValueError(f"{name} proxy split must contain both known labels")
    train_ids = set(df_train["source_id"].astype(str).str.strip().str.casefold())
    val_ids = set(df_val["source_id"].astype(str).str.strip().str.casefold())
    if train_ids & val_ids:
        raise ValueError("Proxy train and validation source groups overlap")


def run_evaluation(train_path=None, validation_path=None, output_root=None):
    """Run isolated train/validation research on synthetic text proxies only."""
    train_path = Path(train_path or Path(SPLITS_DIR) / "train.csv").resolve()
    validation_path = Path(validation_path or Path(SPLITS_DIR) / "val.csv").resolve()
    for path in (train_path, validation_path):
        if any(token in path.name.casefold() for token in ("test", "holdout")):
            raise ValueError("Proxy development refuses test/holdout-named input")
    df_train = pd.read_csv(train_path)
    df_val = pd.read_csv(validation_path)
    validate_proxy_splits(df_train, df_val)

    mod_a = KeywordDensityDetector()
    mod_c = SemanticCoherenceScorer(model_name="all-MiniLM-L6-v2", window_size=2)
    # Both modules now require clean-validation positive percentile calibration.
    a_threshold = float(mod_a.calibrate(df_val))
    c_threshold = float(mod_c.calibrate(df_val))
    if not all(np.isfinite(value) and value > 0 for value in (a_threshold, c_threshold)):
        raise ValueError("Proxy validation calibration is unavailable; no artifacts were written")

    train_x = extract_features(df_train, mod_a, mod_c)
    val_x = extract_features(df_val, mod_a, mod_c)
    train_y = df_train["is_adversarial"].to_numpy(dtype=int)
    val_y = df_val["is_adversarial"].to_numpy(dtype=int)
    model = EnsembleMetaClassifier()
    model.train(train_x[RESEARCH_MODEL_FEATURES], train_y)
    model_predictions = np.asarray(model.predict(val_x[RESEARCH_MODEL_FEATURES]), dtype=int)
    policy_predictions = research_policy_predictions(val_x, model)
    scores = np.asarray(model.predict_proba(val_x[RESEARCH_MODEL_FEATURES]), dtype=float)
    metrics = {
        "split": "validation", "input_mode": "synthetic_text_proxy", "n": int(len(df_val)),
        "model_precision": float(precision_score(val_y, model_predictions, zero_division=0)),
        "model_recall": float(recall_score(val_y, model_predictions, zero_division=0)),
        "model_f1": float(f1_score(val_y, model_predictions, zero_division=0)),
        "model_roc_auc": float(roc_auc_score(val_y, scores)),
        "policy_precision": float(precision_score(val_y, policy_predictions, zero_division=0)),
        "policy_recall": float(recall_score(val_y, policy_predictions, zero_division=0)),
        "policy_f1": float(f1_score(val_y, policy_predictions, zero_division=0)),
    }
    output_root = Path(output_root or Path(RESULTS_DIR) / "research_proxy").resolve()
    deployed = (Path(RESULTS_DIR) / "models").resolve()
    if output_root == deployed or deployed in output_root.parents:
        raise ValueError("Research output cannot overwrite deployed model artifacts")
    output_root.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    output = output_root / f"proxy-{run_id}"
    output.mkdir(exist_ok=False)
    model.save_model(str(output))
    (output / "thresholds.json").write_text(json.dumps({
        "mod_a_threshold": a_threshold,
        "mod_c_variance_threshold": c_threshold,
        "calibration": "clean_validation_p95",
    }, indent=2), encoding="utf-8")
    (output / "validation_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    def file_hash(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    (output / "research_manifest.json").write_text(json.dumps({
        "kind": "synthetic_text_proxy_research", "created_at": datetime.now(timezone.utc).isoformat(),
        "train_manifest_sha256": file_hash(train_path),
        "validation_manifest_sha256": file_hash(validation_path),
        "train_source_hashes": sorted(hashlib.sha256(str(item).strip().casefold().encode()).hexdigest()
                                      for item in set(df_train["source_id"])),
        "validation_source_hashes": sorted(hashlib.sha256(str(item).strip().casefold().encode()).hexdigest()
                                           for item in set(df_val["source_id"])),
        "artifact_hashes": {name: file_hash(output / name) for name in
                            ("meta_classifier.pkl", "scaler.pkl", "thresholds.json", "validation_metrics.json")},
        "warning": "Synthetic Module B markers are not PDF structural evidence; validation is not an independent benchmark.",
    }, indent=2), encoding="utf-8")
    try:
        degradation = validation_degradation_curve(df_val, mod_a, mod_c, model)
    except ValueError as exc:
        logger.warning("Validation degradation plot unavailable: %s", exc)
    else:
        plot_degradation_curve(degradation["budgets"], degradation["f1"], str(output / "degradation_curve.png"))
    logger.info("Synthetic proxy research output: %s", output)
    return output

if __name__ == "__main__":
    run_evaluation()
