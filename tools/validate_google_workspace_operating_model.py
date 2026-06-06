#!/usr/bin/env python3
"""Validate the Google Workspace operating model manifest."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "registry" / "google-workspace-operating-model.v0.json"
EXPECTED_SURFACES = {
    "calendars",
    "groups",
    "sheets",
    "apps_script",
    "dashboards",
    "socioprophet_native",
}


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def load_json(path: Path) -> dict:
    if not path.exists():
        fail(f"missing file: {path.relative_to(ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    model = load_json(MODEL)

    if model.get("mesh_state") != "prepared-but-not-deployed":
        fail("operating model must keep mesh prepared-but-not-deployed")
    if model.get("operating_model_state") != "contract_only":
        fail("operating_model_state must be contract_only")
    if model.get("workspace_role") != "provisional_management_layer":
        fail("workspace_role mismatch")
    if model.get("native_target") != "SocioProphet":
        fail("native_target must be SocioProphet")

    surfaces = model.get("surfaces", {})
    if set(surfaces) != EXPECTED_SURFACES:
        fail("surface set mismatch")

    for key in ["calendars", "groups", "sheets", "dashboards"]:
        if surfaces[key].get("live_asset_creation") is not False:
            fail(f"{key} live_asset_creation must be false")
    if surfaces["apps_script"].get("live_execution") is not False:
        fail("apps_script live_execution must be false")
    if surfaces["apps_script"].get("state") != "blocked_until_gate3_approval":
        fail("apps_script must remain blocked until Gate 3 approval")
    if surfaces["socioprophet_native"].get("live_migration") is not False:
        fail("native migration must be false")

    required_contracts = model.get("required_existing_contracts", [])
    for relative_path in required_contracts:
        if not (ROOT / relative_path).exists():
            fail(f"required contract missing: {relative_path}")

    controls = model.get("controls", {})
    expected_controls = {
        "no_live_calendar_creation": True,
        "no_live_group_creation": True,
        "no_live_sheet_creation": True,
        "no_apps_script_execution": True,
        "no_dashboard_publication": True,
        "no_native_migration": True,
        "candidate_values_printed": False,
        "live_execution": False,
    }
    for key, expected in expected_controls.items():
        if controls.get(key) is not expected:
            fail(f"control {key} expected {expected}, found {controls.get(key)}")

    print("PASS: Google Workspace operating model is valid")
    print("mesh_state=prepared-but-not-deployed")
    print("operating_model_state=contract_only")
    print("workspace_role=provisional_management_layer")
    print(f"surfaces={len(EXPECTED_SURFACES)}")
    print("apps_script_state=blocked_until_gate3_approval")
    print("native_target=SocioProphet")
    print("live_execution=false")


if __name__ == "__main__":
    main()
