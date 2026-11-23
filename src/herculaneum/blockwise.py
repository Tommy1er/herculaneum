"""Overlapping tile planning and block-by-block processing.

Goal: handle very large volumes (the Vesuvius Challenge OME-Zarr scans)
without ever loading more than one tile in memory.

Principle
---------
1. :func:`plan_tiles` computes the tile origins and their "core": the area
   each tile is responsible for. The cores form an EXACT partition of the
   image — no pixel written twice, no pixel forgotten. A consistency check
   (sum of core volumes) runs at construction time and raises an error on a
   bug instead of silently producing a wrong assembly.
2. :func:`iter_tiles` yields each tile with its context (overlap included).
   On a NumPy array, ``data`` is a view, not a copy.
3. :class:`BlockwiseAccumulator` and :func:`predict_blockwise` assemble the
   result by writing cores only, and refuse to return an incomplete array
   (explicit error, never silent zeros).

The overlap gives ``predict_fn`` some context: for a Gaussian filter of
sigma ``s`` (scipy, truncate=4.0 by default, i.e. a radius of ``4 * s``),
taking ``overlap >= 4 * s`` guarantees core values identical to the
whole-image computation — a property tested in ``tests/test_pipeline_h001.py``.

This module complements ``herculaneum.tiles``: ``tiles.spatial_split`` plans
the evaluation zones (tuning/test separation), ``blockwise`` processes large
arrays tile by tile. Imported from the GLM prototype (issue #3); logic
unchanged, comments and identifiers translated to English per AGENTS.md.

Compatibility: any object indexable by NumPy slices works
(``numpy.ndarray``, ``zarr`` arrays...) because only ``arr[slices]``
indexing is used — large volumes are never materialized.
"""

from __future__ import annotations

import operator
from dataclasses import dataclass
from itertools import product
from typing import Any, Callable, Iterator

import numpy as np

__all__ = [
    "TilePlan",
    "TileView",
    "BlockwiseAccumulator",
    "plan_tiles",
    "iter_tiles",
    "predict_blockwise",
]


@dataclass(frozen=True)
class TilePlan:
    """Tiling plan of an array of shape ``shape``.

    ``tile_size`` is the EFFECTIVE tile size per axis: when an axis is
    smaller than the requested tile, the whole axis becomes a single tile and
    the effective size is the axis size.
    """

    shape: tuple[int, ...]
    tile_size: tuple[int, ...]
    overlap: tuple[int, ...]
    origins: list[tuple[int, ...]]
    cores: list[tuple[slice, ...]]

    def __len__(self) -> int:
        return len(self.origins)

    def slices(self, index: int) -> tuple[slice, ...]:
        """Window (overlap included) of tile ``index``."""
        if not 0 <= index < len(self):
            raise IndexError(f"tile index {index} out of range (0..{len(self) - 1}).")
        o = self.origins[index]
        return tuple(slice(oi, oi + ti) for oi, ti in zip(o, self.tile_size))


@dataclass
class TileView:
    """A tile and its coordinates, produced by :func:`iter_tiles`."""

    index: int
    origin: tuple[int, ...]
    slices: tuple[slice, ...]
    core: tuple[slice, ...]
    data: Any


def _axis_origins(n: int, t: int, o: int) -> tuple[list[int], int]:
    """1D tile origins on an axis of size ``n`` + effective tile size.

    Guarantees the last tile ends exactly at ``n`` (if needed by pulling the
    last tile against the border), so the union of tiles covers the axis
    without overshooting.
    """
    if n <= t:
        return [0], n
    step = t - o
    origins = list(range(0, n - t + 1, step))
    if origins[-1] + t < n:
        origins.append(n - t)
    if origins[-1] + t != n:
        raise RuntimeError(
            f"incomplete axis coverage (n={n}, tile={t}, overlap={o}): "
            "planner bug."
        )
    return origins, t


