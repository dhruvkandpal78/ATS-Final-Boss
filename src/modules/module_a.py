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
import re
from bisect import bisect_right
from src.modules.calibration import clean_validation_threshold

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
        # Compile once, longest aliases first. Boundaries prevent aliases such as
        # "ml" from rewriting innocent tokens (HTML, XML, etc.).
        self._aliases = [(re.compile(r"(?<!\w)" + r"\s+".join(map(re.escape, alias.split())) + r"(?!\w)", re.I), standard)
                         for alias, standard in sorted(self.keyword_aliases.items(), key=lambda item: -len(item[0]))]
        self._keyword_patterns = [re.compile(r"(?<!\w)" + r"\s+".join(map(re.escape, word.split())) + r"(?!\w)")
                                  for word in dict.fromkeys(self.keywords)]

    def calibrate(self, val_df: pd.DataFrame, objective: str = "percentile"):
        """
        Calibrate to the documented 95th percentile of clean validation scores.

        The legacy F1-optimized threshold is intentionally rejected so
        calibrators remain consistent with the project methodology.
        """
        self.threshold = None
        if objective != "percentile":
            raise ValueError("Module A only supports objective='percentile'; F1 calibration is not permitted.")
        if not isinstance(val_df, pd.DataFrame) or not {"text", "is_adversarial"}.issubset(val_df.columns):
            raise ValueError("Validation data must be a DataFrame with 'text' and 'is_adversarial' columns.")
        if val_df.empty or not val_df["text"].map(lambda value: isinstance(value, str)).all():
            raise ValueError("Validation data must contain non-empty rows with string text values.")

        scores = val_df["text"].map(lambda text: self._calculate_metrics(text)["score"]).to_numpy(dtype=float)
        self.threshold = clean_validation_threshold(scores, val_df["is_adversarial"].to_numpy(), "Module A")
        logger.info("Module A threshold calibrated to clean-validation P95: %.6g", self.threshold)
        return self.threshold

    def _calculate_metrics(self, text: str) -> dict:
        """
        Calculates keyword frequency and concentration (clustering).
        """
        if not isinstance(text, str) or len(text.strip()) == 0:
            return {"density": 0.0, "concentration": 0.0, "score": 0.0}
            
        text_lower = text.lower()
        
        # Replace aliases with standard forms for consistency
        for pattern, standard in self._aliases:
            text_lower = pattern.sub(standard, text_lower)
            
        total_words = len(text_lower.split())
        if total_words == 0:
            return {"density": 0.0, "concentration": 0.0, "score": 0.0}
            
        # Count keyword occurrences and track their actual token positions
        token_starts = [match.start() for match in re.finditer(r'\S+', text_lower)]
        kw_positions = []
        for pattern in self._keyword_patterns:
            for match in pattern.finditer(text_lower):
                # Binary lookup avoids repeatedly copying/scanning growing prefixes.
                # Tabs and newlines have exactly the same token semantics as spaces.
                kw_positions.append(bisect_right(token_starts, match.start()) - 1)
                
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
        if (isinstance(self.threshold, bool) or not isinstance(self.threshold, (int, float, np.number))
                or not np.isfinite(self.threshold) or self.threshold <= 0):
            raise ValueError("Module A requires a positive finite clean-validation threshold before prediction.")
            
        metrics = self._calculate_metrics(text)
        score = metrics["score"]
        is_anomalous = score > self.threshold
        
        # Normalize score between 0 and 1
        normalized = min(1.0, score / (self.threshold * 2))
        
        return {
            "status": "success",
            "density": metrics["density"],
            "concentration": metrics["concentration"],
            "anomaly_score": normalized,
            "is_flagged": is_anomalous
        }

if __name__ == "__main__":
    pass
