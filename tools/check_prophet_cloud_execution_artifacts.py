#!/usr/bin/env python3
"""Validate Prophet Cloud execution-control artifacts."""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = ROOT / "architecture" / "service-register"
MATRIX = ARTIFACT_ROOT / "prophet-cloud-repo-maturity-matrix.v0.1.csv"
PLAN = ARTIFACT_ROOT / "prophet-cloud-critical-path.v0.1.md"
CANONICAL_REPOS = ARTIFACT_ROOT / "canonical-repo-estate.v1.0.csv"

REQUIRED_MATRIX_COLUMNS = [
    "repo_full_name",
    "service_family",
    "critical_path",
    "prophet_cloud_role",
    "current_maturity",
    "next_action",
]
ALLOWED_CRITICAL_PATH = {"yes", "no"}
ALLOWED_MATURITY = {
    "positioned",
    "validated",
    "verified",
    "contract-backed",
    "reference",
}
REQUIRED_CRITICAL_REPOS = {
    "SocioProphet/sociosphere",
    "SocioProphet/prophet-platform",
    "SocioProphet/agentplane",
    "SocioProphet/agent-registry",
    "SocioProphet/policy-fabric",
    "SocioProphet/guardrail-fabric",
    "SocioProphet/prophet-core-ledger",
    "SocioProphet/hyperswarm-agent-composable-cluster-scaleup",
    "SocioProphet/model-router",
    "SocioProphet/socioprophet",
    "SocioProphet/mcp-a2a-zero-trust",
    "SocioProphet/lampstand",
    "SocioProphet/memory-mesh",
    "SocioProphet/holmes",
    "SocioProphet/sherlock-search",
    "SourceOS-Linux/agent-machine",
    "SourceOS-Linux/sourceos-model-carry",
    "SourceOS-Linux/sourceos-shell",
    "SourceOS-Linux/sourceos-syncd",
}
REQUIRED_PLAN_TERMS = [
    "SocioSphere runtime APIs",
    "Matrix/chat collaboration",
    "Agent mesh hosting",
    "P0 Foundation",
    "P1 Workspace Runtime",
    "P2 Matrix/Chat",
    "P3 Agent Mesh Hosting",
    "P4 Product Surfaces",
    "Success Condition",
]


def fail(message: str) -> int:
    print(f"ERR: {message}")
    return 2


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    for path in (MATRIX, PLAN, CANONICAL_REPOS):
        if not path.exists():
            return fail(f"missing {path.relative_to(ROOT)}")

    matrix_rows = read_csv(MATRIX)
    canonical_rows = read_csv(CANONICAL_REPOS)
    canonical_repos = {row["repo_full_name"] for row in canonical_rows}

    with MATRIX.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != REQUIRED_MATRIX_COLUMNS:
            return fail(f"unexpected matrix columns: {reader.fieldnames!r}")

    matrix_repos = [row["repo_full_name"] for row in matrix_rows]
    if len(matrix_rows) != len(canonical_repos):
        return fail(f"matrix row count {len(matrix_rows)} != canonical repo count {len(canonical_repos)}")
    if set(matrix_repos) != canonical_repos:
        missing = sorted(canonical_repos - set(matrix_repos))[:10]
        extra = sorted(set(matrix_repos) - canonical_repos)[:10]
        return fail(f"matrix repo set mismatch missing={missing} extra={extra}")
    if len(matrix_repos) != len(set(matrix_repos)):
        return fail("matrix contains duplicate repo_full_name values")

    critical_repos = {row["repo_full_name"] for row in matrix_rows if row["critical_path"] == "yes"}
    if not REQUIRED_CRITICAL_REPOS.issubset(critical_repos):
        return fail(f"missing required critical repos: {sorted(REQUIRED_CRITICAL_REPOS - critical_repos)}")

    for index, row in enumerate(matrix_rows, start=2):
        if row["critical_path"] not in ALLOWED_CRITICAL_PATH:
            return fail(f"row {index} invalid critical_path={row['critical_path']!r}")
        if row["current_maturity"] not in ALLOWED_MATURITY:
            return fail(f"row {index} invalid current_maturity={row['current_maturity']!r}")
        for column in REQUIRED_MATRIX_COLUMNS:
            if not row[column].strip():
                return fail(f"row {index} missing {column}")

    plan = PLAN.read_text(encoding="utf-8")
    for term in REQUIRED_PLAN_TERMS:
        if term not in plan:
            return fail(f"critical path plan missing term: {term}")

    print(
        "OK: Prophet Cloud execution artifacts valid "
        f"({len(matrix_rows)} repos, {len(critical_repos)} critical-path repos)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
