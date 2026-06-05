#!/usr/bin/env python3
"""Validate the Workspace mesh dashboard ledger contract."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "workspace-mesh" / "dashboard-ledger.v0.json"
CURRENT_STATE = ROOT / "registry" / "workspace-mesh-current-state.v0.json"
VALUE_ALIGNMENT = ROOT / "registry" / "workspace-mesh-value-projection-alignment.v0.json"

EXPECTED_TABS = {
    "Meetings",
    "Automations",
    "Workstreams",
    "Decisions",
    "Risks",
    "Claims",
    "ValueProjections",
    "GateProofs",
    "OperatorActions",
}

MIN_FIELDS = {
    "Meetings": 7,
    "Automations": 6,
    "Workstreams": 5,
    "Decisions": 5,
    "Risks": 5,
    "Claims": 5,
    "ValueProjections": 5,
    "GateProofs": 5,
    "OperatorActions": 5,
}


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def load_json(path: Path) -> dict:
    if not path.exists():
        fail(f"missing file: {path.relative_to(ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    contract = load_json(CONTRACT)
    current_state = load_json(CURRENT_STATE)
    value_alignment = load_json(VALUE_ALIGNMENT)

    if contract.get("mesh_state") != "prepared-but-not-deployed":
        fail("dashboard ledger must keep mesh prepared-but-not-deployed")
    if contract.get("dashboard_state") != "contract_only":
        fail("dashboard_state must be contract_only")
    if contract.get("sheet_id") != "TODO_GOOGLE_SHEET_ID":
        fail("sheet_id must remain placeholder")
    if contract.get("dashboard_id") != "TODO_DASHBOARD_ID":
        fail("dashboard_id must remain placeholder")
    if contract.get("live_dashboard_created") is not False:
        fail("live_dashboard_created must be false")

    tabs = contract.get("tabs", {})
    if set(tabs) != EXPECTED_TABS:
        fail("dashboard ledger tab set mismatch")
    for tab, minimum in MIN_FIELDS.items():
        fields = tabs.get(tab, {}).get("required_fields", [])
        if len(fields) < minimum:
            fail(f"tab {tab} has too few required fields")
        if len(fields) != len(set(fields)):
            fail(f"tab {tab} contains duplicate fields")

    controls = contract.get("controls", {})
    expected_controls = {
        "no_live_sheet_required": True,
        "no_dashboard_publication": True,
        "no_looker_studio_action": True,
        "no_workspace_mutation": True,
        "candidate_values_printed": False,
        "live_execution": False,
    }
    for key, expected in expected_controls.items():
        if controls.get(key) is not expected:
            fail(f"control {key} expected {expected}, found {controls.get(key)}")

    if current_state.get("mesh_state") != "prepared-but-not-deployed":
        fail("current-state ledger mesh_state mismatch")
    if current_state.get("gates", {}).get("gate_3", {}).get("state") != "blocked":
        fail("Gate 3 must remain blocked")
    if value_alignment.get("value_projection_authority") != "SocioProphet/prophet-platform":
        fail("value projection authority mismatch")

    print("PASS: Workspace mesh dashboard ledger contract is valid")
    print("dashboard_state=contract_only")
    print(f"tabs={len(EXPECTED_TABS)}")
    print("sheet_id=TODO_GOOGLE_SHEET_ID")
    print("dashboard_id=TODO_DASHBOARD_ID")
    print("live_dashboard_created=false")
    print("gate_3=blocked")
    print("live_execution=false")


if __name__ == "__main__":
    main()
