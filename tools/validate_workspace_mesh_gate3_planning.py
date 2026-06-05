#!/usr/bin/env python3
"""Validate the Workspace mesh Gate 3 planning scaffold."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "registry" / "workspace-mesh-gate3-planning.v0.json"
BLOCKER = ROOT / "registry" / "workspace-mesh-gate2-promotion-blocker.v0.json"
CURRENT_STATE = ROOT / "registry" / "workspace-mesh-current-state.v0.json"


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def load_json(path: Path) -> dict:
    if not path.exists():
        fail(f"missing file: {path.relative_to(ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    manifest = load_json(MANIFEST)
    blocker = load_json(BLOCKER)
    current_state = load_json(CURRENT_STATE)

    if manifest.get("mesh_state") != "prepared-but-not-deployed":
        fail("Gate 3 planning must keep mesh prepared-but-not-deployed")
    if manifest.get("gate_2_state") != "planning_only":
        fail("Gate 2 must remain planning_only")
    if manifest.get("gate_3_state") != "blocked":
        fail("Gate 3 must remain blocked")
    if manifest.get("planning_state") != "available":
        fail("Gate 3 planning_state must be available")
    if manifest.get("dry_run_required") is not True:
        fail("dry_run_required must be true")
    if manifest.get("promotion_blocker_required") is not True:
        fail("promotion blocker must be required")
    if manifest.get("gate2_approval_required") is not True:
        fail("Gate 2 approval must be required")
    if manifest.get("gate3_start_record_required") is not True:
        fail("Gate 3 start record must be required")

    if blocker.get("blocker_state") != "active":
        fail("Gate 2 promotion blocker must remain active")
    if blocker.get("gate_3_state") != "blocked":
        fail("blocker must keep Gate 3 blocked")
    if current_state.get("gates", {}).get("gate_3", {}).get("state") != "blocked":
        fail("current-state ledger must keep Gate 3 blocked")

    flags = manifest.get("status_flags", {})
    for key in ["ids_substituted", "candidate_values_printed", "live_execution", "gate3_started"]:
        if flags.get(key) is not False:
            fail(f"status flag {key} must be false")

    required_validations = set(manifest.get("required_prior_validations", []))
    expected_validations = {
        "workspace-mesh-local-checkpoint",
        "workspace-mesh-gate2-promotion-blocker-validate",
        "workspace-mesh-current-state-validate",
    }
    if required_validations != expected_validations:
        fail("required prior validations mismatch")

    print("PASS: Workspace mesh Gate 3 planning scaffold is valid")
    print("mesh_state=prepared-but-not-deployed")
    print("gate_2=planning_only")
    print("gate_3=blocked")
    print("planning_state=available")
    print("dry_run_required=true")
    print("promotion_blocker_required=true")
    print("ids_substituted=false")
    print("candidate_values_printed=false")
    print("live_execution=false")


if __name__ == "__main__":
    main()
