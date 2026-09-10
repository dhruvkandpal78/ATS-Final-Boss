import fitz  # PyMuPDF
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PDFForensicsDetector:
    """
    A structural anomaly detector (Module B) that interrogates the PDF byte-layer
    to identify adversarial text injections such as keyword stuffing and hidden prompts.
    """
    
    def __init__(self, font_size_threshold: float = 1.5, color_tolerance: float = 0.05):
        """
        :param font_size_threshold: Font size (in pts) below which text is flagged as hidden.
        :param color_tolerance: Tolerance for matching text color to background color.
        """
        self.font_size_threshold = font_size_threshold
        self.color_tolerance = color_tolerance

    def analyze_pdf(self, pdf_path: str) -> dict:
        """
        Performs deep structural forensics on a PDF document.
        """
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
            "total_flagged_spans": 0
        }

        # Check OCGs (Optional Content Groups) / Layers
        hidden_ocgs = self._get_hidden_ocgs(doc)

        for page_num in range(len(doc)):
            page = doc[page_num]
            page_rect = page.rect
            
            # Extract dictionary dict to get detailed text block info
            text_dict = page.get_text("dict")
            blocks = text_dict.get("blocks", [])
            
            for block in blocks:
                if "lines" not in block:
                    continue  # Skip image blocks
                for line in block["lines"]:
                    for span in line["spans"]:
                        flags = self._analyze_span(span, page_rect, hidden_ocgs)
                        
                        if any(flags.values()):
                            anomalies["total_flagged_spans"] += 1
                            for key, flagged in flags.items():
                                if flagged:
                                    anomalies[key] += 1

        doc.close()
        
        # Calculate a normalized structural anomaly score (0.0 to 1.0)
        # In a real pipeline, this would be calibrated on the validation set.
        score = min(1.0, anomalies["total_flagged_spans"] / 10.0) 
        
        return {
            "status": "success",
            "anomaly_score": score,
            "details": anomalies
        }

    def _get_hidden_ocgs(self, doc: fitz.Document) -> set:
        """
        PLACEHOLDER: Identifies Optional Content Groups (OCGs) that have
        visibility explicitly set to OFF.

        NOTE: This method currently always returns an empty set — OCG-based
        hidden-text detection is NOT yet implemented. A résumé hidden via
        Optional Content Groups will not be flagged by this check today.
        A real implementation would parse the /OCProperties catalog entry
        (/OFF array) and check span OCG membership against that set.
        See DESIGN_RATIONALE.md "Honest limitations" for details.
        """
        hidden_ocgs = set()
        try:
            ocg_list = doc.get_ocgs()
            for ocg in ocg_list:
                # TODO: implement real OCG visibility check via
                # doc.get_layer(config=0) / /OCProperties /OFF array parsing
                pass 
        except Exception:
            pass
        return hidden_ocgs

    def _analyze_span(self, span: dict, page_rect: fitz.Rect, hidden_ocgs: set) -> dict:
        """
        Analyzes a single text span for structural anomalies.
        """
        flags = {
            "invisible_render_mode": False,
            "zero_sized_bbox": False,
            "out_of_bounds": False,
            "hidden_ocg": False,
            "tiny_font": False,
            "background_color_match": False
        }
        
        bbox = fitz.Rect(span["bbox"])
        
        # 1. Zero-sized Bounding Box
        if bbox.width <= 0 or bbox.height <= 0:
            flags["zero_sized_bbox"] = True
            
        # 2. Out of Bounds (Negative coordinates or outside page dimensions)
        if (bbox.x0 < 0 or bbox.y0 < 0 or 
            bbox.x1 > page_rect.width or bbox.y1 > page_rect.height):
            flags["out_of_bounds"] = True
            
        # 3. Tiny Font Size (e.g., 1pt or less)
        if span["size"] <= self.font_size_threshold:
            flags["tiny_font"] = True
            
        # 4. Text Rendering Mode 3 (Invisible Text)
        # Note: PyMuPDF span dictionary does not natively expose render mode in get_text("dict").
        # This requires parsing the raw PDF stream (TJ/Tj operators) or using fitz.Trace.
        # This is a placeholder flag for where that logic integrates.
        # e.g., if '3 Tr' is detected in the stream for this bounding box.
        
        # 5. Background Color Match (White text on white background)
        # simplified check: assuming page background is white (1,1,1) or (255,255,255)
        # span['color'] is typically an integer representing sRGB.
        srgb_color = span.get("color")
        if srgb_color == 16777215: # 0xFFFFFF (White)
            flags["background_color_match"] = True
            
        return flags

if __name__ == "__main__":
    # Example usage:
    detector = PDFForensicsDetector()
    # result = detector.analyze_pdf("sample_resume.pdf")
    # print(result)
