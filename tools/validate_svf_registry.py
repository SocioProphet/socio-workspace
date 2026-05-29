#!/usr/bin/env python3
"""Validate the Sociosphere Sovereign Validation Fabric registry.

This validator checks the workspace-discovery layer only. It does not execute
SVF Actions and does not certify downstream repository validation behavior.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - dependency failure path is operator-facing
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "registry" / "sovereign-validation-fabric.yaml"

REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SVF_ID_RE = re.compile(r"^svf:(profile|plan|policy):[a-z0-9][a-z0-9_.:-]*$")
MODES = {"advisory", "blocking"}
BACKENDS = {"local", "container", "cluster_sandbox", "qemu_sandbox", "browser_sandbox", "placeholder"}
REQUIRED_SCHEMA_REFS = {"action", "plan", "capability_policy", "run", "receipt"}


def load_yaml(path: Path) -> dict[str, Any]:
    if yaml is None:
        raise RuntimeError("PyYAML is required: python3 -m pip install --user pyyaml")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"registry must be a mapping: {path}")
    return data


def check(condition: bool, check_id: str, diagnostics: list[str] | None = None) -> dict[str, Any]:
    return {"check_id": check_id, "passed": condition, "diagnostics": diagnostics or []}


def validate_registry(registry: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    results.append(check(registry.get("schema_version") == "1.0", "schema-version-is-1.0"))
    results.append(check(registry.get("registry_id") == "svf:registry:sociosphere.workspace", "registry-id-canonical"))
    results.append(check(isinstance(registry.get("receipt_root"), str) and registry["receipt_root"].startswith("artifacts/svf/"), "receipt-root-under-artifacts-svf"))

    authority = registry.get("upstream_authority", {})
    schema_refs = authority.get("schema_refs", {}) if isinstance(authority, dict) else {}
    results.append(check(authority.get("repo") == "SocioProphet/ProCybernetica", "upstream-authority-repo-procybernetica"))
    missing_schema_refs = sorted(REQUIRED_SCHEMA_REFS - set(schema_refs))
    results.append(check(not missing_schema_refs, "upstream-authority-all-schema-refs-present", [f"missing schema ref: {item}" for item in missing_schema_refs]))

    profiles = registry.get("profiles", [])
    results.append(check(isinstance(profiles, list) and len(profiles) >= 1, "profiles-present"))
    if not isinstance(profiles, list):
        return results

    profile_ids: set[str] = set()
    repos: set[str] = set()

    for idx, profile in enumerate(profiles):
        prefix = f"profile[{idx}]"
        if not isinstance(profile, dict):
            results.append(check(False, f"{prefix}-is-mapping"))
            continue

        profile_id = profile.get("profile_id")
        repo = profile.get("repo")
        mode = profile.get("mode")
        backend = profile.get("execution_backend")
        default_plans = profile.get("default_plans", [])
        selectors = profile.get("changed_path_selectors", [])
        policy_ref = profile.get("policy_ref")
        contract_refs = profile.get("contract_refs", [])
        validation_command = profile.get("validation_command")

        results.append(check(isinstance(profile_id, str) and SVF_ID_RE.match(profile_id) is not None and profile_id.startswith("svf:profile:"), f"{prefix}-profile-id-valid"))
        if isinstance(profile_id, str):
            results.append(check(profile_id not in profile_ids, f"{prefix}-profile-id-unique", [profile_id] if profile_id in profile_ids else []))
            profile_ids.add(profile_id)

        results.append(check(isinstance(repo, str) and REPO_RE.match(repo) is not None, f"{prefix}-repo-shape-valid", [str(repo)] if not isinstance(repo, str) or REPO_RE.match(str(repo)) is None else []))
        if isinstance(repo, str):
            repos.add(repo)

        results.append(check(isinstance(profile.get("owning_plane"), str) and len(profile["owning_plane"]) > 0, f"{prefix}-owning-plane-present"))
        results.append(check(mode in MODES, f"{prefix}-mode-valid", [str(mode)] if mode not in MODES else []))
        results.append(check(backend in BACKENDS, f"{prefix}-backend-valid", [str(backend)] if backend not in BACKENDS else []))
        results.append(check(isinstance(policy_ref, str) and policy_ref.startswith("svf:policy:"), f"{prefix}-policy-ref-valid"))
        results.append(check(isinstance(default_plans, list) and len(default_plans) >= 1 and all(isinstance(plan, str) and plan.startswith("svf:plan:") for plan in default_plans), f"{prefix}-default-plans-valid"))
        results.append(check(isinstance(profile.get("required_receipt_classes", []), list), f"{prefix}-required-receipt-classes-list"))
        results.append(check(isinstance(profile.get("non_claims", []), list), f"{prefix}-non-claims-list"))

        contract_refs_valid = isinstance(contract_refs, list) and all(isinstance(item, str) and len(item) > 0 and not item.startswith("/") for item in contract_refs)
        results.append(check(contract_refs_valid, f"{prefix}-contract-refs-valid", [str(contract_refs)] if not contract_refs_valid else []))

        command_valid = validation_command is None or (isinstance(validation_command, str) and len(validation_command.strip()) > 0)
        results.append(check(command_valid, f"{prefix}-validation-command-valid", [str(validation_command)] if not command_valid else []))

        if validation_command:
            results.append(check(backend != "placeholder", f"{prefix}-validation-command-requires-real-backend", [str(profile_id)] if backend == "placeholder" else []))

        placeholder_ok = not (mode == "blocking" and backend == "placeholder")
        results.append(check(placeholder_ok, f"{prefix}-blocking-profile-not-placeholder", [str(profile_id)] if not placeholder_ok else []))

        results.append(check(isinstance(selectors, list) and len(selectors) >= 1, f"{prefix}-selectors-present"))
        if isinstance(selectors, list):
            selector_ids: set[str] = set()
            for selector_idx, selector in enumerate(selectors):
                selector_prefix = f"{prefix}.selector[{selector_idx}]"
                if not isinstance(selector, dict):
                    results.append(check(False, f"{selector_prefix}-is-mapping"))
                    continue
                selector_id = selector.get("selector_id")
                paths = selector.get("paths", [])
                plans = selector.get("plans", [])
                results.append(check(isinstance(selector_id, str) and len(selector_id) > 0, f"{selector_prefix}-id-present"))
                if isinstance(selector_id, str):
                    results.append(check(selector_id not in selector_ids, f"{selector_prefix}-id-unique", [selector_id] if selector_id in selector_ids else []))
                    selector_ids.add(selector_id)
                results.append(check(isinstance(paths, list) and len(paths) >= 1 and all(isinstance(path, str) and len(path) > 0 for path in paths), f"{selector_prefix}-paths-valid"))
                results.append(check(isinstance(plans, list) and len(plans) >= 1 and all(plan in default_plans for plan in plans), f"{selector_prefix}-plans-subset-default-plans"))
                if isinstance(paths, list):
                    invalid_absolute = [path for path in paths if isinstance(path, str) and path.startswith("/")]
                    results.append(check(not invalid_absolute, f"{selector_prefix}-paths-relative", invalid_absolute))
                    unmatchable = [path for path in paths if isinstance(path, str) and not path.strip()]
                    results.append(check(not unmatchable, f"{selector_prefix}-paths-nonempty", unmatchable))

    required_initial_repos = {"SocioProphet/sociosphere", "SocioProphet/ProCybernetica"}
    missing_required = sorted(required_initial_repos - repos)
    results.append(check(not missing_required, "required-initial-profiles-present", [f"missing repo profile: {repo}" for repo in missing_required]))

    return results


def select_plans(registry: dict[str, Any], repo: str, changed_paths: list[str]) -> list[str]:
    selected: list[str] = []
    for profile in registry.get("profiles", []):
        if profile.get("repo") != repo:
            continue
        for selector in profile.get("changed_path_selectors", []):
            patterns = selector.get("paths", [])
            if any(fnmatch.fnmatch(path, pattern) for path in changed_paths for pattern in patterns):
                selected.extend(selector.get("plans", []))
        if not selected:
            selected.extend(profile.get("default_plans", []))
    return sorted(set(selected))


def validate() -> dict[str, Any]:
    registry = load_yaml(REGISTRY_PATH)
    results = validate_registry(registry)
    selector_smoke = select_plans(registry, "SocioProphet/sociosphere", ["registry/sovereign-validation-fabric.yaml"])
    results.append(check("svf:plan:sociosphere.registry-dogfood" in selector_smoke, "selector-smoke-sociosphere-registry"))
    passed = all(result["passed"] for result in results)
    return {
        "validator": "sociosphere_svf_registry.validator.v1",
        "passed": passed,
        "profile_count": len(registry.get("profiles", [])),
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = validate()
    except Exception as exc:  # pragma: no cover - operator-facing failure path
        result = {"validator": "sociosphere_svf_registry.validator.v1", "passed": False, "error": str(exc), "results": []}
    print(json.dumps(result, indent=2, sort_keys=True))
    if not args.json:
        if result["passed"]:
            print("PASS: svf registry")
        else:
            print("FAIL: svf registry", file=sys.stderr)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
