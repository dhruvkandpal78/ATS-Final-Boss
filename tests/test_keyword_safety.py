from src.modules.module_a import KeywordDensityDetector
import numpy as np
import pandas as pd
import pytest


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


def test_zero_threshold_does_not_manufacture_maximum_signal():
    detector = KeywordDensityDetector()
    detector.threshold = 0
    with pytest.raises(ValueError, match="positive finite"):
        detector.predict("Python developer with reporting experience")


def test_calibration_uses_clean_validation_p95_only():
    detector = KeywordDensityDetector()
    validation = pd.DataFrame({
        "text": [
            "python engineer delivered software",
            "python java engineer built software systems",
            "python java sql aws docker python java sql aws docker",
            "Experienced project manager and analyst",
        ],
        "is_adversarial": [0, 0, 1, 1],
    })
    clean_scores = np.array([detector._calculate_metrics(text)["score"] for text in validation.loc[:1, "text"]])

    threshold = detector.calibrate(validation)

    assert threshold == np.percentile(clean_scores, 95)
    assert threshold > 0
    assert detector.predict(validation.loc[0, "text"])["is_flagged"] is False


@pytest.mark.parametrize(
    "validation, message",
    [
        (pd.DataFrame({"text": ["python", "java"], "is_adversarial": [1, 1]}), "both clean and adversarial"),
        (pd.DataFrame({"text": ["python", "java"], "is_adversarial": [0, 2]}), "binary values"),
        (pd.DataFrame({"text": ["experienced analyst", "python"], "is_adversarial": [0, 1]}), "P95 threshold is not positive"),
    ],
)
def test_calibration_rejects_degenerate_or_invalid_validation(validation, message):
    detector = KeywordDensityDetector()

    with pytest.raises(ValueError, match=message):
        detector.calibrate(validation)
    assert detector.threshold is None


def test_f1_calibration_is_rejected():
    detector = KeywordDensityDetector()
    validation = pd.DataFrame({"text": ["python", "experienced analyst"], "is_adversarial": [1, 0]})

    with pytest.raises(ValueError, match="F1 calibration is not permitted"):
        detector.calibrate(validation, objective="f1")
