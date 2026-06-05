#!/usr/bin/env python3
"""Print a compact Workspace mesh operator checkpoint summary.

This script does not validate independently; it summarizes the intended gate
state after the Makefile validators have passed.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE2 = ROOT / "registry" / "workspace-mesh-gate2-id-substitution-planning.v0.json"
GATE1_REVIEWED = ROOT / "registry" / "workspace-mesh-gate1-reviewed-no-promotion-2026-06-05.json"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    gate2 = read_json(GATE2)
    gate1 = read_json(GATE1_REVIEWED)

    print("Workspace Mesh Operator Checkpoint")
    print("==================================")
    print("mesh_state=prepared-but-not-deployed")
    print("gate_0=complete")
    print(f"gate_1={gate1.get('disposition')}")
    print(f"gate_2={gate2.get('status')}")
    print(f"gate_2_disposition={gate2.get('gate_2_disposition')}")
    print("plan_safety=passed")
    print("gate1_artifact_review=passed")
    print("artifact_review_source=plan_json")
    print("placeholders=4")
    print("ids_substituted=false")
    print("live_execution=false")
    print("next_allowed_action=gate_2_planning_record_only")


if __name__ == "__main__":
    main()
