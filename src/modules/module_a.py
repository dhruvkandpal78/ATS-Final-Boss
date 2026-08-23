"""
module_a.py — Statistical Anomaly Detector (Keyword Density)
============================================================
Detects keyword stuffing by analyzing the statistical frequency and density of 
skill keywords relative to the resume's total word count, grounded in established
spam-filtering methodologies.
"""

import pandas as pd
import numpy as np
import logging
import json
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class KeywordDensityDetector:
    def __init__(self, keywords: list = None):
        if keywords is None:
            # We'll use the same robust list from injector.py in a real scenario
            self.keywords = ["python", "java", "sql", "aws", "docker", "machine learning"]
        else:
            self.keywords = keywords
            
        self.threshold = None  # To be calibrated on the validation set

    def calibrate(self, val_df: pd.DataFrame, percentile: float = 95.0):
        """
        Calibrates the density threshold using the validation set.
        """
        logger.info(f"Calibrating Module A on {len(val_df)} validation samples at {percentile}th percentile...")
        
        # Calculate density for all validation samples
        densities = val_df['text'].apply(self._calculate_density)
        self.threshold = np.percentile(densities, percentile)
        
        logger.info(f"Calibration complete. Threshold set to: {self.threshold:.4f}")
        return self.threshold

    def _calculate_density(self, text: str) -> float:
        """
        Calculates the frequency of keywords relative to total word count.
        """
        if not isinstance(text, str) or len(text.split()) == 0:
            return 0.0
            
        words = text.lower().split()
        total_words = len(words)
        
        # Simple count of keyword occurrences
        kw_count = sum(1 for word in words if word in self.keywords)
        
        return kw_count / total_words

    def predict(self, text: str) -> dict:
        """
        Predicts if a resume text exhibits anomalous keyword density.
        """
        if self.threshold is None:
            raise ValueError("Module A must be calibrated before prediction.")
            
        density = self._calculate_density(text)
        is_anomalous = density > self.threshold
        
        # Normalize score between 0 and 1
        score = min(1.0, density / (self.threshold * 2) if self.threshold > 0 else 0)
        
        return {
            "status": "success",
            "density": density,
            "anomaly_score": score,
            "is_flagged": is_anomalous
        }

if __name__ == "__main__":
    pass
