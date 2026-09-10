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
            # Enhanced keywords with aliases mapped to standard forms
            self.keyword_aliases = {
                "amazon web services": "aws",
                "k8s": "kubernetes",
                "ml": "machine learning",
                "dl": "deep learning",
                "nlp": "natural language processing"
            }
            self.keywords = ["python", "java", "sql", "aws", "docker", "machine learning", "kubernetes", "deep learning", "natural language processing"]
        else:
            self.keyword_aliases = {}
            self.keywords = keywords
            
        self.threshold = None  # To be calibrated on the validation set

    def calibrate(self, val_df: pd.DataFrame, percentile: float = 95.0):
        """
        Calibrates the density threshold using the validation set.
        """
        logger.info(f"Calibrating Module A on {len(val_df)} validation samples at {percentile}th percentile...")
        
        # Calculate scores for all validation samples
        scores = val_df['text'].apply(lambda t: self._calculate_metrics(t)['score'])
        self.threshold = np.percentile(scores, percentile)
        
        logger.info(f"Calibration complete. Threshold set to: {self.threshold:.4f}")
        return self.threshold

    def _calculate_metrics(self, text: str) -> dict:
        """
        Calculates keyword frequency and concentration (clustering).
        """
        if not isinstance(text, str) or len(text.split()) == 0:
            return {"density": 0.0, "concentration": 0.0, "score": 0.0}
            
        text_lower = text.lower()
        import string
        # Strip punctuation
        text_clean = text_lower.translate(str.maketrans('', '', string.punctuation))
        
        # Replace aliases
        for alias, std in self.keyword_aliases.items():
            text_clean = text_clean.replace(alias, std)
            
        words = text_clean.split()
        total_words = len(words)
        
        # Count keyword occurrences and track their positions
        kw_positions = []
        for i, word in enumerate(words):
            if word in self.keywords:
                kw_positions.append(i)
                
        # Also check multi-word keywords
        for mw_kw in [k for k in self.keywords if ' ' in k]:
            # Simple count for multi-word without tracking precise pos
            kw_positions.extend([0] * text_clean.count(mw_kw))
                
        kw_count = len(kw_positions)
        density = kw_count / total_words if total_words > 0 else 0
        
        # Calculate concentration (how clumped the keywords are)
        # Low variance in positions = highly clumped = suspicious
        concentration = 0.0
        if kw_count > 3:
            kw_positions.sort()
            gaps = [kw_positions[i+1] - kw_positions[i] for i in range(len(kw_positions)-1)]
            # If average gap is very small compared to text length, it's concentrated
            avg_gap = sum(gaps) / len(gaps)
            if avg_gap < (total_words / 20): # Highly dense section
                concentration = 1.0 - (avg_gap / (total_words / 20))
                
        # Combine density and concentration for a smarter anomaly score
        combined_score = density + (concentration * 0.05)
        
        return {"density": density, "concentration": concentration, "score": combined_score}

    def predict(self, text: str) -> dict:
        """
        Predicts if a resume text exhibits anomalous keyword density.
        """
        if self.threshold is None:
            raise ValueError("Module A must be calibrated before prediction.")
            
        metrics = self._calculate_metrics(text)
        score = metrics["score"]
        is_anomalous = score > self.threshold
        
        # Normalize score between 0 and 1
        normalized = min(1.0, score / (self.threshold * 2) if self.threshold > 0 else 0)
        
        return {
            "status": "success",
            "density": metrics["density"],
            "concentration": metrics["concentration"],
            "anomaly_score": normalized,
            "is_flagged": is_anomalous
        }

if __name__ == "__main__":
    pass
