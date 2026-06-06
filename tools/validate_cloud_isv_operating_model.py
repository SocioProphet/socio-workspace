#!/usr/bin/env python3
"""Validate the SocioProphet cloud ISV operating model."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "registry" / "cloud-isv-operating-model.v0.json"
EXPECTED_CLOUDS = {"aws", "google", "azure", "socioprophet"}


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def load_json(path: Path) -> dict:
    if not path.exists():
        fail(f"missing file: {path.relative_to(ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    model = load_json(MODEL)

    if model.get("model_state") != "planning_only":
        fail("model_state must be planning_only")
    if model.get("mesh_state") != "prepared-but-not-deployed":
        fail("mesh_state must remain prepared-but-not-deployed")
    if model.get("vendor_neutral_control_plane") != "SocioProphet":
        fail("vendor_neutral_control_plane must be SocioProphet")

    cloud_roles = model.get("cloud_roles", {})
    if set(cloud_roles) != EXPECTED_CLOUDS:
        fail("cloud_roles set mismatch")

    for cloud in ["aws", "google", "azure"]:
        role = cloud_roles[cloud]
        if role.get("deployment_authorized") is not False:
            fail(f"{cloud} deployment_authorized must be false")
        if role.get("state") not in {"planning_only", "contract_only"}:
            fail(f"{cloud} state must be planning_only or contract_only")

    if cloud_roles["aws"].get("account_identifier_present") is not False:
        fail("AWS account identifier must not be present")
    if cloud_roles["google"].get("project_identifier_present") is not False:
        fail("Google project identifier must not be present")
    if cloud_roles["azure"].get("subscription_identifier_present") is not False:
        fail("Azure subscription identifier must not be present")
    if cloud_roles["socioprophet"].get("role") != "vendor_neutral_orchestration_governance_and_native_control_plane":
        fail("SocioProphet role mismatch")
    if cloud_roles["socioprophet"].get("native_migration_live") is not False:
        fail("native migration must not be live")

    for relative_path in model.get("required_existing_artifacts", []):
        if not (ROOT / relative_path).exists():
            fail(f"required artifact missing: {relative_path}")

    controls = model.get("controls", {})
    expected_controls = {
        "no_vendor_lock_in": True,
        "no_cloud_deployment": True,
        "no_credentials": True,
        "no_tenant_ids": True,
        "no_subscription_ids": True,
        "no_project_ids": True,
        "live_execution": False,
    }
    for key, expected in expected_controls.items():
        if controls.get(key) is not expected:
            fail(f"control {key} expected {expected}, found {controls.get(key)}")

    print("PASS: Cloud ISV operating model is valid")
    print("model_state=planning_only")
    print("mesh_state=prepared-but-not-deployed")
    print("vendor_neutral_control_plane=SocioProphet")
    print(f"cloud_roles={len(EXPECTED_CLOUDS)}")
    print("aws_deployment_authorized=false")
    print("google_deployment_authorized=false")
    print("azure_deployment_authorized=false")
    print("no_vendor_lock_in=true")
    print("live_execution=false")


if __name__ == "__main__":
    main()
