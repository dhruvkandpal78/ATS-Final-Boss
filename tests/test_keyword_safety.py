from src.modules.module_a import KeywordDensityDetector


def test_aliases_do_not_rewrite_partial_words():
    detector = KeywordDensityDetector()
    assert detector._calculate_metrics('HTML XML mlops workflow')['density'] == 0
    assert detector._calculate_metrics('ML NLP K8S')['density'] > 0


def test_keyword_positions_are_whitespace_invariant():
    detector = KeywordDensityDetector()
    words = 'python java sql aws docker experience delivered projects reliably'.split()
    space = detector._calculate_metrics(' '.join(words))
    assert detector._calculate_metrics('\n'.join(words)) == space
    assert detector._calculate_metrics('\t'.join(words)) == space


def test_multiword_alias_accepts_variable_whitespace():
    detector = KeywordDensityDetector()
    assert detector._calculate_metrics('amazon\tweb\nservices') == detector._calculate_metrics('aws')


def test_duplicate_custom_keywords_are_not_double_counted():
    detector = KeywordDensityDetector(['python', 'python'])
    assert detector._calculate_metrics('python development')['density'] == 0.5
