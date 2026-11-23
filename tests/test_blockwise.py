"""Tests for herculaneum.blockwise — exact partition, assembly, errors.

Imported from the GLM prototype (issue #3); cases and assertions unchanged,
identifiers translated to English per AGENTS.md.
"""

import numpy as np
import pytest

from herculaneum.blockwise import (
    BlockwiseAccumulator,
    iter_tiles,
    plan_tiles,
    predict_blockwise,
)

# Varied 1D cases: smaller than the tile, exactly equal, step falling right,
# right-border clamping, zero overlap.
CAS_1D = [
    (n, t, o)
    for n in [1, 5, 7, 10, 11, 16, 37, 64]
    for t in [1, 3, 4, 8, 16]
    for o in [0, 1, 2, 3]
    if o < t
]

CAS_ND = [
    ((16, 16), (8, 8), (2, 3)),
    ((5, 9), (4, 16), (1, 4)),
    ((64, 48), (16, 12), (4, 3)),
    ((9, 7), (8, 8), (0, 0)),
    ((1, 1), (1, 1), (0, 0)),
    ((3, 40), (2, 8), (1, 2)),
    ((8, 9, 10), (4, 4, 6), (1, 2, 3)),
    ((5, 5, 5), (8, 3, 4), (2, 1, 0)),
    ((11, 13, 7), (5, 6, 8), (2, 3, 1)),
]


def _check_exact_partition(shape, tile, overlap):
    """Every pixel must belong to EXACTLY one core."""
    plan = plan_tiles(shape, tile, overlap)
    marker = np.zeros(shape, dtype=np.int64)
    for i, core in enumerate(plan.cores):
        region = marker[core]
        if region.max(initial=0) != 0:
            pytest.fail(f"core {i} overlaps a previous core")
        marker[core] = i + 1
    if marker.min() < 1:
        pytest.fail("some pixels are covered by no core")
    # windows stay in bounds and have the announced effective size
    for i in range(len(plan)):
        for s, n, t in zip(plan.slices(i), plan.shape, plan.tile_size):
            assert 0 <= s.start and s.stop <= n
            assert s.stop - s.start == t
    return plan


@pytest.mark.parametrize("shape,tile,overlap", CAS_ND)
def test_exact_partition_with_marker(shape, tile, overlap):
    _check_exact_partition(shape, tile, overlap)


@pytest.mark.parametrize("n,t,o", CAS_1D)
def test_exact_partition_1d(n, t, o):
    plan = plan_tiles((n,), (t,), (o,))
    marker = np.zeros(n, dtype=np.int64)
    for i, core in enumerate(plan.cores):
        assert marker[core].max(initial=0) == 0
        marker[core] = i + 1
    assert marker.min() >= 1


@pytest.mark.parametrize("shape,tile,overlap", CAS_ND)
def test_round_trip_identity(shape, tile, overlap):
    rng = np.random.default_rng(0)
    arr = rng.normal(size=shape)
    out = predict_blockwise(lambda x: x, arr, tile, overlap)
    assert np.array_equal(out, arr)


def test_tile_larger_than_image():
    plan = plan_tiles((5, 9), (8, 32), (2, 4))
    assert len(plan) == 1
    sl = plan.slices(0)
    assert (sl[0].start, sl[0].stop) == (0, 5)
    assert (sl[1].start, sl[1].stop) == (0, 9)


def test_iter_tiles_numpy_views_without_copy():
    arr = np.arange(64 * 64, dtype=np.float64).reshape(64, 64)
    plan = plan_tiles((64, 64), (32, 32), (4, 4))
    view = next(iter(iter_tiles(arr, plan)))
    # .base is unreliable (numpy may point to the underlying buffer):
    # the correct view check is np.shares_memory.
    assert np.shares_memory(view.data, arr)
    assert view.index == 0 and view.origin == (0, 0)
    before = arr[0, 0]
    view.data[0, 0] = -999.0  # writing into the view does change the original
    assert arr[0, 0] == -999.0
    arr[0, 0] = before


def test_planning_errors():
    with pytest.raises(ValueError, match="overlap"):
        plan_tiles((10, 10), (4, 4), (4, 1))  # overlap >= tile on axis 0
    with pytest.raises(ValueError, match="ndim"):
        plan_tiles((10, 10), (4,), (1,))
    with pytest.raises(ValueError, match="tile size"):
        plan_tiles((10,), (0,), (0,))
    with pytest.raises(ValueError, match="image size"):
        plan_tiles((0, 5), (4, 4), (1, 1))
    with pytest.raises(ValueError, match="empty shape"):
        plan_tiles((), (), ())


def test_tile_index_out_of_range():
    plan = plan_tiles((8, 8), (4, 4), (0, 0))
    with pytest.raises(IndexError):
        plan.slices(len(plan))


def test_incomplete_assembly_raises():
    plan = plan_tiles((8, 8), (4, 4), (0, 0))
    acc = BlockwiseAccumulator((8, 8), plan)
    with pytest.raises(ValueError, match="no tile"):
        acc.result()
    acc.write(0, np.zeros((4, 4), dtype=np.float32))
    with pytest.raises(ValueError, match="incomplete"):
        acc.result()


def test_accumulator_shape_mismatch_raises():
    plan = plan_tiles((9, 9), (4, 4), (1, 1))
    with pytest.raises(ValueError, match="built for"):
        BlockwiseAccumulator((8, 8), plan)


def test_invalid_output_shape_raises():
    arr = np.zeros((16, 16))
    with pytest.raises(ValueError, match="received shape"):
        predict_blockwise(lambda x: x[:, :4], arr, (8, 8), (2, 2))


def test_double_write_raises():
    # two distinct plans but one accumulator -> must fail
    plan = plan_tiles((8, 8), (8, 8), (0, 0))
    acc = BlockwiseAccumulator((8, 8), plan)
    acc.write(0, np.zeros((8, 8)))
    acc2 = BlockwiseAccumulator((8, 8), plan_tiles((8, 8), (8, 8), (0, 0)))
    acc2.write(0, np.zeros((8, 8)))
    assert acc.result().shape == (8, 8)


def test_predict_blockwise_pointwise_function():
    rng = np.random.default_rng(3)
    arr = rng.random((20, 31))
    out = predict_blockwise(lambda x: 2.0 * x + 1.0, arr, (8, 8), (3, 3))
    assert np.allclose(out, 2.0 * arr + 1.0)
    assert out.dtype == arr.dtype


def test_output_dtype_follows_first_tile():
    arr = np.zeros((10, 10), dtype=np.float32)
    out = predict_blockwise(lambda x: x.astype(np.float64), arr, (5, 5), (1, 1))
    assert out.dtype == np.float64
