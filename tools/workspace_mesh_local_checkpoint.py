#!/usr/bin/env python3
"""Print the full Workspace mesh local checkpoint summary.

This script summarizes state after the standalone Make checkpoint has already
run the detailed validators. It reads only committed state ledgers and prints
non-sensitive status fields.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "registry" / "workspace-mesh-current-state.v0.json"
BLOCKER = ROOT / "registry" / "workspace-mesh-gate2-promotion-blocker.v0.json"


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def load_json(path: Path) -> dict:
    if not path.exists():
        fail(f"missing file: {path.relative_to(ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    ledger = load_json(LEDGER)
    blocker = load_json(BLOCKER)

    gates = ledger.get("gates", {})
    controls = ledger.get("controls", {})

    if ledger.get("mesh_state") != "prepared-but-not-deployed":
        fail("ledger mesh_state mismatch")
    if blocker.get("blocker_state") != "active":
        fail("promotion blocker must be active")
    if blocker.get("gate_3_state") != "blocked":
        fail("Gate 3 must remain blocked")

    expected = {
        "gate_0": "complete",
        "gate_1": "reviewed_no_promotion",
        "gate_2": "planning_only",
        "gate_3": "blocked",
        "gate_4": "not_started",
        "gate_5": "blocked",
        "gate_6": "blocked",
    }
    for gate, state in expected.items():
        if gates.get(gate, {}).get("state") != state:
            fail(f"{gate} expected {state}")

    if controls.get("ids_substituted") is not False:
        fail("ids_substituted must be false")
    if controls.get("candidate_values_printed") is not False:
        fail("candidate_values_printed must be false")
    if controls.get("live_execution") is not False:
        fail("live_execution must be false")
    if controls.get("local_file_only_plan") is not True:
        fail("local_file_only_plan must be true")
    if controls.get("actionable_plan_changes") != 4:
        fail("actionable_plan_changes must be 4")

    print("Workspace Mesh Full Local Checkpoint")
    print("====================================")
    print("mesh_state=prepared-but-not-deployed")
    print("gate_0=complete")
    print("gate_1=reviewed_no_promotion")
    print("gate_2=planning_only")
    print("gate_3=blocked")
    print("gate_4=not_started")
    print("gate_5=blocked")
    print("gate_6=blocked")
    print("plan_safety=passed")
    print("local_file_only_plan=true")
    print("actionable_plan_changes=4")
    print("gate1_artifact_review=passed")
    print("gate2_candidate_lifecycle=passed")
    print("promotion_blocker=active")
    print("current_state_ledger=valid")
    print("ids_substituted=false")
    print("candidate_values_printed=false")
    print("live_execution=false")
    print("next_allowed_action=current_state_validation_or_gate3_planning_scaffold_only")


if __name__ == "__main__":
    main()
