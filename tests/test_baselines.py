"""Tests for herculaneum.baselines — classical ink-detection baselines.

Adapted from the GLM prototype's pipeline tests (issue #3) and extended.
"""

import numpy as np
import pytest

from herculaneum.baselines import (
    background_subtraction,
    mean_combination,
    texture_energy,
)
from herculaneum.synth import make_synthetic_slice

FACTORIES = [
    lambda: background_subtraction(),
    lambda: texture_energy(),
    lambda: mean_combination(background_subtraction(), texture_energy()),
]


@pytest.mark.parametrize("factory_index", range(len(FACTORIES)))
def test_scores_bounded_and_same_shape(factory_index):
    img, _ = make_synthetic_slice(96, 120, seed=2)
    scores = FACTORIES[factory_index]()(img)
    assert scores.shape == img.shape
    assert np.isfinite(scores).all()
    assert scores.min() >= 0.0 and scores.max() <= 1.0


@pytest.mark.parametrize("seed", range(6))
def test_scores_bounded_on_many_seeds(seed):
    img, _ = make_synthetic_slice(64, 96, seed=seed)
    for factory in FACTORIES:
        scores = factory()(img)
        assert np.isfinite(scores).all()
        assert scores.min() >= 0.0 and scores.max() <= 1.0


def test_background_subtraction_flat_image_is_zero():
    img = np.full((48, 48), 0.5, dtype=np.float32)
    scores = background_subtraction()(img)
    assert scores.max() < 1e-6


def test_dark_disk_gets_high_background_score():
    img = np.full((64, 64), 0.6, dtype=np.float32)
    img[28:36, 28:36] = 0.3
    scores = background_subtraction(sigma_background=6.0, ink_scale=0.12)(img)
    assert scores[32, 32] == scores.max()
    assert scores[32, 32] > 0.5


def test_ink_pixels_score_above_background_pixels():
    img, label = make_synthetic_slice(128, 128, seed=5)
    scores = background_subtraction()(img)
    assert scores[label].mean() > scores[~label].mean()


def test_texture_energy_flat_image_is_low():
    img = np.full((48, 48), 0.5, dtype=np.float32)
    scores = texture_energy()(img)
    assert scores.max() < 1e-6


def test_texture_energy_detects_fibers_not_ink():
    img, label = make_synthetic_slice(128, 128, seed=5)
    scores = texture_energy()(img)
    # the "blind" witness reacts to fibers at least as much as to ink
    assert scores[label].mean() < scores.max()


def test_ink_scale_zero_raises():
    with pytest.raises(ValueError, match="ink_scale"):
        background_subtraction(sigma_background=6.0, ink_scale=0.0)


def test_sigma_background_zero_raises():
    with pytest.raises(ValueError, match="sigma_background"):
        background_subtraction(sigma_background=0.0)


def test_texture_energy_invalid_parameters_raise():
    with pytest.raises(ValueError, match="sigma"):
        texture_energy(sigma=0.0)
    with pytest.raises(ValueError, match="scale"):
        texture_energy(sigma=2.0, scale=-1.0)


def test_mean_combination_without_input_raises():
    with pytest.raises(ValueError, match="at least one"):
        mean_combination()


def test_mean_combination_is_the_mean_of_the_maps():
    img, _ = make_synthetic_slice(96, 96, seed=8)
    bg = background_subtraction()(img)
    tex = texture_energy()(img)
    combined = mean_combination(background_subtraction(), texture_energy())(img)
    assert np.allclose(combined, (bg + tex) / 2.0)


def test_mean_combination_shape_mismatch_raises():
    img = np.zeros((32, 32))
    broken = mean_combination(
        background_subtraction(), lambda x: x[:, :8]
    )
    with pytest.raises(ValueError, match="different shapes"):
        broken(img)


def test_1d_input_rejected_with_explicit_message():
    with pytest.raises(ValueError, match="2D"):
        background_subtraction()(np.zeros(64))


def test_baselines_are_deterministic():
    img, _ = make_synthetic_slice(96, 96, seed=9)
    for factory in FACTORIES:
        assert np.array_equal(factory()(img), factory()(img))


def test_ink_scale_maps_residual_linearly():
    """The scale is a FIXED constant of the factory: halving it doubles the
    unclipped scores (no per-image recalibration)."""
    img = np.full((64, 64), 0.6, dtype=np.float32)
    img[28:36, 28:36] = 0.55  # small drop: residual stays unclipped
    s12 = background_subtraction(sigma_background=6.0, ink_scale=0.12)(img)
    s24 = background_subtraction(sigma_background=6.0, ink_scale=0.24)(img)
    center = (32, 32)
    assert 0.0 < s12[center] < 1.0  # unclipped region
    assert s12[center] == pytest.approx(2.0 * s24[center], rel=1e-6)
