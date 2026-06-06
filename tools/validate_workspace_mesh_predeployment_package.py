#!/usr/bin/env python3
"""Validate the Workspace mesh predeployment package."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "registry" / "workspace-mesh-predeployment-package-2026-06-06.json"

EXPECTED_GATE_STATES = {
    "gate_0": "complete",
    "gate_1": "reviewed_no_promotion",
    "gate_2": "planning_only",
    "gate_3": "blocked",
    "gate_4": "not_started",
    "gate_5": "blocked",
    "gate_6": "blocked",
}

EXPECTED_FALSE_CONTROLS = {
    "ids_substituted",
    "candidate_values_printed",
    "live_execution",
    "workspace_assets_created",
    "cloud_deployment_authorized",
    "scheduled_triggers_authorized",
    "production_processing_authorized",
    "native_migration_started",
    "vendor_lock_in_accepted",
}


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def load_json(path: Path) -> dict:
    if not path.exists():
        fail(f"missing file: {path.relative_to(ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))


def require_path(path_string: str) -> None:
    path = ROOT / path_string
    if not path.exists():
        fail(f"package references missing path: {path_string}")


def main() -> None:
    package = load_json(PACKAGE)

    if package.get("mesh_state") != "prepared-but-not-deployed":
        fail("package mesh_state must remain prepared-but-not-deployed")
    if package.get("package_state") != "predeployment_proof_bundle":
        fail("package_state must be predeployment_proof_bundle")
    if package.get("topology_repo") != "SocioProphet/sociosphere":
        fail("topology_repo mismatch")
    if package.get("implementation_repo") != "SocioProphet/prophet-platform-fabric-mlops-ts-suite":
        fail("implementation_repo mismatch")
    if package.get("value_projection_authority") != "SocioProphet/prophet-platform":
        fail("value_projection_authority mismatch")

    proofs = package.get("proofs", {})
    if len(proofs) < 18:
        fail("expected at least 18 proof references")
    for proof_name, proof_path in proofs.items():
        if not proof_name or not proof_path:
            fail("proof key/path cannot be empty")
        require_path(proof_path)

    artifacts = package.get("validated_artifacts", {})
    if len(artifacts) < 7:
        fail("expected at least 7 validated artifact references")
    for artifact_name, artifact_path in artifacts.items():
        if not artifact_name or not artifact_path:
            fail("artifact key/path cannot be empty")
        require_path(artifact_path)

    gate_states = package.get("gate_states", {})
    if gate_states != EXPECTED_GATE_STATES:
        fail("gate states mismatch")

    controls = package.get("controls", {})
    for key in EXPECTED_FALSE_CONTROLS:
        if controls.get(key) is not False:
            fail(f"control {key} must be false")

    current_state = load_json(ROOT / artifacts["current_state_ledger"])
    if current_state.get("mesh_state") != "prepared-but-not-deployed":
        fail("current-state ledger mesh_state mismatch")
    if current_state.get("gates", {}).get("gate_3", {}).get("state") != "blocked":
        fail("current-state ledger must keep Gate 3 blocked")

    print("PASS: Workspace mesh predeployment package is valid")
    print("mesh_state=prepared-but-not-deployed")
    print("package_state=predeployment_proof_bundle")
    print(f"proofs={len(proofs)}")
    print(f"validated_artifacts={len(artifacts)}")
    print("gate_3=blocked")
    print("workspace_assets_created=false")
    print("cloud_deployment_authorized=false")
    print("live_execution=false")


if __name__ == "__main__":
    main()
