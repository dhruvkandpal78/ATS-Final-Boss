"""
meta_classifier.py — Advanced Ensemble Combined Scoring Layer
==============================================================
A high-performance meta-classifier that combines heterogeneous anomaly
scores (Statistical, Structural, Semantic) from Modules A, B, and C
into a single calibrated decision using a Stacking Ensemble of:
    1. XGBoost (Gradient Boosting) — captures non-linear feature interactions
    2. Random Forest — robust bagging for variance reduction
    3. Logistic Regression — stable linear baseline

The final prediction is made by a Logistic Regression meta-learner
that stacks the outputs of all three base classifiers (Stacking Generalization).
"""

import pandas as pd
import numpy as np
import logging
import pickle
import os
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, StackingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score

try:
    from xgboost import XGBClassifier
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class EnsembleMetaClassifier:
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()

    def _build_stacking_clf(self):
        """
        Builds a StackingClassifier with XGBoost + RandomForest as base
        estimators and LogisticRegression as the final meta-learner.
        Falls back to RF + LR stacking if XGBoost is not installed.
        """
        estimators = []

        if HAS_XGBOOST:
            xgb = XGBClassifier(
                n_estimators=200,
                max_depth=4,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                scale_pos_weight=1.0,   # will be overridden in train()
                eval_metric='logloss',
                use_label_encoder=False,
                random_state=42,
                verbosity=0
            )
            estimators.append(('xgb', xgb))
            logger.info("    -> XGBoost loaded.")
        else:
            logger.warning("    -> XGBoost not found. Using RF + LR only.")

        rf = RandomForestClassifier(
            n_estimators=300,
            max_depth=6,
            min_samples_split=5,
            min_samples_leaf=2,
            class_weight='balanced',
            random_state=42,
            n_jobs=-1
        )
        estimators.append(('rf', rf))
        logger.info("    -> Random Forest loaded.")

        lr_base = LogisticRegression(
            C=1.0,
            class_weight='balanced',
            max_iter=1000,
            random_state=42
        )
        estimators.append(('lr', lr_base))
        logger.info("    -> Logistic Regression (base) loaded.")

        # Meta-learner: Logistic Regression stacks the outputs
        meta_learner = LogisticRegression(
            C=1.0,
            max_iter=1000,
            random_state=42
        )

        stack = StackingClassifier(
            estimators=estimators,
            final_estimator=meta_learner,
            cv=5,                   # 5-fold internal cross-validation
            stack_method='predict_proba',
            passthrough=True,       # also pass raw features to meta-learner
            n_jobs=-1
        )
        return stack

    def train(self, X_val: pd.DataFrame, y_val: pd.Series):
        """
        Trains the Stacking Ensemble meta-classifier on the validation
        split's module scores. Uses internal 5-fold CV to prevent leakage.
        """
        logger.info(f"Training Advanced Stacking Meta-Classifier on {len(X_val)} samples...")
        logger.info("Building ensemble stack...")

        # Scale features
        X_scaled = self.scaler.fit_transform(X_val)

        # Handle class imbalance for XGBoost
        if HAS_XGBOOST:
            neg_count = np.sum(y_val == 0)
            pos_count = np.sum(y_val == 1)
            if pos_count > 0:
                scale_pos = neg_count / pos_count
            else:
                scale_pos = 1.0
            logger.info(f"    -> Class balance: neg={neg_count}, pos={pos_count}, scale_pos_weight={scale_pos:.2f}")

        stack = self._build_stacking_clf()

        # Set XGBoost scale_pos_weight dynamically
        if HAS_XGBOOST:
            stack.set_params(xgb__scale_pos_weight=scale_pos)

        # Train
        stack.fit(X_scaled, y_val)
        self.model = stack

        # Report cross-validated performance
        cv_scores = cross_val_score(stack, X_scaled, y_val, cv=3, scoring='f1')
        logger.info(f"Training complete. 3-Fold CV F1: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")

        # Log feature importance from XGBoost if available
        if HAS_XGBOOST:
            xgb_model = stack.named_estimators_['xgb']
            feature_names = X_val.columns.tolist()
            importances = xgb_model.feature_importances_
            importance_dict = dict(zip(feature_names, importances))
            logger.info(f"XGBoost Feature Importances: {importance_dict}")

        # Log RF feature importance
        rf_model = stack.named_estimators_['rf']
        feature_names = X_val.columns.tolist()
        rf_importances = rf_model.feature_importances_
        rf_importance_dict = dict(zip(feature_names, rf_importances))
        logger.info(f"Random Forest Feature Importances: {rf_importance_dict}")

    def predict(self, X_test) -> np.ndarray:
        """
        Predicts whether a resume is an adversarial attack.
        """
        if self.model is None:
            raise ValueError("Meta-Classifier must be trained before prediction.")

        if isinstance(X_test, pd.DataFrame):
            X_scaled = self.scaler.transform(X_test)
        else:
            X_scaled = X_test  # already scaled
        return self.model.predict(X_scaled)

    def predict_proba(self, X_test) -> np.ndarray:
        """
        Returns the probability of being an adversarial attack (class 1).
        """
        if self.model is None:
            raise ValueError("Meta-Classifier must be trained before prediction.")

        if isinstance(X_test, pd.DataFrame):
            X_scaled = self.scaler.transform(X_test)
        else:
            X_scaled = X_test  # already scaled
        return self.model.predict_proba(X_scaled)[:, 1]

    def save_model(self, output_dir: str):
        """Saves the trained model and scaler."""
        os.makedirs(output_dir, exist_ok=True)
        model_path = os.path.join(output_dir, "meta_classifier.pkl")
        scaler_path = os.path.join(output_dir, "scaler.pkl")

        with open(model_path, 'wb') as f:
            pickle.dump(self.model, f)
        with open(scaler_path, 'wb') as f:
            pickle.dump(self.scaler, f)
        logger.info(f"Model and scaler saved to {output_dir}")

    def load_model(self, model_dir: str):
        """Loads the trained model and scaler."""
        model_path = os.path.join(model_dir, "meta_classifier.pkl")
        scaler_path = os.path.join(model_dir, "scaler.pkl")
        
        with open(model_path, 'rb') as f:
            self.model = pickle.load(f)
        with open(scaler_path, 'rb') as f:
            self.scaler = pickle.load(f)
        logger.info(f"Model and scaler loaded from {model_dir}")


if __name__ == "__main__":
    pass
