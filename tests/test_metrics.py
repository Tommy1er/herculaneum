import numpy as np
import pytest

from herculaneum.metrics import binary_scores, fbeta


def test_perfect_prediction():
    t = np.array([[1, 0], [0, 1]])
    s = binary_scores(t, t)
    assert s["precision"] == s["recall"] == s["f1"] == s["f05"] == 1.0
    assert (s["tp"], s["fp"], s["fn"], s["tn"]) == (2, 0, 0, 2)


def test_known_counts():
    pred = np.array([1, 1, 1, 0, 0, 0])
    target = np.array([1, 1, 0, 1, 0, 0])
    s = binary_scores(pred, target)
    assert (s["tp"], s["fp"], s["fn"], s["tn"]) == (2, 1, 1, 2)
    assert s["precision"] == pytest.approx(2 / 3)
    assert s["recall"] == pytest.approx(2 / 3)
    assert s["f1"] == pytest.approx(2 / 3)


def test_f05_weights_precision():
    # high precision, low recall -> F0.5 above F1
    assert fbeta(0.9, 0.3, 0.5) > fbeta(0.9, 0.3, 1.0)
    assert fbeta(0.9, 0.3, 0.5) == pytest.approx(1.25 * 0.27 / (0.25 * 0.9 + 0.3))


def test_empty_prediction_gives_zero_not_nan():
    s = binary_scores(np.zeros(4), np.array([1, 0, 0, 0]))
    assert s["precision"] == 0.0 and s["recall"] == 0.0 and s["f1"] == 0.0


def test_valid_mask_ignores_pixels():
    pred = np.array([1, 1, 0, 0])
    target = np.array([1, 0, 0, 1])
    valid = np.array([True, False, True, False])
    s = binary_scores(pred, target, valid)
    assert (s["tp"], s["fp"], s["fn"], s["tn"]) == (1, 0, 0, 1)


def test_shape_mismatch_raises():
    with pytest.raises(ValueError):
        binary_scores(np.zeros((2, 2)), np.zeros((2, 3)))


def test_float_zero_one_is_accepted():
    s = binary_scores(np.array([1.0, 0.0]), np.array([1, 0], dtype=np.uint8))
    assert s["f1"] == 1.0


@pytest.mark.parametrize("bad", [np.array([0.3, 0.7]), np.array([0, 255], dtype=np.uint8), np.array([-1, 0])])
def test_non_binary_values_are_rejected(bad):
    with pytest.raises(ValueError, match="0/1 or bool"):
        binary_scores(bad, np.zeros(2))
    with pytest.raises(ValueError, match="target"):
        binary_scores(np.zeros(2), bad)
    with pytest.raises(ValueError, match="valid"):
        binary_scores(np.zeros(2), np.zeros(2), bad)


def test_non_numeric_dtype_is_rejected():
    with pytest.raises(TypeError):
        binary_scores(np.array(["1", "0"]), np.zeros(2))
