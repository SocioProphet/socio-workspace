#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "registry" / "environment-sandbox-profiles.yaml"
REQUIRED_STATES = {
    "selected_status",
    "requested_status",
    "running_status",
    "observed_status",
    "failed_status",
    "stale_status",
}
VALID_MODES = {"advisory", "blocking"}
VALID_ROUTING_VALUES = {"not_configured", "configured", "required", "unsupported"}


def check(check_id: str, passed: bool, diagnostics: list[str] | None = None) -> dict[str, Any]:
    return {"check_id": check_id, "passed": bool(passed), "diagnostics": diagnostics or []}


def load_registry() -> dict[str, Any]:
    data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("environment sandbox registry must be a mapping")
    return data


def validate_profile(profile: dict[str, Any], index: int) -> list[dict[str, Any]]:
    prefix = f"profile[{index}]"
    results: list[dict[str, Any]] = []
    profile_id = profile.get("profile_id")
    repo = profile.get("repo")
    routing = profile.get("routing", {})
    execution = profile.get("execution", {})
    policy = profile.get("changed_service_policy", {})

    results.append(check(f"{prefix}:profile-id", isinstance(profile_id, str) and profile_id.startswith("environment-sandbox:profile:"), [str(profile_id)]))
    results.append(check(f"{prefix}:repo", isinstance(repo, str) and "/" in repo, [str(repo)]))
    results.append(check(f"{prefix}:owning-plane", isinstance(profile.get("owning_plane"), str) and len(profile["owning_plane"]) > 0))
    results.append(check(f"{prefix}:mode", profile.get("mode") in VALID_MODES, [str(profile.get("mode"))]))
    results.append(check(f"{prefix}:sandbox-kind", isinstance(profile.get("sandbox_kind"), str) and len(profile["sandbox_kind"]) > 0))
    results.append(check(f"{prefix}:baseline-ref", isinstance(profile.get("baseline_ref"), str) and profile["baseline_ref"].startswith("workspace://"), [str(profile.get("baseline_ref"))]))

    results.append(check(f"{prefix}:changed-service-policy", isinstance(policy, dict)))
    if isinstance(policy, dict):
        results.append(check(f"{prefix}:delta-deploy-boolean", isinstance(policy.get("delta_deploy_allowed"), bool)))
        results.append(check(f"{prefix}:baseline-fallback-boolean", isinstance(policy.get("baseline_fallback_required"), bool)))
        results.append(check(f"{prefix}:changed-service-refs-list", isinstance(policy.get("changed_service_refs"), list)))

    results.append(check(f"{prefix}:routing", isinstance(routing, dict)))
    if isinstance(routing, dict):
        for field in ["http_grpc_routing", "async_queue_isolation", "stateful_resource_isolation"]:
            results.append(check(f"{prefix}:routing:{field}", routing.get(field) in VALID_ROUTING_VALUES, [str(routing.get(field))]))

    results.append(check(f"{prefix}:execution", isinstance(execution, dict)))
    if isinstance(execution, dict):
        results.append(check(f"{prefix}:executor-plane", execution.get("executor_plane") == "AgentPlane", [str(execution.get("executor_plane"))]))
        results.append(check(f"{prefix}:execution-configured-boolean", isinstance(execution.get("execution_configured"), bool)))
        results.append(check(f"{prefix}:validation-command", isinstance(execution.get("validation_command"), str) and len(execution["validation_command"]) > 0))
        results.append(check(f"{prefix}:evidence-required-boolean", isinstance(execution.get("evidence_required"), bool)))
        if execution.get("execution_configured") is False:
            results.append(check(f"{prefix}:unconfigured-evidence-required", execution.get("evidence_required") is True))

    results.append(check(f"{prefix}:consumers", isinstance(profile.get("consumers"), list) and len(profile.get("consumers", [])) >= 1))
    results.append(check(f"{prefix}:non-claims", isinstance(profile.get("non_claims"), list) and len(profile.get("non_claims", [])) >= 1))
    return results


def main() -> int:
    registry = load_registry()
    results: list[dict[str, Any]] = []
    results.append(check("schema-version", registry.get("schema_version") == "1.0"))
    results.append(check("registry-id", registry.get("registry_id") == "environment-sandbox:registry:sociosphere.workspace"))
    results.append(check("plane", registry.get("plane") == "workspace-environment-state"))
    state_model = registry.get("state_model", {})
    missing_states = sorted(REQUIRED_STATES - set(state_model)) if isinstance(state_model, dict) else sorted(REQUIRED_STATES)
    results.append(check("state-model", isinstance(state_model, dict) and not missing_states, missing_states))
    profiles = registry.get("profiles", [])
    results.append(check("profiles", isinstance(profiles, list) and len(profiles) >= 1))
    if isinstance(profiles, list):
        for index, profile in enumerate(profiles):
            if isinstance(profile, dict):
                results.extend(validate_profile(profile, index))
            else:
                results.append(check(f"profile[{index}]:mapping", False))
    passed = all(item["passed"] for item in results)
    print(json.dumps({"validator": "sociosphere.environment-sandbox-profiles.validator.v1", "passed": passed, "results": results}, indent=2, sort_keys=True))
    print(("PASS" if passed else "FAIL") + ": environment sandbox profiles")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
