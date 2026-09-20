import fitz  # PyMuPDF
import logging
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PDFForensicsDetector:
    def __init__(self, font_size_threshold: float = 1.5):
        self.font_size_threshold = font_size_threshold

    def analyze_pdf(self, pdf_path: str) -> dict:
        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            logger.error(f"Failed to open PDF {pdf_path}: {e}")
            return {"status": "error", "error": str(e)}

        anomalies = {
            "invisible_render_mode": 0,
            "zero_sized_bbox": 0,
            "out_of_bounds": 0,
            "hidden_ocg": 0,
            "tiny_font": 0,
            "background_color_match": 0,
            "total_flagged_spans": 0,
            "findings": []
        }

        # OCG handling (just record if there are hidden OCGs globally for now, or check items)
        hidden_ocgs = set()
        try:
            ocgs = doc.get_ocgs()
            for ocg in ocgs:
                if doc.get_ocg_pi(ocg) and doc.get_ocg_pi(ocg).get('state') == 'OFF':
                    hidden_ocgs.add(ocg)
        except Exception:
            pass

        for page_num in range(len(doc)):
            page = doc[page_num]
            page_rect = page.rect
            
            # Get images to check for OCR overlays
            images = page.get_image_info()
            image_rects = [fitz.Rect(img['bbox']) for img in images]
            
            # Get drawings to check background context
            drawings = page.get_drawings()
            dark_bg_rects = []
            for d in drawings:
                # If filled with a color that is not white
                if d.get('type') == 'f' or d.get('type') == 'fs':
                    fill_color = d.get('fill')
                    if fill_color and not (fill_color[0] > 0.95 and fill_color[1] > 0.95 and fill_color[2] > 0.95):
                        dark_bg_rects.append(d['rect'])

            try:
                traces = page.get_texttrace()
            except AttributeError:
                # Fallback for older PyMuPDF or just return empty
                traces = []

            for trace in traces:
                flags = self._analyze_trace(trace, page_rect, image_rects, dark_bg_rects, hidden_ocgs)
                
                if any(flags.values()):
                    anomalies["total_flagged_spans"] += 1
                    active_flags = [k for k, v in flags.items() if v]
                    for key in active_flags:
                        anomalies[key] += 1
                    
                    # Convert chars to string for explanation context
                    chars = trace.get('chars', [])
                    text = "".join(chr(c[0]) for c in chars if len(c) > 0 and isinstance(c[0], int))
                    if len(text) > 20: text = text[:17] + "..."
                    
                    anomalies["findings"].append({
                        "page": page_num + 1,
                        "rect": trace["bbox"],
                        "flags": active_flags,
                        "text": text
                    })

        doc.close()
        
        score = min(1.0, anomalies["total_flagged_spans"] / 10.0) 
        
        return {
            "status": "success",
            "anomaly_score": score,
            "details": anomalies
        }

    def _analyze_trace(self, trace: dict, page_rect: fitz.Rect, image_rects: list, dark_bg_rects: list, hidden_ocgs: set) -> dict:
        flags = {
            "invisible_render_mode": False,
            "zero_sized_bbox": False,
            "out_of_bounds": False,
            "hidden_ocg": False,
            "tiny_font": False,
            "background_color_match": False
        }
        
        bbox = fitz.Rect(trace["bbox"])
        area = bbox.width * bbox.height
        
        if area <= 0.01:
            flags["zero_sized_bbox"] = True
            
        if (bbox.x1 <= 0 or bbox.y1 <= 0 or bbox.x0 >= page_rect.width or bbox.y0 >= page_rect.height):
            flags["out_of_bounds"] = True
            
        if trace.get("size", 10) <= self.font_size_threshold:
            flags["tiny_font"] = True
            
        # Render mode 3 is invisible text
        if trace.get("type") == 3:
            # Check if it overlaps an image (OCR text)
            is_ocr = any(bbox.intersects(img_rect) for img_rect in image_rects)
            if not is_ocr:
                flags["invisible_render_mode"] = True
                
        # White text check
        color = trace.get("color")
        if color and len(color) >= 3:
            if color[0] > 0.95 and color[1] > 0.95 and color[2] > 0.95:
                # White text. Check if it's over a dark background or image
                over_image = any(bbox.intersects(img_rect) for img_rect in image_rects)
                over_dark_bg = any(bbox.intersects(bg_rect) for bg_rect in dark_bg_rects)
                
                if not (over_image or over_dark_bg):
                    flags["background_color_match"] = True
                    
        # Hidden OCG check
        layer = trace.get("layer")
        if layer and layer in hidden_ocgs:
            flags["hidden_ocg"] = True

        return flags
