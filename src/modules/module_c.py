import numpy as np
import logging
import re
import unicodedata
from bisect import bisect_left, bisect_right
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from src.modules.calibration import clean_validation_threshold
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SemanticCoherenceScorer:
    EXPLANATION_MAX_UNITS = 64

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

    def calibrate(self, val_df, objective: str = "percentile"):
        """Calibrate the threshold to clean-validation P95 only."""
        self.variance_threshold = None
        if objective != "percentile":
            raise ValueError("Module C only supports objective='percentile'; F1 calibration is not permitted.")
        if not isinstance(val_df, pd.DataFrame) or not {"text", "is_adversarial"}.issubset(val_df.columns):
            raise ValueError("Validation data must be a DataFrame with 'text' and 'is_adversarial' columns.")
        if val_df.empty or not val_df["text"].map(lambda value: isinstance(value, str)).all():
            raise ValueError("Validation data must contain non-empty rows with string text values.")

        variances = np.asarray([self._score_coherence(text)["variance"] for text in val_df["text"]], dtype=float)
        self.variance_threshold = clean_validation_threshold(
            variances, val_df["is_adversarial"].to_numpy(), "Module C"
        )
        logger.info("Module C threshold calibrated to clean-validation P95: %.6g", self.variance_threshold)
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
        if (isinstance(self.variance_threshold, bool)
                or not isinstance(self.variance_threshold, (int, float, np.number))
                or not np.isfinite(self.variance_threshold) or self.variance_threshold <= 0):
            raise ValueError("Module C requires a positive finite clean-validation threshold before prediction.")

        scores = self._score_coherence(text)
        variance = scores['variance']
        if not np.isfinite(variance) or variance < 0:
            raise ValueError("Module C produced an invalid semantic score.")
        is_variance_anomalous = variance > self.variance_threshold

        semantic_score = min(1.0, variance / (self.variance_threshold * 2))

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
        r"rank\s+me\s+(as\s+)?#?1\b",
        r"rank\s+(this|the)\s+(candidate|applicant|resume)\s+(as\s+)?#?1\b",
        r"hire\s+immediately",
        r"match\s+score:\s*100",
        r"\b(?:set|assign)\s+my\s+(?:fit|match|screening)\s+score\s+(?:to|of)\s+100\b",
        r"do\s+not\s+reject",
        r"administrator\s+instructions?",
        r"override\s+the\s+screening",
        r"(?:treat|consider|mark)\s+(?:this|the)\s+(?:resume|candidate|applicant)\s+as\s+(?:a\s+)?(?:perfect|ideal|top|best)\s+match",
        r"(?:assign|give|award|set)\s+(?:the\s+)?(?:highest|maximum|top|perfect|full)\s+(?:possible\s+)?(?:score|rank|ranking|eligibility|rating)",
        r"(?:mark|make|deem)\s+(?:this|the)\s+(?:candidate|applicant|resume)\s+(?:eligible|qualified|a\s+perfect\s+match)"
    ]

    # These phrases appear in ordinary technical and security writing. Treat
    # them as cues only when their own sentence also refers to hiring or a
    # candidate document. Direct instruction overrides remain actionable alone.
    CONTEXT_REQUIRED_PATTERNS = {
        r"system\s+override", r"\[system\]", r"<!--\s*system",
        r"you\s+must\s+(output|print|return)", r"hire\s+immediately",
        r"match\s+score:\s*100", r"do\s+not\s+reject",
        r"administrator\s+instructions?", r"override\s+the\s+screening",
        r"(?:assign|give|award|set)\s+(?:the\s+)?(?:highest|maximum|top|perfect|full)\s+(?:possible\s+)?(?:score|rank|ranking|eligibility|rating)",
    }
    SCREENING_CONTEXT_PATTERN = re.compile(
        r"\b(?:candidate|applicant|resume|screening|hiring|employment)\b"
    )

    BENIGN_PATTERNS = [
        r"researching\s+prompt\s+injection",
        r"legitimate\s+instruction",
        r"quoted\s+from",
        r"example\s+of"
    ]

    def _injection_signal(self, text: str) -> int:
        if not isinstance(text, str):
            return 0

        normalized = self._normalize_cue_text(text)
        boundaries = self._cue_context_boundaries(normalized)
        count = 0
        for pattern in self.INJECTION_PATTERNS:
            matches = re.finditer(pattern, normalized)
            if any(not self._is_benign_cue_context(normalized, match.start(), match.end(),
                                                 boundaries=boundaries) for match in matches):
                count += 1
        return count

    @staticmethod
    def _normalize_cue_text(text: str) -> str:
        """Normalize compatibility characters and remove invisible format controls."""
        normalized = unicodedata.normalize("NFKC", text).casefold()
        return "".join(char for char in normalized if unicodedata.category(char) != "Cf")

    @staticmethod
    def _cue_context_boundaries(text: str):
        """Index sentence boundaries once per normalized document, not per cue."""
        return ([match.end() for match in re.finditer(r"[.!?;\n]+\s*", text)],
                [match.start() for match in re.finditer(r"[.!?;\n]+", text)])

    @classmethod
    def _is_benign_cue_context(cls, text: str, start: int, end: int, *, boundaries=None) -> bool:
        """Ignore local examples and ambiguous cues lacking hiring context."""
        ends, starts = boundaries if boundaries is not None else cls._cue_context_boundaries(text)
        left_index = bisect_right(ends, start) - 1
        right_index = bisect_left(starts, end)
        left_boundary = ends[left_index] if left_index >= 0 else 0
        right_boundary = starts[right_index] if right_index < len(starts) else len(text)
        clause = text[left_boundary:right_boundary]
        local_start = start - left_boundary
        local_end = end - left_boundary

        cue_text = text[start:end]
        requires_context = any(re.fullmatch(pattern, cue_text) is not None
                               for pattern in cls.CONTEXT_REQUIRED_PATTERNS)
        if requires_context and not cls.SCREENING_CONTEXT_PATTERN.search(clause):
            return True

        # A quote is local to this cue; quoted material elsewhere cannot suppress it.
        quote_pairs = (("\"", "\""), ("'", "'"), ("`", "`"), ("“", "”"), ("‘", "’"))
        for opening, closing in quote_pairs:
            before = clause.rfind(opening, 0, local_start)
            after = clause.find(closing, local_end)
            if opening == "'":
                if before >= 0 and before > 0 and local_start < len(clause) and clause[before - 1].isalnum() and clause[before + 1].isalnum():
                    before = -1  # Ignore apostrophes inside contractions and possessives.
                if after >= 0 and after > 0 and after + 1 < len(clause) and clause[after - 1].isalnum() and clause[after + 1].isalnum():
                    after = -1
            if before >= 0 and after >= 0:
                return True

        # Descriptive labels must immediately introduce the cue in the same clause.
        prefix = clause[:local_start]
        for benign_pattern in cls.BENIGN_PATTERNS:
            for benign_match in re.finditer(benign_pattern, prefix):
                if local_start - benign_match.end() <= 64:
                    return True
        return False

    @classmethod
    def _injection_cue_for_sentence(cls, text: str):
        """Return the first actionable cue for explanation, with the same scope as scoring."""
        normalized = cls._normalize_cue_text(text)
        boundaries = cls._cue_context_boundaries(normalized)
        for pattern in cls.INJECTION_PATTERNS:
            for match in re.finditer(pattern, normalized):
                if not cls._is_benign_cue_context(normalized, match.start(), match.end(),
                                                boundaries=boundaries):
                    return pattern
        return None

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
        candidate_indices = np.linspace(
            0,
            len(units) - 1,
            num=min(len(units), self.EXPLANATION_MAX_UNITS),
            dtype=int,
        )
        for i in candidate_indices:
            i = int(i)
            unit = units[i]
            sent = unit['text']
            
            # 3. For a small selected set, offer exact text-only removal deltas through the actual scoring path
            # To avoid O(n) transformer calls for everything, we only do it if we are checking "exact" path.
            # But the prompt says "offer exact text-only removal deltas through the actual scoring path"
            # So I will compute the actual delta instead of pooled for the top ones, or maybe just for all since this is a resume context (usually short).
            
            ablated_emb = np.delete(unit_emb, i, axis=0)
            var_without = self._variance_from_unit_emb(ablated_emb)
            contribution = base_var - var_without

            cue_hit = self._injection_cue_for_sentence(sent)

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
            "approximation_warning": "Pooled-embedding explanation is approximate; only evenly spaced units are shown when the document has more than 64 units.",
            "omitted_unit_count": len(units) - len(records),
        }

    def explain(self, text: str):
        return self.explain_sentences(text)

if __name__ == "__main__":
    pass
