#!/usr/bin/env python3
"""Read-only Sovereign Validation Fabric workspace runner.

This runner currently supports registry inspection and changed-path plan
selection only. It deliberately does not execute Actions yet.
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


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    if yaml is None:
        raise RuntimeError("PyYAML is required: python3 -m pip install --user pyyaml")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"SVF registry must be a mapping: {path}")
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


def command_not_configured(command: str) -> dict[str, Any]:
    return {
        "command": command,
        "status": "not_configured",
        "diagnostics": [
            "SVF runner execution and receipt operations are intentionally staged after registry validation.",
            "Current runner supports only list and select.",
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

    verify_parser = subparsers.add_parser("verify-receipt", help="Not configured in read-only runner tranche")
    verify_parser.add_argument("receipt_path")

    explain_parser = subparsers.add_parser("explain", help="Not configured in read-only runner tranche")
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
        elif args.command in {"run", "verify-receipt", "explain"}:
            result = command_not_configured(args.command)
        else:  # pragma: no cover
            parser.error(f"unsupported command: {args.command}")
    except Exception as exc:  # pragma: no cover - operator-facing failure path
        result = {"command": args.command, "status": "fail", "diagnostics": [str(exc)]}

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") in {None, "pass", "not_configured"} and result.get("command") in {"list", "select", "run", "verify-receipt", "explain"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
