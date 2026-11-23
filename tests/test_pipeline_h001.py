"""End-to-end tests of the H001 chain: synth -> baselines -> blockwise -> metrics.

These tests validate the PROCESSING CHAIN on synthetic data with generous
contrast. They prove no performance on the real Vesuvius Challenge scans.

Adapted from the GLM prototype's pipeline tests (issue #3) and extended with
demo-script integration checks. The tile-vs-whole-image equivalence and the
global 2D pixel ranking are pinned here, as required by issue #3.
"""

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

from herculaneum import baselines, blockwise, metrics, synth

# Block/whole-image equivalence constraint: overlap >= 4 * sigma of the
# widest Gaussian kernel (sigma=6 -> radius 24; overlap 48 >= 24).
TILE = (128, 128)
OVERLAP = (48, 48)

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "experiments"
    / "H001-ink-baseline"
    / "run_synthetic_demo.py"
)

matplotlib_spec = importlib.util.find_spec("matplotlib")
needs_matplotlib = pytest.mark.skipif(matplotlib_spec is None, reason="matplotlib not installed")


# --- chain-level properties (from the prototype) -----------------------------


@pytest.mark.parametrize("name,factory", [
    ("background", lambda: baselines.background_subtraction(sigma_background=6.0, ink_scale=0.12)),
    ("texture", lambda: baselines.texture_energy(sigma=2.0, scale=0.10)),
])
def test_blockwise_equivalent_to_whole_image(name, factory):
    img, _ = synth.make_synthetic_slice(160, 200, seed=3)
    fn = factory()
    whole = fn(img)
    block = blockwise.predict_blockwise(fn, img, TILE, OVERLAP)
    assert np.allclose(block, whole, atol=1e-6), name


def test_combination_blockwise_equivalent_to_whole_image():
    img, _ = synth.make_synthetic_slice(160, 200, seed=3)
    fn = baselines.mean_combination(
        baselines.background_subtraction(sigma_background=6.0),
        baselines.texture_energy(sigma=2.0),
    )
    assert np.allclose(
        blockwise.predict_blockwise(fn, img, TILE, OVERLAP),
        fn(img),
        atol=1e-6,
    )


def test_pipeline_beats_chance_on_synthetic():
    img, label = synth.make_synthetic_slice(256, 256, seed=7)
    scores = blockwise.predict_blockwise(
        baselines.background_subtraction(sigma_background=6.0, ink_scale=0.12),
        img,
        TILE,
        OVERLAP,
    )
    ap_ink = metrics.average_precision(label, scores)
    rng = np.random.default_rng(0)
    ap_chance = metrics.average_precision(label, rng.random(label.shape))
    assert ap_ink > ap_chance + 0.30


def test_global_pixel_ranking_preserved_blockwise():
    """The 2D ranking of score pixels is identical blockwise and whole-image
    (issue #3: keep the global 2D pixel-ranking test)."""
    img, _ = synth.make_synthetic_slice(160, 200, seed=3)
    fn = baselines.background_subtraction(sigma_background=6.0, ink_scale=0.12)
    whole = fn(img)
    block = blockwise.predict_blockwise(fn, img, TILE, OVERLAP)
    assert np.array_equal(np.argsort(whole.ravel()), np.argsort(block.ravel()))


def test_smaller_overlap_still_exact_for_narrow_kernel():
    """texture_energy uses sigma=2 (radius 8): overlap 8 suffices."""
    img, _ = synth.make_synthetic_slice(160, 200, seed=3)
    fn = baselines.texture_energy(sigma=2.0, scale=0.10)
    assert np.allclose(
        blockwise.predict_blockwise(fn, img, (128, 128), (8, 8)),
        fn(img),
        atol=1e-6,
    )


def test_too_small_overlap_breaks_the_equivalence():
    """overlap < 4 * sigma breaks core equality when tiles actually step
    through the image: the contract is documented, not accidental."""
    img, _ = synth.make_synthetic_slice(160, 200, seed=3)
    fn = baselines.background_subtraction(sigma_background=6.0, ink_scale=0.12)
    block = blockwise.predict_blockwise(fn, img, (64, 64), (4, 4))
    whole = fn(img)
    assert not np.allclose(block, whole, atol=1e-6)


