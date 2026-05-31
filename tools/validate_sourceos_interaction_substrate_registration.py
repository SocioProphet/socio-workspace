#!/usr/bin/env python3
"""Validate SocioSphere registration for the SourceOS interaction substrate."""

from __future__ import annotations

from pathlib import Path

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("pyyaml is required: python3 -m pip install pyyaml") from exc

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "registry" / "sourceos-interaction-substrate.yaml"
INTEGRATION_STATUS = ROOT / "docs" / "INTEGRATION_STATUS.md"

REQUIRED_PLANES = {
    "sourceos_spec": "SourceOS-Linux/sourceos-spec",
    "noetica": "SocioProphet/Noetica",
    "agent_term": "SourceOS-Linux/agent-term",
    "superconscious": "SocioProphet/superconscious",
    "agentplane": "SocioProphet/agentplane",
}

REQUIRED_NON_SCOPE = {
    "feature implementation",
    "runtime event transport",
    "policy admission",
    "identity or grant authority",
    "durable memory writeback",
    "execution evidence production",
}

REQUIRED_VALIDATION_KEYS = {
    "sourceos_spec",
    "noetica",
    "agent_term",
    "superconscious",
    "agentplane",
}

REQUIRED_STATUS_PHRASES = {
    "### SourceOS Interaction Substrate",
    "Workspace routing record: `registry/sourceos-interaction-substrate.yaml`",
    "Current scope in SocioSphere: cross-repo status",
    "Non-scope in SocioSphere: feature implementation",
}


def main() -> int:
    data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("registry root must be a mapping")

    require_equal(data.get("version"), "0.1.0", "version")
    require_equal(data.get("status"), "registered", "status")

    canonical = require_mapping(data, "canonical_contract")
    require_equal(canonical.get("repo"), "SourceOS-Linux/sourceos-spec", "canonical_contract.repo")
    require_equal(canonical.get("schema"), "schemas/SourceOSInteractionEvent.json", "canonical_contract.schema")
    require_nonempty(canonical.get("reference_flow"), "canonical_contract.reference_flow")
    require_nonempty(canonical.get("implementation_ledger"), "canonical_contract.implementation_ledger")
    require_nonempty(canonical.get("latest_merge_commit"), "canonical_contract.latest_merge_commit")

    workspace_role = require_mapping(data, "workspace_role")
    require_nonempty(workspace_role.get("sociosphere"), "workspace_role.sociosphere")
    non_scope = set(workspace_role.get("non_scope") or [])
    missing_non_scope = REQUIRED_NON_SCOPE - non_scope
    if missing_non_scope:
        raise SystemExit("missing non-scope entries: " + ", ".join(sorted(missing_non_scope)))

    planes = require_mapping(data, "planes")
    for plane, repo in REQUIRED_PLANES.items():
        entry = require_mapping(planes, plane)
        require_equal(entry.get("repo"), repo, f"planes.{plane}.repo")
        require_equal(entry.get("status"), "merged", f"planes.{plane}.status")
        require_nonempty(entry.get("role"), f"planes.{plane}.role")

    validation_lanes = require_mapping(data, "validation_lanes")
    missing_validation = REQUIRED_VALIDATION_KEYS - set(validation_lanes)
    if missing_validation:
        raise SystemExit("missing validation lane keys: " + ", ".join(sorted(missing_validation)))
    for key in REQUIRED_VALIDATION_KEYS:
        lanes = validation_lanes.get(key)
        if not isinstance(lanes, list) or not lanes:
            raise SystemExit(f"validation_lanes.{key} must be a non-empty list")

    status_text = INTEGRATION_STATUS.read_text(encoding="utf-8")
    for phrase in REQUIRED_STATUS_PHRASES:
        if phrase not in status_text:
            raise SystemExit(f"integration status missing phrase: {phrase}")

    print("OK: SourceOS interaction substrate registration validated")
    return 0


def require_mapping(parent: dict, key: str) -> dict:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise SystemExit(f"{key} must be a mapping")
    return value


def require_equal(actual: object, expected: object, label: str) -> None:
    if actual != expected:
        raise SystemExit(f"{label}: expected {expected!r}, got {actual!r}")


def require_nonempty(value: object, label: str) -> None:
    if not isinstance(value, str) or not value:
        raise SystemExit(f"{label} must be a non-empty string")


if __name__ == "__main__":
    raise SystemExit(main())
