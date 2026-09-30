"""Descriptive uncertainty for supplied predictions; this module opens no data.

Row Wilson intervals assume independent Bernoulli observations. For related PDF
variants use source-group resampling as the primary interval; a source identifier
does not establish independence of people. Neither method covers label error,
selection bias, policy tuning, or deployment shift.
"""

from numbers import Integral
from statistics import NormalDist

import numpy as np


def _confidence(value):
    if not np.isfinite(value) or not 0 < value < 1:
        raise ValueError("confidence must be finite and strictly between 0 and 1")
    return float(value)


def _count(value, name):
    if isinstance(value, bool) or not isinstance(value, Integral) or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    return int(value)


def wilson_interval(successes, trials, confidence=0.95):
    """Two-sided Wilson score bounds, or None when the denominator is zero."""
    confidence = _confidence(confidence)
    successes, trials = _count(successes, "successes"), _count(trials, "trials")
    if successes > trials:
        raise ValueError("successes must not exceed trials")
    if trials == 0:
        return None
    z = NormalDist().inv_cdf(0.5 + confidence / 2)
    p = successes / trials
    divisor = 1 + z * z / trials
    center = (p + z * z / (2 * trials)) / divisor
    radius = z * np.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / divisor
    return [max(0.0, float(center - radius)), min(1.0, float(center + radius))]


def zero_event_upper_bound(trials, confidence=0.95):
    """Exact one-sided binomial upper bound for zero observed events.

    Requires independent trials; callers must identify the unit of observation.
    No trials yield None, not a claim of zero risk. This bound is applicable only
    when the observed event count is zero.
    """
    confidence = _confidence(confidence)
    trials = _count(trials, "trials")
    return float(-np.expm1(np.log1p(-confidence) / trials)) if trials else None


def _binary_vectors(y_true, y_pred):
    actual, predicted = np.asarray(y_true), np.asarray(y_pred)
    if actual.ndim != 1 or predicted.ndim != 1 or actual.size != predicted.size:
        raise ValueError("labels and predictions must be equal-length one-dimensional vectors")
    if actual.size == 0:
        raise ValueError("at least one labeled row is required")
    if not np.all(np.isin(actual, [0, 1])) or not np.all(np.isin(predicted, [0, 1])):
        raise ValueError("labels and predictions must contain only binary 0/1 values")
    return actual.astype(int), predicted.astype(int)


def binary_confusion_metrics(y_true, y_pred, confidence=0.95):
    """Counts, rates, explicit denominators, and descriptive row Wilson bounds.

    Undefined rates remain None. F1 is undefined if 2TP+FP+FN is zero;
    it is zero when that denominator is positive but TP is zero.
    """
    actual, predicted = _binary_vectors(y_true, y_pred)
    tp = int(np.sum((actual == 1) & (predicted == 1)))
    fp = int(np.sum((actual == 0) & (predicted == 1)))
    tn = int(np.sum((actual == 0) & (predicted == 0)))
    fn = int(np.sum((actual == 1) & (predicted == 0)))
    numerators = {"Precision": tp, "Recall": tp, "False-positive rate": fp, "F1": 2 * tp}
    denominators = {"Precision": tp + fp, "Recall": tp + fn,
                    "False-positive rate": fp + tn, "F1": 2 * tp + fp + fn}
    result = {"N": int(actual.size), "TP": tp, "FP": fp, "TN": tn, "FN": fn}
    result.update({name: numerators[name] / total if total else None
                   for name, total in denominators.items()})
    result["denominators"] = denominators
    result["row_wilson_intervals"] = {
        name: wilson_interval(numerators[name], denominators[name], confidence)
        for name in ("Precision", "Recall", "False-positive rate")}
    result["confidence"] = _confidence(confidence)
    return result


def _group_indices(groups):
    values = np.asarray(groups, dtype=object)
    if values.ndim != 1 or not values.size:
        raise ValueError("groups must be a nonempty one-dimensional vector")
    members = {}
    for index, value in enumerate(values):
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValueError("every row needs a nonmissing source group")
        try:
            if value != value:
                raise ValueError("every row needs a nonmissing source group")
            members.setdefault(value, []).append(index)
        except TypeError as error:
            raise ValueError("source groups must be hashable scalar identifiers") from error
    return [np.asarray(indices, dtype=int) for indices in members.values()]


def iter_source_group_bootstrap_indices(groups, n_resamples=1000, seed=42):
    """Sample G groups with replacement, retaining every row of each draw.

    A repeated group retains all its rows again. Group sizes may differ, so the
    number of rows in a draw can vary. First-occurrence group order is retained.
    """
    n_resamples = _count(n_resamples, "n_resamples")
    if not n_resamples:
        raise ValueError("n_resamples must be positive")
    members = _group_indices(groups)
    rng = np.random.default_rng(seed)
    for _ in range(n_resamples):
        selected = rng.integers(0, len(members), size=len(members))
        yield np.concatenate([members[index] for index in selected])


def source_group_bootstrap(y_true, y_pred, groups, n_resamples=1000, seed=42,
                           confidence=0.95):
    """Percentile intervals for row-weighted metrics from source-group draws.

    Missing-class or no-predicted-positive draws have undefined rates and are
    omitted per metric with their counts reported. Such intervals are conditional
    on defined draws and can be unreliable when many draws are omitted. Fewer
    than two source groups cannot provide a resampling uncertainty estimate.
    """
    actual, predicted = _binary_vectors(y_true, y_pred)
    confidence = _confidence(confidence)
    members = _group_indices(groups)
    if sum(len(indices) for indices in members) != actual.size:
        raise ValueError("every label needs one source group")
    n_resamples = _count(n_resamples, "n_resamples")
    if not n_resamples:
        raise ValueError("n_resamples must be positive")
    names = ("Precision", "Recall", "F1", "False-positive rate")
    samples = {name: [] for name in names}
    for indices in iter_source_group_bootstrap_indices(groups, n_resamples, seed):
        subset = binary_confusion_metrics(actual[indices], predicted[indices], confidence)
        for name in names:
            if subset[name] is not None:
                samples[name].append(subset[name])
    tail = 100 * (1 - confidence) / 2
    return {
        "intervals": {name: ([float(value) for value in np.percentile(values, [tail, 100 - tail])]
                             if values and len(members) >= 2 else None)
                      for name, values in samples.items()},
        "valid_draws": {name: len(values) for name, values in samples.items()},
        "undefined_draws": {name: n_resamples - len(values) for name, values in samples.items()},
        "n_source_groups": len(members), "n_resamples": n_resamples,
        "seed": seed, "confidence": confidence,
        "method": "percentile source-group bootstrap; row-weighted metrics",
        "assumptions": "Independent source groups; source IDs do not establish person independence. "
                       "Intervals omit undefined draws and do not cover label uncertainty or deployment shift.",
    }
