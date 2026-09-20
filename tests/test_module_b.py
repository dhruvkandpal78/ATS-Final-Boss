import fitz
import os
from src.modules.module_b import PDFForensicsDetector

def test_module_b_fixtures(tmp_path):
    doc = fitz.open()
    page = doc.new_page()
    
    # 1. Normal text
    page.insert_text((50, 50), "Normal Text", fontsize=12, color=(0,0,0))
    
    # 2. Tiny text
    page.insert_text((50, 100), "Tiny Text", fontsize=1.0, color=(0,0,0))
    
    # 3. Out of bounds
    page.insert_text((-50, -50), "Out of bounds", fontsize=12)
    
    # 4. Invisible render mode
    page.insert_text((50, 150), "Invisible Text", fontsize=12, render_mode=3)
    
    # 5. White text on white background
    page.insert_text((50, 200), "White Text", fontsize=12, color=(1,1,1))
    
    # 6. Benign white text on dark background
    page.draw_rect(fitz.Rect(40, 240, 150, 280), color=(0,0,0), fill=(0,0,0))
    page.insert_text((50, 260), "Benign White Text", fontsize=12, color=(1,1,1))
    
    pdf_path = str(tmp_path / "test_fixtures.pdf")
    doc.save(pdf_path)
    doc.close()
    
    detector = PDFForensicsDetector()
    res = detector.analyze_pdf(pdf_path)
    
    details = res['details']
    assert details['tiny_font'] == 1, f"Expected 1 tiny_font, got {details['tiny_font']}"
    assert details['out_of_bounds'] == 1, f"Expected 1 out_of_bounds, got {details['out_of_bounds']}"
    assert details['invisible_render_mode'] == 1, f"Expected 1 invisible_render_mode, got {details['invisible_render_mode']}"
    assert details['background_color_match'] == 1, f"Expected 1 background_color_match, got {details['background_color_match']}"
    
    print("All module_b fixtures passed!")

