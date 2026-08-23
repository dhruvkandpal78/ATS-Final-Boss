"""
splitter.py — Phase 1: Strict 60/20/20 Train/Val/Test Splitting
================================================================
Splits the full dataset (clean + adversarial) into three non-overlapping
partitions with strict isolation guarantees to prevent data leakage.

Design Decisions:
    - Stratified by both `attack_type` AND `category` to ensure each split
      has a proportional representation of all attack types and job domains.
    - The TEST split is saved as a separate, clearly named file and must NOT
      be touched until the final evaluation in Phase 5 (Week 5).
    - The VALIDATION split is used exclusively for threshold calibration
      (Module A percentile, Module C coherence threshold) and meta-classifier
      training (Logistic Regression regularization sweep).
    - The TRAIN split is used for building reference corpora (Module C) and
      computing baseline statistics (Module A keyword distributions).

Output:
    data/splits/train.csv   — 60% (~1,966 samples)
    data/splits/val.csv     — 20% (~655 samples)
    data/splits/test.csv    — 20% (~655 samples)  [DO NOT TOUCH UNTIL FINAL EVAL]
    data/splits/split_manifest.json — Metadata about the split for reproducibility.
"""

import pandas as pd
import numpy as np
import os
import json
import logging
from sklearn.model_selection import train_test_split
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
FULL_DATASET_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "processed", "full_dataset.csv"
)
SPLITS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "splits")

TRAIN_RATIO = 0.60
VAL_RATIO = 0.20
TEST_RATIO = 0.20
RANDOM_SEED = 42


# ---------------------------------------------------------------------------
# Main Splitting Pipeline
# ---------------------------------------------------------------------------
def run_splitting_pipeline():
    """
    Executes the strict 60/20/20 stratified split and saves all partitions.
    """
    logger.info("=" * 60)
    logger.info("PHASE 1: STRICT DATA SPLITTING PIPELINE")
    logger.info("=" * 60)

    # Load full dataset
    logger.info(f"Loading full dataset from: {os.path.normpath(FULL_DATASET_PATH)}")
    df = pd.read_csv(FULL_DATASET_PATH)
    logger.info(f"Loaded {len(df)} total samples.")

    # --- First split: Train (60%) vs Temp (40%) ---
    df_train, df_temp = train_test_split(
        df,
        test_size=(VAL_RATIO + TEST_RATIO),
        random_state=RANDOM_SEED,
        stratify=df["attack_type"],
    )

    # --- Second split: Val (50% of 40% = 20%) vs Test (50% of 40% = 20%) ---
    df_val, df_test = train_test_split(
        df_temp,
        test_size=0.5,
        random_state=RANDOM_SEED,
        stratify=df_temp["attack_type"],
    )

    # Reset indices
    df_train = df_train.reset_index(drop=True)
    df_val = df_val.reset_index(drop=True)
    df_test = df_test.reset_index(drop=True)

    # ---------------------------------------------------------------------------
    # Save splits
    # ---------------------------------------------------------------------------
    os.makedirs(SPLITS_DIR, exist_ok=True)

    train_path = os.path.join(SPLITS_DIR, "train.csv")
    val_path = os.path.join(SPLITS_DIR, "val.csv")
    test_path = os.path.join(SPLITS_DIR, "test.csv")

    df_train.to_csv(train_path, index=False)
    df_val.to_csv(val_path, index=False)
    df_test.to_csv(test_path, index=False)

    # ---------------------------------------------------------------------------
    # Save split manifest (for reproducibility and audit trail)
    # ---------------------------------------------------------------------------
    manifest = {
        "created_at": datetime.now().isoformat(),
        "random_seed": RANDOM_SEED,
        "source_file": os.path.normpath(FULL_DATASET_PATH),
        "split_ratios": {
            "train": TRAIN_RATIO,
            "val": VAL_RATIO,
            "test": TEST_RATIO,
        },
        "split_sizes": {
            "train": len(df_train),
            "val": len(df_val),
            "test": len(df_test),
            "total": len(df),
        },
        "attack_type_distribution": {
            "train": df_train["attack_type"].value_counts().to_dict(),
            "val": df_val["attack_type"].value_counts().to_dict(),
            "test": df_test["attack_type"].value_counts().to_dict(),
        },
        "DATA_LEAKAGE_WARNING": (
            "The TEST split must NOT be used for threshold calibration, "
            "hyperparameter tuning, or any intermediate evaluation. "
            "It is touched EXACTLY ONCE during the final evaluation in Phase 5."
        ),
    }

    manifest_path = os.path.join(SPLITS_DIR, "split_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    # ---------------------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------------------
    logger.info("=" * 60)
    logger.info("SPLITTING COMPLETE — SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Train: {len(df_train)} samples ({len(df_train)/len(df)*100:.1f}%)")
    logger.info(f"Val:   {len(df_val)} samples ({len(df_val)/len(df)*100:.1f}%)")
    logger.info(f"Test:  {len(df_test)} samples ({len(df_test)/len(df)*100:.1f}%)")
    logger.info(f"")
    logger.info("Attack type distribution per split:")
    for split_name, split_df in [("TRAIN", df_train), ("VAL", df_val), ("TEST", df_test)]:
        dist = split_df["attack_type"].value_counts().to_dict()
        logger.info(f"  {split_name}: {dist}")
    logger.info(f"")
    logger.info(f"Splits saved to: {os.path.normpath(SPLITS_DIR)}")
    logger.info(f"Manifest saved to: {os.path.normpath(manifest_path)}")
    logger.info("")
    logger.info("⚠️  REMINDER: DO NOT TOUCH test.csv UNTIL FINAL EVALUATION (PHASE 5)")
    logger.info("=" * 60)

    return df_train, df_val, df_test


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    run_splitting_pipeline()
