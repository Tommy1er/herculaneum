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


def _as_bool_mask(x, name: str) -> np.ndarray:
    """Convert an input to a boolean mask, or raise an explicit error.

    Accepts: booleans, integers containing only 0/1, floats containing only
    0.0/1.0 (an arbitrary probability map is rejected with a message that
    asks to binarize it first).
    """
    a = np.asarray(x)
    if a.dtype == bool:
        return a
    if np.issubdtype(a.dtype, np.integer):
        values = set(np.unique(a).tolist())
        if values <= {0, 1}:
            return a != 0
        raise ValueError(
            f"{name}: integer mask containing {sorted(values)}; "
            "only 0/1 values are accepted."
        )
    if np.issubdtype(a.dtype, np.floating):
        if np.isnan(a).any():
            raise ValueError(f"{name}: NaN is not allowed in a binary mask.")
        if a.size and not np.all((a == 0.0) | (a == 1.0)):
            raise ValueError(
                f"{name}: non-binary float mask (values other than 0/1). "
                "If this is a probability map, binarize it first, or use "
                "average_precision for a threshold-free metric."
            )
        return a != 0.0
    raise TypeError(f"{name}: unsupported dtype ({a.dtype}).")


def _check_score(score, shape: tuple) -> np.ndarray:
    """Check that a score map is finite and has the expected shape."""
    s = np.asarray(score, dtype=np.float64)
    if s.shape != tuple(shape):
        raise ValueError(
            f"score: shape {s.shape} incompatible with the reference {tuple(shape)}."
        )
    if not np.isfinite(s).all():
        raise ValueError(
            "score: contains NaN or inf; fix the map upstream rather than "
            "letting the error propagate into the metrics."
        )
    return s


def average_precision(y_true: np.ndarray, score: np.ndarray) -> float:
    """Average precision (AP) of a score map, without choosing a threshold.

    AP = mean of the precision at the rank of every reference positive,
    scores sorted in decreasing order. Multidimensional arrays are flattened
    (the ranking is global, not per axis). Ties are broken by index order
    (stable ``argsort``): a standard approximation to keep in mind on heavily
    quantized score maps.

    Raises ``ValueError`` if ``y_true`` contains no positive (AP undefined) —
    never a silent default value.

    Imported from the GLM prototype (issue #3); algorithm kept verbatim so
    the announced numbers stay reproducible.
    """
    t = _as_bool_mask(y_true, "y_true")
    s = _check_score(score, t.shape)
    n_pos = int(np.count_nonzero(t))
    if n_pos == 0:
        raise ValueError(
            "average_precision: y_true contains no positive — AP is "
            "undefined. Check the reference or use another metric."
        )
    order = np.argsort(-s.ravel(), kind="stable")
    classes = t.ravel()[order]
    cum_tp = np.cumsum(classes)
    ranks = np.arange(1, classes.size + 1)
    precision_per_rank = cum_tp / ranks
    return float(precision_per_rank[classes].sum() / n_pos)
