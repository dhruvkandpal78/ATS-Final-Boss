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

    def calibrate(self, val_df: pd.DataFrame, objective: str = "f1"):
        """
        Calibrates the density threshold using the validation set to maximize an objective (e.g. F1).
        """
        logger.info(f"Calibrating Module A on {len(val_df)} validation samples (objective: {objective})...")
        
        # Calculate scores for all validation samples
        scores = val_df['text'].apply(lambda t: self._calculate_metrics(t)['score']).values
        labels = val_df['is_adversarial'].values
        
        # Search for the threshold that maximizes F1
        best_f1 = 0
        best_threshold = 0
        
        # Test 100 candidate thresholds between min and max score
        min_score, max_score = np.min(scores), np.max(scores)
        if min_score == max_score:
            self.threshold = min_score
            return self.threshold
            
        candidates = np.linspace(min_score, max_score, 100)
        
        for cand in candidates:
            preds = (scores > cand).astype(int)
            # Calculate F1 manually to avoid sklearn dependency overhead here
            tp = np.sum((preds == 1) & (labels == 1))
            fp = np.sum((preds == 1) & (labels == 0))
            fn = np.sum((preds == 0) & (labels == 1))
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            
            if f1 > best_f1:
                best_f1 = f1
                best_threshold = cand
                
        # Fallback if no threshold yields a good F1 (e.g. all 0s)
        if best_f1 == 0:
            best_threshold = np.percentile(scores, 95)
            
        self.threshold = best_threshold
        logger.info(f"Calibration complete. Threshold set to: {self.threshold:.4f} (Validation F1: {best_f1:.4f})")
        return self.threshold

    def _calculate_metrics(self, text: str) -> dict:
        """
        Calculates keyword frequency and concentration (clustering).
        """
        if not isinstance(text, str) or len(text.strip()) == 0:
            return {"density": 0.0, "concentration": 0.0, "score": 0.0}
            
        text_lower = text.lower()
        
        # Replace aliases with standard forms for consistency
        for alias, std in self.keyword_aliases.items():
            text_lower = text_lower.replace(alias, std)
            
        total_words = len(text_lower.split())
        if total_words == 0:
            return {"density": 0.0, "concentration": 0.0, "score": 0.0}
            
        # Count keyword occurrences and track their actual token positions
        import re
        kw_positions = []
        for kw in self.keywords:
            # Use regex boundaries to match exact keywords or multi-word phrases
            pattern = r'\b' + re.escape(kw) + r'\b'
            for match in re.finditer(pattern, text_lower):
                # Count the number of spaces before this match to approximate word index
                prefix = text_lower[:match.start()]
                word_idx = prefix.count(' ')
                kw_positions.append(word_idx)
                
        kw_count = len(kw_positions)
        density = kw_count / total_words
        
        # Calculate concentration (how clumped the keywords are)
        # Low variance in positions = highly clumped = suspicious
        concentration = 0.0
        if kw_count > 3:
            kw_positions.sort()
            gaps = [kw_positions[i+1] - kw_positions[i] for i in range(len(kw_positions)-1)]
            # If average gap is very small compared to text length, it's concentrated
            avg_gap = sum(gaps) / len(gaps)
            # Normal technical resumes have keywords spread naturally. Attackers clump them.
            if avg_gap < (total_words / 20):
                concentration = 1.0 - (avg_gap / (total_words / 20))
                
        # Normalization: If density is extremely high (e.g. 50% of the resume is keywords)
        # cap it so it doesn't skew.
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
        if self.threshold > 0:
            normalized = min(1.0, score / (self.threshold * 2))
        else:
            normalized = 1.0 if score > 0 else 0.0
        
        return {
            "status": "success",
            "density": metrics["density"],
            "concentration": metrics["concentration"],
            "anomaly_score": normalized,
            "is_flagged": is_anomalous
        }

if __name__ == "__main__":
    pass
