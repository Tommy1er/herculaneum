import pytest

from herculaneum.tiles import grid_tiles, spatial_split, tiles_mask


def test_grid_drops_partial_tiles():
    tiles = grid_tiles((100, 130), 32)
    assert len(tiles) == 3 * 4
    assert all(t.y1 <= 100 and t.x1 <= 130 for t in tiles)


@pytest.mark.parametrize("axis", [0, 1])
def test_split_is_disjoint_and_ordered(axis):
    tune, test = spatial_split((256, 256), 32, test_fraction=0.25, axis=axis)
    assert tune and test
    assert not (tiles_mask((256, 256), tune) & tiles_mask((256, 256), test)).any()
    key = (lambda t: (t.y0, t.y1)) if axis == 0 else (lambda t: (t.x0, t.x1))
    assert max(key(t)[1] for t in tune) <= min(key(t)[0] for t in test)


def test_gap_keeps_sets_apart():
    gap = 32
    tune, test = spatial_split((256, 256), 32, test_fraction=0.25, axis=1, gap=gap)
    assert min(t.x0 for t in test) - max(t.x1 for t in tune) >= 2 * gap


def test_invalid_arguments():
    with pytest.raises(ValueError):
        spatial_split((64, 64), 16, test_fraction=1.0)
    with pytest.raises(ValueError):
        spatial_split((64, 64), 16, axis=2)
    with pytest.raises(ValueError):
        spatial_split((64, 64), 16, gap=-1)
