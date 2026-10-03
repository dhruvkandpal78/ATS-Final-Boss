"""Offline parity and rejection tests for the data-only linear artifact."""

from copy import deepcopy
import json

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from src.core.linear_artifacts import (
    FEATURE_ORDER,
    BinaryLinearClassifier,
    FrozenStandardScaler,
    export_linear_artifacts,
    load_linear_artifacts,
    save_linear_artifacts,
)


def fitted_pair():
    features = pd.DataFrame([
        [0.05, 0.1, 0.15], [0.1, 0.0, 0.25], [0.2, 0.1, 0.2],
        [0.8, 0.7, 0.9], [0.9, 0.85, 0.75], [0.7, 0.95, 0.8],
    ], columns=FEATURE_ORDER)
    labels = [0, 0, 0, 1, 1, 1]
    scaler = StandardScaler().fit(features)
    model = LogisticRegression(random_state=42).fit(scaler.transform(features), labels)
    return features, model, scaler


def sample_payload():
    _, model, scaler = fitted_pair()
    return export_linear_artifacts(model, scaler)


def test_export_load_matches_fitted_sklearn(tmp_path):
    features, model, scaler = fitted_pair()
    path = tmp_path / "linear_model.json"
    save_linear_artifacts(model, scaler, path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["feature_order"] == list(FEATURE_ORDER)
    loaded_model, loaded_scaler = load_linear_artifacts(path)
    byte_model, byte_scaler = load_linear_artifacts(path.read_bytes())
    transformed = loaded_scaler.transform(features)
    np.testing.assert_allclose(transformed, scaler.transform(features), rtol=0, atol=1e-12)
    np.testing.assert_allclose(loaded_model.predict_proba(transformed),
                               model.predict_proba(scaler.transform(features)), rtol=0, atol=1e-12)
    np.testing.assert_array_equal(loaded_model.predict(transformed),
                                  model.predict(scaler.transform(features)))
    np.testing.assert_allclose(byte_model.predict_proba(byte_scaler.transform(features)),
                               loaded_model.predict_proba(transformed), rtol=0, atol=0)
    assert loaded_model.classes_.tolist() == [0, 1]
    assert loaded_model.n_features_in_ == loaded_scaler.n_features_in_ == 3


def test_save_does_not_overwrite(tmp_path):
    _, model, scaler = fitted_pair()
    path = tmp_path / "linear_model.json"
    save_linear_artifacts(model, scaler, path)
    original = path.read_bytes()
    with pytest.raises(FileExistsError):
        save_linear_artifacts(model, scaler, path)
    assert path.read_bytes() == original


@pytest.mark.parametrize("change", [
    lambda p: p.update(extra=True),
    lambda p: p.pop("kind"),
    lambda p: p.update(feature_order=list(reversed(p["feature_order"]))),
    lambda p: p["model"].update(classes=[False, 1]),
    lambda p: p["model"].update(classes=[1, 0]),
    lambda p: p["model"].update(coef=[0.1, 0.2]),
    lambda p: p["model"].update(intercept=float("nan")),
    lambda p: p["model"].update(intercept=1e30),
    lambda p: p["scaler"].update(mean=[0.0, float("inf"), 0.0]),
    lambda p: p["scaler"].update(scale=[1.0, 0.0, 1.0]),
    lambda p: p["scaler"].update(scale=[1.0, -1.0, 1.0]),
    lambda p: p["model"].update(unexpected=True),
])
def test_closed_schema_rejects_bad_payload(change):
    payload = deepcopy(sample_payload())
    change(payload)
    with pytest.raises(ValueError):
        load_linear_artifacts(payload)


def test_strict_json_rejects_duplicate_nonfinite_and_oversized(tmp_path):
    payload = sample_payload()
    encoded = json.dumps(payload)
    cases = [
        encoded.replace('"kind":', '"kind":"duplicate","kind":', 1),
        encoded.replace('"intercept":', '"intercept":NaN,"duplicate":', 1),
        " " * (16 * 1024 + 1),
    ]
    for index, case in enumerate(cases):
        path = tmp_path / f"malformed-{index}.json"
        path.write_text(case, encoding="utf-8")
        with pytest.raises(ValueError):
            load_linear_artifacts(path)
        with pytest.raises(ValueError):
            load_linear_artifacts(case.encode("utf-8"))


def test_runtime_rejects_wrong_order_nonfinite_and_unbounded_input():
    features, model, scaler = fitted_pair()
    loaded_model, loaded_scaler = load_linear_artifacts(export_linear_artifacts(model, scaler))
    with pytest.raises(ValueError, match="out of order"):
        loaded_scaler.transform(features[list(reversed(FEATURE_ORDER))])
    with pytest.raises(ValueError):
        loaded_scaler.transform([[float("nan"), 0.0, 0.0]])
    with pytest.raises(ValueError):
        loaded_model.predict_proba([[float("inf"), 0.0, 0.0]])
    with pytest.raises(ValueError):
        loaded_scaler.transform([[True, False, True]])
    with pytest.raises(ValueError):
        loaded_model.predict([[1e20, 0.0, 0.0]])


def test_transformed_and_logit_bounds_fail_closed():
    scaler = FrozenStandardScaler([0.0, 0.0, 0.0], [1e-12, 1.0, 1.0])
    with pytest.raises(ValueError, match="Scaler produced"):
        scaler.transform([[10.0, 0.0, 0.0]])
    classifier = BinaryLinearClassifier([1e12, 0.0, 0.0], 0.0)
    with pytest.raises(ValueError, match="logits"):
        classifier.predict_proba([[2.0, 0.0, 0.0]])


def test_sigmoid_is_stable_for_extreme_valid_logits():
    classifier = BinaryLinearClassifier([1000.0, 0.0, 0.0], 0.0)
    probability = classifier.predict_proba([[1.0, 0.0, 0.0], [-1.0, 0.0, 0.0]])
    assert np.isfinite(probability).all()
    np.testing.assert_allclose(probability.sum(axis=1), [1.0, 1.0])
    np.testing.assert_array_equal(classifier.predict([[1.0, 0.0, 0.0], [-1.0, 0.0, 0.0]]), [1, 0])


def test_logit_zero_tie_predicts_class_zero_like_sklearn():
    classifier = BinaryLinearClassifier([0.0, 0.0, 0.0], 0.0)
    np.testing.assert_allclose(classifier.predict_proba([[0.0, 0.0, 0.0]]), [[0.5, 0.5]])
    np.testing.assert_array_equal(classifier.predict([[0.0, 0.0, 0.0]]), [0])


def test_export_requires_fitted_exact_types_and_feature_order():
    features, model, scaler = fitted_pair()
    with pytest.raises(ValueError, match="fitted"):
        export_linear_artifacts(LogisticRegression(), scaler)
    with pytest.raises(ValueError, match="fitted"):
        export_linear_artifacts(model, StandardScaler())
    with pytest.raises(ValueError):
        export_linear_artifacts(model, object())
    wrong_order = StandardScaler().fit(features[list(reversed(FEATURE_ORDER))])
    with pytest.raises(ValueError, match="feature order"):
        export_linear_artifacts(model, wrong_order)
    no_intercept = LogisticRegression(fit_intercept=False).fit(
        scaler.transform(features), [0, 0, 0, 1, 1, 1])
    with pytest.raises(ValueError, match="intercept"):
        export_linear_artifacts(no_intercept, scaler)


def test_huge_integer_json_parameter_fails_as_bounded_value_error():
    import json
    from src.core.linear_artifacts import load_linear_artifacts
    payload = {"schema_version":"1.0","kind":"binary_logistic_standard_scaler",
               "feature_order":["Module_A_Score","Module_B_Score","Module_C_Score"],
               "model":{"classes":[0,1],"coef":[1,1,1],"intercept":10**1000},
               "scaler":{"mean":[0,0,0],"scale":[1,1,1]}}
    with pytest.raises(ValueError, match="finite and bounded"):
        load_linear_artifacts(json.dumps(payload).encode())
