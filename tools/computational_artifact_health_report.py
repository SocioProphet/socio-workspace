#!/usr/bin/env python3
"""Emit a deterministic health report for registry/computational-artifacts.yaml.

This captures the artifact-health-report behavior from stale #308 without
clobbering the newer workspace runner implementation.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "registry" / "computational-artifacts.yaml"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def load_computational_artifacts(path: Path = REGISTRY) -> dict[str, Any]:
    if yaml is None:
        return {}
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def artifact_health_state(entry: dict[str, Any]) -> str:
    safety = entry.get("safetyClass", "")
    if safety == "prohibited":
        return "blocked"
    status = entry.get("status", "")
    if status == "deprecated":
        return "deprecated"
    if status == "seed":
        return "stale"
    if status == "drifted":
        return "drifted"
    if status == "blocked":
        return "blocked"
    if status in ("fresh", "active", "promoted"):
        return "fresh"
    return "stale"


def artifact_health_report_payload(registry: dict[str, Any]) -> dict[str, Any]:
    spec = registry.get("spec") or {}
    entries = spec.get("registryEntries") or []
    blocked_auto_promote = {"privileged", "prohibited"}

    rows: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        safety_cls = entry.get("safetyClass", "")
        rows.append(
            {
                "id": entry.get("id"),
                "ownerRepo": entry.get("ownerRepo"),
                "runtimeProfile": entry.get("runtimeProfile"),
                "safetyClass": safety_cls,
                "evidenceStatus": entry.get("status", "unknown"),
                "requiredEvidence": entry.get("requiredEvidence") or [],
                "downstreamConsumers": entry.get("downstreamConsumers") or [],
                "slashTopics": entry.get("slashTopics") or [],
                "healthState": artifact_health_state(entry),
                "autoPromotionBlocked": safety_cls in blocked_auto_promote,
            }
        )

    return {
        "kind": "ComputationalArtifactHealthReport",
        "generatedAt": now_iso(),
        "registryVersion": (registry.get("metadata") or {}).get("version", "unknown"),
        "artifacts": rows,
    }


def emit_table(payload: dict[str, Any]) -> None:
    artifacts = payload["artifacts"]
    header = f"{'id':32s} {'ownerRepo':36s} {'safetyClass':12s} {'healthState':10s} {'evidenceStatus':14s}"
    print(header)
    print("-" * len(header))
    for artifact in artifacts:
        blocked_flag = " [NO-AUTO-PROMOTE]" if artifact["autoPromotionBlocked"] else ""
        print(
            f"{str(artifact['id'] or '-'):32s} "
            f"{str(artifact['ownerRepo'] or '-'):36s} "
            f"{str(artifact['safetyClass'] or '-'):12s} "
            f"{str(artifact['healthState'] or '-'):10s} "
            f"{str(artifact['evidenceStatus'] or '-'):14s}"
            f"{blocked_flag}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit computational artifact health report")
    parser.add_argument("--output", default="-", metavar="FILE", help="Output file path (default: stdout)")
    parser.add_argument("--table", action="store_true", help="Print as human-readable table instead of JSON")
    args = parser.parse_args()

    registry = load_computational_artifacts()
    if not registry:
        print(
            "ERR: could not load registry/computational-artifacts.yaml "
            "(ensure PyYAML is installed: pip install pyyaml)",
            file=sys.stderr,
        )
        return 2

    payload = artifact_health_report_payload(registry)
    if args.table:
        emit_table(payload)
    elif args.output == "-":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"[artifact-health-report] wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
