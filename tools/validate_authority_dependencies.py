#!/usr/bin/env python3
"""Validate SocioSphere authority-dependency graph contracts.

Dependency-free by design. The registry is JSON-compatible YAML so the stdlib
json parser can validate it while preserving the canonical registry/*.yaml path.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "authority-dependency.schema.json"
REGISTRY = ROOT / "registry" / "authority-dependencies.yaml"
VALID_DIR = ROOT / "examples" / "authority-dependencies" / "valid"
INVALID_DIR = ROOT / "examples" / "authority-dependencies" / "invalid"

VALID_STATUSES = {"draft", "active", "deprecated", "blocked"}
VALID_EFFECTS = {
    "read", "write", "execute", "route", "publish", "persist_memory",
    "promote", "merge", "deploy", "replicate", "quarantine", "revoke",
    "repair", "model_route", "network_egress", "credential_access",
    "browser_control", "terminal_control", "host_mutation",
}
HIGH_RISK_EFFECTS = VALID_EFFECTS - {"read", "write"}
REVOCABLE_EFFECTS = HIGH_RISK_EFFECTS - {"quarantine", "revoke", "repair"}
REQUIRED_EDGE_KEYS = [
    "id", "owner_repo", "status", "source", "target", "authority_surface_refs",
    "control_effects", "policy_refs", "evidence_refs", "cancellation_binding_refs",
    "recovery_refs",
]
REQUIRED_REF_KEYS = ["repo", "component", "kind"]


class ValidationError(Exception):
    pass


def fail(message: str) -> None:
    print(f"[authority-dependencies] ERROR: {message}", file=sys.stderr)
    raise SystemExit(2)


def load_json(path: Path) -> Any:
    if not path.exists():
        fail(f"missing file: {path.relative_to(ROOT)}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON-compatible content in {path.relative_to(ROOT)}: {exc}")


def require_object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError(f"{path} must be an object")
    return value


def require_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{path} must be a non-empty string")
    return value


def require_list(value: Any, path: str, *, allow_empty: bool = False) -> list[Any]:
    if not isinstance(value, list):
        raise ValidationError(f"{path} must be a list")
    if not allow_empty and not value:
        raise ValidationError(f"{path} must not be empty")
    return value


def validate_schema_shape(schema: dict[str, Any]) -> None:
    for key in ["$schema", "$id", "title", "type", "required", "properties", "$defs"]:
        if key not in schema:
            raise ValidationError(f"schema missing {key}")
    required = set(schema.get("required", []))
    for key in ["schema_version", "kind", "authority_dependencies"]:
        if key not in required:
            raise ValidationError(f"schema.required missing {key}")


def validate_repo_ref(ref: Any, path: str) -> None:
    obj = require_object(ref, path)
    for key in REQUIRED_REF_KEYS:
        require_string(obj.get(key), f"{path}.{key}")
    if "/" not in obj["repo"]:
        raise ValidationError(f"{path}.repo must be owner/name")


def validate_edge(edge: Any, path: str) -> None:
    obj = require_object(edge, path)
    missing = [key for key in REQUIRED_EDGE_KEYS if key not in obj]
    if missing:
        raise ValidationError(f"{path} missing keys: {missing}")

    require_string(obj["id"], f"{path}.id")
    owner_repo = require_string(obj["owner_repo"], f"{path}.owner_repo")
    if "/" not in owner_repo:
        raise ValidationError(f"{path}.owner_repo must be owner/name")

    status = require_string(obj["status"], f"{path}.status")
    if status not in VALID_STATUSES:
        raise ValidationError(f"{path}.status unsupported: {status}")

    validate_repo_ref(obj["source"], f"{path}.source")
    validate_repo_ref(obj["target"], f"{path}.target")

    authority_refs = require_list(obj["authority_surface_refs"], f"{path}.authority_surface_refs")
    policy_refs = require_list(obj["policy_refs"], f"{path}.policy_refs")
    evidence_refs = require_list(obj["evidence_refs"], f"{path}.evidence_refs", allow_empty=True)
    cancellation_refs = require_list(obj["cancellation_binding_refs"], f"{path}.cancellation_binding_refs", allow_empty=True)
    recovery_refs = require_list(obj["recovery_refs"], f"{path}.recovery_refs", allow_empty=True)
    effects = [require_string(v, f"{path}.control_effects[]") for v in require_list(obj["control_effects"], f"{path}.control_effects")]

    for index, ref in enumerate(authority_refs):
        require_string(ref, f"{path}.authority_surface_refs[{index}]")
    for index, ref in enumerate(policy_refs):
        require_string(ref, f"{path}.policy_refs[{index}]")
    for index, ref in enumerate(evidence_refs):
        require_string(ref, f"{path}.evidence_refs[{index}]")
    for index, ref in enumerate(cancellation_refs):
        require_string(ref, f"{path}.cancellation_binding_refs[{index}]")
    for index, ref in enumerate(recovery_refs):
        require_string(ref, f"{path}.recovery_refs[{index}]")

    unknown_effects = sorted(set(effects) - VALID_EFFECTS)
    if unknown_effects:
        raise ValidationError(f"{path}.control_effects unsupported values: {unknown_effects}")
    if len(effects) != len(set(effects)):
        raise ValidationError(f"{path}.control_effects must be unique")

    high_risk = set(effects) & HIGH_RISK_EFFECTS
    if high_risk and not evidence_refs:
        raise ValidationError(f"{path} high-risk effects require evidence refs: {sorted(high_risk)}")

    revocable = set(effects) & REVOCABLE_EFFECTS
    if revocable and not cancellation_refs:
        raise ValidationError(f"{path} revocable effects require cancellation bindings: {sorted(revocable)}")

    if cancellation_refs and not evidence_refs:
        raise ValidationError(f"{path} cancellation bindings require evidence preservation refs")

    if {"quarantine", "revoke", "repair"} & set(effects) and not recovery_refs:
        raise ValidationError(f"{path} quarantine/revoke/repair effects require recovery refs")

    for index, ref in enumerate(obj.get("related_refs", [])):
        require_string(ref, f"{path}.related_refs[{index}]")


def validate_graph(graph: Any) -> None:
    obj = require_object(graph, "registry")
    if obj.get("schema_version") != "0.1":
        raise ValidationError("registry.schema_version must be 0.1")
    if obj.get("kind") != "AuthorityDependencyGraph":
        raise ValidationError("registry.kind must be AuthorityDependencyGraph")
    seen: set[str] = set()
    for index, edge in enumerate(require_list(obj.get("authority_dependencies"), "registry.authority_dependencies")):
        validate_edge(edge, f"registry.authority_dependencies[{index}]")
        edge_id = edge["id"]
        if edge_id in seen:
            raise ValidationError(f"duplicate authority dependency id: {edge_id}")
        seen.add(edge_id)


def validate_invalid_fixtures() -> None:
    fixtures = sorted(INVALID_DIR.glob("*.json"))
    if not fixtures:
        raise ValidationError("missing invalid authority-dependency fixtures")
    for fixture in fixtures:
        try:
            validate_edge(load_json(fixture), f"invalid/{fixture.name}")
        except ValidationError:
            continue
        raise ValidationError(f"invalid fixture unexpectedly passed: {fixture.relative_to(ROOT)}")


def main() -> int:
    try:
        validate_schema_shape(require_object(load_json(SCHEMA), "schema"))
        validate_graph(load_json(REGISTRY))
        valid_fixtures = sorted(VALID_DIR.glob("*.json"))
        if not valid_fixtures:
            raise ValidationError("missing valid authority-dependency fixtures")
        for fixture in valid_fixtures:
            validate_edge(load_json(fixture), f"valid/{fixture.name}")
        validate_invalid_fixtures()
    except ValidationError as exc:
        fail(str(exc))

    print("[authority-dependencies] OK: schema, registry, valid fixtures, and invalid fixtures validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
