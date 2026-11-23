"""Synthetic papyrus-slice generator.

Used ONLY to validate the processing chain (tests, CI, H001 demonstration).
The image loosely mimics a papyrus slice: oriented fibers (slightly wavy
sinusoidal bands), thin dark ink strokes, measurement noise. Numbers obtained
on these data say nothing about performance on the real Vesuvius Challenge
scans: the real ink/papyrus contrast is far weaker — see
``experiments/H001-ink-baseline/README.md``.

Every function is deterministic for a given ``seed``: two calls with the same
parameters return exactly the same arrays.

Imported from the GLM prototype (issue #3); logic unchanged, comments and
identifiers translated to English per AGENTS.md.
"""

from __future__ import annotations

import numpy as np

__all__ = ["make_synthetic_slice"]


def make_synthetic_slice(
    height: int = 256,
    width: int = 256,
    *,
    seed: int = 0,
    n_strokes: int = 14,
    stroke_steps: int = 110,
    ink_delta: float = 0.10,
    fibre_amp: float = 0.06,
    noise_sigma: float = 0.02,
) -> tuple[np.ndarray, np.ndarray]:
    """Return ``(image, label)``: a float slice in [0, 1] and the ink mask.

    ``ink_delta``: ink darkening — deliberately GENEROUS compared to the real
    scan contrast, to stay within the "chain validation" scope, not
    "detection performance".
    """
    if min(height, width) < 32:
        raise ValueError("synthetic image too small (min 32 x 32).")
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:height, 0:width]
    yy = yy.astype(np.float64)
    xx = xx.astype(np.float64)

    # Fibers: oriented sinusoidal bands, slightly wavy.
    theta = rng.uniform(0.0, np.pi)
    lam = rng.uniform(18.0, 40.0)
    phase = rng.uniform(0.0, 2.0 * np.pi)
    u = xx * np.cos(theta) + yy * np.sin(theta)
    img = 0.60 + fibre_amp * np.sin(
        2.0 * np.pi * u / lam + phase + 0.5 * np.sin(yy / 23.0)
    )

    # Ink strokes: smoothed random walks, ~2 pixel thick.
    label = np.zeros((height, width), dtype=bool)
    for _ in range(n_strokes):
        x = rng.uniform(0.0, float(width))
        y = rng.uniform(0.0, float(height))
        angle = rng.uniform(0.0, 2.0 * np.pi)
        curvature_phase = rng.uniform(0.0, 2.0 * np.pi)
        for step in range(stroke_steps):
            angle += 0.10 * np.sin(step / 7.0 + curvature_phase)
            x += 1.6 * np.cos(angle)
            y += 1.6 * np.sin(angle)
            xi = int(round(x))
            yi = int(round(y))
            if not (0 <= xi < width and 0 <= yi < height):
                break
            label[yi, xi] = True
            if yi + 1 < height:
                label[yi + 1, xi] = True

    img[label] -= ink_delta
    img += rng.normal(0.0, noise_sigma, img.shape)
    img = np.clip(img, 0.0, 1.0).astype(np.float32)
    return img, label