def _axis_cores(n: int, origins: list[int], extent: int) -> list[tuple[int, int]]:
    """1D core bounds: exact partition of [0, n).

    The seam between two consecutive tiles sits in the middle of their
    overlap zone (rounded up), which spreads the context evenly and makes
    the cores disjoint by construction.
    """
    seams: list[int] = []
    for i in range(len(origins) - 1):
        w = origins[i] + extent - origins[i + 1]
        if w < 0:
            raise RuntimeError(
                f"negative overlap ({w}) between tiles {i} and {i + 1}: internal bug."
            )
        seam = origins[i + 1] + ((w + 1) // 2 if w > 0 else 0)
        seams.append(seam)
    cores: list[tuple[int, int]] = []
    for i in range(len(origins)):
        start = 0 if i == 0 else seams[i - 1]
        end = n if i == len(origins) - 1 else seams[i]
        if end <= start:
            raise RuntimeError(
                f"empty core [{start}, {end}) for tile {i}: internal bug."
            )
        cores.append((start, end))
    return cores


def plan_tiles(shape, tile, overlap) -> TilePlan:
    """Build the tiling plan of an array of shape ``shape``.

    Parameters: ``shape`` array shape (2D, 3D...), ``tile`` target tile size
    per axis, ``overlap`` overlap per axis, with the constraint
    ``0 <= overlap < tile`` on each axis.
    """
    shape = tuple(operator.index(s) for s in shape)
    tile = tuple(operator.index(t) for t in tile)
    overlap = tuple(operator.index(o) for o in overlap)
    if len(shape) == 0:
        raise ValueError("empty shape: at least one axis is required.")
    if not (len(shape) == len(tile) == len(overlap)):
        raise ValueError(
            f"inconsistent ndim: shape {shape}, tile {tile}, overlap {overlap}."
        )
    for axis, (n, t, o) in enumerate(zip(shape, tile, overlap)):
        if n < 1:
            raise ValueError(f"axis {axis}: image size {n} < 1.")
        if t < 1:
            raise ValueError(f"axis {axis}: tile size {t} < 1.")
        if not 0 <= o < t:
            raise ValueError(
                f"axis {axis}: overlap {o} out of bounds (constraint: "
                f"0 <= overlap < tile = {t})."
            )

    axis_origins: list[list[int]] = []
    extents: list[int] = []
    axis_cores: list[list[tuple[int, int]]] = []
    for n, t, o in zip(shape, tile, overlap):
        origins, extent = _axis_origins(n, t, o)
        axis_origins.append(origins)
        extents.append(extent)
        axis_cores.append(_axis_cores(n, origins, extent))

    origins_list = [tuple(c) for c in product(*axis_origins)]
    cores_list = [
        tuple(slice(a, b) for a, b in c) for c in product(*axis_cores)
    ]

    # Allocation-free consistency check: the sum of core volumes must equal
    # the total volume (exact partition). Any divergence is a planning bug we
    # refuse to let through.
    total = 1
    for n in shape:
        total *= n
    cores_sum = 0
    for core in cores_list:
        vol = 1
        for s in core:
            vol *= s.stop - s.start
        cores_sum += vol
    if cores_sum != total:
        raise RuntimeError(
            f"inconsistent partition: cores = {cores_sum} pixels, image = "
            f"{total} pixels — planner bug."
        )

    return TilePlan(
        shape=shape,
        tile_size=tuple(extents),
        overlap=overlap,
        origins=origins_list,
        cores=cores_list,
    )


def iter_tiles(arr, plan: TilePlan) -> Iterator[TileView]:
    """Iterate over the tiles of ``arr`` according to ``plan``.

    On a NumPy array, ``TileView.data`` is a VIEW (no copy); on a zarr
    array, ``arr[slices]`` triggers reading only the tile data. ``core`` is
    the global slice the tile is allowed to write in the final result.
    """
    for i in range(len(plan)):
        sl = plan.slices(i)
        yield TileView(
            index=i,
            origin=plan.origins[i],
            slices=sl,
            core=plan.cores[i],
            data=arr[sl],
        )


class BlockwiseAccumulator:
    """Assemble a full result by writing tile cores only.

    The output array is allocated on the first ``write`` (its dtype is the
    dtype of the first written tile) and ``result()`` refuses to return an
    array whose pixels were covered by no core.
    """

    def __init__(self, shape, plan: TilePlan):
        self.shape = tuple(operator.index(s) for s in shape)
        if plan.shape != self.shape:
            raise ValueError(
                f"plan built for {plan.shape}, accumulator created for "
                f"{self.shape}."
            )
        self.plan = plan
        self._out: np.ndarray | None = None
        self._written = np.zeros(self.shape, dtype=bool)

    def write(self, index: int, tile_data) -> None:
        """Write the core of ``tile_data`` (tile ``index``) to the output."""
        sl = self.plan.slices(index)
        window = tuple(s.stop - s.start for s in sl)
        data = np.asarray(tile_data)
        if data.shape != window:
            raise ValueError(
                f"tile {index}: received shape {data.shape}, expected {window} "
                "(shape of plan.slices(index))."
            )
        core = self.plan.cores[index]
        core_local = tuple(
            slice(c.start - o, c.stop - o)
            for c, o in zip(core, self.plan.origins[index])
        )
        values = data[core_local]
        if self._out is None:
            self._out = np.zeros(self.shape, dtype=values.dtype)
        if self._written[core].any():
            raise ValueError(
                f"tile {index}: core pixels already written — overlapping "
                "cores, inconsistent tile plan."
            )
        self._out[core] = values
        self._written[core] = True

    def result(self) -> np.ndarray:
        """Return the assembled array, or raise if it is incomplete."""
        if self._out is None:
            raise ValueError("no tile written: empty result.")
        missing = int((~self._written).sum())
        if missing:
            raise ValueError(
                f"incomplete assembly: {missing} pixel(s) not covered by the "
                "cores of the written tiles."
            )
        return self._out


def predict_blockwise(
    predict_fn: Callable, arr, tile, overlap
) -> np.ndarray:
    """Apply ``predict_fn`` tile by tile and assemble the result.

    ``predict_fn`` receives each tile WITH its overlap context and must
    return an array of the same shape; only cores are written to the output.
    ``arr`` can be a ``numpy.ndarray`` (tiles are views) or a zarr array
    (block-wise reads): ``arr`` is never converted to a dense array, so a
    huge zarr volume stays processable.
    """
    plan = plan_tiles(tuple(arr.shape), tile, overlap)
    acc = BlockwiseAccumulator(tuple(arr.shape), plan)
    for view in iter_tiles(arr, plan):
        acc.write(view.index, predict_fn(view.data))
    return acc.result()
