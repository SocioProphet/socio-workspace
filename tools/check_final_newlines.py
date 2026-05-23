#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
CHECKED = [
    "Makefile",
    "registry/spine-v0.txt",
    "manifest/active-spine.repos.toml",
    "governance/CANONICAL_SOURCES.yaml",
    "catalog/boundaries.yaml",
    "docs/governance/active-spine-audit-2026-05-23.md",
    "docs/governance/runner-overlay-integration-note-2026-05-23.md",
    "tools/check_spine_v0.py",
    "tools/check_active_spine_overlay.py",
    "tools/check_active_spine_sources.py",
    "tools/check_active_spine_boundaries.py",
    "tools/check_runner_overlay_discovery.py",
    "tools/check_runner_overlay_merge_order.py",
    "tools/runner/manifest_layers.py",
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
