import fitz
from src.modules.module_b import PDFForensicsDetector


def test_white_grayscale_and_partial_background_do_not_evade():
    detector = PDFForensicsDetector()
    trace = {'bbox': (10, 10, 100, 30), 'size': 12, 'color': (1.0,), 'type': 0}
    page = fitz.Rect(0, 0, 600, 800)
    assert detector._analyze_trace(trace, page, [], [], set())['background_color_match']
    assert detector._analyze_trace(trace, page, [], [fitz.Rect(9, 9, 11, 11)], set())['background_color_match']
    assert not detector._analyze_trace(trace, page, [], [fitz.Rect(0, 0, 200, 100)], set())['background_color_match']


def test_real_invisible_text_and_disabled_layer_metadata(tmp_path):
    path = tmp_path / 'hidden.pdf'
    with fitz.open() as doc:
        page = doc.new_page()
        page.insert_text((60, 60), 'Visible resume context.')
        page.insert_text((60, 100), 'Hidden instructions.', render_mode=3)
        layer = doc.add_ocg('Hidden text', on=False)
        page.insert_text((60, 140), 'Disabled layer content.', oc=layer)
        doc.save(path)
    result = PDFForensicsDetector().analyze_pdf(path)
    assert result['status'] == 'success'
    assert result['details']['invisible_render_mode'] >= 1
    assert result['details']['hidden_ocg_groups'] == 1
    assert result['capabilities']['optional_content_complete'] is False
    assert any('Disabled' in text for text in result['limitations'])


def test_zero_opacity_is_detected():
    trace = {'bbox': (10, 10, 100, 30), 'size': 12, 'color': (0,), 'opacity': 0}
    flags = PDFForensicsDetector()._analyze_trace(trace, fitz.Rect(0, 0, 600, 800), [], [], set())
    assert flags['invisible_render_mode']
