#!/usr/bin/env python3
"""Service dependency edge validator and hard-cycle classifier."""
from __future__ import annotations

import csv
import os
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = ROOT / "architecture" / "service-register"
EDGES = ARTIFACT_ROOT / "service-dependency-edges.v0.1.csv"
REGISTER = ARTIFACT_ROOT / "service-architecture-register.v1.0.csv"

EXPECTED_EDGE_ROWS = 119
EXPECTED_BOOT_REQUIRED = 28
EXPECTED_ALLOWED_CYCLES = 7
HARD_CYCLE_MODES = {"hard", "policy-required"}

ALLOWED_EDGE_KINDS = {
    "depends_on",
    "consumes",
    "emits_to",
    "governs",
    "ui_surface",
    "evidence_feed",
}
ALLOWED_DEPENDENCY_MODES = {
    "hard",
    "soft",
    "optional-extension",
    "runtime-callback",
    "policy-required",
    "governance-feedback",
    "evaluation-orchestration",
    "evidence-feed",
    "ui-consumes",
}
ALLOWED_CYCLE_POLICIES = {
    "forbidden",
    "allowed-if-optional",
    "allowed-runtime-feedback",
    "allowed-governance-loop",
}
ALLOWED_CYCLE_POLICIES_NON_FORBIDDEN = ALLOWED_CYCLE_POLICIES - {"forbidden"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def warn(message: str) -> None:
    print(f"WARN: {message}")


def fail(message: str) -> None:
    print(f"FAIL: {message}")


def ok(message: str) -> None:
    print(f"OK: {message}")


def boolish(value: str | None) -> bool:
    return str(value).strip().lower() == "true"


def service_ids_from_register() -> set[str]:
    if not REGISTER.exists():
        return set()
    return {row["service_id"] for row in read_csv(REGISTER) if row.get("service_id")}


def hard_cycle_edges(edges: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        edge for edge in edges
        if edge.get("dependency_mode") in HARD_CYCLE_MODES
        and edge.get("cycle_policy") == "forbidden"
    ]


def canonical_cycle(cycle: list[str]) -> tuple[str, ...]:
    body = cycle[:-1]
    rotations = [tuple(body[i:] + body[:i]) for i in range(len(body))]
    return min(rotations)


def find_cycles(edges: list[dict[str, str]]) -> list[list[str]]:
    graph: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        graph[edge["from_service_id"]].append(edge["to_service_id"])

    cycles: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()

    def visit(node: str, path: list[str]) -> None:
        for nxt in graph.get(node, []):
            if nxt in path:
                cycle = path[path.index(nxt):] + [nxt]
                key = canonical_cycle(cycle)
                if key not in seen:
                    seen.add(key)
                    cycles.append(cycle)
            elif len(path) < 12:
                visit(nxt, path + [nxt])

    for node in sorted(graph):
        visit(node, [node])
    return cycles


def record(strict: bool, failures: list[str], message: str) -> None:
    if strict:
        fail(message)
        failures.append(message)
    else:
        warn(message)


def main() -> int:
    print("SocioSphere service dependency cycle check")
    strict = os.environ.get("SERVICE_REGISTER_STRICT", "0") == "1"
    failures: list[str] = []

    if not EDGES.exists():
        message = f"missing {EDGES.relative_to(ROOT)}; cycle classification cannot run yet"
        record(strict, failures, message)
        return 1 if failures else 0

    if not REGISTER.exists():
        message = f"missing {REGISTER.relative_to(ROOT)}; service references cannot be validated"
        record(strict, failures, message)
        return 1 if failures else 0

    edges = read_csv(EDGES)
    services = service_ids_from_register()

    if len(edges) == EXPECTED_EDGE_ROWS:
        ok(f"edge rows={len(edges)}")
    else:
        record(strict, failures, f"edge row count {len(edges)} != expected {EXPECTED_EDGE_ROWS}")

    boot_required = sum(1 for edge in edges if boolish(edge.get("required_for_bootstrap")))
    if boot_required == EXPECTED_BOOT_REQUIRED:
        ok(f"boot-required edges={boot_required}")
    else:
        record(strict, failures, f"boot-required edge count {boot_required} != expected {EXPECTED_BOOT_REQUIRED}")

    allowed_cycle_edges = [edge for edge in edges if edge.get("cycle_policy") in ALLOWED_CYCLE_POLICIES_NON_FORBIDDEN]
    if len(allowed_cycle_edges) == EXPECTED_ALLOWED_CYCLES:
        ok(f"declared allowed-cycle edges={len(allowed_cycle_edges)}")
    else:
        record(strict, failures, f"declared allowed-cycle edges {len(allowed_cycle_edges)} != expected {EXPECTED_ALLOWED_CYCLES}")

    for edge in edges:
        edge_id = edge.get("edge_id", "<missing-edge-id>")
        if edge.get("edge_kind") not in ALLOWED_EDGE_KINDS:
            record(strict, failures, f"{edge_id} has invalid edge_kind={edge.get('edge_kind')}")
        if edge.get("dependency_mode") not in ALLOWED_DEPENDENCY_MODES:
            record(strict, failures, f"{edge_id} has invalid dependency_mode={edge.get('dependency_mode')}")
        if edge.get("cycle_policy") not in ALLOWED_CYCLE_POLICIES:
            record(strict, failures, f"{edge_id} has invalid cycle_policy={edge.get('cycle_policy')}")
        if edge.get("from_service_id") not in services:
            record(strict, failures, f"{edge_id} from_service_id missing from register: {edge.get('from_service_id')}")
        if edge.get("to_service_id") not in services:
            record(strict, failures, f"{edge_id} to_service_id missing from register: {edge.get('to_service_id')}")

    forbidden_cycles = find_cycles(hard_cycle_edges(edges))
    if forbidden_cycles:
        record(strict, failures, f"forbidden hard cycles detected={len(forbidden_cycles)}: {forbidden_cycles}")
    else:
        ok("no forbidden hard cycles detected")

    if failures:
        return 1
    print("dependency cycle check complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
