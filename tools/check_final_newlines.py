#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
CHECKED = [
    "Makefile",
    "registry/spine-v0.txt",
    "manifest/active-spine.repos.toml",
    "tools/check_spine_v0.py",
    "tools/check_active_spine_overlay.py",
]


def main() -> int:
    failed = False
    for rel in CHECKED:
        path = ROOT / rel
        data = path.read_bytes()
        if not data:
            print(f"ERR: empty file: {rel}", file=sys.stderr)
            failed = True
            continue
        if not data.endswith(b"\n"):
            print(f"ERR: missing trailing newline: {rel}", file=sys.stderr)
            failed = True
    if failed:
        return 1
    print("OK: checked files end with trailing newlines")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
