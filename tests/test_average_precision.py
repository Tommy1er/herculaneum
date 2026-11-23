"""Tests for herculaneum.metrics.average_precision (GLM, issue #3).

The implementation is the one imported from the GLM prototype: per-rank
precision at every reference positive, stable argsort (ties broken by index
order), ValueError when the reference has no positive. These tests pin that
contract, including the global 2D pixel ranking.
"""

import numpy as np
import pytest

from herculaneum.metrics import average_precision


def _ap_bruteforce_no_ties(score, target):
    """Independent reference, valid for tie-free scores: O(n log n) step
    interpolation with precision evaluated at group ends."""
    s = np.asarray(score, float).ravel()
    t = np.asarray(target, bool).ravel()
    total = int(t.sum())
    order = np.argsort(-s, kind="stable")
    tp = np.cumsum(t[order])
    fp = np.cumsum(~t[order])
    ends = np.r_[np.nonzero(np.diff(s[order]))[0], s.size - 1]
    precision = tp[ends] / (ends + 1)
    recall = tp[ends] / total
    return float(np.sum(np.diff(np.r_[0.0, recall]) * precision))


def test_perfect_ranking():
    y = np.array([1, 1, 0, 0], dtype=bool)
    assert average_precision(y, np.array([0.9, 0.8, 0.1, 0.0])) == pytest.approx(1.0)


def test_positives_at_the_bottom():
    # worst ranking: positives last -> per-rank mean of 1/3 and 2/4
    y = np.array([1, 1, 0, 0], dtype=bool)
    assert average_precision(y, np.array([0.6, 0.7, 0.8, 0.9])) == pytest.approx(
        (1 / 3 + 2 / 4) / 2
    )


def test_manual_interleaved_case():
    y = np.array([0, 1, 0, 1, 0], dtype=bool)
    s = np.array([5.0, 4.0, 3.0, 2.0, 1.0])
    # positives at ranks 2 and 4: precisions 1/2 and 2/4
    assert average_precision(y, s) == pytest.approx((1 / 2 + 2 / 4) / 2)


def test_all_positives_is_one():
    y = np.ones(5, dtype=bool)
    assert average_precision(y, np.array([0.3, 0.8, 0.1, 0.6, 0.4])) == pytest.approx(1.0)


def test_no_positive_raises():
    with pytest.raises(ValueError, match="no positive"):
        average_precision(np.zeros(4, dtype=bool), np.zeros(4))


def test_nan_in_score_raises():
    with pytest.raises(ValueError, match="NaN"):
        average_precision(np.array([1, 0], dtype=bool), np.array([np.nan, 0.1]))


def test_inf_in_score_raises():
    with pytest.raises(ValueError, match="NaN or inf"):
        average_precision(np.array([1, 0], dtype=bool), np.array([np.inf, 0.1]))


def test_non_binary_reference_rejected_with_hint():
    with pytest.raises(ValueError, match="binarize"):
        average_precision(np.array([0.1, 0.9, 0.4]), np.array([1.0, 0.0, 1.0]))


def test_integer_reference_with_values_beyond_0_1_rejected():
    with pytest.raises(ValueError, match="only 0/1"):
        average_precision(np.array([0, 2, 1], dtype=int), np.array([1.0, 0.0, 1.0]))


def test_binary_input_variants_accepted():
    y = np.array([1, 0, 0])
    for variant in (
        np.array([1, 0, 1]),
        np.array([1.0, 0.0, 1.0]),
        np.array([True, False, True]),
    ):
        assert average_precision(y, variant) == pytest.approx(1.0)


def test_shape_mismatch_raises():
    with pytest.raises(ValueError, match="incompatible"):
        average_precision(np.ones((2, 2), dtype=bool), np.zeros((2, 3)))


def test_tied_scores_broken_by_index_order():
    # all scores tied: the ranking follows index order (documented
    # approximation) -> deterministic hand-computed values
    assert average_precision(np.array([1, 0], dtype=bool), np.array([0.5, 0.5])) == pytest.approx(1.0)
    assert average_precision(np.array([0, 1], dtype=bool), np.array([0.5, 0.5])) == pytest.approx(0.5)


def test_ties_do_not_reward_lower_scores():
    # a positive tied with negatives at the top gets the group-ends precision
    y = np.array([1, 0, 0, 0], dtype=bool)
    s = np.array([1.0, 1.0, 1.0, 1.0])
    assert average_precision(y, s) == pytest.approx(1.0)


