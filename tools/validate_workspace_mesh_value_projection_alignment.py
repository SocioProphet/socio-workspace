#!/usr/bin/env python3
"""Validate Sociosphere alignment to the Workspace PROPHET value projection fixture."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALIGNMENT = ROOT / "registry" / "workspace-mesh-value-projection-alignment.v0.json"
CURRENT_STATE = ROOT / "registry" / "workspace-mesh-current-state.v0.json"
GATE3 = ROOT / "registry" / "workspace-mesh-gate3-planning.v0.json"

EXPECTED_KPIS = {
    "validated_control_loop_steps",
    "blocked_unapproved_action_classes",
}


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def load_json(path: Path) -> dict:
    if not path.exists():
        fail(f"missing file: {path.relative_to(ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    alignment = load_json(ALIGNMENT)
    current_state = load_json(CURRENT_STATE)
    gate3 = load_json(GATE3)

    if alignment.get("mesh_state") != "prepared-but-not-deployed":
        fail("alignment must keep mesh prepared-but-not-deployed")
    if alignment.get("topology_authority") != "SocioProphet/sociosphere":
        fail("topology authority mismatch")
    if alignment.get("value_projection_authority") != "SocioProphet/prophet-platform":
        fail("value projection authority mismatch")

    fixture = alignment.get("prophet_platform_fixture", {})
    if fixture.get("repository") != "SocioProphet/prophet-platform":
        fail("fixture repository mismatch")
    if fixture.get("path") != "contracts/workspace-prophet/e2e/value-claim-projection-workspace-prophet-v0.json":
        fail("fixture path mismatch")
    if fixture.get("validator") != "tools/validate_workspace_prophet_value_projection.py":
        fail("fixture validator mismatch")
    if fixture.get("production_ready") is not False:
        fail("fixture production_ready must be false")
    if fixture.get("observation_window") != "fixture_validation_only":
        fail("fixture observation_window must be fixture_validation_only")
    if fixture.get("primary_value_driver") != "productivity":
        fail("primary value driver must be productivity")
    if set(fixture.get("required_kpis", [])) != EXPECTED_KPIS:
        fail("required KPI set mismatch")

    sx = alignment.get("sociosphere_alignment", {})
    if sx.get("does_not_duplicate_value_logic") is not True:
        fail("Sociosphere must not duplicate value logic")
    if sx.get("references_external_value_authority") is not True:
        fail("Sociosphere must reference external value authority")
    if sx.get("gate_state_dependency") != "gate_3_blocked":
        fail("alignment must depend on Gate 3 remaining blocked")

    if current_state.get("gates", {}).get("gate_3", {}).get("state") != "blocked":
        fail("current-state ledger must keep Gate 3 blocked")
    if gate3.get("gate_3_state") != "blocked":
        fail("Gate 3 planning manifest must keep Gate 3 blocked")

    flags = alignment.get("status_flags", {})
    for key in [
        "ids_substituted",
        "candidate_values_printed",
        "live_execution",
        "production_processing",
        "value_claim_projection_copied_into_sociosphere",
    ]:
        if flags.get(key) is not False:
            fail(f"status flag {key} must be false")

    print("PASS: Workspace mesh value projection alignment is valid")
    print("topology_authority=SocioProphet/sociosphere")
    print("value_projection_authority=SocioProphet/prophet-platform")
    print("fixture_path=contracts/workspace-prophet/e2e/value-claim-projection-workspace-prophet-v0.json")
    print("primary_value_driver=productivity")
    print("required_kpis=2")
    print("production_ready=false")
    print("gate_3=blocked")
    print("live_execution=false")


if __name__ == "__main__":
    main()
