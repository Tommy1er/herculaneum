"""Tests for herculaneum.synth — deterministic synthetic slices.

Adapted from the GLM prototype's pipeline tests (issue #3) and extended with
seeded property checks.
"""

import numpy as np
import pytest

from herculaneum.synth import make_synthetic_slice

SEEDS = list(range(8))


def test_deterministic_same_seed():
    a = make_synthetic_slice(96, 96, seed=11)
    b = make_synthetic_slice(96, 96, seed=11)
    assert np.array_equal(a[0], b[0]) and np.array_equal(a[1], b[1])


def test_different_seed_gives_different_image():
    a = make_synthetic_slice(96, 96, seed=11)
    c = make_synthetic_slice(96, 96, seed=12)
    assert not np.array_equal(a[0], c[0])


def test_image_and_label_consistent():
    img, label = make_synthetic_slice(128, 160, seed=5)
    assert img.shape == (128, 160) and label.shape == (128, 160)
    assert img.dtype == np.float32
    assert img.min() >= 0.0 and img.max() <= 1.0
    assert 0.0 < label.mean() < 0.5


def test_ink_darker_than_background():
    img, label = make_synthetic_slice(128, 128, seed=5)
    assert img[label].mean() < img[~label].mean() - 0.03


@pytest.mark.parametrize("seed", SEEDS)
def test_deterministic_for_every_seed(seed):
    img1, label1 = make_synthetic_slice(64, 80, seed=seed)
    img2, label2 = make_synthetic_slice(64, 80, seed=seed)
    assert np.array_equal(img1, img2)
    assert np.array_equal(label1, label2)


@pytest.mark.parametrize("seed", SEEDS)
def test_shape_and_range_for_every_seed(seed):
    img, label = make_synthetic_slice(80, 96, seed=seed)
    assert img.shape == (80, 96)
    assert label.shape == (80, 96)
    assert img.dtype == np.float32
    assert 0.0 <= float(img.min()) and float(img.max()) <= 1.0


@pytest.mark.parametrize("seed", SEEDS)
def test_label_is_boolean_binary(seed):
    _, label = make_synthetic_slice(80, 80, seed=seed)
    assert label.dtype == np.bool_
    assert set(np.unique(label)).issubset({False, True})


@pytest.mark.parametrize("seed", SEEDS)
def test_ink_fraction_in_plausible_range(seed):
    _, label = make_synthetic_slice(128, 128, seed=seed)
    fraction = float(label.mean())
    assert 0.005 <= fraction <= 0.25, f"seed {seed}: ink fraction {fraction:.4f}"


@pytest.mark.parametrize("seed", SEEDS)
def test_ink_pixels_darker_for_every_seed(seed):
    img, label = make_synthetic_slice(128, 128, seed=seed)
    assert img[label].mean() < img[~label].mean()


def test_zero_strokes_gives_empty_label():
    _, label = make_synthetic_slice(64, 64, seed=0, n_strokes=0)
    assert not label.any()


def test_more_strokes_give_more_ink():
    _, small = make_synthetic_slice(128, 128, seed=3, n_strokes=2)
    _, large = make_synthetic_slice(128, 128, seed=3, n_strokes=20)
    assert large.mean() > small.mean()


def test_higher_ink_delta_darkens_ink():
    img_lo, label = make_synthetic_slice(128, 128, seed=5, ink_delta=0.02)
    img_hi, _ = make_synthetic_slice(128, 128, seed=5, ink_delta=0.30)
    assert img_hi[label].mean() < img_lo[label].mean()


def test_too_small_image_raises():
    with pytest.raises(ValueError, match="too small"):
        make_synthetic_slice(31, 64, seed=0)
    with pytest.raises(ValueError, match="too small"):
        make_synthetic_slice(64, 16, seed=0)


def test_minimum_size_is_accepted():
    img, label = make_synthetic_slice(32, 32, seed=0)
    assert img.shape == (32, 32)
    assert label.shape == (32, 32)


def test_demo_seed_42_has_ink_in_both_zones():
    """The demo zones must all contain ink, otherwise no score is defined."""
    _, label = make_synthetic_slice(256, 640, seed=42)
    assert label[:, 0:200].any(), "validation zone has no ink"
    assert label[:, 440:640].any(), "test zone has no ink"
