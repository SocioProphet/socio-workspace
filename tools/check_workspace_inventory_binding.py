#!/usr/bin/env python3
"""Warn-only workspace-inventory binding checker.

PR-E records `SocioProphet/workspace-inventory` as the future canonical repo
estate source. This checker remains local and warn-only until the external repo
exports a stable artifact path and CI is allowed to fetch it.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = ROOT / "architecture" / "service-register"
BINDING = ARTIFACT_ROOT / "workspace-inventory-source.v0.1.json"
LOCAL_CANONICAL = ARTIFACT_ROOT / "canonical-repo-estate.v1.0.csv"
EXPECTED_REPO_COUNT = 125


def warn(message: str) -> None:
    print(f"WARN: {message}")


def ok(message: str) -> None:
    print(f"OK: {message}")


def count_csv_rows(path: Path) -> int:
    with path.open(encoding="utf-8") as handle:
        # Header minus blank lines.
        lines = [line for line in handle.read().splitlines() if line.strip()]
    return max(0, len(lines) - 1)


def main() -> int:
    print("SocioSphere workspace-inventory source binding check")
    if not BINDING.exists():
        warn(f"missing {BINDING.relative_to(ROOT)}")
        return 0

    try:
        binding = json.loads(BINDING.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        warn(f"invalid binding JSON: {exc}")
        return 0

    source_repo = binding.get("source_repository")
    if source_repo == "SocioProphet/workspace-inventory":
        ok("workspace-inventory source repository declared")
    else:
        warn(f"unexpected source_repository={source_repo!r}")

    if binding.get("validator_mode") == "warn-only":
        ok("validator_mode=warn-only")
    else:
        warn(f"unexpected validator_mode={binding.get('validator_mode')!r}")

    if not LOCAL_CANONICAL.exists():
        warn(f"local canonical repo artifact absent: {LOCAL_CANONICAL.relative_to(ROOT)}")
        print("PR-E binding checker is warn-only by design; exiting 0")
        return 0

    row_count = count_csv_rows(LOCAL_CANONICAL)
    if row_count == EXPECTED_REPO_COUNT:
        ok(f"local canonical repo rows={row_count}")
    else:
        warn(f"local canonical repo rows {row_count} != expected {EXPECTED_REPO_COUNT}")

    print("PR-E binding checker is warn-only by design; exiting 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
