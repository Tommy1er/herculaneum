"""H001 — classical ink-detection baselines on one real window (protocol in README.md).

Two steps, run and committed separately so the order is visible in git:

    python run_h001.py freeze   --data DATA.npz --out results/frozen.json
    python run_h001.py evaluate --data DATA.npz --frozen results/frozen.json --out results/scores.json

`freeze` reads only the tuning tiles' labels: it fixes the split, lists every
candidate configuration in order, and keeps for B1 and C1 the one with the
best F0.5 on tuning pixels (first one wins ties). `evaluate` refuses to run if
the frozen file does not match the data, then scores the test tiles once.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from importlib import metadata
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from herculaneum.metrics import binary_scores  # noqa: E402
from herculaneum.tiles import spatial_split, tiles_mask  # noqa: E402

# ---- Split (geometric, fixed before looking at labels) -----------------------
TILE = 128
TEST_FRACTION = 0.25
AXIS = 1  # columns: the window is wider than tall, test band on the right
TRUNCATE = 3.0  # gaussian kernel radius = TRUNCATE * sigma
SIGMAS = [2.0, 4.0, 8.0]
GAP = int(np.ceil(TRUNCATE * max(SIGMAS))) + 8  # 24 px max context radius + 8 px slack = 32

# ---- Candidate configurations (order matters for ties) -----------------------
# Layer windows centred on the surface layer (z = 32 of 65, where labels are stored).
LAYER_WINDOWS = [(30, 35), (28, 37), (24, 41), (16, 49), (0, 65)]
POLARITIES = [+1, -1]  # +1: ink is brighter, -1: ink is darker
N_THRESHOLDS = 99  # thresholds at the 1st..99th percentiles of the tuning scores


def git_hash() -> str:
    try:
        return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load(path: Path):
    d = np.load(path)
    volume, ink, sup = d["volume"], d["ink"].astype(bool), d["supervision"].astype(bool)
    if volume.dtype != np.uint8 or volume.ndim != 3 or ink.shape != volume.shape[1:] or sup.shape != ink.shape:
        raise ValueError("unexpected data layout")
    return volume, ink, sup


def split_masks(shape):
    tune, test = spatial_split(shape, TILE, test_fraction=TEST_FRACTION, axis=AXIS, gap=GAP)
    return tune, test, tiles_mask(shape, tune), tiles_mask(shape, test)


def layer_mean(volume: np.ndarray, window: tuple[int, int]) -> np.ndarray:
    z0, z1 = window
    return volume[z0:z1].mean(axis=0, dtype=np.float32)


def score_map(method: str, mean: np.ndarray, sigma: float | None, polarity: int) -> np.ndarray:
    if method == "B1":
        s = mean
    elif method == "C1":  # local contrast: pixel minus its gaussian neighbourhood
        s = mean - gaussian_filter(mean, sigma, truncate=TRUNCATE)
    else:
        raise ValueError(method)
    return polarity * s


def best_threshold(scores: np.ndarray, labels: np.ndarray) -> tuple[float, float]:
    """Best F0.5 over percentile thresholds (pred = score > t). First best wins."""
    thresholds = np.percentile(scores, np.arange(1, N_THRESHOLDS + 1))
    pos = np.sort(scores[labels])
    neg = np.sort(scores[~labels])
    best_t, best_f = float(thresholds[0]), -1.0
    for t in thresholds:
        tp = pos.size - np.searchsorted(pos, t, side="right")
        fp = neg.size - np.searchsorted(neg, t, side="right")
        fn = pos.size - tp
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / (tp + fn) if tp + fn else 0.0
        f = 1.25 * p * r / (0.25 * p + r) if (0.25 * p + r) else 0.0
        if f > best_f + 1e-12:
            best_t, best_f = float(t), float(f)
    return best_t, best_f


def candidates():
    order = 0
    for window in LAYER_WINDOWS:
        for polarity in POLARITIES:
            yield {"order": order, "method": "B1", "layers": list(window), "sigma": None, "polarity": polarity}
            order += 1
    for sigma in SIGMAS:
        for window in LAYER_WINDOWS:
            for polarity in POLARITIES:
                yield {"order": order, "method": "C1", "layers": list(window), "sigma": sigma, "polarity": polarity}
                order += 1


def freeze(args) -> int:
    volume, ink, sup = load(args.data)
    tune, test, tune_m, test_m = split_masks(ink.shape)
    tune_eval = tune_m & sup
    if not (ink & tune_eval).any():
        print("tuning tiles contain no annotated ink: selection suspended (protocol)")
        return 2

    means = {tuple(w): layer_mean(volume, w) for w in LAYER_WINDOWS}
    labels = ink[tune_eval]
    tried, best = [], {}
    for c in candidates():
        s = score_map(c["method"], means[tuple(c["layers"])], c["sigma"], c["polarity"])[tune_eval]
        t, f = best_threshold(s, labels)
        c = {**c, "threshold": t, "tune_f05": round(f, 6)}
        tried.append(c)
        if c["method"] not in best or f > best[c["method"]]["tune_f05"] + 1e-12:
            best[c["method"]] = c

    frozen = {
        "experiment": "H001",
        "data_file": args.data.name,
        "data_sha256": file_sha256(args.data),
        "code_commit_at_freeze": git_hash(),
        "split": {
            "function": "herculaneum.tiles.spatial_split",
            "tile_size_px": TILE, "test_fraction": TEST_FRACTION, "axis": AXIS, "gap_px": GAP,
            "gap_justification": f"largest x/y context radius = {TRUNCATE} * {max(SIGMAS)} = "
                                 f"{TRUNCATE * max(SIGMAS):.0f} px (C1 gaussian); B1 has radius 0",
            "tune_tiles": len(tune), "test_tiles": len(test),
            "tune_rects_yxyx": [[t.y0, t.x0, t.y1, t.x1] for t in tune],
            "test_rects_yxyx": [[t.y0, t.x0, t.y1, t.x1] for t in test],
            "tune_supervised_px": int(tune_eval.sum()),
            "tune_ink_px": int((ink & tune_eval).sum()),
        },
        "selection_rule": "max F0.5 on tuning pixels; thresholds at percentiles 1..99 of tuning scores; "
                          "prediction = score > threshold; first configuration in listed order wins ties",
        "selected": best,
        "all_candidates_in_order": tried,
        "frozen_before_test": True,
        "dependency_versions": {p: metadata.version(p) for p in ("numpy", "scipy")},
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(frozen, indent=2))
    print(json.dumps({m: {k: v for k, v in c.items() if k != "order"} for m, c in best.items()}, indent=2))
    return 0


def evaluate(args) -> int:
    frozen = json.loads(args.frozen.read_text())
    if frozen["data_sha256"] != file_sha256(args.data):
        raise SystemExit("data file does not match the frozen configuration")
    volume, ink, sup = load(args.data)
    tune, test, _, test_m = split_masks(ink.shape)
    if [[t.y0, t.x0, t.y1, t.x1] for t in test] != frozen["split"]["test_rects_yxyx"]:
        raise SystemExit("split differs from the frozen one")
    test_eval = test_m & sup
    if not test_eval.any():
        raise SystemExit("test set is empty: no score (protocol)")

    results = {}
    shape = ink.shape
    results["B0_all_no_ink"] = binary_scores(np.zeros(shape, bool), ink, test_eval)
    results["B0_all_ink"] = binary_scores(np.ones(shape, bool), ink, test_eval)
    for method, c in frozen["selected"].items():
        s = score_map(method, layer_mean(volume, tuple(c["layers"])), c["sigma"], c["polarity"])
        results[method] = {**binary_scores(s > c["threshold"], ink, test_eval),
                           "config": {k: c[k] for k in ("layers", "sigma", "polarity", "threshold", "tune_f05")}}

    n = int(test_eval.sum())
    out = {
        "experiment": "H001",
        "frozen_file": str(args.frozen),
        "frozen_sha256": file_sha256(args.frozen),
        "code_commit_at_evaluation": git_hash(),
        "test_pixels": n,
        "test_ink_pixels": int((ink & test_eval).sum()),
        "test_prevalence": round(float((ink & test_eval).sum()) / n, 6),
        "zero_denominator_cases": [k for k, v in results.items() if v["tp"] + v["fp"] == 0],
        "scores": results,
    }
    args.out.write_text(json.dumps(out, indent=2))
    print(f"test pixels {n}, prevalence {out['test_prevalence']:.4f}")
    print(f"{'method':<15}{'precision':>10}{'recall':>9}{'F1':>8}{'F0.5':>8}")
    for k, v in results.items():
        print(f"{k:<15}{v['precision']:>10.4f}{v['recall']:>9.4f}{v['f1']:>8.4f}{v['f05']:>8.4f}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("freeze")
    f.add_argument("--data", type=Path, required=True)
    f.add_argument("--out", type=Path, required=True)
    e = sub.add_parser("evaluate")
    e.add_argument("--data", type=Path, required=True)
    e.add_argument("--frozen", type=Path, required=True)
    e.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    return freeze(args) if args.cmd == "freeze" else evaluate(args)


if __name__ == "__main__":
    sys.exit(main())
