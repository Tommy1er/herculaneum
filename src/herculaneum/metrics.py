"""Pixel-wise scores for binary ink predictions."""

from __future__ import annotations

import numpy as np


def _safe_div(num: float, den: float) -> float:
    return float(num / den) if den else 0.0


def fbeta(precision: float, recall: float, beta: float) -> float:
    """F-beta score. beta < 1 weights precision more (F0.5 was used in the
    Vesuvius Challenge ink detection competition)."""
    b2 = beta * beta
    return _safe_div((1 + b2) * precision * recall, b2 * precision + recall)


def binary_scores(
    pred: np.ndarray,
    target: np.ndarray,
    valid: np.ndarray | None = None,
) -> dict[str, float]:
    """Compare a binary prediction to a binary reference mask.

    Args:
        pred: predicted ink mask (bool or 0/1), any shape.
        target: reference ink mask, same shape as ``pred``.
        valid: optional mask of pixels to score (e.g. papyrus only). Pixels
            where ``valid`` is False are ignored.

    Returns:
        Counts (tp, fp, fn, tn) and precision, recall, f1, f05.
    """
    pred = np.asarray(pred).astype(bool)
    target = np.asarray(target).astype(bool)
    if pred.shape != target.shape:
        raise ValueError(f"shape mismatch: pred {pred.shape} vs target {target.shape}")
    if valid is None:
        valid = np.ones(pred.shape, dtype=bool)
    else:
        valid = np.asarray(valid).astype(bool)
        if valid.shape != pred.shape:
            raise ValueError(f"shape mismatch: valid {valid.shape} vs pred {pred.shape}")

    p, t = pred[valid], target[valid]
    tp = int(np.count_nonzero(p & t))
    fp = int(np.count_nonzero(p & ~t))
    fn = int(np.count_nonzero(~p & t))
    tn = int(np.count_nonzero(~p & ~t))

    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "f1": fbeta(precision, recall, 1.0),
        "f05": fbeta(precision, recall, 0.5),
    }
