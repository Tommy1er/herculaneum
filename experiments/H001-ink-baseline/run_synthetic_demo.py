"""H001 — end-to-end demonstration on SYNTHETIC data.

Validates the full chain: data -> tiles -> predictions -> threshold tuned on
the validation zone only -> metrics on the test zone -> JSON + figure report.
The numbers only hold for this synthetic data (generous ink contrast): see
the H001 README for the protocol and its limits.

Two threshold criteria are reported, both tuned on the validation zone only:

- ``initial_criterion``: maximize F1, ties keep the highest threshold. This
  is the criterion of the original GLM prototype; its test numbers are the
  ones announced on issue #3.
- ``t05_criterion``: maximize F0.5, ties keep the first recorded
  configuration (the highest threshold, in the recorded descending order).
  This is the criterion of the T05 protocol revision (PR #1); reported in
  addition because it changes the selection.

AP is threshold-free and identical under both criteria.

Development-trial status (review of issue #3, 2026-11-23): the seed-42 scene
and these numbers were used to bring the chain up (the generator choice and
one texture-method adjustment were made while looking at the test band).
They are published as a development trial; the independent check is the
pre-registered multi-seed evaluation (run_multiseed_evaluation.py).

Usage (from the repository root):

    python experiments/H001-ink-baseline/run_synthetic_demo.py

Outputs (experiments/H001-ink-baseline/results/):
    metrics_synthetic.json  — parameters, thresholds, metrics per method
    scores_chart.svg        — committed vector figure of the test scores
    map_synthetic.svg       — 3-panel map; deterministic and timestamp-free
                              but raster-heavy, so it is regenerated locally
                              rather than committed

The prototype wrote its outputs to ``outputs/``; the repository convention
(AGENTS.md) is ``results/``. The seed, versions and command are recorded
inside the JSON so every number is reproducible.
"""

from __future__ import annotations

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

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"

SEED = 42
HEIGHT, WIDTH = 256, 640
TILE = (128, 128)
OVERLAP = (48, 48)  # >= 4 x sigma=6 of the widest Gaussian kernel (radius 24)
VAL = (0, 200)  # threshold-tuning zone
GAP = (200, 440)  # band with no evaluation (no spatial leakage)
TEST = (440, 640)  # reporting zone, never used for tuning

N_SWEEP = 129  # quantile levels of the threshold sweep
FIGURE_DPI = 40  # keeps the committed SVG artifact a compact text file


def zone(span: tuple[int, int]) -> slice:
    return slice(span[0], span[1])


def sweep_thresholds(y_true: np.ndarray, score: np.ndarray) -> list[dict]:
    """Evaluate the score map over a recorded threshold list (descending).

    Default thresholds: 129 evenly spread quantiles of the validation-zone
    scores plus one threshold just above the maximum (empty prediction), so
    the sweep covers the whole spectrum including the "no prediction" case.
    Each row carries the full binary_scores output (tp/fp/fn/tn and the four
    rates), so both criteria select from exactly the same recorded table.
    """
    t = np.asarray(y_true).astype(bool)
    s = np.asarray(score, dtype=np.float64)
    if s.shape != t.shape:
        raise ValueError(f"shape mismatch: score {s.shape} vs target {t.shape}")
    quantiles = np.quantile(s, np.linspace(0.0, 1.0, N_SWEEP))
    thresholds = np.unique(np.concatenate([quantiles, [np.nextafter(s.max(), np.inf)]]))
    rows: list[dict] = []
    for th in thresholds[::-1]:  # descending order = recorded order
        row = metrics.binary_scores(s >= float(th), t)
        row["threshold"] = float(th)
        rows.append(row)
    return rows


def select_by_criterion(rows: list[dict], key: str) -> dict:
    """Row maximizing ``key``; ties keep the first recorded (highest) one."""
    best = rows[0]
    for row in rows[1:]:
        if row[key] > best[key]:
            best = row
    return best


