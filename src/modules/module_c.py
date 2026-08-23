"""
module_c.py — Semantic Coherence Scorer (MiniLM Embeddings)
===========================================================
Detects context-less keywords, LLM-obfuscated injections, and semantic blurring
using 'all-MiniLM-L6-v2' via a sliding-window cosine similarity check.
Includes SHAP-based explainability integration.
"""

import numpy as np
import logging
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import shap

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SemanticCoherenceScorer:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2', window_size: int = 2):
        """
        :param model_name: Pretrained sentence-transformer model.
        :param window_size: Number of sentences in the sliding window.
        """
        self.model_name = model_name
        self.window_size = window_size
        logger.info(f"Loading Semantic Coherence Scorer with model: {model_name}...")
        try:
            self.model = SentenceTransformer(model_name)
        except Exception as e:
            logger.error(f"Failed to load sentence-transformer: {e}")
            raise
        self.variance_threshold = None  # To be calibrated on validation set

    def calibrate(self, val_df, percentile: float = 95.0):
        """
        Calibrates the semantic variance threshold using the validation set.
        """
        logger.info(f"Calibrating Module C on {len(val_df)} validation samples at {percentile}th percentile...")
        
        variances = []
        for text in val_df['text']:
            scores = self._score_coherence(text)
            variances.append(scores['variance'])
            
        self.variance_threshold = np.percentile(variances, percentile)
        logger.info(f"Calibration complete. Variance threshold set to: {self.variance_threshold:.4f}")
        return self.variance_threshold

    def _get_sentences(self, text: str) -> list:
        # Sentence splitting used by the *scoring* path. Kept intentionally stable
        # so the meta-classifier's feature distribution matches what it trained on.
        import re
        sentences = [s.strip() for s in re.split(r'(?<=[.!?]) +', text) if len(s.strip()) > 10]
        return sentences

    def _get_display_units(self, text: str) -> list:
        # Finer splitting used only by the explainability path: break on line
        # breaks *and* sentence punctuation so an injected footer becomes its own
        # highlightable clause. This does not affect the scoring path above.
        import re
        raw = re.split(r'(?<=[.!?])\s+|\n+', text)
        return [s.strip() for s in raw if len(s.strip()) > 3]

    def _score_coherence(self, text: str) -> dict:
        """
        Calculates sliding-window semantic variance. High variance indicates
        abrupt topical shifts typical of jargon stuffing or semantic blurring.
        """
        sentences = self._get_sentences(text)
        if len(sentences) < self.window_size + 1:
            return {"variance": 0.0, "mean_similarity": 1.0}

        # Create overlapping windows
        windows = [" ".join(sentences[i:i+self.window_size]) for i in range(len(sentences) - self.window_size + 1)]
        
        # Compute embeddings for all windows
        embeddings = self.model.encode(windows, convert_to_numpy=True)
        
        # Calculate sequential cosine similarities between adjacent windows
        similarities = []
        for i in range(len(embeddings) - 1):
            sim = cosine_similarity([embeddings[i]], [embeddings[i+1]])[0][0]
            similarities.append(sim)
            
        variance = np.var(similarities) if similarities else 0.0
        mean_sim = np.mean(similarities) if similarities else 1.0
        
        return {"variance": float(variance), "mean_similarity": float(mean_sim)}

    def _injection_signal(self, text: str) -> int:
        """
        Counts direct-instruction prompt-injection cues (Type D2). A pure
        injection footer carries no keyword density (Module A blind) and no
        PDF hiding marker (Module B blind), so Module C — the semantic /
        instruction-coherence module — is responsible for catching it. These
        imperative override phrases never occur in genuine resume prose.
        """
        if not isinstance(text, str):
            return 0
        low = text.lower()
        return sum(1 for cue in self.INJECTION_CUES if cue in low)

    def predict(self, text: str) -> dict:
        """
        Predicts if a resume text exhibits anomalous semantic blurring OR
        carries a direct-instruction prompt injection.
        """
        if self.variance_threshold is None:
            raise ValueError("Module C must be calibrated before prediction.")

        scores = self._score_coherence(text)
        variance = scores['variance']
        is_anomalous = variance > self.variance_threshold

        # Normalize score
        anomaly_score = min(1.0, variance / (self.variance_threshold * 2) if self.variance_threshold > 0 else 0)

        # Direct-instruction injection override: a resume containing imperative
        # "ignore previous instructions" style overrides is semantically
        # incoherent by construction and must be surfaced even when the sliding
        # window variance stays low (e.g. a short footer injection).
        n_cues = self._injection_signal(text)
        if n_cues > 0:
            anomaly_score = max(anomaly_score, min(1.0, 0.85 + 0.05 * n_cues))
            is_anomalous = True

        return {
            "status": "success",
            "variance": variance,
            "mean_similarity": scores['mean_similarity'],
            "anomaly_score": anomaly_score,
            "injection_cues": n_cues,
            "is_flagged": bool(is_anomalous)
        }

    # ---------------------------------------------------------------------
    # Explainability: sentence-level attribution
    # ---------------------------------------------------------------------
    # Lexical cues for direct-instruction prompt injection (Type D attacks).
    # These are additive evidence layered on top of the semantic ablation signal
    # so the XAI dashboard can highlight the exact offending clause.
    INJECTION_CUES = [
        "ignore all previous instructions", "ignore previous instructions",
        "disregard all previous", "system override", "[system]", "<!-- system",
        "you must output", "rank as #1", "top match", "hire immediately",
        "match score: 100", "as an ai", "new instructions",
    ]

    def _base_variance(self, sentences: list) -> float:
        """Semantic variance for an explicit list of sentences (windowed)."""
        if len(sentences) < self.window_size + 1:
            return 0.0
        windows = [" ".join(sentences[i:i + self.window_size])
                   for i in range(len(sentences) - self.window_size + 1)]
        embeddings = self.model.encode(windows, convert_to_numpy=True)
        sims = [cosine_similarity([embeddings[i]], [embeddings[i + 1]])[0][0]
                for i in range(len(embeddings) - 1)]
        return float(np.var(sims)) if sims else 0.0

    def _variance_from_unit_emb(self, unit_emb) -> float:
        """
        Windowed-variance computed from *cached* per-unit embeddings. Window
        embeddings are approximated by mean-pooling consecutive unit vectors,
        so the whole leave-one-out sweep runs on cached vectors with zero
        re-encoding — O(n^2) tiny cosines instead of O(n) transformer calls.
        Used only for explainability (not the scoring path), where the ranking
        of contributions matters more than exact variance magnitude.
        """
        n = len(unit_emb)
        if n < self.window_size + 1:
            return 0.0
        win = np.array([unit_emb[i:i + self.window_size].mean(axis=0)
                        for i in range(n - self.window_size + 1)])
        # cosine similarity between adjacent window vectors
        norm = np.linalg.norm(win, axis=1)
        sims = []
        for i in range(len(win) - 1):
            denom = norm[i] * norm[i + 1]
            sims.append(float(win[i] @ win[i + 1] / denom) if denom else 0.0)
        return float(np.var(sims)) if sims else 0.0

    def explain_sentences(self, text: str) -> dict:
        """
        Real per-sentence attribution via leave-one-sentence-out (LOO) ablation.

        For each sentence we remove it, recompute the sliding-window semantic
        variance, and measure how much the anomaly *drops*. A large drop means
        that sentence was driving the incoherence (context-less keyword blob or an
        injected instruction) — i.e. it is a strong positive contributor to the
        flag. This is a Shapley-style marginal-contribution approximation grounded
        directly in the Module-C decision function, plus a lexical injection-cue
        boost so prompt-injection footers are surfaced even when short.

        All units are embedded once and every ablation reuses those cached
        vectors, so this stays fast (well under a second) even on full-page PDFs.

        Returns a dict with the base variance and a ranked list of
        {sentence, contribution, injection_cue, suspicious} records.
        """
        sentences = self._get_display_units(text)
        if not sentences:
            return {"base_variance": 0.0, "sentences": []}

        # Single batched encode of every display unit — the only model call.
        unit_emb = self.model.encode(sentences, convert_to_numpy=True)
        base_var = self._variance_from_unit_emb(unit_emb)

        records = []
        for i, sent in enumerate(sentences):
            ablated_emb = np.delete(unit_emb, i, axis=0)
            var_without = self._variance_from_unit_emb(ablated_emb)
            # Marginal semantic contribution of this sentence to the anomaly.
            contribution = base_var - var_without

            low = sent.lower()
            cue_hit = next((c for c in self.INJECTION_CUES if c in low), None)

            records.append({
                "sentence": sent,
                "contribution": float(contribution),
                "injection_cue": cue_hit,
            })

        # Normalise contributions to [0, 1] for heat-mapping in the UI.
        contribs = [r["contribution"] for r in records]
        max_pos = max([c for c in contribs if c > 0], default=0.0)
        for r in records:
            norm = (r["contribution"] / max_pos) if max_pos > 0 and r["contribution"] > 0 else 0.0
            # A direct-injection cue is inherently suspicious regardless of variance.
            if r["injection_cue"]:
                norm = max(norm, 0.85)
            r["heat"] = float(min(1.0, norm))
            r["suspicious"] = bool(r["heat"] >= 0.5)

        records.sort(key=lambda r: r["heat"], reverse=True)
        return {"base_variance": base_var, "sentences": records}

    def explain(self, text: str):
        """
        Backwards-compatible entry point. Returns the full sentence-level
        attribution produced by :meth:`explain_sentences`.
        """
        logger.info("Running leave-one-out semantic attribution for explainability...")
        return self.explain_sentences(text)

if __name__ == "__main__":
    pass
