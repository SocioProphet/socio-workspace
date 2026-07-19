#!/usr/bin/env python3
"""Review GitHub Actions workflow permissions for the Angel hardening regime.

The checker is intentionally conservative for v0.1:
- blocks workflows without top-level permissions;
- blocks permissions shorthand values such as write-all;
- blocks selected high-impact write scopes unless explicitly excepted;
- warns on missing job-level permissions and marketplace actions not pinned to immutable SHAs.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS_DIR = ROOT / ".github" / "workflows"
POLICY_PATH = ROOT / "standards" / "angel-of-the-lord" / "policies" / "ci_permissions.v0.json"
OUT_PATH = ROOT / "artifacts" / "angel-of-the-lord" / "ci-permissions-report.json"
SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def fail(message: str) -> None:
    raise SystemExit(f"ERR: {message}")


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text("utf-8"))
    except FileNotFoundError:
        fail(f"missing policy: {path}")
    except json.JSONDecodeError as exc:
        fail(f"policy is not valid JSON: {path}: {exc}")
    if not isinstance(data, dict):
        fail("policy root must be an object")
    return data


def load_yaml(path: Path) -> dict[str, Any]:
    if yaml is None:
        fail("PyYAML is required for CI permissions review")
    try:
        data = yaml.safe_load(path.read_text("utf-8"))
    except Exception as exc:  # pragma: no cover - defensive path
        fail(f"workflow YAML parse failed for {path}: {exc}")
    if not isinstance(data, dict):
        fail(f"workflow must parse to object: {path}")
    return data


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def finding(
    *,
    rule_id: str,
    severity: str,
    path: str,
    message: str,
    remediation: str,
    evidence_ref: str | None = None,
) -> dict[str, Any]:
    return {
        "id": rule_id,
        "severity": severity,
        "surface": "ci_permissions",
        "path": path,
        "message": message,
        "evidence_ref": evidence_ref or path,
        "remediation": remediation,
        "restricted": False,
    }


def normalize_permission_entries(value: Any) -> tuple[str | None, dict[str, str]]:
    if value is None:
        return None, {}
    if isinstance(value, str):
        return value, {}
    if isinstance(value, dict):
        out: dict[str, str] = {}
        for key, perm in value.items():
            out[str(key)] = str(perm)
        return None, out
    return "invalid", {}


def has_exception(policy: dict[str, Any], path: str, scope: str) -> bool:
    for item in policy.get("workflow_write_exceptions", []):
        if item.get("path") == path and item.get("scope") == scope:
            return True
    return False


def action_ref_is_immutable(action_ref: str) -> bool:
    if "@" not in action_ref:
        return False
    _, ref = action_ref.rsplit("@", 1)
    return bool(SHA_RE.fullmatch(ref))


def action_is_local(action_ref: str, policy: dict[str, Any]) -> bool:
    return any(action_ref.startswith(prefix) for prefix in policy.get("trusted_local_action_prefixes", []))


def inspect_permissions(path: str, wf: dict[str, Any], policy: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    shorthand, permissions = normalize_permission_entries(wf.get("permissions"))

    if shorthand is None and not permissions:
        out.append(
            finding(
                rule_id="ci-missing-workflow-permissions",
                severity="blocker" if policy.get("required_workflow_permissions_block", True) else "medium",
                path=path,
                message="Workflow does not declare top-level permissions.",
                remediation="Declare least-privilege top-level permissions, usually `permissions: contents: read`.",
            )
        )
    elif shorthand:
        severity = "blocker" if shorthand in set(policy.get("deny_permissions_shorthand", [])) else "medium"
        out.append(
            finding(
                rule_id="ci-permissions-shorthand",
                severity=severity,
                path=path,
                message=f"Workflow uses permissions shorthand `{shorthand}`.",
                remediation="Replace permissions shorthand with explicit least-privilege scope mapping.",
            )
        )

    allowed_write = set(policy.get("allowed_write_scopes", []))
    blocked_without_exception = set(policy.get("blocked_write_scopes_without_exception", []))
    for scope, perm in permissions.items():
        if perm != "write":
            continue
        if scope not in allowed_write:
            out.append(
                finding(
                    rule_id="ci-unknown-write-scope",
                    severity="blocker",
                    path=path,
                    message=f"Workflow grants unknown or unsupported write scope `{scope}`.",
                    remediation="Remove the write scope or add a reviewed policy exception if this scope is legitimate.",
                )
            )
        elif scope in blocked_without_exception and not has_exception(policy, path, scope):
            out.append(
                finding(
                    rule_id="ci-blocked-write-scope",
                    severity="blocker",
                    path=path,
                    message=f"Workflow grants high-impact write scope `{scope}` without explicit exception.",
                    remediation="Remove the write scope or record an explicit exception in ci_permissions.v0.json.",
                )
            )

    jobs = wf.get("jobs", {})
    if isinstance(jobs, dict):
        for job_name, job in jobs.items():
            if not isinstance(job, dict):
                continue
            job_shorthand, job_permissions = normalize_permission_entries(job.get("permissions"))
            if job_shorthand is None and not job_permissions:
                out.append(
                    finding(
                        rule_id="ci-missing-job-permissions",
                        severity="medium" if not policy.get("required_job_permissions_block", False) else "blocker",
                        path=path,
                        message=f"Job `{job_name}` does not declare job-level permissions.",
                        remediation="Declare job-level permissions where practical, or document why workflow-level permissions are sufficient.",
                    )
                )
            if job_shorthand:
                severity = "blocker" if job_shorthand in set(policy.get("deny_permissions_shorthand", [])) else "medium"
                out.append(
                    finding(
                        rule_id="ci-job-permissions-shorthand",
                        severity=severity,
                        path=path,
                        message=f"Job `{job_name}` uses permissions shorthand `{job_shorthand}`.",
                        remediation="Replace job permissions shorthand with explicit least-privilege scope mapping.",
                    )
                )
            for scope, perm in job_permissions.items():
                if perm != "write":
                    continue
                if scope not in allowed_write:
                    out.append(
                        finding(
                            rule_id="ci-job-unknown-write-scope",
                            severity="blocker",
                            path=path,
                            message=f"Job `{job_name}` grants unknown or unsupported write scope `{scope}`.",
                            remediation="Remove the write scope or add a reviewed policy exception if this scope is legitimate.",
                        )
                    )
                elif scope in blocked_without_exception and not has_exception(policy, path, scope):
                    out.append(
                        finding(
                            rule_id="ci-job-blocked-write-scope",
                            severity="blocker",
                            path=path,
                            message=f"Job `{job_name}` grants high-impact write scope `{scope}` without explicit exception.",
                            remediation="Remove the write scope or record an explicit exception in ci_permissions.v0.json.",
                        )
                    )
    return out


def iter_steps(wf: dict[str, Any]) -> list[dict[str, Any]]:
    jobs = wf.get("jobs", {})
    steps: list[dict[str, Any]] = []
    if not isinstance(jobs, dict):
        return steps
    for job in jobs.values():
        if isinstance(job, dict) and isinstance(job.get("steps"), list):
            for step in job["steps"]:
                if isinstance(step, dict):
                    steps.append(step)
    return steps


def inspect_actions(path: str, wf: dict[str, Any], policy: dict[str, Any]) -> list[dict[str, Any]]:
    if not policy.get("warn_on_unpinned_actions", True):
        return []
    out: list[dict[str, Any]] = []
    for step in iter_steps(wf):
        uses = step.get("uses")
        if not isinstance(uses, str) or action_is_local(uses, policy):
            continue
        if not action_ref_is_immutable(uses):
            out.append(
                finding(
                    rule_id="ci-action-not-immutable",
                    severity="medium",
                    path=path,
                    message=f"Workflow uses marketplace action `{uses}` without immutable commit SHA pinning.",
                    remediation="Pin third-party actions to reviewed immutable commit SHAs or record an exception policy.",
                )
            )
    return out


def result_from_findings(findings: list[dict[str, Any]]) -> str:
    if any(f["severity"] == "blocker" for f in findings):
        return "fail"
    if findings:
        return "warn"
    return "pass"


def build_report(root: Path, policy_path: Path) -> dict[str, Any]:
    policy = load_json(policy_path)
    workflow_files = sorted((root / ".github" / "workflows").glob("*.yml")) + sorted(
        (root / ".github" / "workflows").glob("*.yaml")
    )
    findings: list[dict[str, Any]] = []
    surfaces: list[str] = []
    found_boundaries: list[str] = []
    missing_boundaries: list[str] = []
    accepted_evidence: list[str] = []
    missing_evidence: list[str] = []

    for workflow in workflow_files:
        path = rel(workflow)
        surfaces.append(path)
        wf = load_yaml(workflow)
        wf_findings = inspect_permissions(path, wf, policy) + inspect_actions(path, wf, policy)
        findings.extend(wf_findings)
        if "permissions" in wf:
            found_boundaries.append(f"{path}: top-level permissions declared")
            accepted_evidence.append(f"{path}: workflow permissions block")
        else:
            missing_boundaries.append(f"{path}: top-level permissions missing")
            missing_evidence.append(f"{path}: workflow permissions block")

    result = result_from_findings(findings)
    return {
        "schema_version": "sociosphere.angel-of-the-lord-report/v1",
        "generated_at": now_iso(),
        "target": {
            "repository": "SocioProphet/sociosphere",
            "ref": "workspace",
            "commit": "unknown-local",
        },
        "review_context": {
            "lane": "ci_permissions",
            "mode": "ci",
            "workflow": "validate",
            "actor": "angel-of-the-lord",
        },
        "surfaces_inspected": surfaces,
        "result": result,
        "findings": findings,
        "trust_boundaries": {
            "found": sorted(found_boundaries),
            "missing": sorted(missing_boundaries),
        },
        "evidence": {
            "accepted": sorted(accepted_evidence),
            "missing": sorted(set(missing_evidence + (["immutable action pinning evidence"] if any(f["id"] == "ci-action-not-immutable" for f in findings) else []))),
        },
        "decision": {
            "merge": "block" if result == "fail" else ("manual_review" if result == "warn" else "allow"),
            "release": "not_applicable",
            "publish": "manual_review" if result != "pass" else "allow",
            "deploy": "not_applicable",
            "restricted_handling_required": False,
        },
        "remediation_backlog": [
            {
                "id": "AOL-CI-001",
                "title": "Pin marketplace actions to reviewed immutable refs or define exception policy",
                "priority": "P1",
                "owner": "sociosphere",
                "status": "open",
            }
        ] if any(f["id"] == "ci-action-not-immutable" for f in findings) else [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Review GitHub Actions workflow permissions.")
    parser.add_argument("--root", default=str(ROOT), help="Repository root to inspect.")
    parser.add_argument("--policy", default=str(POLICY_PATH), help="CI permissions policy JSON.")
    parser.add_argument("--json-out", default=str(OUT_PATH), help="Report output path. Use '-' for stdout only.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    policy_path = Path(args.policy).resolve()
    report = build_report(root, policy_path)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"

    if args.json_out == "-":
        print(rendered, end="")
    else:
        out = Path(args.json_out).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered, "utf-8")
        print(f"[ci-permissions] wrote {out}")
        print(f"[ci-permissions] result={report['result']} findings={len(report['findings'])}")

    return 2 if report["result"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
