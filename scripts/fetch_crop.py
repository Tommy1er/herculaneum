"""Download one window of a Vesuvius Challenge ink segment, without the whole scroll.

Only the zarr blocks that intersect the window are fetched (HTTP range of
chunks), so a 2048 x 3072 window costs ~100 MB instead of tens of GB.

Usage:
    python scripts/fetch_crop.py --y0 3584 --x0 24192 --height 2048 --width 3072 \
        --out data/phercparis4_w00_y3584_x24192.npz

Writes the .npz (volume uint8 [z, y, x], ink bool [y, x], supervision bool [y, x])
and a manifest JSON next to it (sources, window, checksums, label semantics).
Requires: numpy, zarr<3, fsspec, aiohttp, requests.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from importlib import metadata
from pathlib import Path

import numpy as np

DEFAULT_SEGMENT = (
    "https://huggingface.co/buckets/scrollprize/datasets/resolve/"
    "ink/phercparis4/w00_20231016151002"
)


def sha256(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def label_plane(array, ys: slice, xs: slice, name: str) -> tuple[np.ndarray, str]:
    """Return the 2D label map stored in a 3D stack.

    In the PHercParis4 ink segments the 2D labels sit on a single layer (the
    middle one, z = 32 of 65) and every other layer is 0. This is checked on
    the window, not assumed: exactly one non-empty layer, or all layers equal.
    """
    stack = np.asarray(array[:, ys, xs])
    values = np.unique(stack)
    if not set(values.tolist()) <= {0, 255}:
        raise ValueError(f"{name}: unexpected values {values[:10]} (expected 0/255)")
    nonempty = [int(z) for z in np.flatnonzero(stack.reshape(stack.shape[0], -1).any(axis=1))]
    if len(nonempty) == 1:
        z = nonempty[0]
        return stack[z] == 255, f"stored on layer {z} only (all {stack.shape[0] - 1} other layers are 0)"
    if all(np.array_equal(stack[0], layer) for layer in stack[1:]):
        return stack[0] == 255, "identical across all layers; layer 0 used"
    raise ValueError(f"{name}: labels on several different layers {nonempty[:10]}; inspect before use")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--segment", default=DEFAULT_SEGMENT, help="base URL of the segment folder")
    p.add_argument("--segment-id", default="w00_20231016151002")
    p.add_argument("--y0", type=int, required=True)
    p.add_argument("--x0", type=int, required=True)
    p.add_argument("--height", type=int, required=True)
    p.add_argument("--width", type=int, required=True)
    p.add_argument("--selection-rule", default="", help="how the window was chosen (recorded in the manifest)")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()

    import zarr  # imported here so --help works without it

    sid = args.segment_id
    uris = {
        "volume": f"{args.segment}/{sid}.zarr/0",
        "ink": f"{args.segment}/{sid}_inklabels.zarr/0",
        "supervision": f"{args.segment}/{sid}_supervision_mask.zarr/0",
    }
    arrays = {k: zarr.open(u, mode="r") for k, u in uris.items()}
    shapes = {k: list(a.shape) for k, a in arrays.items()}
    if len({tuple(s) for s in shapes.values()}) != 1:
        raise ValueError(f"volume and labels do not share a grid: {shapes}")

    ys = slice(args.y0, args.y0 + args.height)
    xs = slice(args.x0, args.x0 + args.width)
    full_h, full_w = shapes["volume"][1:]
    if ys.stop > full_h or xs.stop > full_w or args.y0 < 0 or args.x0 < 0:
        raise ValueError(f"window outside the segment ({full_h} x {full_w})")

    print(f"fetching volume {uris['volume']} ...", flush=True)
    volume = np.asarray(arrays["volume"][:, ys, xs])
    print("fetching labels ...", flush=True)
    ink, ink_note = label_plane(arrays["ink"], ys, xs, "ink")
    sup, sup_note = label_plane(arrays["supervision"], ys, xs, "supervision")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.out, volume=volume, ink=ink, supervision=sup)

    manifest = {
        "status": "data fetched; split and methods not yet frozen",
        "fragment_id": "PHercParis4",
        "surface_id": sid,
        "source_volume_uri": uris["volume"],
        "source_mask_uri": uris["ink"],
        "source_validity_mask_uri": uris["supervision"],
        "source_index": "https://scrollprize.org/tutorial5",
        "license_and_attribution": "Vesuvius Challenge open data; check scrollprize.org data terms before redistribution",
        "access_date_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "source_array_shape_zyx": shapes["volume"],
        "source_chunks_zyx": list(arrays["volume"].chunks),
        "selected_roi_zyx": {"z": [0, shapes["volume"][0]], "y": [ys.start, ys.stop], "x": [xs.start, xs.stop]},
        "roi_selection_rule": args.selection_rule,
        "image_shape_zyx": list(volume.shape),
        "axes_orientation": "z = layer index of the flattened surface volume (65 layers), y/x = surface pixels",
        "intensity_preprocessing": "none (raw uint8)",
        "mask_semantics": {
            "ink": "255 = ink annotated; 0 = no ink (meaningful only where supervision = 255)",
            "supervision": "255 = pixel annotated and usable for scoring; 0 = excluded",
            "ink_layers": ink_note,
            "supervision_layers": sup_note,
            "provenance": "annotations come from the reading work on this scroll; no separate validation mask is provided",
        },
        "label_registration_transform": "none: labels and volume share the same zarr grid and chunking",
        "counts": {
            "pixels": int(ink.size),
            "supervised": int(sup.sum()),
            "ink_in_supervised": int((ink & sup).sum()),
        },
        "checksums_sha256": {"volume": sha256(volume), "ink": sha256(ink), "supervision": sha256(sup)},
        "dependency_versions": {pkg: metadata.version(pkg) for pkg in ("numpy", "zarr", "fsspec")},
        "output_file": str(args.out),
    }
    manifest_path = args.out.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest["counts"]), "->", args.out, "and", manifest_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
