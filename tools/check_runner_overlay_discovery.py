#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools" / "runner" / "runner.py"
OVERLAY = ROOT / "manifest" / "active-spine.repos.toml"

REQUIRED_RUNNER_MARKERS = [
    'MANIFEST_PATH = ROOT / "manifest" / "workspace.toml"',
    'OVERRIDES_PATH = ROOT / "manifest" / "overrides.toml"',
    "def merge_manifest_and_overrides",
    "def load_workspace_and_repos",
]


def main() -> int:
    runner_text = RUNNER.read_text(encoding="utf-8")
    failed = False

    if not OVERLAY.exists():
        print(f"ERR: missing active spine overlay: {OVERLAY.relative_to(ROOT)}", file=sys.stderr)
        failed = True

    for marker in REQUIRED_RUNNER_MARKERS:
        if marker not in runner_text:
            print(f"ERR: runner manifest loader marker missing: {marker}", file=sys.stderr)
            failed = True

    if "active-spine.repos.toml" in runner_text:
        print("ERR: runner consumes active-spine overlay directly; update this discovery check", file=sys.stderr)
        failed = True

    if failed:
        return 1

    print("OK: runner has no committed active-spine overlay consumption path")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
