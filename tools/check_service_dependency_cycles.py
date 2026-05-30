#!/usr/bin/env python3
"""Warn-only service dependency edge validator and cycle classifier.

PR-C establishes the dependency-graph validation lane. It remains warn-only
until the edge table is committed and critical-path generation is introduced in
PR-D.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = ROOT / "architecture" / "service-register"
EDGES = ARTIFACT_ROOT / "service-dependency-edges.v0.1.csv"
REGISTER = ARTIFACT_ROOT / "service-architecture-register.v1.0.csv"

EXPECTED_EDGE_ROWS = 119
EXPECTED_BOOT_REQUIRED = 28
EXPECTED_ALLOWED_CYCLES = 7

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


def ok(message: str) -> None:
    print(f"OK: {message}")


def boolish(value: str | None) -> bool:
    return str(value).strip().lower() == "true"


def service_ids_from_register() -> set[str]:
    if not REGISTER.exists():
        return set()
    return {row["service_id"] for row in read_csv(REGISTER) if row.get("service_id")}


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
                key = tuple(cycle)
                if key not in seen:
                    seen.add(key)
                    cycles.append(cycle)
            elif len(path) < 12:
                visit(nxt, path + [nxt])

    for node in sorted(graph):
        visit(node, [node])
    return cycles


def edge_lookup(edges: list[dict[str, str]]) -> dict[tuple[str, str], list[dict[str, str]]]:
    lookup: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for edge in edges:
        lookup[(edge["from_service_id"], edge["to_service_id"])].append(edge)
    return lookup


def classify_cycle(cycle: list[str], lookup: dict[tuple[str, str], list[dict[str, str]]]) -> str:
    policies: list[str] = []
    for left, right in zip(cycle, cycle[1:]):
        policies.extend(edge.get("cycle_policy", "forbidden") for edge in lookup.get((left, right), []))
    if any(policy in ALLOWED_CYCLE_POLICIES_NON_FORBIDDEN for policy in policies):
        return "allowed"
    return "forbidden"


def main() -> int:
    print("SocioSphere service dependency cycle check")
    if not EDGES.exists():
        warn(f"missing {EDGES.relative_to(ROOT)}; cycle classification cannot run yet")
        print("PR-C cycle checker is warn-only by design; exiting 0")
        return 0

    edges = read_csv(EDGES)
    services = service_ids_from_register()

    if len(edges) == EXPECTED_EDGE_ROWS:
        ok(f"edge rows={len(edges)}")
    else:
        warn(f"edge row count {len(edges)} != expected {EXPECTED_EDGE_ROWS}")

    boot_required = sum(1 for edge in edges if boolish(edge.get("required_for_bootstrap")))
    if boot_required == EXPECTED_BOOT_REQUIRED:
        ok(f"boot-required edges={boot_required}")
    else:
        warn(f"boot-required edge count {boot_required} != expected {EXPECTED_BOOT_REQUIRED}")

    allowed_cycle_edges = [edge for edge in edges if edge.get("cycle_policy") in ALLOWED_CYCLE_POLICIES_NON_FORBIDDEN]
    if len(allowed_cycle_edges) == EXPECTED_ALLOWED_CYCLES:
        ok(f"declared allowed-cycle edges={len(allowed_cycle_edges)}")
    else:
        warn(f"declared allowed-cycle edges {len(allowed_cycle_edges)} != expected {EXPECTED_ALLOWED_CYCLES}")

    for edge in edges:
        if edge.get("edge_kind") not in ALLOWED_EDGE_KINDS:
            warn(f"{edge.get('edge_id')} has invalid edge_kind={edge.get('edge_kind')}")
        if edge.get("dependency_mode") not in ALLOWED_DEPENDENCY_MODES:
            warn(f"{edge.get('edge_id')} has invalid dependency_mode={edge.get('dependency_mode')}")
        if edge.get("cycle_policy") not in ALLOWED_CYCLE_POLICIES:
            warn(f"{edge.get('edge_id')} has invalid cycle_policy={edge.get('cycle_policy')}")
        if services:
            if edge.get("from_service_id") not in services:
                warn(f"{edge.get('edge_id')} from_service_id missing from register: {edge.get('from_service_id')}")
            if edge.get("to_service_id") not in services:
                warn(f"{edge.get('edge_id')} to_service_id missing from register: {edge.get('to_service_id')}")

    cycles = find_cycles(edges)
    lookup = edge_lookup(edges)
    forbidden_cycles = [cycle for cycle in cycles if classify_cycle(cycle, lookup) == "forbidden"]
    allowed_cycles = [cycle for cycle in cycles if classify_cycle(cycle, lookup) == "allowed"]

    if allowed_cycles:
        ok(f"allowed cycles detected={len(allowed_cycles)}")
    else:
        warn("no allowed cycles detected; expected feedback loops may be absent or artifacts missing")

    if forbidden_cycles:
        warn(f"forbidden cycles detected={len(forbidden_cycles)}: {forbidden_cycles}")
    else:
        ok("no forbidden cycles detected")

    print("PR-C cycle checker is warn-only by design; exiting 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
