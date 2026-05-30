#!/usr/bin/env python3
"""Validate SocioSphere's workspace-inventory repo-estate binding."""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = ROOT / "architecture" / "service-register"
BINDING = ARTIFACT_ROOT / "workspace-inventory-source.v0.1.json"
LOCAL_CANONICAL = ARTIFACT_ROOT / "canonical-repo-estate.v1.0.csv"
EXPECTED_REPO_COUNT = 125
EXPECTED_SOURCE_REPO = "SocioProphet/workspace-inventory"
EXPECTED_SOURCE_PATH = "exports/canonical-repo-estate.v1.0.csv"
EXPECTED_MANIFEST_PATH = "exports/canonical-repo-estate.v1.0.json"


def warn(message: str) -> None:
    print(f"WARN: {message}")


def error(message: str) -> None:
    print(f"ERROR: {message}")


def ok(message: str) -> None:
    print(f"OK: {message}")


def count_csv_rows(path: Path) -> int:
    with path.open(encoding="utf-8") as handle:
        lines = [line for line in handle.read().splitlines() if line.strip()]
    return max(0, len(lines) - 1)


def record(required: bool, failures: list[str], message: str) -> None:
    if required:
        error(message)
        failures.append(message)
    else:
        warn(message)


def main() -> int:
    print("SocioSphere workspace-inventory source binding check")
    required = os.environ.get("SERVICE_REGISTER_STRICT", "0") == "1"
    failures: list[str] = []

    if not BINDING.exists():
        record(required, failures, f"missing {BINDING.relative_to(ROOT)}")
        return 1 if failures else 0

    try:
        binding = json.loads(BINDING.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        record(required, failures, f"invalid binding JSON: {exc}")
        return 1 if failures else 0

    checks = {
        "source_repository": EXPECTED_SOURCE_REPO,
        "source_artifact_path": EXPECTED_SOURCE_PATH,
        "source_manifest_path": EXPECTED_MANIFEST_PATH,
        "binding_mode": "stable-export",
        "validator_mode": "strict-local-binding",
    }
    for key, expected in checks.items():
        actual = binding.get(key)
        if actual == expected:
            ok(f"{key}={actual}")
        else:
            record(required, failures, f"unexpected {key}={actual!r}; expected {expected!r}")

    if binding.get("expected_canonical_repo_count") == EXPECTED_REPO_COUNT:
        ok(f"expected_canonical_repo_count={EXPECTED_REPO_COUNT}")
    else:
        record(required, failures, f"expected_canonical_repo_count {binding.get('expected_canonical_repo_count')} != {EXPECTED_REPO_COUNT}")

    if not LOCAL_CANONICAL.exists():
        record(required, failures, f"local canonical repo artifact absent: {LOCAL_CANONICAL.relative_to(ROOT)}")
        return 1 if failures else 0

    row_count = count_csv_rows(LOCAL_CANONICAL)
    if row_count == EXPECTED_REPO_COUNT:
        ok(f"local canonical repo rows={row_count}")
    else:
        record(required, failures, f"local canonical repo rows {row_count} != expected {EXPECTED_REPO_COUNT}")

    if failures:
        return 1
    print("workspace-inventory binding check complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
