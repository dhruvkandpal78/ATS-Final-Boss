"""Bounded PDF trace heuristics, with explicit capability limitations."""
import fitz
import math


class PDFForensicsDetector:
    def __init__(self, font_size_threshold=1.5):
        self.font_size_threshold = font_size_threshold

    def analyze_pdf(self, pdf_path):
        try:
            with fitz.open(pdf_path) as doc:
                if doc.needs_pass or len(doc) > 20:
                    return {"status": "error", "error": "Encrypted PDF or page limit exceeded."}
                return self._analyze_document(doc)
        except Exception:
            return {"status": "error", "error": "PDF structural analysis failed."}

    def _analyze_document(self, doc):
        anomalies = {key: 0 for key in ("invisible_render_mode", "zero_sized_bbox", "out_of_bounds",
            "hidden_ocg", "tiny_font", "background_color_match", "total_flagged_spans")}
        anomalies["findings"] = []
        limitations = ["Image overlap and background colors are heuristics, not pixel-level visibility proof.",
                      "Clipping paths, occluding objects and complex optional-content membership are not fully resolved."]
        # get_texttrace reports layer names; get_ocgs is keyed by xref and exposes 'on'.
        ocgs = doc.get_ocgs()
        hidden_layers = {item.get("name") for item in ocgs.values() if item.get("on") is False}
        if hidden_layers:
            limitations.append("Disabled optional-content groups are present; their hidden content may be omitted by text extraction.")
        trace_count = 0
        for page_num, page in enumerate(doc):
            image_rects = [fitz.Rect(img["bbox"]) for img in page.get_image_info()]
            backgrounds = []
            for drawing in page.get_drawings():
                fill = drawing.get("fill")
                if drawing.get("type") in ("f", "fs") and fill and min(fill) < 0.8:
                    backgrounds.append(fitz.Rect(drawing["rect"]))
            traces = page.get_texttrace()
            for trace in traces:
                trace_count += 1
                if trace_count > 20_000:
                    return {"status": "error", "error": "PDF trace limit exceeded."}
                flags = self._analyze_trace(trace, page.rect, image_rects, backgrounds, hidden_layers)
                active = [key for key, value in flags.items() if value]
                if not active:
                    continue
                anomalies["total_flagged_spans"] += 1
                for key in active:
                    anomalies[key] += 1
                if len(anomalies["findings"]) < 200:
                    anomalies["findings"].append({"page": page_num + 1, "rect": list(trace["bbox"]), "flags": active})
        anomalies["hidden_ocg_groups"] = len(hidden_layers)
        anomalies["findings_omitted"] = max(0, anomalies["total_flagged_spans"] - len(anomalies["findings"]))
        return {"status": "success", "anomaly_score": min(1.0, anomalies["total_flagged_spans"] / 10),
                "details": anomalies, "limitations": limitations,
                "capabilities": {"text_traces": True, "optional_content_complete": False, "pixel_visibility": False}}

    @staticmethod
    def _covered(bbox, regions):
        # A tiny overlap should not exempt an otherwise invisible text span.
        return any(region.contains(bbox) for region in regions)

    def _analyze_trace(self, trace, page_rect, image_rects, dark_bg_rects, hidden_ocgs):
        flags = {key: False for key in ("invisible_render_mode", "zero_sized_bbox", "out_of_bounds",
                                      "hidden_ocg", "tiny_font", "background_color_match")}
        coords = trace.get("bbox")
        if not coords or len(coords) != 4 or not all(math.isfinite(float(value)) for value in coords):
            raise ValueError("Missing or invalid text bounding box")
        bbox = fitz.Rect(coords)
        flags["zero_sized_bbox"] = bbox.width * bbox.height <= 0.01
        flags["out_of_bounds"] = bbox.x1 <= page_rect.x0 or bbox.y1 <= page_rect.y0 or bbox.x0 >= page_rect.x1 or bbox.y0 >= page_rect.y1
        flags["tiny_font"] = trace.get("size", 10) <= self.font_size_threshold
        over_image = self._covered(bbox, image_rects)
        if trace.get("type") == 3 or trace.get("opacity", 1) == 0:
            flags["invisible_render_mode"] = not over_image
        color = trace.get("color")
        if isinstance(color, (tuple, list)) and len(color) in (1, 3) and all(channel > 0.95 for channel in color):
            flags["background_color_match"] = not (over_image or self._covered(bbox, dark_bg_rects))
        flags["hidden_ocg"] = bool(trace.get("layer") and trace["layer"] in hidden_ocgs)
        return flags
