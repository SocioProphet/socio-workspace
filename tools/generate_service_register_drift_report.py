#!/usr/bin/env python3
"""Generate a warn-only service-register drift report.

PR-F adds drift-report scaffolding and CI gate policy. The script remains
warn-only until the service register CSVs and workspace-inventory export path are
stable.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = ROOT / "architecture" / "service-register"
POLICY = ARTIFACT_ROOT / "service-register-gate-policy.v0.1.json"
REGISTER = ARTIFACT_ROOT / "service-architecture-register.v1.0.csv"
CANONICAL_REPOS = ARTIFACT_ROOT / "canonical-repo-estate.v1.0.csv"
EDGES = ARTIFACT_ROOT / "service-dependency-edges.v0.1.csv"
STUBS = ARTIFACT_ROOT / "critical-contract-path-stubs.v0.1.csv"
OUT = ARTIFACT_ROOT / "service-register-drift-report.generated.csv"

EXPECTED = {
    "service_rows": 46,
    "canonical_repos": 125,
    "edge_rows": 119,
    "contract_stubs": 4,
}


def warn(message: str) -> None:
    print(f"WARN: {message}")


def ok(message: str) -> None:
    print(f"OK: {message}")


def count_csv_rows(path: Path) -> int | None:
    if not path.exists():
        return None
    with path.open(newline="", encoding="utf-8") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def load_policy() -> dict[str, object]:
    if not POLICY.exists():
        warn(f"missing gate policy: {POLICY.relative_to(ROOT)}")
        return {}
    try:
        return json.loads(POLICY.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        warn(f"invalid gate policy JSON: {exc}")
        return {}


def add_row(rows: list[dict[str, str]], check_id: str, status: str, expected: str, actual: str, notes: str) -> None:
    rows.append({
        "check_id": check_id,
        "status": status,
        "expected": expected,
        "actual": actual,
        "notes": notes,
    })


def main() -> int:
    print("SocioSphere service-register drift report")
    policy = load_policy()
    gate_mode = str(policy.get("gate_mode", "warn-only")) if policy else "warn-only"

    rows: list[dict[str, str]] = []
    add_row(rows, "gate_mode", "ok" if gate_mode == "warn-only" else "warn", "warn-only", gate_mode, "hard gates remain disabled in PR-F")

    artifacts = [
        ("service_rows", REGISTER, EXPECTED["service_rows"]),
        ("canonical_repos", CANONICAL_REPOS, EXPECTED["canonical_repos"]),
        ("edge_rows", EDGES, EXPECTED["edge_rows"]),
        ("contract_stubs", STUBS, EXPECTED["contract_stubs"]),
    ]
    for check_id, path, expected in artifacts:
        actual_count = count_csv_rows(path)
        if actual_count is None:
            add_row(rows, check_id, "warn", str(expected), "missing", f"{path.relative_to(ROOT)} is not present")
        elif actual_count == expected:
            add_row(rows, check_id, "ok", str(expected), str(actual_count), "count matches expected")
        else:
            add_row(rows, check_id, "warn", str(expected), str(actual_count), "count mismatch")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = ["check_id", "status", "expected", "actual", "notes"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    warnings = sum(1 for row in rows if row["status"] == "warn")
    if warnings:
        warn(f"drift warnings={warnings}; output={OUT.relative_to(ROOT)}")
    else:
        ok(f"no drift warnings; output={OUT.relative_to(ROOT)}")

    print("PR-F drift checker is warn-only by design; exiting 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
