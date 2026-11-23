"""Spatially separated tuning/test splits for 2D images.

Random pixel or tile splits leak information: neighbouring pixels are highly
correlated, so a method tuned on one tile and tested on the tile next to it
looks better than it is. Here the image is cut into bands along one axis; the
last band is used for testing, and tiles too close to the boundary are dropped.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Tile:
    y0: int
    y1: int
    x0: int
    x1: int

    def slice(self) -> tuple[slice, slice]:
        return slice(self.y0, self.y1), slice(self.x0, self.x1)


def grid_tiles(shape: tuple[int, int], tile: int) -> list[Tile]:
    """Non-overlapping full tiles covering ``shape`` (partial edge tiles are dropped)."""
    h, w = shape
    if tile <= 0:
        raise ValueError("tile must be positive")
    return [
        Tile(y, y + tile, x, x + tile)
        for y in range(0, h - tile + 1, tile)
        for x in range(0, w - tile + 1, tile)
    ]


def spatial_split(
    shape: tuple[int, int],
    tile: int,
    test_fraction: float = 0.25,
    axis: int = 1,
    *,
    gap: int,
) -> tuple[list[Tile], list[Tile]]:
    """Split full tiles into (tune, test) by position along ``axis``.

    Tiles whose far edge is at or before ``boundary - gap`` go to tune; tiles
    whose near edge is at or after ``boundary + gap`` go to test; tiles in
    between are dropped. ``boundary`` sits at ``(1 - test_fraction)`` of the
    axis length.

    ``gap`` has no default on purpose: it must be at least the largest x/y
    context radius of any method evaluated (H001 protocol). The two sets are
    then at least ``2 * gap`` pixels apart, so a filter of radius ``gap`` never
    reads the same raw pixel from both sides.
    """
    if not 0 < test_fraction < 1:
        raise ValueError("test_fraction must be in (0, 1)")
    if axis not in (0, 1):
        raise ValueError("axis must be 0 (rows) or 1 (columns)")
    if gap < 0:
        raise ValueError("gap must be >= 0")

    length = shape[axis]
    boundary = int(round(length * (1 - test_fraction)))
    tune: list[Tile] = []
    test: list[Tile] = []
    for t in grid_tiles(shape, tile):
        lo, hi = (t.y0, t.y1) if axis == 0 else (t.x0, t.x1)
        if hi <= boundary - gap:
            tune.append(t)
        elif lo >= boundary + gap:
            test.append(t)
    return tune, test


def tiles_mask(shape: tuple[int, int], tiles: list[Tile]) -> np.ndarray:
    """Boolean mask that is True on the given tiles."""
    mask = np.zeros(shape, dtype=bool)
    for t in tiles:
        mask[t.slice()] = True
    return mask
