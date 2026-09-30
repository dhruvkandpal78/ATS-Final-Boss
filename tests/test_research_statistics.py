"""Statistical contract checks using synthetic examples, never held-out data."""

from collections import Counter
import math

import numpy as np
import pytest

from src.evaluation.statistics import (
    binary_confusion_metrics, iter_source_group_bootstrap_indices,
    source_group_bootstrap, wilson_interval, zero_event_upper_bound,
)


def test_known_confusion_counts_and_explicit_denominators():
    # A hand-counted eight-row example: three TP, two FP, two TN, one FN.
    result = binary_confusion_metrics([1, 1, 1, 1, 0, 0, 0, 0],
                                      [1, 1, 1, 0, 1, 1, 0, 0])
    assert (result["TP"], result["FP"], result["TN"], result["FN"], result["N"]) == (3, 2, 2, 1, 8)
    assert result["Precision"] == 0.6
    assert result["Recall"] == 0.75
    assert result["False-positive rate"] == 0.5
    assert result["F1"] == pytest.approx(2 / 3)
    assert result["denominators"] == {"Precision": 5, "Recall": 4,
                                      "False-positive rate": 4, "F1": 9}


def test_wilson_matches_published_fair_coin_example_and_boundary_values():
    # Standard 95% Wilson interval for 50 successes in 100 trials.
    assert wilson_interval(50, 100) == pytest.approx([0.40383153, 0.59616847], abs=1e-8)
    assert wilson_interval(0, 100) == pytest.approx([0, 0.03699350], abs=1e-8)
    assert wilson_interval(100, 100) == pytest.approx([0.96300650, 1], abs=1e-8)
    assert wilson_interval(0, 0) is None


def test_zero_event_upper_is_one_sided_exact_bound():
    upper = zero_event_upper_bound(100)
    assert upper == pytest.approx(0.0295130496, abs=1e-10)
    # At the upper bound the probability of zero events is alpha, not alpha/2.
    assert (1 - upper) ** 100 == pytest.approx(0.05)
    assert zero_event_upper_bound(1) == pytest.approx(0.95)
    assert zero_event_upper_bound(0) is None
    assert zero_event_upper_bound(10**12) > 0


def test_undefined_metrics_are_distinct_from_observed_zero():
    clean = binary_confusion_metrics([0, 0], [0, 0])
    assert clean["Precision"] is clean["Recall"] is clean["F1"] is None
    assert clean["False-positive rate"] == 0
    assert clean["row_wilson_intervals"]["Precision"] is None
    missed = binary_confusion_metrics([1, 1], [0, 0])
    assert missed["Precision"] is None
    assert missed["Recall"] == missed["F1"] == 0
    assert missed["False-positive rate"] is None


@pytest.mark.parametrize("labels,predictions", [([], []), ([0], [0, 1]),
    ([[0]], [[0]]), ([0, math.nan], [0, 1]), ([0, 2], [0, 1]), ([0], [0.2])])
def test_invalid_binary_inputs_fail_closed(labels, predictions):
    with pytest.raises(ValueError):
        binary_confusion_metrics(labels, predictions)


@pytest.mark.parametrize("successes,trials,confidence", [(2, 1, .95), (-1, 2, .95),
    (1, 2.5, .95), (True, 2, .95), (1, 2, 1), (1, 2, 0), (1, 2, math.nan)])
def test_invalid_interval_inputs_fail_closed(successes, trials, confidence):
    with pytest.raises(ValueError):
        wilson_interval(successes, trials, confidence)


def test_seeded_bootstrap_retains_whole_unequal_clusters_and_multiplicity():
    groups = ["a", "b", "a", "c", "b", "b"]
    first = list(iter_source_group_bootstrap_indices(groups, 60, seed=21))
    second = list(iter_source_group_bootstrap_indices(groups, 60, seed=21))
    assert all(np.array_equal(a, b) for a, b in zip(first, second))
    observed_sizes = set()
    repeated_group_seen = False
    for draw in first:
        counts = Counter(draw.tolist())
        # Every row in the same source appears the same number of times.
        assert counts[0] == counts[2]
        assert counts[1] == counts[4] == counts[5]
        assert counts[0] + counts[1] + counts[3] == 3
        observed_sizes.add(len(draw))
        repeated_group_seen |= max(counts.values()) > 1
    assert len(observed_sizes) > 1
    assert repeated_group_seen


def test_cluster_bootstrap_constant_rates_and_zero_bound_caveat():
    report = source_group_bootstrap([1, 0, 1, 0], [1, 0, 1, 0],
                                    ["a", "a", "b", "b"], n_resamples=50)
    assert report["intervals"]["Recall"] == [1, 1]
    assert report["intervals"]["False-positive rate"] == [0, 0]
    assert report["valid_draws"]["Recall"] == 50
    assert report["n_source_groups"] == 2
    # Empirical zero bootstrap bounds coexist with a strictly positive exact
    # zero-event upper bound; a degenerate bootstrap is not proof of zero risk.
    assert zero_event_upper_bound(2) > 0


def test_missing_class_draws_are_reported_and_deterministic():
    args = ([1, 0], [1, 0], ["positive", "negative"])
    result = source_group_bootstrap(*args, n_resamples=200, seed=5)
    assert result == source_group_bootstrap(*args, n_resamples=200, seed=5)
    assert 0 < result["undefined_draws"]["Recall"] < 200
    assert 0 < result["undefined_draws"]["False-positive rate"] < 200
    for metric in result["intervals"]:
        assert result["valid_draws"][metric] + result["undefined_draws"][metric] == 200


def test_one_source_has_no_resampling_uncertainty_estimate():
    result = source_group_bootstrap([0, 1], [0, 1], ["a", "a"], n_resamples=10)
    assert all(value is None for value in result["intervals"].values())


@pytest.mark.parametrize("groups", [["a"], ["a", None], ["a", math.nan], ["a", ""]])
def test_source_group_length_and_missing_values_are_rejected(groups):
    with pytest.raises(ValueError):
        source_group_bootstrap([0, 1], [0, 1], groups, n_resamples=10)
