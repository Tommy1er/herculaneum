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


def as_binary(array: np.ndarray, name: str) -> np.ndarray:
    """Return ``array`` as bool, refusing anything that is not already binary.

    Only bool arrays and numeric arrays whose values are all 0 or 1 are
    accepted. A probability map (0.3, 0.7...) or a 0/255 image raises instead
    of being silently turned into "nonzero = True": threshold or rescale it
    explicitly first.
    """
    a = np.asarray(array)
    if a.dtype == bool:
        return a
    if not (np.issubdtype(a.dtype, np.integer) or np.issubdtype(a.dtype, np.floating)):
        raise TypeError(f"{name}: expected a bool or numeric array, got dtype {a.dtype}")
    bad = (a != 0) & (a != 1)
    if bad.any():
        examples = np.unique(a[bad])[:5].tolist()
        raise ValueError(
            f"{name}: values must be 0/1 or bool, found {examples}; "
            "threshold probabilities or rescale 0/255 masks before scoring"
        )
    return a.astype(bool)


def binary_scores(
    pred: np.ndarray,
    target: np.ndarray,
    valid: np.ndarray | None = None,
) -> dict[str, float]:
    """Compare a binary prediction to a binary reference mask.

    Args:
        pred: predicted ink mask (bool or 0/1), any shape.
        target: reference ink mask (bool or 0/1), same shape as ``pred``.
        valid: optional mask (bool or 0/1) of pixels to score, e.g. annotated
            papyrus only. Pixels where ``valid`` is False are ignored.

    Raises:
        ValueError: on shape mismatch or non-binary values (see ``as_binary``).

    Returns:
        Counts (tp, fp, fn, tn) and precision, recall, f1, f05.
    """
    pred = as_binary(pred, "pred")
    target = as_binary(target, "target")
    if pred.shape != target.shape:
        raise ValueError(f"shape mismatch: pred {pred.shape} vs target {target.shape}")
    if valid is None:
        valid = np.ones(pred.shape, dtype=bool)
    else:
        valid = as_binary(valid, "valid")
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
