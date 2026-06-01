#!/usr/bin/env python3
"""Validate SocioSphere's workspace-inventory repo-estate binding."""
from __future__ import annotations

import csv
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = ROOT / "architecture" / "service-register"
BINDING = ARTIFACT_ROOT / "workspace-inventory-source.v0.1.json"
LOCAL_CANONICAL = ARTIFACT_ROOT / "canonical-repo-estate.v1.0.csv"
EXPECTED_REPO_COUNT = 122
EXPECTED_SOURCE_REPO = "SocioProphet/workspace-inventory"
EXPECTED_SOURCE_PATH = "exports/canonical-repo-estate.v1.0.csv"
EXPECTED_MANIFEST_PATH = "exports/canonical-repo-estate.v1.0.json"
EXPECTED_SOURCE_VALIDATION_TOOL = "tools/check_canonical_repo_export.py"
EXPECTED_SOURCE_VALIDATION_WORKFLOW = ".github/workflows/inventory.yml"
EXPECTED_SOURCE_MANIFEST = {
    "artifact_id": "workspace_inventory.canonical_repo_estate.v1.0",
    "status": "canonical-export",
    "export_path": EXPECTED_SOURCE_PATH,
    "repo_count": EXPECTED_REPO_COUNT,
}
EXPECTED_SOURCE_COLUMNS = [
    "repo_full_name",
    "owned_services",
    "supporting_services",
    "contract_services",
    "canonical_status",
]


def warn(message: str) -> None:
    print(f"WARN: {message}")


def error(message: str) -> None:
    print(f"ERROR: {message}")


def ok(message: str) -> None:
    print(f"OK: {message}")


def count_csv_rows(path: Path) -> int:
    with path.open(newline="", encoding="utf-8") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def record(required: bool, failures: list[str], message: str) -> None:
    if required:
        error(message)
        failures.append(message)
    else:
        warn(message)


def expect_equal(required: bool, failures: list[str], label: str, actual: object, expected: object) -> None:
    if actual == expected:
        ok(f"{label}={actual}")
    else:
        record(required, failures, f"unexpected {label}={actual!r}; expected {expected!r}")


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
        "source_validation_tool": EXPECTED_SOURCE_VALIDATION_TOOL,
        "source_validation_workflow": EXPECTED_SOURCE_VALIDATION_WORKFLOW,
        "binding_mode": "stable-export",
        "validator_mode": "strict-local-binding-with-upstream-contract",
        "expected_canonical_repo_count": EXPECTED_REPO_COUNT,
        "expected_source_manifest": EXPECTED_SOURCE_MANIFEST,
        "expected_source_columns": EXPECTED_SOURCE_COLUMNS,
    }
    for key, expected in checks.items():
        expect_equal(required, failures, key, binding.get(key), expected)

    consumer_artifacts = binding.get("consumer_artifacts")
    if isinstance(consumer_artifacts, list) and str(LOCAL_CANONICAL.relative_to(ROOT)) in consumer_artifacts:
        ok(f"consumer_artifacts includes {LOCAL_CANONICAL.relative_to(ROOT)}")
    else:
        record(required, failures, f"consumer_artifacts does not include {LOCAL_CANONICAL.relative_to(ROOT)}")

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
