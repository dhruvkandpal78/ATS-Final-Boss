"""
meta_classifier.py — Advanced Ensemble Combined Scoring Layer
==============================================================
A meta-classifier that combines heterogeneous anomaly scores (Statistical,
Structural, Semantic) from Modules A, B, and C using a stacking ensemble.
The default base estimators are Random Forest and Logistic Regression.
XGBoost is optional and must be enabled explicitly.

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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class EnsembleMetaClassifier:
    def __init__(self, use_xgboost: bool = False, n_jobs: int = 1):
        """Create the lightweight default ensemble.

        XGBoost is optional and loaded only when explicitly enabled. Parallelism
        defaults to one worker to keep local inference and tests predictable.
        """
        if not isinstance(n_jobs, int) or n_jobs < 1:
            raise ValueError("n_jobs must be a positive integer.")
        self.model = None
        self.scaler = StandardScaler()
        self.use_xgboost = bool(use_xgboost)
        self.n_jobs = n_jobs

    def _build_stacking_clf(self, cv: int):
        """
        Build a stacking classifier with an inner CV fold count sized for the
        available minority class. XGBoost is included only by explicit request.
        """
        estimators = []

        if self.use_xgboost:
            try:
                from xgboost import XGBClassifier
            except ImportError as exc:
                raise ImportError(
                    "XGBoost was requested but is not installed. Install the optional models extra."
                ) from exc
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
                n_jobs=self.n_jobs,
                verbosity=0
            )
            estimators.append(('xgb', xgb))
            logger.info("    -> XGBoost loaded.")

        rf = RandomForestClassifier(
            n_estimators=300,
            max_depth=6,
            min_samples_split=5,
            min_samples_leaf=2,
            class_weight='balanced',
            random_state=42,
            n_jobs=self.n_jobs
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
            cv=cv,
            stack_method='predict_proba',
            passthrough=True,       # also pass raw features to meta-learner
            n_jobs=self.n_jobs
        )
        return stack

    def train(self, X_train: pd.DataFrame, y_train: pd.Series):
        """
        Fit the ensemble on the supplied training rows.

        Stacking uses stratified out-of-fold predictions internally. No outer
        cross-validation score is reported here: callers should evaluate on a
        separately held-out validation split with the complete preprocessing
        pipeline to avoid scaler leakage and misleading nested-CV claims.
        """
        if not isinstance(X_train, pd.DataFrame):
            X_train = pd.DataFrame(X_train)
        if X_train.empty or X_train.shape[1] == 0:
            raise ValueError("Training features must contain at least one row and one column.")
        if X_train.isna().any().any():
            raise ValueError("Training features must not contain missing values.")
        try:
            feature_values = X_train.to_numpy(dtype=float)
        except (TypeError, ValueError) as exc:
            raise ValueError("Training features must be numeric.") from exc
        if not np.isfinite(feature_values).all():
            raise ValueError("Training features must contain only finite values.")

        y_array = np.asarray(y_train)
        if y_array.ndim != 1 or len(y_array) != len(X_train):
            raise ValueError("Training labels must be one-dimensional and match the feature row count.")
        if pd.isna(y_array).any() or not np.isin(y_array, [0, 1]).all():
            raise ValueError("Training labels must contain only binary values 0 and 1.")
        classes, counts = np.unique(y_array, return_counts=True)
        if len(classes) != 2:
            raise ValueError("Training requires examples from both classes 0 and 1.")
        minority_count = int(counts.min())
        if minority_count < 2:
            raise ValueError("Training requires at least two examples from each class for stacking CV.")

        inner_cv = min(5, minority_count)
        logger.info(
            "Training stacking meta-classifier on %d rows with %d-fold internal CV...",
            len(X_train), inner_cv,
        )
        logger.info("Building ensemble stack...")

        # The scaler is fitted only on the rows supplied for model training.
        X_scaled = self.scaler.fit_transform(X_train)

        stack = self._build_stacking_clf(cv=inner_cv)

        # Set XGBoost scale_pos_weight dynamically when explicitly enabled.
        if self.use_xgboost:
            neg_count = int(np.sum(y_array == 0))
            pos_count = int(np.sum(y_array == 1))
            scale_pos = neg_count / pos_count
            stack.set_params(xgb__scale_pos_weight=scale_pos)

        stack.fit(X_scaled, y_array)
        self.model = stack
        logger.info("Training complete. No held-out performance metric was computed.")

        # Log feature importance from XGBoost if available
        if self.use_xgboost:
            xgb_model = stack.named_estimators_['xgb']
            feature_names = X_train.columns.tolist()
            importances = xgb_model.feature_importances_
            importance_dict = dict(zip(feature_names, importances))
            logger.info(f"XGBoost Feature Importances: {importance_dict}")

        # Log RF feature importance
        rf_model = stack.named_estimators_['rf']
        feature_names = X_train.columns.tolist()
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