@pytest.mark.parametrize("seed", range(10))
def test_matches_bruteforce_on_tie_free_scores(seed):
    rng = np.random.default_rng(seed)
    n = 60 + seed * 10
    score = rng.normal(size=n)  # continuous: no exact ties
    target = rng.random(n) < 0.3
    target[0] = True
    assert average_precision(target, score) == pytest.approx(
        _ap_bruteforce_no_ties(score, target), abs=1e-10
    )


@pytest.mark.parametrize(
    "transform",
    [
        lambda x: x**2,
        lambda x: np.exp(x),
        lambda x: np.log1p(x - x.min()),
        lambda x: x * 17.0 + 3.0,
        lambda x: np.sqrt(x - x.min()),
    ],
)
def test_ap_invariant_under_increasing_transform(transform):
    rng = np.random.default_rng(123)
    score = rng.uniform(size=200)
    target = rng.random(200) < 0.25
    base = average_precision(target, score)
    assert average_precision(target, transform(score)) == pytest.approx(base, abs=1e-12)


def test_ap_of_2d_map_equals_ap_of_flat_array():
    """The ranking is GLOBAL over all pixels of the 2D map (not per row/axis)."""
    rng = np.random.default_rng(7)
    score = rng.random((20, 30))
    target = rng.random((20, 30)) < 0.2
    assert average_precision(target, score) == pytest.approx(
        average_precision(target.ravel(), score.ravel()), abs=1e-15
    )


def test_global_ranking_differs_from_per_row_average():
    """A case where per-row ranking would give a different (wrong) answer."""
    score = np.zeros((2, 4))
    score[0] = [0.9, 0.8, 0.7, 0.6]  # row 0: its positive is global rank 2 of 8
    score[1] = [0.4, 0.3, 0.2, 0.1]  # row 1: its positive is global rank 6 of 8
    target = np.zeros((2, 4), dtype=bool)
    target[0, 1] = True
    target[1, 1] = True
    # global ranking: precisions 1/2 at rank 2, then 2/6 at rank 6
    expected_global = (1 / 2 + 2 / 6) / 2
    per_row_mean = (3 / 4 + 3 / 4) / 2
    got = average_precision(target, score)
    assert got == pytest.approx(expected_global)
    assert got != pytest.approx(per_row_mean)


def test_negatives_below_all_positives_do_not_change_ap():
    y = np.array([1, 0], dtype=bool)
    base = average_precision(y, np.array([0.5, 0.4]))
    extended_score = np.array([0.5, 0.4, 0.3, 0.2, 0.1])
    extended_y = np.array([1, 0, 0, 0, 0], dtype=bool)
    assert average_precision(extended_y, extended_score) == pytest.approx(base)


@pytest.mark.parametrize("seed", range(12))
def test_ap_between_zero_and_one(seed):
    rng = np.random.default_rng(seed)
    score = rng.normal(size=100)
    target = rng.random(100) < 0.2
    target[0] = True
    assert 0.0 <= average_precision(target, score) <= 1.0


@pytest.mark.parametrize("seed", range(8))
def test_better_ranking_higher_ap(seed):
    rng = np.random.default_rng(seed)
    n = 150
    target = rng.random(n) < 0.3
    target[0] = True
    signal = np.where(target, 1.0, 0.0)
    noise = rng.normal(scale=0.5, size=n)
    weak = average_precision(target, signal + noise)
    strong = average_precision(target, signal + noise / 10)
    assert strong >= weak


def test_constant_score_is_deterministic():
    y = np.array([1, 0, 1, 0], dtype=bool)
    first = average_precision(y, np.zeros(4))
    second = average_precision(y, np.zeros(4))
    assert first == second
    assert 0.0 <= first <= 1.0


def test_ap_on_the_demo_score_maps_stays_in_range():
    from herculaneum import baselines, blockwise, synth

    img, label = synth.make_synthetic_slice(96, 120, seed=3)
    for fn in (
        baselines.background_subtraction(),
        baselines.texture_energy(),
        baselines.mean_combination(
            baselines.background_subtraction(), baselines.texture_energy()
        ),
    ):
        scores = blockwise.predict_blockwise(fn, img, (48, 48), (24, 24))
        ap = average_precision(label, scores)
        assert 0.0 <= ap <= 1.0
