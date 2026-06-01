#!/usr/bin/env python3
"""Validate registry/computational-artifacts.yaml."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "registry" / "computational-artifacts.yaml"

REQUIRED_FRESHNESS_STATES = {"fresh", "stale", "drifted", "blocked", "deprecated"}
REQUIRED_PROPAGATION_TRIGGERS = {
    "artifactContractChanged",
    "runtimeProfileChanged",
    "policyChanged",
    "evidenceChanged",
    "safetyClassPrivileged",
    "safetyClassProhibited",
}
REQUIRED_SAFETY_CLASSES = {"advisory", "bounded", "privileged", "prohibited"}
REQUIRED_ENTRY_FIELDS = {"id", "ownerRepo", "runtimeProfile", "safetyClass", "downstreamConsumers", "requiredEvidence"}


def fail(message: str) -> int:
    print(f"ERR: {message}", file=sys.stderr)
    return 1


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def require_dict(obj: Any, key: str, ctx: str) -> dict[str, Any]:
    val = obj.get(key) if isinstance(obj, dict) else None
    require(isinstance(val, dict), f"{ctx}.{key} must be a mapping")
    return val  # type: ignore[return-value]


def require_list(obj: Any, key: str, ctx: str) -> list[Any]:
    val = obj.get(key) if isinstance(obj, dict) else None
    require(isinstance(val, list), f"{ctx}.{key} must be a list")
    return val  # type: ignore[return-value]


def main() -> int:
    if yaml is None:
        return fail("PyYAML is required: pip install pyyaml")
    try:
        data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
        require(isinstance(data, dict), "registry must be a YAML mapping")
        require(data.get("apiVersion") == "sociosphere.socioprophet.org/v1alpha1", "invalid apiVersion")
        require(data.get("kind") == "ComputationalArtifactRegistry", "invalid kind")
        metadata = require_dict(data, "metadata", "root")
        require(isinstance(metadata.get("name"), str), "metadata.name must be a string")
        require(isinstance(metadata.get("version"), str), "metadata.version must be a string")
        spec = require_dict(data, "spec", "root")
        safety_classes = require_dict(spec, "safetyClasses", "spec")
        missing_safety = sorted(REQUIRED_SAFETY_CLASSES - set(safety_classes))
        require(not missing_safety, f"spec.safetyClasses missing: {missing_safety}")
        for safety_class in ("privileged", "prohibited"):
            default_review = safety_classes[safety_class].get("defaultReview")
            require(
                default_review in ("human-required", "blocked"),
                f"spec.safetyClasses.{safety_class}.defaultReview must be human-required or blocked",
            )
        health_model = require_dict(spec, "healthModel", "spec")
        freshness = set(require_list(health_model, "freshnessStates", "spec.healthModel"))
        missing_states = sorted(REQUIRED_FRESHNESS_STATES - freshness)
        require(not missing_states, f"spec.healthModel.freshnessStates missing: {missing_states}")
        require_list(health_model, "requiredSignals", "spec.healthModel")
        prop_rules = require_list(spec, "propagationRules", "spec")
        actual_triggers = {rule.get("when") for rule in prop_rules if isinstance(rule, dict)}
        missing_triggers = sorted(REQUIRED_PROPAGATION_TRIGGERS - actual_triggers)
        require(not missing_triggers, f"spec.propagationRules missing triggers: {missing_triggers}")
        for rule in prop_rules:
            if not isinstance(rule, dict):
                continue
            if rule.get("when") in ("safetyClassPrivileged", "safetyClassProhibited"):
                require(rule.get("blockAutoPromotion") is True, f"{rule.get('when')} must block auto-promotion")
                require(rule.get("requireHumanReview") is True, f"{rule.get('when')} must require human review")
        governance = require_dict(spec, "governance", "spec")
        slash_binding = require_dict(governance, "slashTopicBinding", "spec.governance")
        require(isinstance(slash_binding.get("namespace"), str), "slashTopicBinding.namespace must be a string")
        require_list(slash_binding, "topics", "spec.governance.slashTopicBinding")
        require(isinstance(slash_binding.get("governingRepo"), str), "slashTopicBinding.governingRepo must be a string")
        entries = require_list(spec, "registryEntries", "spec")
        require(entries, "spec.registryEntries must not be empty")
        seen_ids: set[str] = set()
        for entry in entries:
            require(isinstance(entry, dict), "each registryEntry must be a mapping")
            entry_id = entry.get("id", "<unknown>")
            require(entry_id not in seen_ids, f"duplicate registryEntry id: {entry_id}")
            seen_ids.add(entry_id)
            for field in REQUIRED_ENTRY_FIELDS:
                require(field in entry, f"registryEntry '{entry_id}' missing required field: {field}")
            require(entry.get("safetyClass") in safety_classes, f"registryEntry '{entry_id}' has unknown safetyClass")
            require(isinstance(entry.get("downstreamConsumers"), list) and entry["downstreamConsumers"], f"registryEntry '{entry_id}' downstreamConsumers must be non-empty list")
    except FileNotFoundError:
        return fail(f"missing registry file: {REGISTRY}")
    except ValueError as exc:
        return fail(str(exc))

    print(f"OK: validated computational-artifacts registry ({len(entries)} entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
