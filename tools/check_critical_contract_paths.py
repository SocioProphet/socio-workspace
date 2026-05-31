#!/usr/bin/env python3
"""Validate critical contract path target rows tracked by SocioSphere."""
from __future__ import annotations

import csv
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = ROOT / "architecture" / "service-register"
STUBS = ARTIFACT_ROOT / "critical-contract-path-stubs.v0.1.csv"
EXPECTED_ROWS = 4
EXPECTED_MODE = "target_exists_required"


def warn(message: str) -> None:
    print(f"WARN: {message}")


def error(message: str) -> None:
    print(f"ERROR: {message}")


def ok(message: str) -> None:
    print(f"OK: {message}")


def record(required: bool, failures: list[str], message: str) -> None:
    if required:
        error(message)
        failures.append(message)
    else:
        warn(message)


def main() -> int:
    print("SocioSphere critical contract path check")
    required = os.environ.get("SERVICE_REGISTER_STRICT", "0") == "1"
    failures: list[str] = []

    if not STUBS.exists():
        record(required, failures, f"missing {STUBS.relative_to(ROOT)}")
        return 1 if failures else 0

    rows = list(csv.DictReader(STUBS.open(newline="", encoding="utf-8")))
    if len(rows) == EXPECTED_ROWS:
        ok(f"critical contract rows={len(rows)}")
    else:
        record(required, failures, f"critical contract rows {len(rows)} != expected {EXPECTED_ROWS}")

    for row in rows:
        service_id = row.get("service_id", "<missing-service-id>")
        target = row.get("contract_paths_target", "")
        target_exists = row.get("target_exists", "").strip().lower()
        mode = row.get("validator_mode", "")
        repo = row.get("contract_repo", "")

        if not repo or "/" not in repo:
            record(required, failures, f"{service_id} has invalid contract_repo={repo!r}")
        if not target:
            record(required, failures, f"{service_id} has empty contract_paths_target")
        if target_exists != "true":
            record(required, failures, f"{service_id} target_exists={target_exists!r}; expected true")
        if mode != EXPECTED_MODE:
            record(required, failures, f"{service_id} validator_mode={mode!r}; expected {EXPECTED_MODE!r}")

    if failures:
        return 1
    print("critical contract path check complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
