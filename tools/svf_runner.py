#!/usr/bin/env python3
"""Sovereign Validation Fabric workspace runner.

The runner supports registry inspection, changed-path plan selection, receipt
verification, and the first bounded local execution backend for Sociosphere
dogfood validation. It executes only registered Actions referenced by registered
Plans. It does not accept arbitrary shell strings.
"""

from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import hashlib
import json
import os
import subprocess
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


def utc_now() -> str:
    # Reproducible-fixture support. When SVF_SOURCE_DATE_EPOCH is set (the
    # `make validate` smoke targets set it), every timestamp is pinned to that
    # instant so the generated run/receipt/export artifacts are byte-identical
    # across machines and CI can gate on a clean tree. An invalid value raises
    # rather than silently poisoning artifacts. Unset (real runs) keeps
    # wall-clock time, so production receipts still record when they actually ran.
    epoch = os.environ.get("SVF_SOURCE_DATE_EPOCH")
    if epoch:
        try:
            seconds = int(epoch)
        except ValueError:
            raise ValueError(
                f"SVF_SOURCE_DATE_EPOCH must be an integer Unix epoch in seconds; got {epoch!r}"
            ) from None
        moment = dt.datetime.fromtimestamp(seconds, dt.timezone.utc)
    else:
        moment = dt.datetime.now(dt.timezone.utc)
    return moment.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest_bytes(payload: bytes, algorithm: str = "sha256") -> dict[str, str]:
    if algorithm != "sha256":
        raise ValueError(f"unsupported digest algorithm: {algorithm}")
    return {"algorithm": algorithm, "digest": hashlib.sha256(payload).hexdigest()}


def digest_data(data: Any) -> dict[str, str]:
    return digest_bytes(canonical_json(data).encode("utf-8"))


def digest_file(path: Path) -> dict[str, str]:
    return digest_bytes(path.read_bytes())


def relative_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def ensure_under_root(path: Path) -> Path:
    resolved = path.resolve()
    root = ROOT.resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError(f"path escapes repository root: {path}")
    return resolved


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


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def profiles(registry: dict[str, Any]) -> list[dict[str, Any]]:
    items = registry.get("profiles", [])
    if not isinstance(items, list):
        raise ValueError("SVF registry profiles must be a list")
    return items


def actions(registry: dict[str, Any]) -> list[dict[str, Any]]:
    items = registry.get("actions", [])
    if not isinstance(items, list):
        raise ValueError("SVF registry actions must be a list")
    return items


def plans(registry: dict[str, Any]) -> list[dict[str, Any]]:
    items = registry.get("plans", [])
    if not isinstance(items, list):
        raise ValueError("SVF registry plans must be a list")
    return items


def find_profile(registry: dict[str, Any], repo: str) -> dict[str, Any] | None:
    for profile in profiles(registry):
        if profile.get("repo") == repo:
            return profile
    return None


def find_action(registry: dict[str, Any], action_id: str) -> dict[str, Any] | None:
    for action in actions(registry):
        if action.get("action_id") == action_id:
            return action
    return None


def find_plan(registry: dict[str, Any], plan_id: str) -> dict[str, Any] | None:
    for plan in plans(registry):
        if plan.get("plan_id") == plan_id:
            return plan
    return None


def policy_projection(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "policy_ref": profile.get("policy_ref"),
        "profile_id": profile.get("profile_id"),
        "repo": profile.get("repo"),
        "mode": profile.get("mode"),
        "execution_backend": profile.get("execution_backend"),
        "required_receipt_classes": profile.get("required_receipt_classes", []),
    }


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


def materialized_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return ensure_under_root(path)


