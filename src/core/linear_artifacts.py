"""Bounded, data-only inference for a three-feature binary linear candidate.

This format deliberately supports only a fitted sklearn LogisticRegression
following a fitted StandardScaler. It stores no Python object graph and loads
no pickle. It does not establish calibration, provenance, or trust by itself.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
import stat
from typing import Any, Mapping

import numpy as np


FEATURE_ORDER = ("Module_A_Score", "Module_B_Score", "Module_C_Score")
SCHEMA_VERSION = "1.0"
KIND = "binary_logistic_standard_scaler"
MAX_JSON_BYTES = 16 * 1024
MAX_ROWS = 10_000
MAX_ABS_VALUE = 1e12
MIN_SCALE = 1e-12


def _number(value: Any, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a JSON number")
    try:
        number = float(value)
    except OverflowError:
        raise ValueError(f"{name} must be finite and bounded") from None
    if not math.isfinite(number) or abs(number) > MAX_ABS_VALUE:
        raise ValueError(f"{name} must be finite and bounded")
    if positive and number < MIN_SCALE:
        raise ValueError(f"{name} must be a positive bounded scale")
    return number


def _vector(value: Any, name: str, *, positive: bool = False) -> list[float]:
    if not isinstance(value, list) or len(value) != len(FEATURE_ORDER):
        raise ValueError(f"{name} must contain exactly three numbers")
    return [_number(item, f"{name}[{index}]", positive=positive)
            for index, item in enumerate(value)]


def _validated(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict) or set(payload) != {
        "schema_version", "kind", "feature_order", "model", "scaler"
    }:
        raise ValueError("Linear artifact has an unknown or missing top-level field")
    if payload["schema_version"] != SCHEMA_VERSION or payload["kind"] != KIND:
        raise ValueError("Linear artifact schema or estimator kind is unsupported")
    if payload["feature_order"] != list(FEATURE_ORDER):
        raise ValueError("Linear artifact feature order does not match deployment")
    model = payload["model"]
    scaler = payload["scaler"]
    if not isinstance(model, dict) or set(model) != {"classes", "coef", "intercept"}:
        raise ValueError("Linear model fields are invalid")
    if not isinstance(scaler, dict) or set(scaler) != {"mean", "scale"}:
        raise ValueError("Linear scaler fields are invalid")
    classes = model["classes"]
    if (not isinstance(classes, list) or len(classes) != 2 or
            any(type(value) is not int for value in classes) or classes != [0, 1]):
        raise ValueError("Linear model requires integer classes [0, 1]")
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND,
        "feature_order": list(FEATURE_ORDER),
        "model": {
            "classes": [0, 1],
            "coef": _vector(model["coef"], "model.coef"),
            "intercept": _number(model["intercept"], "model.intercept"),
        },
        "scaler": {
            "mean": _vector(scaler["mean"], "scaler.mean"),
            "scale": _vector(scaler["scale"], "scaler.scale", positive=True),
        },
    }


def _matrix(values: Any, label: str) -> np.ndarray:
    if hasattr(values, "columns") and list(values.columns) != list(FEATURE_ORDER):
        raise ValueError(f"{label} feature columns are missing or out of order")
    raw = np.asarray(values)
    if raw.ndim != 2 or raw.shape[1] != len(FEATURE_ORDER) or not 0 < raw.shape[0] <= MAX_ROWS:
        raise ValueError(f"{label} requires a bounded N x 3 numeric matrix")
    if raw.dtype.kind not in "iuf":
        raise ValueError(f"{label} requires numeric, non-boolean values")
    matrix = raw.astype(np.float64, copy=False)
    if not np.isfinite(matrix).all() or np.abs(matrix).max() > MAX_ABS_VALUE:
        raise ValueError(f"{label} contains nonfinite or unbounded values")
    return matrix


class FrozenStandardScaler:
    """The minimal ``StandardScaler.transform`` contract used by inference."""

    def __init__(self, mean: list[float], scale: list[float]):
        self.mean_ = np.asarray(mean, dtype=np.float64)
        self.scale_ = np.asarray(scale, dtype=np.float64)
        self.mean_.setflags(write=False)
        self.scale_.setflags(write=False)
        self.n_features_in_ = len(FEATURE_ORDER)
        self.feature_names_in_ = np.asarray(FEATURE_ORDER)
        self.with_mean = True
        self.with_std = True

    def transform(self, values: Any) -> np.ndarray:
        matrix = _matrix(values, "Scaler input")
        with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
            transformed = (matrix - self.mean_) / self.scale_
        if not np.isfinite(transformed).all() or np.abs(transformed).max() > MAX_ABS_VALUE:
            raise ValueError("Scaler produced nonfinite or unbounded features")
        return transformed


class BinaryLinearClassifier:
    """A read-only sklearn-like binary LogisticRegression prediction surface."""

    def __init__(self, coef: list[float], intercept: float):
        self.coef_ = np.asarray([coef], dtype=np.float64)
        self.intercept_ = np.asarray([intercept], dtype=np.float64)
        self.classes_ = np.asarray([0, 1], dtype=int)
        self.coef_.setflags(write=False)
        self.intercept_.setflags(write=False)
        self.classes_.setflags(write=False)
        self.n_features_in_ = len(FEATURE_ORDER)

    def _logits(self, values: Any) -> np.ndarray:
        matrix = _matrix(values, "Classifier input")
        with np.errstate(over="ignore", invalid="ignore"):
            logits = matrix @ self.coef_[0] + self.intercept_[0]
        if not np.isfinite(logits).all() or np.abs(logits).max() > MAX_ABS_VALUE:
            raise ValueError("Classifier produced nonfinite or unbounded logits")
        return logits

    def predict_proba(self, values: Any) -> np.ndarray:
        logits = self._logits(values)
        positive = np.empty_like(logits)
        nonnegative = logits >= 0
        positive[nonnegative] = 1.0 / (1.0 + np.exp(-logits[nonnegative]))
        exp_logits = np.exp(logits[~nonnegative])
        positive[~nonnegative] = exp_logits / (1.0 + exp_logits)
        probabilities = np.column_stack((1.0 - positive, positive))
        if not np.isfinite(probabilities).all():
            raise ValueError("Classifier produced nonfinite probabilities")
        return probabilities

    def predict(self, values: Any) -> np.ndarray:
        # sklearn's LinearClassifierMixin uses scores > 0, so a tie is class 0.
        return (self._logits(values) > 0).astype(int)


def export_linear_artifacts(model: Any, scaler: Any) -> dict[str, Any]:
    """Export only fitted, exact sklearn classes; never serialize estimators."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    if type(model) is not LogisticRegression or type(scaler) is not StandardScaler:
        raise ValueError("Only fitted sklearn LogisticRegression and StandardScaler are exportable")
    if not all(hasattr(model, name) for name in ("n_features_in_", "classes_", "coef_", "intercept_")):
        raise ValueError("LogisticRegression must be fitted before export")
    if not all(hasattr(scaler, name) for name in ("n_features_in_", "mean_", "scale_")):
        raise ValueError("StandardScaler must be fitted before export")
    if model.n_features_in_ != 3 or scaler.n_features_in_ != 3:
        raise ValueError("Export requires exactly three fitted features")
    if not model.fit_intercept or getattr(model, "multi_class", "auto") == "multinomial":
        raise ValueError("Export requires an intercept and binary one-vs-rest logistic inference")
    if not scaler.with_mean or not scaler.with_std:
        raise ValueError("Export requires centered and scaled StandardScaler")
    for name, fitted in (("model", model), ("scaler", scaler)):
        feature_names = getattr(fitted, "feature_names_in_", None)
        if feature_names is not None and list(feature_names) != list(FEATURE_ORDER):
            raise ValueError(f"{name} feature order does not match deployment")
    if np.asarray(model.coef_).shape != (1, 3) or np.asarray(model.intercept_).shape != (1,):
        raise ValueError("Export requires a binary linear coefficient shape")
    payload = {
        "schema_version": SCHEMA_VERSION, "kind": KIND,
        "feature_order": list(FEATURE_ORDER),
        "model": {
            "classes": np.asarray(model.classes_).tolist(),
            "coef": np.asarray(model.coef_[0]).tolist(),
            "intercept": float(model.intercept_[0]),
        },
        "scaler": {
            "mean": np.asarray(scaler.mean_).tolist(),
            "scale": np.asarray(scaler.scale_).tolist(),
        },
    }
    normalized = _validated(payload)
    # A small fixed probe detects incompatible prediction semantics before
    # freezing an artifact; solver and regularization only affect coefficients.
    probe = np.asarray([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0],
                        [0.0, 1.0, 0.0], [0.0, 0.0, 1.0], [-1.0, -1.0, -1.0]])
    frozen = BinaryLinearClassifier(normalized["model"]["coef"], normalized["model"]["intercept"])
    try:
        probability_match = np.allclose(frozen.predict_proba(probe), model.predict_proba(probe),
                                        rtol=0, atol=1e-12)
        decision_match = np.array_equal(frozen.predict(probe), model.predict(probe))
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("Fitted logistic estimator is incompatible with the linear contract") from exc
    if not probability_match or not decision_match:
        raise ValueError("Fitted logistic estimator does not match the linear inference contract")
    return normalized


