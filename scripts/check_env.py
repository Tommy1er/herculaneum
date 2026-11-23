"""Print what this machine can do for HERCULANUM. Standard library only.

Usage:  python scripts/check_env.py
Paste the output into docs/contexte.md (task T02).
"""

from __future__ import annotations

import ctypes
import os
import platform
import shutil
import subprocess
import sys
from importlib import metadata

PACKAGES = ["numpy", "scipy", "scikit-image", "tifffile", "zarr", "pytest"]
MIN_PY = (3, 11)
MIN_RAM_GB = 8
MIN_FREE_DISK_GB = 20


def run(cmd: list[str]) -> str | None:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip() or None


def cpu_name() -> str:
    if sys.platform == "win32":
        name = run(["powershell", "-NoProfile", "-Command",
                    "(Get-CimInstance Win32_Processor).Name"])
        if name:
            return name
    elif sys.platform.startswith("linux"):
        try:
            with open("/proc/cpuinfo", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("model name"):
                        return line.split(":", 1)[1].strip()
        except OSError:
            pass
    return platform.processor() or "unknown"


def ram_gb() -> float | None:
    if sys.platform == "win32":
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
            return stat.ullTotalPhys / 1024**3
        return None
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1024**3
    except (ValueError, OSError, AttributeError):
        return None


def mark(ok: bool) -> str:
    return "OK " if ok else "!! "


def main() -> int:
    problems = 0
    print("=== HERCULANUM — environment check ===")
    print(f"OS        : {platform.platform()}")
    print(f"CPU       : {cpu_name()} ({os.cpu_count()} threads)")

    ram = ram_gb()
    ok = ram is not None and ram >= MIN_RAM_GB - 0.5
    problems += not ok
    print(f"{mark(ok)}RAM     : {ram:.1f} GB" if ram else "!! RAM     : unknown")

    free = shutil.disk_usage(os.getcwd()).free / 1024**3
    ok = free >= MIN_FREE_DISK_GB
    problems += not ok
    print(f"{mark(ok)}Disk    : {free:.1f} GB free (want >= {MIN_FREE_DISK_GB})")

    ok = sys.version_info[:2] >= MIN_PY
    problems += not ok
    print(f"{mark(ok)}Python  : {platform.python_version()} ({sys.executable})")

    git = run(["git", "--version"])
    problems += git is None
    print(f"{mark(git is not None)}Git     : {git or 'not found'}")

    for pkg in PACKAGES:
        try:
            version = metadata.version(pkg)
            print(f"OK {pkg:<14}: {version}")
        except metadata.PackageNotFoundError:
            problems += 1
            print(f"!! {pkg:<14}: missing (pip install -r requirements.txt)")

    print("GPU       : local GPU not used (CPU only); use Colab/Kaggle for GPU work")
    print(f"=== {problems} problem(s) ===")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