def main() -> int:
    RESULTS.mkdir(parents=True, exist_ok=True)

    # 1. Synthetic data (deterministic) — image and ground truth.
    img, label = synth.make_synthetic_slice(HEIGHT, WIDTH, seed=SEED)
    prevalence_test = float(label[:, zone(TEST)].mean())

    # 2. Methods: each predict_fn is applied block by block (overlap 48 px
    #    >= the 24 px radius of the widest Gaussian kernel, so blockwise
    #    results equal the whole-image computation — tested in
    #    tests/test_pipeline_h001.py).
    methods = {
        "background_subtraction": baselines.background_subtraction(
            sigma_background=6.0, ink_scale=0.12
        ),
        "texture_energy": baselines.texture_energy(sigma=2.0, scale=0.10),
        "mean_combination": baselines.mean_combination(
            baselines.background_subtraction(sigma_background=6.0, ink_scale=0.12),
            baselines.texture_energy(sigma=2.0, scale=0.10),
        ),
    }

    results: dict = {}
    maps: dict[str, np.ndarray] = {}
    for name, fn in methods.items():
        score_map = blockwise.predict_blockwise(fn, img, TILE, OVERLAP)
        maps[name] = score_map

        # Threshold tuning ONLY on the validation zone: one recorded sweep,
        # two selection criteria read from the same rows.
        rows = sweep_thresholds(label[:, zone(VAL)], score_map[:, zone(VAL)])
        best_f1 = select_by_criterion(rows, "f1")
        best_f05 = select_by_criterion(rows, "f05")

        def evaluate(best: dict, criterion: str) -> dict:
            rule = (
                "max F1 on the validation zone, ties keep the highest "
                "threshold (original prototype criterion)"
                if criterion == "initial"
                else "max F0.5 on the validation zone, ties keep the first "
                "recorded (highest) threshold (T05 criterion, PR #1)"
            )
            return {
                "rule": rule,
                "threshold": round(best["threshold"], 6),
                "validation": {
                    k: best[k] for k in ("tp", "fp", "fn", "tn", "precision", "recall", "f1", "f05")
                },
                "test": metrics.binary_scores(
                    score_map[:, zone(TEST)] >= best["threshold"],
                    label[:, zone(TEST)],
                ),
            }

        ap_test = metrics.average_precision(label[:, zone(TEST)], score_map[:, zone(TEST)])
        results[name] = {
            "initial_criterion": evaluate(best_f1, "initial"),
            "t05_criterion": evaluate(best_f05, "t05"),
            "ap_test": round(ap_test, 4),
        }

    # 3. Trivial references on the test zone (for context).
    p = prevalence_test
    trivial = {
        "no_prediction": metrics.binary_scores(
            np.zeros(label[:, zone(TEST)].shape, dtype=bool), label[:, zone(TEST)]
        ),
        "all_ink": metrics.binary_scores(
            np.ones(label[:, zone(TEST)].shape, dtype=bool), label[:, zone(TEST)]
        ),
    }

    # 4. JSON report.
    report = {
        "experiment": "H001-ink-baseline",
        "data": f"synthetic seed={SEED}, {HEIGHT}x{WIDTH}",
        "zones": {"validation": VAL, "gap": GAP, "test": TEST},
        "tiling": {"tile": TILE, "overlap": OVERLAP},
        "separation": {
            "rule": "validation and test zones are separated by an unevaluated "
            "gap band; the only quantity tuned is a global threshold chosen "
            "from validation-zone scores",
            "gap_width_px": GAP[1] - GAP[0],
            "max_filter_radius_px": 24,  # scipy Gaussian: 4 * sigma_max = 4 * 6
            "gap_at_least_twice_filter_radius": (GAP[1] - GAP[0]) >= 2 * 24,
            "blockwise_overlap_at_least_filter_radius": OVERLAP[0] >= 4 * 6,
            "note": "the synthetic scene has no non-papyrus pixels, so every "
            "pixel is scored (a papyrus-valid mask would be applied on real data)",
        },
        "prevalence_test": round(p, 4),
        "methods": results,
        "trivial_references_test": trivial,
        "versions": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "command": "python experiments/H001-ink-baseline/run_synthetic_demo.py",
        "seed": SEED,
        "warning": (
            "Données SYNTHÉTIQUES : ces chiffres valident la chaîne de "
            "traitement, ils ne préjugent d'aucune performance sur les scans "
            "réels du Vesuvius Challenge."
        ),
    }
    json_path = RESULTS / "metrics_synthetic.json"
    json_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # 5. Figure: image, best probability map, ground truth (optional).
    svg_path = None
    try:
        import matplotlib

        matplotlib.use("Agg")
        matplotlib.rcParams["svg.fonttype"] = "none"  # keep text as text
        matplotlib.rcParams["svg.hashsalt"] = "h001-synthetic-demo"  # deterministic ids
        import matplotlib.pyplot as plt

        best_name = max(results, key=lambda k: results[k]["ap_test"])
        fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.6), constrained_layout=True)
        axes[0].imshow(img, cmap="gray")
        axes[0].set_title("Image synthétique (entrée)")
        im = axes[1].imshow(maps[best_name], cmap="magma", vmin=0, vmax=1)
        axes[1].set_title(f"Probabilité d'encre — « {best_name} »")
        fig.colorbar(im, ax=axes[1], fraction=0.046)
        axes[2].imshow(label, cmap="gray_r")
        axes[2].set_title("Vérité terrain (encre)")
        for ax in axes:
            for bound in (VAL[1], TEST[0]):
                ax.axvline(bound, color="w", linestyle="--", linewidth=1.2)
            ax.set_xlabel("colonnes : validation | écart | test")
        fig.suptitle(
            "H001 — chaîne validée sur données synthétiques (ne préjuge pas des scans réels)"
        )
        svg_path = RESULTS / "map_synthetic.svg"
        fig.savefig(svg_path, dpi=FIGURE_DPI, metadata={"Date": None})

        # Compact pure-vector chart of the test scores — this is the figure
        # committed to the repository (the 3-panel map above embeds raster
        # blobs and is regenerated locally instead).
        names = list(results.keys())
        shown = ("f1", "f05", "AP")
        width = 0.26
        x = np.arange(len(names))
        fig2, ax2 = plt.subplots(figsize=(8, 4.5), constrained_layout=True)
        for i, metric in enumerate(shown):
            values = (
                [results[n]["ap_test"] for n in names]
                if metric == "AP"
                else [results[n]["initial_criterion"]["test"][metric] for n in names]
            )
            bars = ax2.bar(x + (i - 1) * width, values, width, label=metric)
            ax2.bar_label(bars, fmt="%.3f", fontsize=8, padding=2)
        ax2.set_xticks(x, names, fontsize=9)
        ax2.set_ylim(0.0, 1.12)
        ax2.set_ylabel("score (test zone)")
        ax2.set_title("H001 synthetic scores per method (initial criterion)")
        ax2.legend(loc="upper left", ncols=3, fontsize=9)
        chart_path = RESULTS / "scores_chart.svg"
        fig2.savefig(chart_path, dpi=FIGURE_DPI, metadata={"Date": None})
        plt.close(fig2)
    except ImportError:
        print(
            "matplotlib not installed: figure skipped (scores are unaffected).",
            file=sys.stderr,
        )

    # 6. Readable table on stdout.
    print(f"Ink prevalence (test): {p:.4f}")
    header = (
        f"{'method':<24}{'thr(val)':>9}{'P(test)':>9}{'R(test)':>9}"
        f"{'F1':>8}{'F0.5':>8}{'AP':>8}   criterion"
    )
    print(header)
    for name, r in results.items():
        for crit in ("initial_criterion", "t05_criterion"):
            t = r[crit]["test"]
            tag = "initial" if crit == "initial_criterion" else "T05"
            print(
                f"{name:<24}{r[crit]['threshold']:>9.4f}{t['precision']:>9.4f}"
                f"{t['recall']:>9.4f}{t['f1']:>8.4f}{t['f05']:>8.4f}"
                f"{r['ap_test']:>8.4f}   {tag}"
            )
    print(
        f"trivial references (F1 test): no_prediction={trivial['no_prediction']['f1']:.4f}, "
        f"all_ink={trivial['all_ink']['f1']:.4f}"
    )
    print(f"\nWritten: {json_path}")
    if svg_path:
        print(f"         {svg_path}")
        print(f"         {RESULTS / 'scores_chart.svg'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
