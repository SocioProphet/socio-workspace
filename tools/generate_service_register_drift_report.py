#!/usr/bin/env python3
"""Generate and optionally enforce service-register drift checks."""
from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = ROOT / "architecture" / "service-register"
POLICY = ARTIFACT_ROOT / "service-register-gate-policy.v0.1.json"
REGISTER = ARTIFACT_ROOT / "service-architecture-register.v1.0.csv"
CANONICAL_REPOS = ARTIFACT_ROOT / "canonical-repo-estate.v1.0.csv"
CANONICAL_REPOS_MIRROR = ARTIFACT_ROOT / "canonical-repo-estate.mirror.v1.0.json"
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


def git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("utf-8")
    return hashlib.sha1(header + data).hexdigest()


def load_json(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        warn(f"invalid JSON in {path.relative_to(ROOT)}: {exc}")
        return None
    if not isinstance(data, dict):
        warn(f"invalid JSON shape in {path.relative_to(ROOT)}: expected object")
        return None
    return data


def load_policy() -> dict[str, object]:
    policy = load_json(POLICY)
    if policy is None:
        warn(f"missing or invalid gate policy: {POLICY.relative_to(ROOT)}")
        return {}
    return policy


def add_row(rows: list[dict[str, str]], check_id: str, status: str, expected: str, actual: str, notes: str) -> None:
    rows.append({
        "check_id": check_id,
        "status": status,
        "expected": expected,
        "actual": actual,
        "notes": notes,
    })


def add_mirror_pin_row(rows: list[dict[str, str]], strict: bool) -> None:
    manifest = load_json(CANONICAL_REPOS_MIRROR)
    if manifest is None:
        add_row(
            rows,
            "canonical_repo_mirror_pin",
            "fail" if strict else "warn",
            "valid mirror manifest with expected_git_blob_sha",
            "missing-or-invalid",
            f"{CANONICAL_REPOS_MIRROR.relative_to(ROOT)} is not present or invalid",
        )
        return

    local_path = manifest.get("local_artifact_path")
    expected_sha = manifest.get("expected_git_blob_sha")
    if not isinstance(local_path, str) or not local_path:
        add_row(rows, "canonical_repo_mirror_pin", "fail" if strict else "warn", "local_artifact_path", repr(local_path), "mirror manifest missing local_artifact_path")
        return
    if not isinstance(expected_sha, str) or len(expected_sha) != 40:
        add_row(rows, "canonical_repo_mirror_pin", "fail" if strict else "warn", "40-char Git blob SHA", repr(expected_sha), "mirror manifest missing valid expected_git_blob_sha")
        return

    artifact = ROOT / local_path
    if not artifact.exists():
        add_row(rows, "canonical_repo_mirror_pin", "fail" if strict else "warn", expected_sha, "missing", f"{local_path} is not present")
        return

    actual_sha = git_blob_sha(artifact.read_bytes())
    if actual_sha == expected_sha:
        add_row(rows, "canonical_repo_mirror_pin", "ok", expected_sha, actual_sha, "local mirror Git blob SHA matches pinned upstream mirror identity")
    else:
        add_row(rows, "canonical_repo_mirror_pin", "fail" if strict else "warn", expected_sha, actual_sha, "local mirror Git blob SHA mismatch")


def main() -> int:
    print("SocioSphere service-register drift report")
    policy = load_policy()
    gate_mode = str(policy.get("gate_mode", "warn-only")) if policy else "warn-only"
    strict_env = os.environ.get("SERVICE_REGISTER_STRICT", "0") == "1"
    strict = strict_env or bool(policy.get("hard_gate_enabled"))

    rows: list[dict[str, str]] = []
    add_row(rows, "gate_mode", "ok" if gate_mode in {"warn-only", "artifact-count-strict"} else "warn", "warn-only|artifact-count-strict", gate_mode, "strict artifact-count gate may be enabled by policy or SERVICE_REGISTER_STRICT=1")

    artifacts = [
        ("service_rows", REGISTER, EXPECTED["service_rows"]),
        ("canonical_repos", CANONICAL_REPOS, EXPECTED["canonical_repos"]),
        ("edge_rows", EDGES, EXPECTED["edge_rows"]),
        ("contract_stubs", STUBS, EXPECTED["contract_stubs"]),
    ]
    for check_id, path, expected in artifacts:
        actual_count = count_csv_rows(path)
        if actual_count is None:
            add_row(rows, check_id, "fail" if strict else "warn", str(expected), "missing", f"{path.relative_to(ROOT)} is not present")
        elif actual_count == expected:
            add_row(rows, check_id, "ok", str(expected), str(actual_count), "count matches expected")
        else:
            add_row(rows, check_id, "fail" if strict else "warn", str(expected), str(actual_count), "count mismatch")

    add_mirror_pin_row(rows, strict)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = ["check_id", "status", "expected", "actual", "notes"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    failures = sum(1 for row in rows if row["status"] == "fail")
    warnings = sum(1 for row in rows if row["status"] == "warn")
    if failures:
        warn(f"drift failures={failures}; output={OUT.relative_to(ROOT)}")
    elif warnings:
        warn(f"drift warnings={warnings}; output={OUT.relative_to(ROOT)}")
    else:
        ok(f"no drift warnings; output={OUT.relative_to(ROOT)}")

    if failures:
        return 1
    print("service-register drift check complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
