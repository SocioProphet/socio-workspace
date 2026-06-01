#!/usr/bin/env python3
"""Validate registry/computational-artifacts.yaml.

Checks:
- Required top-level structure (apiVersion, kind, metadata, spec).
- spec.safetyClasses includes advisory, bounded, privileged, prohibited.
- spec.healthModel.freshnessStates includes all required states.
- spec.propagationRules covers artifactContractChanged, runtimeProfileChanged,
  policyChanged, evidenceChanged, safetyClassPrivileged, safetyClassProhibited.
- privileged and prohibited safety classes block auto-promotion.
- spec.governance.slashTopicBinding is present.
- Each registryEntry has required fields and valid safetyClass.
"""
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
REQUIRED_ENTRY_FIELDS = {
    "id",
    "ownerRepo",
    "runtimeProfile",
    "safetyClass",
    "downstreamConsumers",
    "requiredEvidence",
}
BLOCKED_AUTO_PROMOTE_CLASSES = {"privileged", "prohibited"}


def fail(message: str) -> int:
    print(f"ERR: {message}", file=sys.stderr)
    return 1


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def require_list(obj: Any, key: str, ctx: str) -> list[Any]:
    val = obj.get(key) if isinstance(obj, dict) else None
    require(isinstance(val, list), f"{ctx}.{key} must be a list")
    return val  # type: ignore[return-value]


def require_dict(obj: Any, key: str, ctx: str) -> dict[str, Any]:
    val = obj.get(key) if isinstance(obj, dict) else None
    require(isinstance(val, dict), f"{ctx}.{key} must be a mapping")
    return val  # type: ignore[return-value]


def main() -> int:
    if yaml is None:
        return fail("PyYAML is required: pip install pyyaml")
    if not REGISTRY.exists():
        return fail(f"missing registry file: {REGISTRY}")

    try:
        data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
        require(isinstance(data, dict), "registry must be a YAML mapping")

        require(
            data.get("apiVersion") == "sociosphere.socioprophet.org/v1alpha1",
            "apiVersion must be sociosphere.socioprophet.org/v1alpha1",
        )
        require(
            data.get("kind") == "ComputationalArtifactRegistry",
            "kind must be ComputationalArtifactRegistry",
        )
        metadata = require_dict(data, "metadata", "root")
        require(isinstance(metadata.get("name"), str), "metadata.name must be a string")
        require(isinstance(metadata.get("version"), str), "metadata.version must be a string")

        spec = require_dict(data, "spec", "root")

        safety_classes = require_dict(spec, "safetyClasses", "spec")
        actual_safety = set(safety_classes.keys())
        missing_safety = sorted(REQUIRED_SAFETY_CLASSES - actual_safety)
        require(not missing_safety, f"spec.safetyClasses missing: {missing_safety}")
        for cls in BLOCKED_AUTO_PROMOTE_CLASSES:
            cls_def = safety_classes[cls]
            require(isinstance(cls_def, dict), f"spec.safetyClasses.{cls} must be a mapping")
            require(
                cls_def.get("defaultReview") in ("human-required", "blocked"),
                f"spec.safetyClasses.{cls}.defaultReview must be human-required or blocked",
            )

        health_model = require_dict(spec, "healthModel", "spec")
        freshness = require_list(health_model, "freshnessStates", "spec.healthModel")
        actual_states = set(freshness)
        missing_states = sorted(REQUIRED_FRESHNESS_STATES - actual_states)
        require(not missing_states, f"spec.healthModel.freshnessStates missing: {missing_states}")
        require_list(health_model, "requiredSignals", "spec.healthModel")

        prop_rules = require_list(spec, "propagationRules", "spec")
        actual_triggers = {r.get("when") for r in prop_rules if isinstance(r, dict)}
        missing_triggers = sorted(REQUIRED_PROPAGATION_TRIGGERS - actual_triggers)
        require(not missing_triggers, f"spec.propagationRules missing triggers: {missing_triggers}")

        for rule in prop_rules:
            if not isinstance(rule, dict):
                continue
            when = rule.get("when", "")
            if when in ("safetyClassPrivileged", "safetyClassProhibited"):
                require(
                    rule.get("blockAutoPromotion") is True,
                    f"spec.propagationRules[when={when}].blockAutoPromotion must be true",
                )
                require(
                    rule.get("requireHumanReview") is True,
                    f"spec.propagationRules[when={when}].requireHumanReview must be true",
                )

        governance = require_dict(spec, "governance", "spec")
        slash_binding = require_dict(governance, "slashTopicBinding", "spec.governance")
        require(
            isinstance(slash_binding.get("namespace"), str),
            "spec.governance.slashTopicBinding.namespace must be a string",
        )
        require_list(slash_binding, "topics", "spec.governance.slashTopicBinding")
        require(
            isinstance(slash_binding.get("governingRepo"), str),
            "spec.governance.slashTopicBinding.governingRepo must be a string",
        )

        entries = require_list(spec, "registryEntries", "spec")
        require(bool(entries), "spec.registryEntries must not be empty")
        seen_ids: set[str] = set()
        for entry in entries:
            require(isinstance(entry, dict), "each registryEntry must be a mapping")
            entry_id = entry.get("id", "<unknown>")
            require(entry_id not in seen_ids, f"duplicate registryEntry id: {entry_id}")
            seen_ids.add(entry_id)
            for field in REQUIRED_ENTRY_FIELDS:
                require(field in entry, f"registryEntry '{entry_id}' missing required field: {field}")
            safety_cls = entry.get("safetyClass")
            require(
                safety_cls in actual_safety,
                f"registryEntry '{entry_id}' has unknown safetyClass: {safety_cls}",
            )
            consumers = entry.get("downstreamConsumers")
            require(
                isinstance(consumers, list) and bool(consumers),
                f"registryEntry '{entry_id}' downstreamConsumers must be non-empty list",
            )

    except ValueError as exc:
        return fail(str(exc))

    entry_count = len(entries)
    noun = "entry" if entry_count == 1 else "entries"
    print(f"OK: validated computational-artifacts registry ({entry_count} {noun})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
