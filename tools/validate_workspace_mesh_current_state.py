#!/usr/bin/env python3
"""Validate the Workspace mesh current-state ledger."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "registry" / "workspace-mesh-current-state.v0.json"

EXPECTED_GATE_STATES = {
    "gate_0": "complete",
    "gate_1": "reviewed_no_promotion",
    "gate_2": "planning_only",
    "gate_3": "blocked",
    "gate_4": "not_started",
    "gate_5": "blocked",
    "gate_6": "blocked",
}


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def require_path(relative_path: str) -> None:
    path = ROOT / relative_path
    if not path.exists():
        fail(f"ledger references missing path: {relative_path}")


def main() -> None:
    if not LEDGER.exists():
        fail(f"missing ledger: {LEDGER.relative_to(ROOT)}")

    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))

    if ledger.get("mesh_state") != "prepared-but-not-deployed":
        fail("mesh_state must remain prepared-but-not-deployed")

    gates = ledger.get("gates", {})
    if set(gates) != set(EXPECTED_GATE_STATES):
        fail("gate set mismatch")

    for gate_key, expected_state in EXPECTED_GATE_STATES.items():
        state = gates.get(gate_key, {}).get("state")
        if state != expected_state:
            fail(f"{gate_key} state expected {expected_state}, found {state}")

    gate0_proof = gates["gate_0"].get("proof")
    if gate0_proof:
        require_path(gate0_proof)
    else:
        fail("gate_0 proof missing")

    for gate_key in ["gate_1", "gate_2"]:
        proofs = gates[gate_key].get("proofs", [])
        if not proofs:
            fail(f"{gate_key} proofs missing")
        for proof in proofs:
            require_path(proof)

    blocked_by = gates["gate_3"].get("blocked_by")
    if blocked_by:
        require_path(blocked_by)
    else:
        fail("gate_3 blocked_by missing")

    controls = ledger.get("controls", {})
    expected_controls = {
        "local_file_only_plan": True,
        "candidate_values_printed": False,
        "ids_substituted": False,
        "live_execution": False,
        "gate3_approval_artifact_present": False,
    }
    for key, expected in expected_controls.items():
        if controls.get(key) is not expected:
            fail(f"control {key} expected {expected}, found {controls.get(key)}")
    if controls.get("plan_safety") != "passed":
        fail("plan_safety must be passed")
    if controls.get("actionable_plan_changes") != 4:
        fail("actionable_plan_changes must be 4")

    print("PASS: Workspace mesh current-state ledger is valid")
    print("mesh_state=prepared-but-not-deployed")
    print("gate_0=complete")
    print("gate_1=reviewed_no_promotion")
    print("gate_2=planning_only")
    print("gate_3=blocked")
    print("ids_substituted=false")
    print("candidate_values_printed=false")
    print("live_execution=false")


if __name__ == "__main__":
    main()
