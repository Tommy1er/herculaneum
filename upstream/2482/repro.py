"""Reproduce villa #2482 with the official readers (no GPU).

Builds synthetic 12 x 12 tifxyz surfaces and checks:
  1. which mask pixel values (0, 1, 128, 254, 255) leave a vertex valid;
  2. what happens when mask.tif does not tile the 12 x 12 grid (9 x 9).

Reader A: vc_reader.tifxyz.read (used by VC3D and vc_tifxyz2obj).
Reader B (optional, --vos-bin): vc_object_store ingestion. The same files are
ingested with vc_object_ingest, exported with vc_object_export --valid-only
(invalid vertices written as missing points), and read back with vc_reader.
Values 0 and 255 are controls: every rule agrees on them.

Usage:  python repro.py [--villa-commit SHA] [--vos-bin DIR] [--out results.json]
Requires: numpy, tifffile, vc_reader (built from ScrollPrize/villa/vc_reader);
for reader B, the vc_object_ingest and vc_object_export binaries.
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

import numpy as np
import tifffile

ROWS = COLS = 12
TESTED_VALUES = [0, 1, 128, 254, 255]
# One probe vertex per tested value, on the diagonal; every other pixel stays 255.
PROBES = {v: (2 * i + 1, 2 * i + 1) for i, v in enumerate(TESTED_VALUES)}


def surface_uuid(name: str) -> str:
    # vc_object_store requires a real UUID; derive it so runs are deterministic.
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"herculaneum/villa-2482/{name}"))


def write_surface(path: Path, mask: np.ndarray | None) -> str:
    path.mkdir(parents=True)
    r, c = np.meshgrid(np.arange(ROWS, dtype=np.float32), np.arange(COLS, dtype=np.float32), indexing="ij")
    xyz = np.stack([c * 2 + 10, r * 2 + 20, np.full_like(r, 30)], -1).astype(np.float32)
    for axis, name in enumerate("xyz"):
        tifffile.imwrite(path / f"{name}.tif", xyz[..., axis])
    if mask is not None:
        tifffile.imwrite(path / "mask.tif", mask)
    uid = surface_uuid(path.name)
    meta = {"uuid": uid, "scale": [1, 1], "bbox": [[-1, -1, -1], [-1, -1, -1]]}
    (path / "meta.json").write_text(json.dumps(meta))
    return uid


def probe_validity(valid: np.ndarray) -> tuple[dict[str, bool], bool]:
    per_value = {str(v): bool(valid[y, x]) for v, (y, x) in PROBES.items()}
    others = valid.copy()
    for y, x in PROBES.values():
        others[y, x] = True
    return per_value, bool(others.all())


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=300)


class ObjectStore:
    """Reader B: round trip through vc_object_ingest / vc_object_export."""

    def __init__(self, bin_dir: Path, work: Path):
        self.ingest_bin = str(bin_dir / "vc_object_ingest")
        self.export_bin = str(bin_dir / "vc_object_export")
        self.work = work

    def ingest(self, surface: Path) -> tuple[Path, subprocess.CompletedProcess]:
        db = self.work / f"{surface.name}.vcobj"
        proc = run([self.ingest_bin, "--db", str(db), "--author", "herculaneum",
                    "--surface", str(surface), "--no-progress"])
        return db, proc

    def valid(self, surface: Path, uid: str, tifxyz) -> np.ndarray:
        db, proc = self.ingest(surface)
        if proc.returncode != 0 or "1 ingested" not in proc.stdout:
            raise RuntimeError(f"ingest failed: {proc.stdout.strip()} {proc.stderr.strip()}")
        out = self.work / f"{surface.name}-export"
        proc = run([self.export_bin, "--db", str(db), "--uuid", uid, "--output", str(out), "--valid-only"])
        if proc.returncode != 0:
            raise RuntimeError(f"export failed: {proc.stdout.strip()} {proc.stderr.strip()}")
        return np.asarray(tifxyz.read(out).valid)


def value_case(root: Path, tifxyz, store: ObjectStore | None) -> dict:
    mask = np.full((ROWS, COLS), 255, np.uint8)
    for value, (y, x) in PROBES.items():
        mask[y, x] = value
    surface = root / "values"
    uid = write_surface(surface, mask)

    readers = {"vc_reader": np.asarray(tifxyz.read(surface).valid)}
    if store is not None:
        readers["vc_object_store"] = store.valid(surface, uid, tifxyz)

    result = {}
    for name, valid in readers.items():
        per_value, others_ok = probe_validity(valid)
        result[name] = {"vertex_valid_by_mask_value": per_value, "all_other_vertices_valid": others_ok}
    if store is not None:
        a, b = readers["vc_reader"], readers["vc_object_store"]
        result["readers_disagree_on_mask_values"] = [
            str(v) for v, (y, x) in PROBES.items() if a[y, x] != b[y, x]
        ]
        result["readers_disagree_on_other_vertices"] = int(
            sum(a[y, x] != b[y, x] for y in range(ROWS) for x in range(COLS) if (y, x) not in PROBES.values())
        )
    return result


def size_case(root: Path, tifxyz, store: ObjectStore | None) -> dict:
    surface = root / "size"
    write_surface(surface, np.full((9, 9), 255, np.uint8))
    result: dict = {"mask_shape": [9, 9]}
    try:
        valid = np.asarray(tifxyz.read(surface).valid)
        result["vc_reader"] = {"outcome": "loaded", "valid_vertices": int(valid.sum()), "total_vertices": int(valid.size)}
    except Exception as exc:  # report, do not hide
        result["vc_reader"] = {"outcome": "error", "error_type": type(exc).__name__, "message": str(exc)}
    if store is not None:
        _, proc = store.ingest(surface)
        ingested = "1 ingested" in proc.stdout
        result["vc_object_store"] = {
            "outcome": "ingested" if ingested else "rejected",
            "message": (proc.stdout + proc.stderr).strip().splitlines()[-1:] or [""],
        }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--villa-commit", default="unknown")
    parser.add_argument("--vos-bin", type=Path, help="directory with vc_object_ingest and vc_object_export")
    parser.add_argument("--out", type=Path, default=Path("results.json"))
    args = parser.parse_args()

    from vc_reader import tifxyz  # imported here so --help works without the package

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        store = ObjectStore(args.vos_bin, root) if args.vos_bin else None
        results = {
            "issue": "ScrollPrize/villa#2482",
            "villa_commit": args.villa_commit,
            "python": platform.python_version(),
            "platform": platform.platform(),
            "grid": [ROWS, COLS],
            "value_case": value_case(root, tifxyz, store),
            "size_case": size_case(root, tifxyz, store),
        }

    documented = {str(v): v >= 255 for v in TESTED_VALUES}  # lasagna/tifxyz_format.md, vc_object_store docs
    observed = results["value_case"]["vc_reader"]["vertex_valid_by_mask_value"]
    results["vc_reader_differs_from_documented_rule"] = [v for v in documented if documented[v] != observed[v]]

    args.out.write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))

    names = [n for n in ("vc_reader", "vc_object_store") if n in results["value_case"]]
    print("\nmask value | " + " | ".join(f"valid ({n})" for n in names) + " | documented (>= 255)")
    for v in TESTED_VALUES:
        cells = [str(results["value_case"][n]["vertex_valid_by_mask_value"][str(v)]) for n in names]
        print(f"{v:>10} | " + " | ".join(f"{c:>{len(n) + 8}}" for c, n in zip(cells, names)) + f" | {documented[str(v)]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
