#!/usr/bin/env python3
"""Read-only Sovereign Validation Fabric workspace runner.

This runner currently supports registry inspection, changed-path plan
selection, and committed receipt shape verification. It deliberately does not
execute Actions yet.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - operator-facing dependency path
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "registry" / "sovereign-validation-fabric.yaml"
RECEIPT_REQUIRED_FIELDS = {
    "schema_version",
    "receipt_id",
    "run_ref",
    "run_digest",
    "plan_ref",
    "plan_digest",
    "policy_ref",
    "policy_digest",
    "input_digests",
    "output_digests",
    "certified_claims",
    "non_certified_claims",
    "verification",
    "issued_at",
}
CLAIM_SCOPES = {
    "schema_conformant",
    "fixtures_validated",
    "tests_passed",
    "semantic_roundtrip_preserved",
    "policy_boundary_preserved",
    "non_production_only",
    "runtime_smoke_passed",
    "artifact_integrity_verified",
    "receipt_integrity_verified",
}


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    if yaml is None:
        raise RuntimeError("PyYAML is required: python3 -m pip install --user pyyaml")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"SVF registry must be a mapping: {path}")
    return data


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON object expected: {path}")
    return data


def profiles(registry: dict[str, Any]) -> list[dict[str, Any]]:
    items = registry.get("profiles", [])
    if not isinstance(items, list):
        raise ValueError("SVF registry profiles must be a list")
    return items


def find_profile(registry: dict[str, Any], repo: str) -> dict[str, Any] | None:
    for profile in profiles(registry):
        if profile.get("repo") == repo:
            return profile
    return None


def select_plans(profile: dict[str, Any], changed_paths: list[str]) -> list[dict[str, Any]]:
    selected: dict[str, dict[str, Any]] = {}
    for selector in profile.get("changed_path_selectors", []):
        patterns = selector.get("paths", [])
        matched_paths = [path for path in changed_paths if any(fnmatch.fnmatch(path, pattern) for pattern in patterns)]
        if matched_paths:
            for plan_id in selector.get("plans", []):
                selected[plan_id] = {
                    "plan_id": plan_id,
                    "selector_id": selector.get("selector_id"),
                    "matched_paths": matched_paths,
                    "selection_reason": "changed_path_selector",
                }
    if not selected:
        for plan_id in profile.get("default_plans", []):
            selected[plan_id] = {
                "plan_id": plan_id,
                "selector_id": None,
                "matched_paths": [],
                "selection_reason": "default_plan",
            }
    return list(selected.values())


def command_list(args: argparse.Namespace) -> dict[str, Any]:
    registry = load_registry(Path(args.registry))
    profile_rows = []
    for profile in profiles(registry):
        profile_rows.append(
            {
                "profile_id": profile.get("profile_id"),
                "repo": profile.get("repo"),
                "owning_plane": profile.get("owning_plane"),
                "mode": profile.get("mode"),
                "execution_backend": profile.get("execution_backend"),
                "default_plans": profile.get("default_plans", []),
            }
        )
    return {
        "command": "list",
        "registry_id": registry.get("registry_id"),
        "profile_count": len(profile_rows),
        "profiles": profile_rows,
        "non_claims": [
            "List only inspects workspace registry metadata.",
            "List does not execute validation actions or certify plan results.",
        ],
    }


def command_select(args: argparse.Namespace) -> dict[str, Any]:
    registry = load_registry(Path(args.registry))
    profile = find_profile(registry, args.repo)
    if profile is None:
        return {
            "command": "select",
            "status": "not_configured",
            "repo": args.repo,
            "selected_plans": [],
            "diagnostics": [f"no SVF profile registered for repo: {args.repo}"],
        }
    selected = select_plans(profile, args.changed_path)
    return {
        "command": "select",
        "status": "pass" if selected else "not_configured",
        "repo": args.repo,
        "profile_id": profile.get("profile_id"),
        "mode": profile.get("mode"),
        "execution_backend": profile.get("execution_backend"),
        "changed_paths": args.changed_path,
        "selected_plans": selected,
        "non_claims": [
            "Selection does not execute validation actions.",
            "Selection does not certify that a receipt exists or verifies.",
        ],
    }


def digest_record_valid(record: Any) -> bool:
    return (
        isinstance(record, dict)
        and record.get("algorithm") in {"sha256", "sha512"}
        and isinstance(record.get("digest"), str)
        and len(record["digest"]) >= 16
    )


def named_digest_list_valid(items: Any) -> bool:
    return (
        isinstance(items, list)
        and len(items) >= 1
        and all(
            isinstance(item, dict)
            and isinstance(item.get("name"), str)
            and len(item["name"]) > 0
            and digest_record_valid(item)
            for item in items
        )
    )


def verify_receipt_shape(receipt: dict[str, Any]) -> list[str]:
    diagnostics: list[str] = []
    missing = sorted(RECEIPT_REQUIRED_FIELDS - set(receipt))
    diagnostics.extend(f"missing required field: {field}" for field in missing)

    if receipt.get("schema_version") != "1.0":
        diagnostics.append("schema_version must equal 1.0")
    for field, prefix in {
        "receipt_id": "svf:receipt:",
        "run_ref": "svf:run:",
        "plan_ref": "svf:plan:",
        "policy_ref": "svf:policy:",
    }.items():
        value = receipt.get(field)
        if not isinstance(value, str) or not value.startswith(prefix):
            diagnostics.append(f"{field} must start with {prefix}")

    for field in ["run_digest", "plan_digest", "policy_digest"]:
        if not digest_record_valid(receipt.get(field)):
            diagnostics.append(f"{field} must contain algorithm and digest")

    if not named_digest_list_valid(receipt.get("input_digests")):
        diagnostics.append("input_digests must be a nonempty named digest list")
    if not named_digest_list_valid(receipt.get("output_digests")):
        diagnostics.append("output_digests must be a nonempty named digest list")

    claims = receipt.get("certified_claims")
    if not isinstance(claims, list) or not claims:
        diagnostics.append("certified_claims must be a nonempty list")
    elif any(claim not in CLAIM_SCOPES for claim in claims):
        diagnostics.append("certified_claims contains unsupported claim scope")

    non_certified = receipt.get("non_certified_claims")
    if not isinstance(non_certified, list) or not non_certified:
        diagnostics.append("non_certified_claims must be a nonempty list")

    verification = receipt.get("verification")
    if not isinstance(verification, dict):
        diagnostics.append("verification must be an object")
    else:
        if verification.get("status") not in {"verified", "failed", "not_checked"}:
            diagnostics.append("verification.status invalid")
        if not isinstance(verification.get("verifier"), str) or not verification.get("verifier"):
            diagnostics.append("verification.verifier required")
        if not isinstance(verification.get("verified_at"), str) or not verification.get("verified_at"):
            diagnostics.append("verification.verified_at required")

    if not isinstance(receipt.get("issued_at"), str) or not receipt.get("issued_at"):
        diagnostics.append("issued_at required")
    return diagnostics


def command_verify_receipt(args: argparse.Namespace) -> dict[str, Any]:
    receipt_path = Path(args.receipt_path)
    if not receipt_path.is_absolute():
        receipt_path = ROOT / receipt_path
    receipt = load_json(receipt_path)
    diagnostics = verify_receipt_shape(receipt)
    return {
        "command": "verify-receipt",
        "status": "pass" if not diagnostics else "fail",
        "receipt_path": str(receipt_path.relative_to(ROOT)) if receipt_path.is_relative_to(ROOT) else str(receipt_path),
        "receipt_id": receipt.get("receipt_id"),
        "diagnostics": diagnostics,
        "non_claims": [
            "This is receipt shape verification only.",
            "It does not recompute artifact digests or execute validation actions.",
            "It does not certify downstream repository behavior.",
        ],
    }


def command_explain(args: argparse.Namespace) -> dict[str, Any]:
    result = command_verify_receipt(args)
    result["command"] = "explain"
    result["explanation"] = "Receipt explanation is currently limited to shape verification diagnostics and explicit non-claims."
    return result


def command_not_configured(command: str) -> dict[str, Any]:
    return {
        "command": command,
        "status": "not_configured",
        "diagnostics": [
            "SVF runner execution is intentionally staged after registry validation and receipt shape checks.",
            "Current runner does not execute Actions.",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", default=str(REGISTRY_PATH), help="Path to SVF registry YAML")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="List registered SVF profiles")

    select_parser = subparsers.add_parser("select", help="Select SVF plans for a repo and changed paths")
    select_parser.add_argument("--repo", required=True, help="Repository full name, e.g. SocioProphet/sociosphere")
    select_parser.add_argument("--changed-path", action="append", required=True, help="Changed path relative to repository root; repeatable")

    run_parser = subparsers.add_parser("run", help="Not configured in read-only runner tranche")
    run_parser.add_argument("--plan", required=True, help="SVF plan id")

    verify_parser = subparsers.add_parser("verify-receipt", help="Verify committed receipt fixture shape")
    verify_parser.add_argument("receipt_path")

    explain_parser = subparsers.add_parser("explain", help="Explain committed receipt fixture shape diagnostics")
    explain_parser.add_argument("receipt_path")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "list":
            result = command_list(args)
        elif args.command == "select":
            result = command_select(args)
        elif args.command == "verify-receipt":
            result = command_verify_receipt(args)
        elif args.command == "explain":
            result = command_explain(args)
        elif args.command == "run":
            result = command_not_configured(args.command)
        else:  # pragma: no cover
            parser.error(f"unsupported command: {args.command}")
    except Exception as exc:  # pragma: no cover - operator-facing failure path
        result = {"command": args.command, "status": "fail", "diagnostics": [str(exc)]}

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") in {None, "pass", "not_configured"} and result.get("command") in {"list", "select", "run", "verify-receipt", "explain"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
