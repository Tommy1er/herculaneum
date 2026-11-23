"""Reproduce villa #2482 with the official vc_reader package (no GPU).

Builds a synthetic 12 x 12 tifxyz surface and checks, with vc_reader.tifxyz.read:
  1. which mask pixel values (0, 1, 128, 254, 255) leave a vertex valid;
  2. what happens when mask.tif does not tile the 12 x 12 grid (9 x 9).

Usage:  python repro.py [--villa-commit SHA] [--out results.json]
Requires: numpy, tifffile, vc_reader (built from ScrollPrize/villa/vc_reader).
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import tempfile
from pathlib import Path

import numpy as np
import tifffile

ROWS = COLS = 12
TESTED_VALUES = [0, 1, 128, 254, 255]
# One probe vertex per tested value, on the diagonal; every other pixel stays 255.
PROBES = {v: (2 * i + 1, 2 * i + 1) for i, v in enumerate(TESTED_VALUES)}


def write_surface(path: Path, mask: np.ndarray | None) -> None:
    path.mkdir(parents=True)
    r, c = np.meshgrid(np.arange(ROWS, dtype=np.float32), np.arange(COLS, dtype=np.float32), indexing="ij")
    xyz = np.stack([c * 2 + 10, r * 2 + 20, np.full_like(r, 30)], -1).astype(np.float32)
    for axis, name in enumerate("xyz"):
        tifffile.imwrite(path / f"{name}.tif", xyz[..., axis])
    if mask is not None:
        tifffile.imwrite(path / "mask.tif", mask)
    meta = {"uuid": path.name, "scale": [1, 1], "bbox": [[-1, -1, -1], [-1, -1, -1]]}
    (path / "meta.json").write_text(json.dumps(meta))


def value_case(root: Path, tifxyz) -> dict:
    mask = np.full((ROWS, COLS), 255, np.uint8)
    for value, (y, x) in PROBES.items():
        mask[y, x] = value
    write_surface(root / "values", mask)
    valid = np.asarray(tifxyz.read(root / "values").valid)
    per_value = {str(v): bool(valid[y, x]) for v, (y, x) in PROBES.items()}
    others = valid.copy()
    for y, x in PROBES.values():
        others[y, x] = True
    return {"vertex_valid_by_mask_value": per_value, "all_other_vertices_valid": bool(others.all())}


def size_case(root: Path, tifxyz) -> dict:
    write_surface(root / "size", np.full((9, 9), 255, np.uint8))
    try:
        surface = tifxyz.read(root / "size")
    except Exception as exc:  # report, do not hide
        return {"mask_shape": [9, 9], "outcome": "error", "error_type": type(exc).__name__, "message": str(exc)}
    valid = np.asarray(surface.valid)
    return {"mask_shape": [9, 9], "outcome": "loaded", "valid_vertices": int(valid.sum()), "total_vertices": int(valid.size)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--villa-commit", default="unknown")
    parser.add_argument("--out", type=Path, default=Path("results.json"))
    args = parser.parse_args()

    from vc_reader import tifxyz  # imported here so --help works without the package

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        results = {
            "issue": "ScrollPrize/villa#2482",
            "villa_commit": args.villa_commit,
            "python": platform.python_version(),
            "platform": platform.platform(),
            "grid": [ROWS, COLS],
            "value_case": value_case(root, tifxyz),
            "size_case": size_case(root, tifxyz),
        }

    documented = {str(v): v >= 255 for v in TESTED_VALUES}  # lasagna/tifxyz_format.md and vc_object_store
    observed = results["value_case"]["vertex_valid_by_mask_value"]
    results["differs_from_documented_rule"] = [v for v in documented if documented[v] != observed[v]]

    args.out.write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))
    print("\nmask value | vertex valid (vc_reader) | documented rule (>= 255)")
    for v in TESTED_VALUES:
        print(f"{v:>10} | {str(observed[str(v)]):>24} | {str(documented[str(v)]):>24}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
