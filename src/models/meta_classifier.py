"""
meta_classifier.py — Ensemble Combined Scoring Layer
====================================================
A model-agnostic meta-classifier (Logistic Regression) that combines
heterogeneous anomaly scores (Statistical, Structural, Semantic) from
Modules A, B, and C into a single calibrated decision.
"""

import pandas as pd
import numpy as np
import logging
import pickle
import os
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnsembleMetaClassifier:
    def __init__(self, c_values: list = None):
        """
        :param c_values: List of C values for light regularization sweep.
        """
        if c_values is None:
            self.c_values = [0.01, 0.1, 1.0, 10.0]
        else:
            self.c_values = c_values
            
        self.model = None
        self.scaler = StandardScaler()

    def train(self, X_val: pd.DataFrame, y_val: pd.Series):
        """
        Trains the Logistic Regression meta-classifier strictly on the validation
        split's module scores to prevent test-set data leakage.
        """
        logger.info(f"Training Meta-Classifier on {len(X_val)} validation samples...")
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X_val)
        
        best_score = -1
        best_c = None
        best_model = None
        
        # Light regularization sweep
        for c in self.c_values:
            lr = LogisticRegression(C=c, class_weight='balanced', random_state=42, max_iter=1000)
            lr.fit(X_scaled, y_val)
            score = lr.score(X_scaled, y_val)
            
            if score > best_score:
                best_score = score
                best_c = c
                best_model = lr
                
        self.model = best_model
        logger.info(f"Training complete. Best C: {best_c} with Val Accuracy: {best_score:.4f}")
        
        # Log feature importance (coefficients)
        feature_names = X_val.columns.tolist()
        coefs = self.model.coef_[0]
        importance = dict(zip(feature_names, coefs))
        logger.info(f"Feature coefficients: {importance}")

    def predict(self, X_test: pd.DataFrame) -> np.ndarray:
        """
        Predicts whether a resume is an adversarial attack.
        """
        if self.model is None:
            raise ValueError("Meta-Classifier must be trained before prediction.")
            
        X_scaled = self.scaler.transform(X_test)
        return self.model.predict(X_scaled)

    def predict_proba(self, X_test: pd.DataFrame) -> np.ndarray:
        """
        Returns the probability of being an adversarial attack (class 1).
        """
        if self.model is None:
            raise ValueError("Meta-Classifier must be trained before prediction.")
            
        X_scaled = self.scaler.transform(X_test)
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

if __name__ == "__main__":
    pass
