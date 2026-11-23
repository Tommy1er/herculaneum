"""Classical ink-detection methods — H001 baselines.

These are COMPARISON POINTS, not competitive models: Herculaneum ink is
carbon-based and its contrast with papyrus is very low, which is why the
official project moved to machine learning. The point of these baselines is
to measure honestly what lightweight methods bring (probably little) before
investing elsewhere.

Each factory returns a ``predict_fn`` compatible with
:func:`herculaneum.blockwise.predict_blockwise`: input a 2D tile, output an
array of the same shape with scores in [0, 1] (1 = likely ink).

Important contract for block-by-block processing: the normalization scales
are FIXED parameters (no per-tile recalibration), so the blockwise result is
identical to the whole-image computation — a property verified in
``tests/test_pipeline_h001.py``. For a Gaussian filter of sigma ``s``, use
``overlap >= 4 * s`` (scipy kernel radius).

Imported from the GLM prototype (issue #3); logic unchanged, comments and
identifiers translated to English per AGENTS.md.
"""

from __future__ import annotations

from typing import Callable

import numpy as np
from scipy.ndimage import gaussian_filter

__all__ = ["background_subtraction", "texture_energy", "mean_combination"]


def _check_2d_tile(x: np.ndarray) -> np.ndarray:
    if x.ndim != 2:
        raise ValueError(
            f"2D baseline: expected a 2D tile, got ndim {x.ndim}. "
            "Apply these baselines slice by slice (z axis)."
        )
    return x.astype(np.float64, copy=False)


def background_subtraction(
    sigma_background: float = 6.0, ink_scale: float = 0.12
) -> Callable:
    """Ink = local density above the background.

    Subtract a heavily smoothed background: ``residual = background - image``.
    Areas denser than their neighbourhood (the ink) get a positive residual,
    bounded to [0, 1] by ``ink_scale`` (fixed scale, see the module contract).
    """
    if sigma_background <= 0 or ink_scale <= 0:
        raise ValueError("sigma_background and ink_scale must be > 0.")

    def predict(tile) -> np.ndarray:
        x = _check_2d_tile(tile)
        background = gaussian_filter(x, sigma=sigma_background, mode="reflect")
        residual = background - x
        return np.clip(residual / ink_scale, 0.0, 1.0)

    return predict


def texture_energy(sigma: float = 2.0, scale: float = 0.10) -> Callable:
    """Texture energy: local standard deviation.

    Responds to fibers AND to ink: a deliberately "blind" baseline, useful to
    check that a supposedly discriminant method actually beats a plain
    texture detector.
    """
    if sigma <= 0 or scale <= 0:
        raise ValueError("sigma and scale must be > 0.")

    def predict(tile) -> np.ndarray:
        x = _check_2d_tile(tile)
        m = gaussian_filter(x, sigma=sigma, mode="reflect")
        m2 = gaussian_filter(x * x, sigma=sigma, mode="reflect")
        std = np.sqrt(np.clip(m2 - m * m, 0.0, None))
        return np.clip(std / scale, 0.0, 1.0)

    return predict


def mean_combination(*predict_fns: Callable) -> Callable:
    """Mean of several score maps (the simplest combination)."""

    if not predict_fns:
        raise ValueError("mean_combination: at least one predict_fn is required.")

    def predict(tile) -> np.ndarray:
        maps = [np.asarray(fn(tile), dtype=np.float64) for fn in predict_fns]
        shape = maps[0].shape
        if any(m.shape != shape for m in maps):
            raise ValueError(
                f"mean_combination: score maps of different shapes "
                f"({[m.shape for m in maps]})."
            )
        return np.mean(maps, axis=0)

    return predict