def save_linear_artifacts(model: Any, scaler: Any, path: os.PathLike | str) -> None:
    """Create a new bounded JSON file; never overwrite an existing artifact."""
    payload = export_linear_artifacts(model, scaler)
    encoded = (json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    if len(encoded) > MAX_JSON_BYTES:
        raise ValueError("Linear artifact exceeds its size bound")
    with Path(path).open("xb") as handle:
        handle.write(encoded)


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Linear artifact contains duplicate JSON keys")
        result[key] = value
    return result


def _invalid_constant(value: str) -> None:
    raise ValueError("Linear artifact contains a nonfinite JSON constant")


def load_linear_artifacts(source: os.PathLike | str | bytes | Mapping[str, Any]) -> tuple[BinaryLinearClassifier, FrozenStandardScaler]:
    """Load strictly validated JSON data into small inference-only adapters."""
    if isinstance(source, Mapping):
        payload = dict(source)
    elif isinstance(source, bytes):
        if len(source) > MAX_JSON_BYTES:
            raise ValueError("Linear artifact exceeds its size bound")
        raw = source
    else:
        path = Path(source)
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode) or info.st_size > MAX_JSON_BYTES:
            raise ValueError("Linear artifact must be a bounded regular JSON file")
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        with os.fdopen(os.open(path, flags), "rb") as handle:
            opened = os.fstat(handle.fileno())
            if not stat.S_ISREG(opened.st_mode) or opened.st_size > MAX_JSON_BYTES:
                raise ValueError("Linear artifact changed or exceeded its size bound")
            raw = handle.read(MAX_JSON_BYTES + 1)
            if len(raw) != opened.st_size or len(raw) > MAX_JSON_BYTES:
                raise ValueError("Linear artifact changed or exceeded its size bound")
    if not isinstance(source, Mapping):
        try:
            payload = json.loads(raw, object_pairs_hook=_unique_pairs,
                                 parse_constant=_invalid_constant)
        except (UnicodeError, ValueError, RecursionError):
            raise ValueError("Linear artifact is not strict bounded JSON") from None
    normalized = _validated(payload)
    return (
        BinaryLinearClassifier(normalized["model"]["coef"], normalized["model"]["intercept"]),
        FrozenStandardScaler(normalized["scaler"]["mean"], normalized["scaler"]["scale"]),
    )
