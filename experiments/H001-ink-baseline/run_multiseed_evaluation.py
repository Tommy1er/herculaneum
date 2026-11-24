"""H001 — pre-registered multi-seed evaluation (independent check).

Protocol, frozen BEFORE any execution of this script (see the commit that
introduced this file):

- generator: ``synth.make_synthetic_slice(256, 640)``, same constants as the
  frozen demonstration (zones, tiling, overlap);
- methods: the three frozen baselines (sigma/ink_scale/scale fixed);
- threshold rule: one recorded sweep (129 quantiles + one above-max) on the
  validation zone only; the two selection criteria (initial: max F1; T05:
  max F0.5) are read from the same recorded rows, ties keep the first
  recorded (highest) threshold;
- seeds: the fixed list below, chosen before the first execution and never
  adjusted afterwards; each seed is evaluated exactly once;
- ALL outputs are published per seed, including unfavorable ones.

This script imports the frozen pipeline from ``run_synthetic_demo.py`` and
does not modify it. It adds no tuning, no selection and no re-running: one
pass over the registered seeds. The development seed (42) is deliberately
not part of the list — its numbers are published separately as a
development trial, as required by the review on issue #3.
"""

from __future__ import annotations

import importlib.util
import json
import platform
import sys
from pathlib import Path

import numpy as np
import scipy

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from herculaneum import baselines, blockwise, metrics, synth  # noqa: E402

# Frozen pipeline module (development trial), imported untouched.
_SPEC = importlib.util.spec_from_file_location(
    "run_synthetic_demo",
    Path(__file__).resolve().parent / "run_synthetic_demo.py",
)
_demo = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_demo)

# Pre-registered seed list: fixed before the first execution of this script,
# disjoint from the development seed (42) and from every seed used by the
# test suite or during development. Not to be edited after seeing results.
SEEDS = [101, 202, 303, 404, 505, 606, 707, 808, 909, 1010]

OUT_DIR = Path(__file__).resolve().parent / "results" / "multiseed"

METHOD_FACTORIES = {
    "background_subtraction": lambda: baselines.background_subtraction(
        sigma_background=6.0, ink_scale=0.12
    ),
    "texture_energy": lambda: baselines.texture_energy(sigma=2.0, scale=0.10),
    "mean_combination": lambda: baselines.mean_combination(
        baselines.background_subtraction(sigma_background=6.0, ink_scale=0.12),
        baselines.texture_energy(sigma=2.0, scale=0.10),
    ),
}


def evaluate_seed(seed: int) -> dict:
    """One pass of the frozen pipeline on one seed (no tuning beyond the
    validation-zone threshold rule, exactly as in the frozen demonstration)."""
    img, label = synth.make_synthetic_slice(_demo.HEIGHT, _demo.WIDTH, seed=seed)
    val = _demo.zone(_demo.VAL)
    test = _demo.zone(_demo.TEST)
    prevalence_test = float(label[:, test].mean())

    per_method: dict = {}
    for name, factory in METHOD_FACTORIES.items():
        score_map = blockwise.predict_blockwise(factory(), img, _demo.TILE, _demo.OVERLAP)
        rows = _demo.sweep_thresholds(label[:, val], score_map[:, val])
        best_f1 = _demo.select_by_criterion(rows, "f1")
        best_f05 = _demo.select_by_criterion(rows, "f05")
        per_method[name] = {
            "initial_criterion": {
                "threshold": round(best_f1["threshold"], 6),
                "test": metrics.binary_scores(
                    score_map[:, test] >= best_f1["threshold"], label[:, test]
                ),
            },
            "t05_criterion": {
                "threshold": round(best_f05["threshold"], 6),
                "test": metrics.binary_scores(
                    score_map[:, test] >= best_f05["threshold"], label[:, test]
                ),
            },
            "ap_test": round(metrics.average_precision(label[:, test], score_map[:, test]), 4),
        }

    trivial = {
        "no_prediction": metrics.binary_scores(
            np.zeros(label[:, test].shape, dtype=bool), label[:, test]
        ),
        "all_ink": metrics.binary_scores(
            np.ones(label[:, test].shape, dtype=bool), label[:, test]
        ),
    }
    return {
        "seed": seed,
        "data": f"synthetic seed={seed}, {_demo.HEIGHT}x{_demo.WIDTH}",
        "zones": {"validation": list(_demo.VAL), "gap": list(_demo.GAP), "test": list(_demo.TEST)},
        "tiling": {"tile": list(_demo.TILE), "overlap": list(_demo.OVERLAP)},
        "prevalence_test": round(prevalence_test, 4),
        "methods": per_method,
        "trivial_references_test": trivial,
    }


def summarize(reports: list[dict]) -> dict:
    """Aggregate the published per-seed outputs (no selection of any kind)."""

    def stats(values: list[float]) -> dict:
        return {
            "mean": round(sum(values) / len(values), 4),
            "min": round(min(values), 4),
            "max": round(max(values), 4),
        }

    summary: dict = {
        "rule": "one run per pre-registered seed; every output published; "
        "no seed replacement, no re-run, no selection",
        "seeds": [r["seed"] for r in reports],
        "n_seeds": len(reports),
        "prevalence_test": stats([r["prevalence_test"] for r in reports]),
    }
    for name in METHOD_FACTORIES:
        entry: dict = {}
        for crit in ("initial_criterion", "t05_criterion"):
            entry[crit] = {
                key: stats([r["methods"][name][crit]["test"][key] for r in reports])
                for key in ("precision", "recall", "f1", "f05")
            }
        entry["ap"] = stats([r["methods"][name]["ap_test"] for r in reports])
        entry["all_ink_f1"] = stats(
            [r["trivial_references_test"]["all_ink"]["f1"] for r in reports]
        )
        summary[name] = entry
    return summary


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    reports = []
    for seed in SEEDS:
        report = evaluate_seed(seed)
        path = OUT_DIR / f"seed_{seed}.json"
        path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        reports.append(report)
        comb = report["methods"]["mean_combination"]
        print(
            f"seed={seed}: comb F1={comb['initial_criterion']['test']['f1']:.4f} "
            f"F0.5={comb['initial_criterion']['test']['f05']:.4f} "
            f"AP={comb['ap_test']:.4f} (published to {path.name})"
        )

    summary = summarize(reports)
    summary["versions"] = {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
    }
    summary["command"] = "python experiments/H001-ink-baseline/run_multiseed_evaluation.py"
    summary["warning"] = (
        "Données SYNTHÉTIQUES : ces chiffres valident la chaîne de traitement, "
        "ils ne préjugent d'aucune performance sur les scans réels du "
        "Vesuvius Challenge."
    )
    summary_path = OUT_DIR / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSummary written to {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
