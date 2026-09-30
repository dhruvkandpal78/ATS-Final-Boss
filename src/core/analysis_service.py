"""Canonical document analysis used by CLI and HTTP adapters.

The saved three-feature classifier is a legacy research artifact trained with a
synthetic structural proxy. Its output is an uncalibrated experimental score,
and it cannot score plain text or incomplete PDF evidence honestly.
"""

from __future__ import annotations

from datetime import datetime, timezone
import math
import hashlib
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, Optional
from uuid import uuid4

import pandas as pd

from src.core.schemas import AnalysisResult
from src.core.evidence import instruction_spans
from src.core.review_policy import POLICY_VERSION, keyword_repetition


FEATURE_ORDER = ("Module_A_Score", "Module_B_Score", "Module_C_Score")
MAX_PDF_PAGES = 20
MAX_TEXT_CHARS = 100_000
MODEL_ID = "legacy-three-feature-v1"

MODULE_META = {
    "a": ("Module A", "Keyword density", "Skill-keyword frequency and concentration."),
    "b": ("Module B", "PDF structure", "Physical PDF text and layer anomalies."),
    "c": ("Module C", "Semantic coherence", "Sentence-window variance and direct-instruction cues."),
}


def _module(key: str, status: str, score: Optional[float] = None,
            reason: Optional[str] = None, **extra: Any) -> Dict[str, Any]:
    name, sub, desc = MODULE_META[key]
    return {"name": name, "sub": sub, "desc": desc, "status": status,
            "score": score, "reason": reason, "evidence_ids": [],
            "capabilities": {"score_available": score is not None}, **extra}


