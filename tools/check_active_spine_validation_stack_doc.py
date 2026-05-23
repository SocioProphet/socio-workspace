#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "governance" / "active-spine-validation-stack-2026-05-23.md"

REQUIRED = [
    "registry/spine-v0.txt",
    "manifest/active-spine.repos.toml",
    "governance/CANONICAL_SOURCES.yaml",
    "catalog/boundaries.yaml",
    "docs/TOPOLOGY.md",
    "spine-v0-validate",
    "active-spine-overlay-validate",
    "active-spine-sources-validate",
    "spine-canonical-sources-drift-validate",
    "topology-doc-active-spine-validate",
    "active-spine-boundaries-validate",
    "runner-overlay-discovery-validate",
    "runner-overlay-merge-order-validate",
    "hygiene-check",
    "tools/check_final_newlines.py",
    "Issue #364",
]


def main() -> int:
    text = DOC.read_text(encoding="utf-8")
    failed = False
    for needle in REQUIRED:
        if needle not in text:
            print(f"ERR: active-spine validation stack doc missing: {needle}", file=sys.stderr)
            failed = True
    if failed:
        return 1
    print("OK: active-spine validation stack doc is complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