def verify_receipt_integrity(receipt: dict[str, Any], registry: dict[str, Any]) -> list[str]:
    diagnostics: list[str] = []

    run_artifact = receipt.get("run_artifact")
    if not isinstance(run_artifact, str):
        # Legacy committed fixtures are shape-only. Newly issued receipts include
        # run_artifact and materialized input/output paths, which triggers real
        # digest recomputation below.
        return diagnostics

    run_path = materialized_path(run_artifact)
    if not run_path.exists():
        diagnostics.append(f"run_artifact missing: {run_artifact}")
    elif digest_file(run_path) != receipt.get("run_digest"):
        diagnostics.append("run_digest does not match run_artifact")

    plan = find_plan(registry, str(receipt.get("plan_ref")))
    if plan is None:
        diagnostics.append(f"plan_ref not registered: {receipt.get('plan_ref')}")
    elif digest_data(plan) != receipt.get("plan_digest"):
        diagnostics.append("plan_digest does not match registered plan")

    profile_id = receipt.get("profile_ref")
    profile = None
    for candidate in profiles(registry):
        if candidate.get("profile_id") == profile_id:
            profile = candidate
            break
    if profile is None:
        diagnostics.append(f"profile_ref not registered: {profile_id}")
    elif digest_data(policy_projection(profile)) != receipt.get("policy_digest"):
        diagnostics.append("policy_digest does not match registered policy projection")

    declared_claims = set(plan.get("declared_claims", [])) if isinstance(plan, dict) else set()
    certified_claims = set(receipt.get("certified_claims", [])) if isinstance(receipt.get("certified_claims"), list) else set()
    unsupported = sorted(certified_claims - declared_claims)
    if unsupported:
        diagnostics.append(f"certified claims outside plan scope: {unsupported}")

    for item in receipt.get("input_digests", []):
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            continue
        path = materialized_path(item["path"])
        if not path.exists():
            diagnostics.append(f"input artifact missing: {item['path']}")
        elif digest_file(path) != {"algorithm": item.get("algorithm"), "digest": item.get("digest")}:
            diagnostics.append(f"input digest mismatch: {item['name']}")

    for item in receipt.get("output_digests", []):
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            diagnostics.append(f"output digest path missing: {item.get('name') if isinstance(item, dict) else item}")
            continue
        path = materialized_path(item["path"])
        if not path.exists():
            diagnostics.append(f"output artifact missing: {item['path']}")
        elif digest_file(path) != {"algorithm": item.get("algorithm"), "digest": item.get("digest")}:
            diagnostics.append(f"output digest mismatch: {item['name']}")

    return diagnostics


def command_verify_receipt(args: argparse.Namespace) -> dict[str, Any]:
    receipt_path = Path(args.receipt_path)
    if not receipt_path.is_absolute():
        receipt_path = ROOT / receipt_path
    receipt = load_json(receipt_path)
    diagnostics = verify_receipt_shape(receipt)

    registry = load_registry(Path(args.registry))
    if not diagnostics:
        diagnostics.extend(verify_receipt_integrity(receipt, registry))

    return {
        "command": "verify-receipt",
        "status": "pass" if not diagnostics else "fail",
        "receipt_path": relative_path(receipt_path),
        "receipt_id": receipt.get("receipt_id"),
        "diagnostics": diagnostics,
        "verified_claims": receipt.get("certified_claims", []) if not diagnostics else [],
        "non_claims": [
            "Receipt verification recomputes registered plan, policy projection, run, input, and output digests when artifact paths are present.",
            "Receipt verification does not certify production readiness or live infrastructure behavior.",
        ],
    }


def command_explain(args: argparse.Namespace) -> dict[str, Any]:
    result = command_verify_receipt(args)
    result["command"] = "explain"
    result["explanation"] = "Receipt explanation reports digest verification status, certified claims, diagnostics, and explicit non-claims."
    return result


def reject_unsafe_action(action: dict[str, Any], profile: dict[str, Any]) -> list[str]:
    diagnostics: list[str] = []
    if action.get("backend") != "local":
        diagnostics.append(f"unsupported action backend: {action.get('backend')}")
    if profile.get("execution_backend") != "local":
        diagnostics.append(f"unsupported profile backend: {profile.get('execution_backend')}")
    if action.get("network_mode") not in {"not_required"}:
        diagnostics.append(f"unsupported local network mode: {action.get('network_mode')}")
    if action.get("credential_policy") not in {"none"}:
        diagnostics.append(f"unsupported credential policy: {action.get('credential_policy')}")
    if action.get("side_effect_class") not in {"read_only", "artifact_write"}:
        diagnostics.append(f"unsupported side effect class: {action.get('side_effect_class')}")
    argv = action.get("argv")
    if not isinstance(argv, list) or not argv or not all(isinstance(item, str) and item for item in argv):
        diagnostics.append("action argv must be a nonempty list of strings")
    if any(isinstance(item, str) and (";" in item or "&&" in item or "|" in item) for item in argv or []):
        diagnostics.append("action argv contains shell metacharacters")
    if action.get("shell", False):
        diagnostics.append("shell execution is forbidden")
    return diagnostics


