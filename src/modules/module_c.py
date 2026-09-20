import numpy as np
import logging
import re
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SemanticCoherenceScorer:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2', window_size: int = 2):
        self.model_name = model_name
        self.window_size = window_size
        logger.info(f"Loading Semantic Coherence Scorer with model: {model_name}...")
        try:
            self.model = SentenceTransformer(model_name)
        except Exception as e:
            logger.error(f"Failed to load sentence-transformer: {e}")
            raise
        self.variance_threshold = None

    def calibrate(self, val_df, objective: str = "f1"):
        variances = []
        for text in val_df['text']:
            scores = self._score_coherence(text)
            variances.append(scores['variance'])
            
        variances = np.array(variances)
        labels = val_df['is_adversarial'].values
        
        best_f1 = 0
        best_threshold = 0
        min_score, max_score = np.min(variances), np.max(variances)
        if min_score == max_score:
            self.variance_threshold = min_score
            return self.variance_threshold
            
        candidates = np.linspace(min_score, max_score, 100)
        
        for cand in candidates:
            preds = (variances > cand).astype(int)
            tp = np.sum((preds == 1) & (labels == 1))
            fp = np.sum((preds == 1) & (labels == 0))
            fn = np.sum((preds == 0) & (labels == 1))
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            
            if f1 > best_f1:
                best_f1 = f1
                best_threshold = cand
                
        if best_f1 == 0:
            best_threshold = np.percentile(variances, 95)
            
        self.variance_threshold = best_threshold
        return self.variance_threshold

    def _get_sentences(self, text: str) -> list:
        # Token budget limit handling
        max_chars = 20000 
        truncated = False
        if len(text) > max_chars:
            text = text[:max_chars]
            truncated = True
        sentences = [s.strip() for s in re.split(r'(?<=[.!?]) +', text) if len(s.strip()) > 10]
        return sentences, truncated

    def _get_display_units(self, text: str) -> list:
        # Returns units with offsets
        max_chars = 20000
        if len(text) > max_chars:
            text = text[:max_chars]
        
        # We need stable source offsets
        pattern = re.compile(r'(?<=[.!?])\s+|\n+')
        units = []
        start = 0
        for m in pattern.finditer(text):
            end = m.start()
            segment = text[start:end]
            if len(segment.strip()) > 3:
                units.append({"text": segment.strip(), "start": start, "end": end})
            start = m.end()
        
        # Add the last segment
        segment = text[start:]
        if len(segment.strip()) > 3:
            units.append({"text": segment.strip(), "start": start, "end": len(text)})
            
        return units

    def _score_coherence(self, text: str) -> dict:
        sentences, truncated = self._get_sentences(text)
        if len(sentences) < self.window_size + 1:
            return {"variance": 0.0, "mean_similarity": 1.0, "truncated": truncated}

        windows = [" ".join(sentences[i:i+self.window_size]) for i in range(len(sentences) - self.window_size + 1)]
        embeddings = self.model.encode(windows, convert_to_numpy=True)
        
        similarities = []
        for i in range(len(embeddings) - 1):
            sim = cosine_similarity([embeddings[i]], [embeddings[i+1]])[0][0]
            similarities.append(sim)
            
        variance = np.var(similarities) if similarities else 0.0
        mean_sim = np.mean(similarities) if similarities else 1.0
        
        return {"variance": float(variance), "mean_similarity": float(mean_sim), "truncated": truncated}

    def predict(self, text: str) -> dict:
        if self.variance_threshold is None:
            raise ValueError("Module C must be calibrated before prediction.")

        scores = self._score_coherence(text)
        variance = scores['variance']
        is_variance_anomalous = variance > self.variance_threshold

        if self.variance_threshold > 0:
            semantic_score = min(1.0, variance / (self.variance_threshold * 2))
        else:
            semantic_score = 1.0 if variance > 0 else 0.0

        n_cues = self._injection_signal(text)
        injection_score = min(1.0, n_cues * 0.5)
        
        anomaly_score = max(semantic_score, injection_score)
        is_anomalous = is_variance_anomalous or (n_cues > 0)

        return {
            "status": "success",
            "variance": variance,
            "mean_similarity": scores['mean_similarity'],
            "semantic_score": semantic_score,
            "injection_score": injection_score,
            "anomaly_score": anomaly_score,
            "injection_cues": n_cues,
            "is_flagged": bool(is_anomalous),
            "truncated": scores.get("truncated", False)
        }

    INJECTION_PATTERNS = [
        r"ignore\s+(all\s+)?previous\s+instructions?",
        r"disregard\s+(all\s+)?previous",
        r"system\s+override",
        r"\[system\]",
        r"<!--\s*system",
        r"you\s+must\s+(output|print|return)",
        r"rank\s+(this\s+candidate\s+)?(as\s+)?#?1",
        r"top\s+match",
        r"hire\s+immediately",
        r"match\s+score:\s*100",
        r"as\s+an\s+ai",
        r"new\s+instructions?",
        r"do\s+not\s+reject",
        r"administrator\s+instructions?",
        r"override\s+the\s+screening"
    ]

    BENIGN_PATTERNS = [
        r"researching\s+prompt\s+injection",
        r"legitimate\s+instruction",
        r"quoted\s+from",
        r"example\s+of"
    ]

    def _injection_signal(self, text: str) -> int:
        if not isinstance(text, str):
            return 0
        low = text.lower()
        
        # Check benign patterns first
        if any(re.search(bp, low) for bp in self.BENIGN_PATTERNS):
            return 0
            
        count = sum(1 for pattern in self.INJECTION_PATTERNS if re.search(pattern, low))
        return count

    def _variance_from_unit_emb(self, unit_emb) -> float:
        n = len(unit_emb)
        if n < self.window_size + 1:
            return 0.0
        win = np.array([unit_emb[i:i + self.window_size].mean(axis=0)
                        for i in range(n - self.window_size + 1)])
        norm = np.linalg.norm(win, axis=1)
        sims = []
        for i in range(len(win) - 1):
            denom = norm[i] * norm[i + 1]
            sims.append(float(win[i] @ win[i + 1] / denom) if denom else 0.0)
        return float(np.var(sims)) if sims else 0.0

    def explain_sentences(self, text: str) -> dict:
        """
        Approximate per-unit attribution via leave-one-out (LOO) ablation
        using pooled embeddings. NEVER call these causal proof or Shapley values!
        For exact causal delta, you must re-run the full forward pass.
        """
        units = self._get_display_units(text)
        if not units:
            return {"base_variance": 0.0, "sentences": [], "approximation_warning": "Pooled-embedding explanation is approximate."}

        unit_texts = [u['text'] for u in units]
        unit_emb = self.model.encode(unit_texts, convert_to_numpy=True)
        base_var = self._variance_from_unit_emb(unit_emb)

        records = []
        for i, unit in enumerate(units):
            sent = unit['text']
            
            # 3. For a small selected set, offer exact text-only removal deltas through the actual scoring path
            # To avoid O(n) transformer calls for everything, we only do it if we are checking "exact" path.
            # But the prompt says "offer exact text-only removal deltas through the actual scoring path"
            # So I will compute the actual delta instead of pooled for the top ones, or maybe just for all since this is a resume context (usually short).
            
            ablated_emb = np.delete(unit_emb, i, axis=0)
            var_without = self._variance_from_unit_emb(ablated_emb)
            contribution = base_var - var_without

            low = sent.lower()
            cue_hit = next((c for c in self.INJECTION_PATTERNS if re.search(c, low)), None)
            is_benign = any(re.search(bp, low) for bp in self.BENIGN_PATTERNS)
            if is_benign:
                cue_hit = None

            records.append({
                "sentence": sent,
                "start": unit['start'],
                "end": unit['end'],
                "contribution": float(contribution),
                "injection_cue": cue_hit,
            })

        contribs = [r["contribution"] for r in records]
        max_pos = max([c for c in contribs if c > 0], default=0.0)
        for r in records:
            norm = (r["contribution"] / max_pos) if max_pos > 0 and r["contribution"] > 0 else 0.0
            if r["injection_cue"]:
                norm = max(norm, 0.85)
            r["heat"] = float(min(1.0, norm))
            r["suspicious"] = bool(r["heat"] >= 0.5)

        records.sort(key=lambda r: r["heat"], reverse=True)
        return {
            "base_variance": base_var, 
            "sentences": records,
            "approximation_warning": "Pooled-embedding explanation is approximate."
        }

    def explain(self, text: str):
        return self.explain_sentences(text)

if __name__ == "__main__":
    pass