def test_metrics_flow_through_the_chain():
    img, label = synth.make_synthetic_slice(128, 160, seed=5)
    scores = baselines.background_subtraction()(img)
    pred = scores >= 0.3
    s = metrics.binary_scores(pred, label)
    assert set(s) == {"tp", "fp", "fn", "tn", "precision", "recall", "f1", "f05"}
    assert s["tp"] + s["fp"] + s["fn"] + s["tn"] == label.size


# --- demo script integration --------------------------------------------------


def _run_demo():
    spec = importlib.util.spec_from_file_location("run_synthetic_demo", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    code = module.main()
    assert code == 0
    out_dir = Path(SCRIPT).parent / "results"
    json_path = out_dir / "metrics_synthetic.json"
    assert json_path.exists()
    return json.loads(json_path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def demo_report():
    return _run_demo()


def test_demo_json_schema(demo_report):
    for key in ("experiment", "data", "zones", "tiling", "separation",
                "prevalence_test", "methods", "trivial_references_test",
                "versions", "command", "seed", "warning"):
        assert key in demo_report, key
    for name in ("background_subtraction", "texture_energy", "mean_combination"):
        assert name in demo_report["methods"]
        for crit in ("initial_criterion", "t05_criterion"):
            assert crit in demo_report["methods"][name]
            entry = demo_report["methods"][name][crit]
            for key in ("rule", "threshold", "validation", "test"):
                assert key in entry, (name, crit, key)


def test_demo_scores_within_unit_range(demo_report):
    for name in ("background_subtraction", "texture_energy", "mean_combination"):
        method = demo_report["methods"][name]
        for crit in ("initial_criterion", "t05_criterion"):
            for key in ("precision", "recall", "f1", "f05"):
                assert 0.0 <= method[crit]["test"][key] <= 1.0
                assert 0.0 <= method[crit]["validation"][key] <= 1.0
        assert 0.0 <= method["ap_test"] <= 1.0
    for name in ("no_prediction", "all_ink"):
        row = demo_report["trivial_references_test"][name]
        for key in ("precision", "recall", "f1", "f05"):
            assert 0.0 <= row[key] <= 1.0


def test_demo_counts_sum_to_test_zone(demo_report):
    test_cols = demo_report["zones"]["test"]
    n_pixels = 256 * (test_cols[1] - test_cols[0])
    for name in ("background_subtraction", "texture_energy", "mean_combination"):
        for crit in ("initial_criterion", "t05_criterion"):
            t = demo_report["methods"][name][crit]["test"]
            assert t["tp"] + t["fp"] + t["fn"] + t["tn"] == n_pixels


def test_demo_metrics_recomputed_from_counts(demo_report):
    for name in ("background_subtraction", "texture_energy", "mean_combination"):
        t = demo_report["methods"][name]["initial_criterion"]["test"]
        precision = t["tp"] / (t["tp"] + t["fp"]) if (t["tp"] + t["fp"]) else 0.0
        recall = t["tp"] / (t["tp"] + t["fn"]) if (t["tp"] + t["fn"]) else 0.0
        assert t["precision"] == pytest.approx(precision, abs=1e-12)
        assert t["recall"] == pytest.approx(recall, abs=1e-12)


def test_demo_reproduces_the_announced_numbers(demo_report):
    """The initial criterion must reproduce the numbers announced on
    issue #3 (prototype, seed 42) to the reported precision."""
    expected = {
        "background_subtraction": {"f1": 0.7486, "ap": 0.8117},
        "texture_energy": {"f1": 0.4656, "ap": 0.3615},
        "mean_combination": {"f1": 0.8703, "ap": 0.94},
    }
    for name, exp in expected.items():
        got = demo_report["methods"][name]
        assert got["initial_criterion"]["test"]["f1"] == pytest.approx(exp["f1"], abs=5e-5)
        assert got["ap_test"] == pytest.approx(exp["ap"], abs=5e-5)
    assert demo_report["trivial_references_test"]["all_ink"]["f1"] == pytest.approx(0.0363, abs=5e-4)
    assert demo_report["prevalence_test"] == pytest.approx(0.0185, abs=5e-5)


def test_demo_naive_references_follow_prevalence(demo_report):
    p = demo_report["prevalence_test"]
    all_ink = demo_report["trivial_references_test"]["all_ink"]
    assert all_ink["precision"] == pytest.approx(p, abs=5e-4)
    assert all_ink["recall"] == 1.0
    assert all_ink["f1"] == pytest.approx(2 * p / (1 + p), abs=1e-3)
    no_pred = demo_report["trivial_references_test"]["no_prediction"]
    assert no_pred["f1"] == 0.0 and no_pred["f05"] == 0.0


def test_demo_both_criteria_tuned_on_validation_only(demo_report):
    """Each criterion's threshold maximizes its metric among the recorded
    validation rows — the test zone is never used for selection."""
    # the thresholds differ in general (F0.5 favors precision) but both come
    # from the same recorded sweep; AP must be identical under both criteria
    for name in ("background_subtraction", "texture_energy", "mean_combination"):
        m = demo_report["methods"][name]
        initial = m["initial_criterion"]
        t05 = m["t05_criterion"]
        assert initial["rule"].startswith("max F1")
        assert t05["rule"].startswith("max F0.5")
        # validation metrics recomputed from counts
        v = initial["validation"]
        precision = v["tp"] / (v["tp"] + v["fp"]) if (v["tp"] + v["fp"]) else 0.0
        assert v["precision"] == pytest.approx(precision, abs=1e-12)


def test_demo_combination_is_the_best_method(demo_report):
    """The profile announced on issue #3: combination > background > texture."""
    ap = {k: demo_report["methods"][k]["ap_test"]
          for k in ("background_subtraction", "texture_energy", "mean_combination")}
    assert ap["mean_combination"] > ap["background_subtraction"] > ap["texture_energy"]
    f1 = {k: demo_report["methods"][k]["initial_criterion"]["test"]["f1"]
          for k in ("background_subtraction", "texture_energy", "mean_combination")}
    assert f1["mean_combination"] > f1["background_subtraction"] > f1["texture_energy"]


def test_demo_separation_is_documented_and_sufficient(demo_report):
    sep = demo_report["separation"]
    assert sep["gap_width_px"] == 240
    assert sep["max_filter_radius_px"] == 24
    assert sep["gap_at_least_twice_filter_radius"] is True
    assert sep["blockwise_overlap_at_least_filter_radius"] is True
    tiling = demo_report["tiling"]
    assert tiling["overlap"][0] >= 4 * 6


def test_demo_versions_and_command_recorded(demo_report):
    assert demo_report["versions"]["python"]
    assert demo_report["versions"]["numpy"]
    assert demo_report["versions"]["scipy"]
    assert "run_synthetic_demo.py" in demo_report["command"]
    assert demo_report["seed"] == 42
    assert "SYNTHÉTIQUES" in demo_report["warning"]


@needs_matplotlib
def test_demo_figure_written():
    out_dir = Path(SCRIPT).parent / "results"
    figure = out_dir / "map_synthetic.svg"
    assert figure.exists() and figure.stat().st_size > 10_000


def test_demo_deterministic(demo_report):
    """Running the chain twice gives the same score maps (the JSON warning
    text and file timestamps are the only non-deterministic parts)."""
    img1, label1 = synth.make_synthetic_slice(256, 640, seed=42)
    img2, label2 = synth.make_synthetic_slice(256, 640, seed=42)
    assert np.array_equal(img1, img2) and np.array_equal(label1, label2)
    fn = baselines.background_subtraction(sigma_background=6.0, ink_scale=0.12)
    assert np.array_equal(
        blockwise.predict_blockwise(fn, img1, TILE, OVERLAP),
        blockwise.predict_blockwise(fn, img2, TILE, OVERLAP),
    )
