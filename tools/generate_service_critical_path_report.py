#!/usr/bin/env python3
"""Generate critical-path reporting from service edges."""
from __future__ import annotations

import csv
import os
from collections import defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = ROOT / "architecture" / "service-register"
REGISTER = ARTIFACT_ROOT / "service-architecture-register.v1.0.csv"
EDGES = ARTIFACT_ROOT / "service-dependency-edges.v0.1.csv"
OUT = ARTIFACT_ROOT / "critical-path-blocking-report.generated.csv"

TIER_WEIGHT = {
    "substrate": 5,
    "managed-substrate": 4,
    "workspace-substrate": 3,
    "platform-core": 3,
    "product-service": 2,
    "application": 1,
    "misc": 0,
}
BLOCKING_STATUSES = {"planning", "prototype"}
TRAVERSABLE_MODES = {"hard", "policy-required"}
ALLOWED_FEEDBACK_POLICIES = {
    "allowed-if-optional",
    "allowed-runtime-feedback",
    "allowed-governance-loop",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def warn(message: str) -> None:
    print(f"WARN: {message}")


def error(message: str) -> None:
    print(f"ERROR: {message}")


def ok(message: str) -> None:
    print(f"OK: {message}")


def downstream_graph(edges: list[dict[str, str]]) -> dict[str, list[str]]:
    graph: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        if edge.get("cycle_policy") in ALLOWED_FEEDBACK_POLICIES:
            continue
        if edge.get("dependency_mode") not in TRAVERSABLE_MODES:
            continue
        graph[edge["from_service_id"]].append(edge["to_service_id"])
    return graph


def blast_radius(service_id: str, graph: dict[str, list[str]]) -> set[str]:
    seen: set[str] = set()
    queue: deque[str] = deque(graph.get(service_id, []))
    while queue:
        node = queue.popleft()
        if node in seen:
            continue
        seen.add(node)
        queue.extend(graph.get(node, []))
    return seen


def main() -> int:
    print("SocioSphere generated critical-path report")
    required = os.environ.get("SERVICE_REGISTER_STRICT", "0") == "1"

    if not REGISTER.exists() or not EDGES.exists():
        message = "missing register or edge CSV; generated critical-path report cannot run yet"
        if required:
            error(message)
            return 1
        warn(message)
        return 0

    services = read_csv(REGISTER)
    edges = read_csv(EDGES)
    graph = downstream_graph(edges)

    rows: list[dict[str, str | int]] = []
    for service in services:
        status = service.get("product_status", "")
        if status not in BLOCKING_STATUSES:
            continue
        service_id = service["service_id"]
        affected = blast_radius(service_id, graph)
        weight = TIER_WEIGHT.get(service.get("stack_tier", ""), 0)
        score = len(affected) * weight
        severity = "BLOCKING" if len(affected) > 2 else "HARDENING"
        rows.append({
            "service_id": service_id,
            "service_name": service.get("service_name", ""),
            "stack_tier": service.get("stack_tier", ""),
            "product_status": status,
            "blast_radius": len(affected),
            "tier_weight": weight,
            "score": score,
            "severity": severity,
            "affected_services": ",".join(sorted(affected)) or "-",
            "recommendation": "promote before downstream hardening" if severity == "BLOCKING" else "track during hardening",
        })

    rows.sort(key=lambda row: (-int(row["score"]), str(row["service_id"])))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "rank",
            "service_id",
            "service_name",
            "stack_tier",
            "product_status",
            "blast_radius",
            "tier_weight",
            "score",
            "severity",
            "affected_services",
            "recommendation",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for rank, row in enumerate(rows, start=1):
            writer.writerow({"rank": rank, **row})

    blocking = sum(1 for row in rows if row["severity"] == "BLOCKING")
    hardening = sum(1 for row in rows if row["severity"] == "HARDENING")
    if not rows:
        message = f"generated zero critical-path rows; output={OUT.relative_to(ROOT)}"
        if required:
            error(message)
            return 1
        warn(message)
        return 0
    ok(f"generated rows={len(rows)} blocking={blocking} hardening={hardening} output={OUT.relative_to(ROOT)}")
    print("critical-path generation complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
