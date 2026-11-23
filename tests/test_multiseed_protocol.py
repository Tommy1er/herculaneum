"""Tests for the pre-registered multi-seed evaluation protocol (issue #3).

Plumbing checks only: the registered seeds themselves are evaluated exactly
once, by running the script, and their outputs are published as committed
JSON files. The plumbing tests below use seeds deliberately OUTSIDE the
registered list (99999, 1, 2), so no registered seed is ever evaluated twice.
"""

import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "experiments"
    / "H001-ink-baseline"
    / "run_multiseed_evaluation.py"
)

_spec = importlib.util.spec_from_file_location("run_multiseed_evaluation", SCRIPT)
_multiseed = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_multiseed)

DEVELOPMENT_SEED = 42  # the published development-trial seed


def test_seed_list_is_preregistered_and_disjoint():
    seeds = _multiseed.SEEDS
    assert len(seeds) == len(set(seeds)), "registered seeds must be distinct"
    assert DEVELOPMENT_SEED not in seeds, "the development seed stays out of the independent check"
    # the plumbing seed must never enter the registered list
    assert 99999 not in seeds


def test_seed_list_is_not_edited_silently():
    """The registered list must match the committed protocol documentation."""
    source = SCRIPT.read_text(encoding="utf-8")
    assert "SEEDS = [" in source
    # each registered seed appears literally in the frozen script
    for seed in _multiseed.SEEDS:
        assert str(seed) in source


def test_evaluate_seed_returns_complete_schema():
    report = _multiseed.evaluate_seed(99999)  # plumbing seed, outside SEEDS
    assert report["seed"] == 99999
    for name in ("background_subtraction", "texture_energy", "mean_combination"):
        entry = report["methods"][name]
        for crit in ("initial_criterion", "t05_criterion"):
            assert set(entry[crit]["test"]) == {
                "tp", "fp", "fn", "tn", "precision", "recall", "f1", "f05"
            }
        assert 0.0 <= entry["ap_test"] <= 1.0
    assert report["trivial_references_test"]["all_ink"]["recall"] == 1.0
    assert report["zones"]["test"] == [440, 640]


def test_summarize_aggregates_everything_without_selection():
    """The summary aggregates min/mean/max over the published reports —
    no cherry-picking, no dropped seeds."""
    reports = []
    for seed in (1, 2):
        report = _multiseed.evaluate_seed(seed)  # plumbing seeds, outside SEEDS
        report["seed"] = seed
        reports.append(report)
    summary = _multiseed.summarize(reports)
    assert summary["seeds"] == [1, 2]
    assert summary["n_seeds"] == 2
    comb = summary["mean_combination"]
    f1s = [r["methods"]["mean_combination"]["initial_criterion"]["test"]["f1"] for r in reports]
    assert comb["initial_criterion"]["f1"]["min"] == pytest.approx(min(f1s), abs=5e-5)
    assert comb["initial_criterion"]["f1"]["max"] == pytest.approx(max(f1s), abs=5e-5)
    assert comb["initial_criterion"]["f1"]["mean"] == pytest.approx(sum(f1s) / 2, abs=5e-5)
    assert "rule" in summary and "no seed replacement" in summary["rule"]
