#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "registry" / "sovereign-validation-fabric.yaml"


def load_registry() -> dict[str, Any]:
    data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("registry must be a mapping")
    return data


def state_for(profile: dict[str, Any]) -> dict[str, Any]:
    command = profile.get("validation_command")
    refs = profile.get("contract_refs", [])
    warnings = []
    status = "selected_missing_observation" if command else "not_configured"
    if command:
        warnings.append("validation_observation_missing")
    else:
        warnings.append("validation_command_missing")
    if not refs:
        warnings.append("contract_refs_missing")
    return {
        "profile_id": profile.get("profile_id"),
        "repo": profile.get("repo"),
        "owning_plane": profile.get("owning_plane"),
        "mode": profile.get("mode"),
        "policy_ref": profile.get("policy_ref"),
        "default_plans": profile.get("default_plans", []),
        "contract_refs": refs,
        "validation_command": command,
        "required_receipt_classes": profile.get("required_receipt_classes", []),
        "validation_status": status,
        "warnings": warnings,
        "observed_validation_commands": [],
        "receipt_refs": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo")
    args = parser.parse_args()
    registry = load_registry()
    profiles = registry.get("profiles", [])
    selected = [p for p in profiles if isinstance(p, dict) and (args.repo is None or p.get("repo") == args.repo)]
    output = {
        "schema_version": "1.0",
        "state_id": "svf:workspace-state:sociosphere.current",
        "registry_id": registry.get("registry_id"),
        "profile_count": len(selected),
        "profiles": [state_for(p) for p in selected],
        "non_claims": [
            "This is registry-derived workspace state.",
            "Missing observations remain explicit.",
            "Receipt refs are empty unless observed evidence is attached."
        ]
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