def execute_action(action: dict[str, Any], out_dir: Path, ordinal: int) -> dict[str, Any]:
    action_id = str(action["action_id"])
    started = utc_now()
    argv = [str(item) for item in action["argv"]]
    timeout_seconds = int(action.get("timeout_seconds", 60))
    env = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONHASHSEED": "0",
        "SVF_LOCAL_EXECUTION": "1",
    }
    try:
        completed = subprocess.run(
            argv,
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
        status = "pass" if completed.returncode == 0 else "fail"
        result = {
            "action_id": action_id,
            "status": status,
            "exit_code": completed.returncode,
            "started_at": started,
            "ended_at": utc_now(),
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "failure_taxonomy": [] if status == "pass" else ["action_exit_nonzero"],
        }
    except subprocess.TimeoutExpired as exc:
        result = {
            "action_id": action_id,
            "status": "fail",
            "exit_code": None,
            "started_at": started,
            "ended_at": utc_now(),
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "failure_taxonomy": ["timeout"],
        }

    safe_name = action_id.replace(":", "_").replace("/", "_")
    result_path = out_dir / f"{ordinal:02d}-{safe_name}.result.json"
    write_json(result_path, result)
    result["artifact_path"] = relative_path(result_path)
    result["artifact_digest"] = digest_file(result_path)
    return result


def resolve_run_plan(registry: dict[str, Any], repo: str, plan_id: str | None, changed_paths: list[str]) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    profile = find_profile(registry, repo)
    if profile is None:
        raise ValueError(f"no SVF profile registered for repo: {repo}")
    if plan_id is None:
        selected = select_plans(profile, changed_paths)
        if not selected:
            raise ValueError(f"no SVF plan selected for repo: {repo}")
        plan_id = selected[0]["plan_id"]
    plan = find_plan(registry, plan_id)
    if plan is None:
        raise ValueError(f"SVF plan is not registered: {plan_id}")

    resolved_actions: list[dict[str, Any]] = []
    for action_id in plan.get("actions", []):
        action = find_action(registry, action_id)
        if action is None:
            raise ValueError(f"plan references unknown action: {action_id}")
        diagnostics = reject_unsafe_action(action, profile)
        if diagnostics:
            raise ValueError(f"action rejected: {action_id}: {diagnostics}")
        resolved_actions.append(action)
    if not resolved_actions:
        raise ValueError(f"plan has no executable actions: {plan_id}")
    return profile, plan, resolved_actions


def command_run(args: argparse.Namespace) -> dict[str, Any]:
    registry_path = Path(args.registry)
    registry = load_registry(registry_path)
    changed_paths = args.changed_path or []
    profile, plan, plan_actions = resolve_run_plan(registry, args.repo, args.plan, changed_paths)
    out_dir = materialized_path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    run_started = utc_now()
    action_results = [execute_action(action, out_dir, idx + 1) for idx, action in enumerate(plan_actions)]
    run_status = "pass" if all(item["status"] == "pass" for item in action_results) else "fail"
    run_id_suffix = hashlib.sha256(f"{args.repo}|{plan['plan_id']}|{run_started}".encode("utf-8")).hexdigest()[:16]
    run_ref = f"svf:run:{run_id_suffix}"

    run_record = {
        "schema_version": "1.0",
        "run_ref": run_ref,
        "repo": args.repo,
        "profile_ref": profile.get("profile_id"),
        "plan_ref": plan.get("plan_id"),
        "policy_ref": profile.get("policy_ref"),
        "backend": "local",
        "changed_paths": changed_paths,
        "started_at": run_started,
        "ended_at": utc_now(),
        "status": run_status,
        "action_results": action_results,
        "non_claims": [
            "Local execution does not certify production readiness.",
            "Local execution does not certify container, browser, QEMU, cluster, or vendor parity.",
        ],
    }
    run_path = out_dir / "validation-run.json"
    write_json(run_path, run_record)
    run_digest = digest_file(run_path)

    output_digests = []
    for result in action_results:
        output_digests.append(
            {
                "name": result["action_id"],
                "path": result["artifact_path"],
                **result["artifact_digest"],
            }
        )

    certified_claims = list(plan.get("declared_claims", [])) if run_status == "pass" else ["non_production_only"]
    if "receipt_integrity_verified" in certified_claims:
        certified_claims.remove("receipt_integrity_verified")

    receipt_id = f"svf:receipt:{run_id_suffix}"
    receipt = {
        "schema_version": "1.0",
        "receipt_id": receipt_id,
        "run_ref": run_ref,
        "run_artifact": relative_path(run_path),
        "run_digest": run_digest,
        "repo": args.repo,
        "profile_ref": profile.get("profile_id"),
        "plan_ref": plan.get("plan_id"),
        "plan_digest": digest_data(plan),
        "policy_ref": profile.get("policy_ref"),
        "policy_digest": digest_data(policy_projection(profile)),
        "input_digests": [
            {
                "name": "registry",
                "path": relative_path(registry_path),
                **digest_file(registry_path),
            }
        ],
        "output_digests": output_digests,
        "certified_claims": certified_claims,
        "non_certified_claims": [
            "production_readiness",
            "live_infrastructure_safety",
            "container_runtime_parity",
            "browser_runtime_parity",
            "qemu_runtime_parity",
            "signadot_vendor_parity",
            "network_isolation_enforced",
        ],
        "verification": {
            "status": "not_checked",
            "verifier": "sociosphere.svf_runner.local",
            "verified_at": utc_now(),
        },
        "issued_at": utc_now(),
    }
    receipt_path = out_dir / "validation-receipt.json"
    write_json(receipt_path, receipt)

    verification_diagnostics = verify_receipt_shape(receipt)
    verification_diagnostics.extend(verify_receipt_integrity(receipt, registry))
    receipt["verification"] = {
        "status": "verified" if not verification_diagnostics else "failed",
        "verifier": "sociosphere.svf_runner.local",
        "verified_at": utc_now(),
        "diagnostics": verification_diagnostics,
    }
    if receipt["verification"]["status"] == "verified" and "receipt_integrity_verified" in plan.get("declared_claims", []):
        receipt["certified_claims"] = sorted(set(receipt["certified_claims"] + ["receipt_integrity_verified"]))
    write_json(receipt_path, receipt)

    return {
        "command": "run",
        "status": run_status if receipt["verification"]["status"] == "verified" else "fail",
        "repo": args.repo,
        "profile_id": profile.get("profile_id"),
        "plan_id": plan.get("plan_id"),
        "run_ref": run_ref,
        "run_artifact": relative_path(run_path),
        "receipt_id": receipt_id,
        "receipt_path": relative_path(receipt_path),
        "verification": receipt["verification"],
        "action_count": len(action_results),
        "non_claims": [
            "This is local-only SVF execution.",
            "This does not claim Signadot vendor integration or full runtime parity.",
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

    run_parser = subparsers.add_parser("run", help="Run a registered local SVF plan")
    run_parser.add_argument("--repo", required=True, help="Repository full name, e.g. SocioProphet/sociosphere")
    run_parser.add_argument("--plan", help="SVF plan id; defaults to selected/default plan")
    run_parser.add_argument("--changed-path", action="append", default=[], help="Changed path relative to repository root; repeatable")
    run_parser.add_argument("--out", default="artifacts/svf/runs/local-smoke", help="Output directory for run and receipt artifacts")

    verify_parser = subparsers.add_parser("verify-receipt", help="Verify receipt shape and available artifact digests")
    verify_parser.add_argument("receipt_path")

    explain_parser = subparsers.add_parser("explain", help="Explain receipt verification diagnostics")
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
            result = command_run(args)
        else:  # pragma: no cover
            parser.error(f"unsupported command: {args.command}")
    except Exception as exc:  # pragma: no cover - operator-facing failure path
        result = {"command": args.command, "status": "fail", "diagnostics": [str(exc)]}

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") in {None, "pass"} and result.get("command") in {"list", "select", "run", "verify-receipt", "explain"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
