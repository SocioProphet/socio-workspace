#!/usr/bin/env python3
"""Emit a deterministic health report for registry/computational-artifacts.yaml."""
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

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "registry" / "computational-artifacts.yaml"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _load_computational_artifacts() -> dict[str, Any]:
    if yaml is None or not REGISTRY.exists():
        return {}
    try:
        data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _artifact_health_state(entry: dict[str, Any]) -> str:
    if entry.get("safetyClass") == "prohibited":
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
    entries = ((registry.get("spec") or {}).get("registryEntries") or [])
    rows: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        safety_cls = entry.get("safetyClass", "")
        rows.append({
            "id": entry.get("id"),
            "ownerRepo": entry.get("ownerRepo"),
            "runtimeProfile": entry.get("runtimeProfile"),
            "safetyClass": safety_cls,
            "evidenceStatus": entry.get("status", "unknown"),
            "requiredEvidence": entry.get("requiredEvidence") or [],
            "downstreamConsumers": entry.get("downstreamConsumers") or [],
            "slashTopics": entry.get("slashTopics") or [],
            "healthState": _artifact_health_state(entry),
            "autoPromotionBlocked": safety_cls in {"privileged", "prohibited"},
        })
    return {
        "kind": "ComputationalArtifactHealthReport",
        "generatedAt": now_iso(),
        "registryVersion": (registry.get("metadata") or {}).get("version", "unknown"),
        "artifacts": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="-", metavar="FILE")
    parser.add_argument("--table", action="store_true")
    args = parser.parse_args(argv)
    registry = _load_computational_artifacts()
    if not registry:
        print("ERR: could not load registry/computational-artifacts.yaml (ensure PyYAML is installed)", file=sys.stderr)
        return 2
    payload = artifact_health_report_payload(registry)
    if args.table:
        header = f"{'id':32s} {'ownerRepo':36s} {'safetyClass':12s} {'healthState':10s} {'evidenceStatus':14s}"
        print(header)
        print("-" * len(header))
        for artifact in payload["artifacts"]:
            blocked = " [NO-AUTO-PROMOTE]" if artifact["autoPromotionBlocked"] else ""
            print(
                f"{str(artifact['id'] or '-'):32s} "
                f"{str(artifact['ownerRepo'] or '-'):36s} "
                f"{str(artifact['safetyClass'] or '-'):12s} "
                f"{str(artifact['healthState'] or '-'):10s} "
                f"{str(artifact['evidenceStatus'] or '-'):14s}{blocked}"
            )
        return 0
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output == "-":
        print(text, end="")
    else:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"[artifact-health-report] wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
