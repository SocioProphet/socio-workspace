#!/usr/bin/env python3
"""Validate that Gate 2 cannot promote into Gate 3 yet.

The current mesh is allowed to remain in Gate 2 planning. Gate 3 start requires
a separate future approval record. This validator fails if a Gate 3 start record
appears without that approval record.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLOCKER = ROOT / "registry" / "workspace-mesh-gate2-promotion-blocker.v0.json"
APPROVAL = ROOT / "registry" / "workspace-mesh-gate2-promotion-approval.v0.json"
GATE3_START = ROOT / "registry" / "workspace-mesh-gate3-start.v0.json"
GATE2_PLANNING = ROOT / "registry" / "workspace-mesh-gate2-id-substitution-planning.v0.json"
SCHEMA_PROOF = ROOT / "docs" / "operations" / "workspace-mesh-gate2-schema-lifecycle-proof-2026-06-05.md"
LIFECYCLE_PROOF = ROOT / "docs" / "operations" / "workspace-mesh-gate2-candidate-lifecycle-proof-2026-06-05.md"


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def load_json(path: Path) -> dict:
    if not path.exists():
        fail(f"missing file: {path.relative_to(ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    blocker = load_json(BLOCKER)
    planning = load_json(GATE2_PLANNING)

    if blocker.get("gate_id") != "gate-2-id-substitution-review":
        fail("blocker gate_id mismatch")
    if blocker.get("mesh_state") != "prepared-but-not-deployed":
        fail("blocker must keep mesh prepared-but-not-deployed")
    if blocker.get("gate_2_state") != "planning_only":
        fail("Gate 2 must remain planning_only")
    if blocker.get("gate_3_state") != "blocked":
        fail("Gate 3 must remain blocked")
    if blocker.get("blocker_state") != "active":
        fail("promotion blocker must be active")
    if blocker.get("approval_artifact_required_before_gate3") is not True:
        fail("approval artifact must be required before Gate 3")

    if planning.get("status") != "planning_only":
        fail("Gate 2 planning manifest must remain planning_only")
    if planning.get("gate_2_disposition") != "not_started":
        fail("Gate 2 disposition must remain not_started")

    if GATE3_START.exists() and not APPROVAL.exists():
        fail("Gate 3 start artifact exists without Gate 2 promotion approval")
    if APPROVAL.exists() and not GATE3_START.exists():
        fail("Gate 2 promotion approval exists but Gate 3 start artifact is absent; review transition manually")

    for path in [SCHEMA_PROOF, LIFECYCLE_PROOF]:
        if not path.exists():
            fail(f"required Gate 2 proof missing: {path.relative_to(ROOT)}")

    flags = blocker.get("status_flags", {})
    expected_false = ["ids_substituted", "live_execution", "candidate_values_printed", "gate3_started"]
    for key in expected_false:
        if flags.get(key) is not False:
            fail(f"status flag {key} must be false")

    print("PASS: Workspace mesh Gate 2 promotion blocker is active")
    print("mesh_state=prepared-but-not-deployed")
    print("gate_2=planning_only")
    print("gate_3=blocked")
    print(f"approval_artifact_present={str(APPROVAL.exists()).lower()}")
    print("ids_substituted=false")
    print("candidate_values_printed=false")
    print("live_execution=false")


if __name__ == "__main__":
    main()