def _finite_score(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and 0.0 <= number <= 1.0 else None


def _anchor(page_index: Optional[int] = None, bbox: Optional[list] = None) -> Dict[str, Any]:
    return {"page_index": page_index, "char_start": None,
            "char_end": None, "bbox": bbox}


class AnalysisService:
    def __init__(self, models_dir: Optional[str] = None, mod_a=None, mod_b=None,
                 mod_c=None, meta_clf=None, scaler=None):
        self.model_id = MODEL_ID if meta_clf is not None else None
        self.candidate_model = False
        if models_dir is not None:
            # Local trusted artifacts only. Never pass uploaded model files here.
            from src.inference import load_pipeline
            meta_clf, scaler, mod_a, mod_b, mod_c = load_pipeline(models_dir)
            manifest = Path(models_dir) / "candidate_manifest.json"
            self.candidate_model = manifest.is_file()
            self.model_id = ("candidate-" + hashlib.sha256(manifest.read_bytes()).hexdigest()[:16]
                             if self.candidate_model else MODEL_ID)
        self.mod_a = mod_a
        self.mod_b = mod_b
        self.mod_c = mod_c
        self.meta_clf = meta_clf
        self.scaler = scaler

    def analyze_text(self, text: str, b_score: Optional[float] = None) -> AnalysisResult:
        """Analyze text without inventing PDF structure.

        ``b_score`` is accepted for source compatibility but deliberately ignored:
        only ``analyze_pdf`` may provide physical structural evidence.
        """
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Text must contain non-whitespace content")
        if len(text) > MAX_TEXT_CHARS:
            raise ValueError(f"Text exceeds the {MAX_TEXT_CHARS} character limit")
        return self._analyze(text, "text", None, None, {"pages_total": None,
                             "pages_analyzed": None, "limitations": []})

    def analyze_pdf(self, file_path: str, include_previews: bool = False) -> AnalysisResult:
        """Bound PDF parsing and return structured coverage on unsupported input."""
        started = perf_counter()
        coverage = {"pages_total": None, "pages_analyzed": 0, "limitations": []}
        if self.mod_b is None:
            return self._unscorable("pdf", coverage, "pdf_detector_unavailable", started)
        try:
            import fitz
            with fitz.open(str(Path(file_path))) as doc:
                coverage["pages_total"] = len(doc)
                if doc.needs_pass:
                    return self._unscorable("pdf", coverage, "encrypted_pdf", started)
                if len(doc) == 0:
                    return self._unscorable("pdf", coverage, "empty_pdf", started)
                if len(doc) > MAX_PDF_PAGES:
                    coverage["limitations"].append(f"PDF exceeds the {MAX_PDF_PAGES}-page processing limit.")
                    return self._unscorable("pdf", coverage, "page_limit_exceeded", started)
                chunks = []
                chars = 0
                truncated = False
                pages_without_text = 0
                for page in doc:
                    page_text = page.get_text()
                    if not page_text.strip():
                        pages_without_text += 1
                    remaining = MAX_TEXT_CHARS - chars
                    if len(page_text) > remaining:
                        chunks.append(page_text[:remaining])
                        truncated = True
                    else:
                        chunks.append(page_text)
                    chars += len(chunks[-1])
                    coverage["pages_analyzed"] += 1
                    if truncated:
                        break
                text = "\n".join(chunks)
        except Exception:
            return self._unscorable("pdf", coverage, "pdf_parse_error", started)

        if truncated:
            coverage["limitations"].append(f"Text extraction stopped at {MAX_TEXT_CHARS} characters.")
        if pages_without_text:
            coverage["limitations"].append(f"{pages_without_text} PDF page(s) have no extractable text; OCR was not performed.")
        try:
            b_raw = self.mod_b.analyze_pdf(file_path)
        except Exception:
            b_raw = {"status": "error"}
        if not isinstance(b_raw, dict) or b_raw.get("status") not in ("success", "ok"):
            b_raw = {"status": "error"}
            coverage["limitations"].append("PDF structural analysis failed.")
        else:
            coverage["limitations"].extend(str(item) for item in b_raw.get("limitations", []) if item)

        if not text.strip():
            coverage["limitations"].append("No extractable text; OCR and semantic analysis are unavailable.")
        raw_details = b_raw.get("details") or {}
        hidden_groups = raw_details.get("hidden_ocg_groups", 0) if isinstance(raw_details, dict) else 0
        result = self._analyze(text, "pdf", b_raw, None, coverage,
                               force_partial=truncated or pages_without_text > 0 or hidden_groups > 0)
        if include_previews:
            from src.core.pdf_preview import build_evidence_previews
            try:
                result["previews"] = build_evidence_previews(file_path, result["findings"])
                if result["findings"]:
                    coverage["limitations"].append("Evidence previews are limited to three finding pages and 2 MiB; highlights locate traces, not proof of intent.")
            except Exception:
                result["previews"] = []
                coverage["limitations"].append("PDF evidence preview could not be rendered.")
        result["timings_ms"]["total"] = round((perf_counter() - started) * 1000, 2)
        return result

    def _score_model(self, features: Dict[str, Optional[float]]) -> tuple[Optional[float], Optional[bool]]:
        if self.meta_clf is None or self.scaler is None or any(
            features.get(key) is None for key in FEATURE_ORDER
        ):
            return None, None
        frame = pd.DataFrame([{key: features[key] for key in FEATURE_ORDER}], columns=FEATURE_ORDER)
        scaled = self.scaler.transform(frame)
        probabilities = self.meta_clf.predict_proba(scaled)
        classes = list(self.meta_clf.classes_)
        positive = next((i for i, value in enumerate(classes) if value == 1 or value == "1"), None)
        if positive is None:
            raise ValueError("Classifier has no positive class 1")
        score = _finite_score(probabilities[0][positive])
        if score is None:
            raise ValueError("Classifier returned an invalid score")
        prediction = self.meta_clf.predict(scaled)[0]
        return score, bool(prediction == 1 or prediction == "1")

    def _analyze(self, text: str, mode: str, b_raw: Optional[dict],
                 _unused: Any, coverage: Dict[str, Any],
                 force_partial: bool = False) -> AnalysisResult:
        started = perf_counter()
        modules = {
            "a": _module("a", "unsupported", reason="No extractable text."),
            "b": _module("b", "not_applicable" if mode == "text" else "error",
                         reason="PDF structure is unavailable for text input." if mode == "text" else "Structural analysis failed."),
            "c": _module("c", "unsupported", reason="No extractable text."),
        }
        findings = []
        features: Dict[str, Optional[float]] = dict.fromkeys(FEATURE_ORDER)
        a_raw: dict = {}
        c_raw: dict = {}
        semantic_truncated = False
        if text.strip():
            for key, detector, feature in (("a", self.mod_a, "Module_A_Score"),
                                           ("c", self.mod_c, "Module_C_Score")):
                if detector is None:
                    modules[key] = _module(key, "unsupported", reason="Detector unavailable.")
                    continue
                threshold_name = "threshold" if key == "a" else "variance_threshold"
                if hasattr(detector, threshold_name):
                    threshold = getattr(detector, threshold_name)
                    try:
                        valid = not isinstance(threshold, (bool, str)) and math.isfinite(threshold) and threshold > 0
                    except TypeError:
                        valid = False
                    if not valid:
                        reason = ("Keyword" if key == "a" else "Semantic") + " calibration is unavailable. Configure a positive threshold using source-disjoint validation data."
                        modules[key] = _module(key, "unsupported", reason=reason)
                        coverage["limitations"].append(reason)
                        if key == "c" and callable(getattr(detector, "_injection_signal", None)):
                            cues = detector._injection_signal(text)
                            c_raw = {"injection_cues": cues}
                            modules[key]["injection_cues"] = cues
                            if cues:
                                findings.append({"id": "c-instruction-1", "detector": "c",
                                    "category": "direct_instruction", "severity": "high",
                                    "explanation_method": "pattern_rule",
                                    "explanation": "Text contains a direct instruction pattern aimed at a reviewer or screening system.",
                                    "anchor": _anchor(), "uncertainty": "The pattern alone does not establish intent."})
                        continue
                try:
                    raw = detector.predict(text)
                    score = _finite_score(raw.get("anomaly_score"))
                    if score is None:
                        raise ValueError("Detector score invalid")
                    features[feature] = score
                    modules[key] = _module(key, "ok", score=score,
                                           flagged=bool(raw.get("is_flagged")))
                    if key == "a":
                        a_raw = raw
                        modules[key]["density"] = raw.get("density")
                        if raw.get("is_flagged"):
                            findings.append({"id": "a-density-1", "detector": "a",
                                "category": "keyword_density", "severity": "medium",
                                "explanation_method": "detector_score",
                                "explanation": "Skill keywords are unusually dense under the configured detector threshold.",
                                "anchor": _anchor(), "uncertainty": "No exact text span is attributed."})
                    else:
                        c_raw = raw
                        modules[key]["variance"] = raw.get("variance")
                        modules[key]["injection_cues"] = int(raw.get("injection_cues", 0))
                        if raw.get("injection_cues", 0) > 0:
                            findings.append({"id": "c-instruction-1", "detector": "c",
                                "category": "direct_instruction", "severity": "high",
                                "explanation_method": "pattern_rule",
                                "explanation": "Text contains a direct instruction pattern aimed at a reviewer or screening system.",
                                "anchor": _anchor(), "uncertainty": "The pattern alone does not establish intent."})
                        elif raw.get("is_flagged"):
                            findings.append({"id": "c-variance-1", "detector": "c",
                                "category": "semantic_variance", "severity": "medium",
                                "explanation_method": "detector_score",
                                "explanation": "Semantic coherence varies above the configured detector threshold.",
                                "anchor": _anchor(), "uncertainty": "This is an approximate document-level signal."})
                    if raw.get("truncated"):
                        coverage["limitations"].append("Semantic analysis uses only the first 20,000 characters.")
                        semantic_truncated = True
                except Exception:
                    modules[key] = _module(key, "error", reason="Detector analysis failed.")
                    coverage["limitations"].append(f"Module {key.upper()} analysis failed.")

        if mode == "pdf":
            b_score = _finite_score(b_raw.get("anomaly_score")) if b_raw and b_raw.get("status") in ("ok", "success") else None
            if b_score is not None:
                features["Module_B_Score"] = b_score
                details = b_raw.get("details") or {}
                if not isinstance(details, dict):
                    details = {}
                explicit_trace = any((details.get(key) or 0) > 0 for key in
                                     ("invisible_render_mode", "hidden_ocg", "background_color_match"))
                modules["b"] = _module("b", "ok", score=b_score, flagged=b_score >= 0.5 or explicit_trace,
                                       details=details, coverage_status="partial" if details.get("hidden_ocg_groups", 0) > 0 else "complete")
                modules["b"]["capabilities"].update(b_raw.get("capabilities") or {})
                for i, item in enumerate(details.get("findings", [])[:50], 1):
                    page = item.get("page")
                    page_index = page - 1 if isinstance(page, int) and page > 0 else None
                    rect = item.get("rect")
                    try:
                        bbox = [float(x) for x in rect] if len(rect) == 4 and all(math.isfinite(float(x)) for x in rect) else None
                    except (TypeError, ValueError):
                        bbox = None
                    findings.append({"id": f"b-structure-{i}", "detector": "b",
                        "category": "pdf_structure", "severity": "high" if b_score >= 0.9 else "medium",
                        "explanation_method": "pdf_trace", "explanation": "PDF text trace has structural anomaly flags: " + ", ".join(item.get("flags", [])),
                        "anchor": _anchor(page_index, bbox),
                        "uncertainty": "A structural anomaly is not proof of manipulation."})
                if len(details.get("findings", [])) > 50:
                    coverage["limitations"].append("Only the first 50 structural findings are listed.")
            else:
                coverage["limitations"].append("PDF structural score is unavailable.")

        # Anchors refer to the exact submitted text, never normalized positions.
        # PDF extraction offsets are not page coordinates and are not exposed as such.
        if mode == "text" and c_raw.get("injection_cues", 0) > 0:
            spans = instruction_spans(text, self.mod_c)
            if spans:
                template = next((item for item in findings if item["category"] == "direct_instruction"), None)
                if template is not None:
                    findings.remove(template)
                    for index, span in enumerate(spans, 1):
                        findings.append({**template, "id": f"c-instruction-{index}",
                                         "anchor": {**_anchor(), **span}})
        repetition = keyword_repetition(text, self.mod_a) if text.strip() else None
        if repetition:
            findings.append({"id": "a-repetition-1", "detector": "a",
                "category": "keyword_repetition", "severity": "high",
                "explanation_method": "pattern_rule",
                "explanation": "A skill-dominated token sequence repeats contiguously at least eight times over at least 32 tokens.",
                "anchor": _anchor(), "uncertainty": "Exact repetition warrants inspection but does not establish intent."})
        for finding in findings:
            finding["review_trigger"] = finding["category"] in ("direct_instruction", "keyword_repetition")
            modules[finding["detector"]]["evidence_ids"].append(finding["id"])

        score = None
        model_decision = None
        if mode == "pdf" and not force_partial and not semantic_truncated and all(modules[key]["status"] == "ok" for key in ("a", "b", "c")):
            try:
                score, model_decision = self._score_model(features)
            except Exception:
                coverage["limitations"].append("Classifier inference failed.")
        if mode == "text":
            coverage["limitations"].append("No validated text-only model; PDF structural evidence is not applicable.")
        elif score is not None:
            coverage["limitations"].append(
                "Experimental candidate score: trained on PDF features, but probability calibration and independent real-world validation are not established."
                if self.candidate_model else
                "Experimental score: legacy model used synthetic structural proxies in training and is not calibrated on real PDFs.")

        density_advisory = modules["a"].get("flagged", False)
        rule_density = repetition is not None
        rule_injection = modules["c"].get("injection_cues", 0) > 0
        structural_details = modules["b"].get("details") or {}
        explicit_structure = any(
            (structural_details.get(key) or 0) > 0
            for key in ("invisible_render_mode", "hidden_ocg", "background_color_match")
        ) if isinstance(structural_details, dict) else False
        rule_structure = mode == "pdf" and features["Module_B_Score"] is not None and (
            features["Module_B_Score"] >= 0.9 or explicit_structure
        )
        complete = mode == "pdf" and not force_partial and not semantic_truncated and all(modules[key]["status"] == "ok" for key in ("a", "b", "c"))
        reason_codes = []
        if rule_density:
            reason_codes.append("keyword_repetition_signal")
        if rule_injection:
            reason_codes.append("direct_instruction_cue")
        if rule_structure:
            reason_codes.append("pdf_structure_advisory")
        if density_advisory:
            reason_codes.append("keyword_density_advisory")
        if model_decision:
            reason_codes.append("experimental_model_advisory")
        if not complete:
            reason_codes.append("analysis_incomplete" if mode == "pdf" else "text_model_unavailable")
        if rule_density or rule_injection:
            decision = "review_recommended"
        elif complete and score is not None:
            decision = "no_signals_detected"
        else:
            decision = "insufficient_evidence"
        coverage["limitations"].append("Policy 2.0 requires direct instruction cues or sustained skill repetition for review. Structural, density and experimental model anomalies remain advisory; subtle attacks may be missed.")

        if mode == "text":
            status = "partial"
        elif complete:
            status = "complete"
        elif any(m["status"] == "ok" for m in modules.values()):
            status = "partial"
        else:
            status = "unscorable"

        result: AnalysisResult = {
            "schema_version": "2.0", "analysis_id": str(uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": status, "input_mode": mode,
            "model": {"id": self.model_id if self.meta_clf is not None else None, "calibrated": False},
            "policy_version": POLICY_VERSION, "score": score,
            "score_kind": "model_score" if score is not None else "unavailable",
            "decision": decision, "reason_codes": reason_codes,
            "coverage": coverage, "modules": modules, "findings": findings,
            "timings_ms": {"total": round((perf_counter() - started) * 1000, 2)},
            # Compatibility aliases; policy_proba is never an override-derived value.
            "features": features, "module_a": {**a_raw, "score": features["Module_A_Score"]},
            "module_b": {"score": features["Module_B_Score"], "status": modules["b"]["status"]},
            "module_c": {**c_raw, "score": features["Module_C_Score"]},
            "injection_cues": int(c_raw.get("injection_cues", 0)),
            "model_decision": model_decision, "model_proba": score,
            "policy_decision": decision == "review_recommended", "policy_proba": score,
            "verdict": "attack" if decision == "review_recommended" else "clean" if decision == "no_signals_detected" else "insufficient_evidence",
            "proba": score, "threshold": 0.5 if score is not None else None,
        }
        return result

    def _unscorable(self, mode: str, coverage: Dict[str, Any], reason: str,
                    started: float) -> AnalysisResult:
        coverage["limitations"].append(reason.replace("_", " ").capitalize() + ".")
        result = self._analyze("", mode, None, None, coverage)
        result["reason_codes"] = [reason]
        result["timings_ms"]["total"] = round((perf_counter() - started) * 1000, 2)
        return result
