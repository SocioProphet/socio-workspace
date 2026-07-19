#!/usr/bin/env python3
"""Validate Angel of the Lord report fixtures.

This is intentionally lightweight and stdlib-only. It validates the required
shape used by CI-produced Angel reports without requiring jsonschema at runtime.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORTS = [ROOT / "standards" / "angel-of-the-lord" / "examples" / "angel_report.example.v1.json"]
SEVERITIES = {"blocker", "high", "medium", "low", "info"}
RESULTS = {"pass", "warn", "fail"}
DECISIONS = {"allow", "block", "manual_review", "not_applicable"}


def fail(message: str) -> None:
    raise SystemExit(f"ERR: {message}")


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text("utf-8"))
    except FileNotFoundError:
        fail(f"report not found: {path}")
    except json.JSONDecodeError as exc:
        fail(f"report is not valid JSON: {path}: {exc}")
    if not isinstance(data, dict):
        fail(f"{path}: report root must be an object")
    return data


def require_obj(data: dict[str, Any], key: str, rel: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        fail(f"{rel}: {key} must be an object")
    return value


def require_list(data: dict[str, Any], key: str, rel: str, non_empty: bool = False) -> list[Any]:
    value = data.get(key)
    if not isinstance(value, list):
        fail(f"{rel}: {key} must be a list")
    if non_empty and not value:
        fail(f"{rel}: {key} must not be empty")
    return value


def require_str(data: dict[str, Any], key: str, rel: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        fail(f"{rel}: {key} must be a non-empty string")
    return value


def validate_report(path: Path) -> None:
    data = load_json(path)
    rel = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)

    if data.get("schema_version") != "sociosphere.angel-of-the-lord-report/v1":
        fail(f"{rel}: unsupported schema_version={data.get('schema_version')!r}")
    require_str(data, "generated_at", rel)

    target = require_obj(data, "target", rel)
    for key in ("repository", "ref", "commit"):
        require_str(target, key, rel)

    ctx = require_obj(data, "review_context", rel)
    require_str(ctx, "lane", rel)
    if ctx.get("mode") not in {"ci", "manual", "release_gate", "workspace"}:
        fail(f"{rel}: review_context.mode is invalid")

    surfaces = require_list(data, "surfaces_inspected", rel, non_empty=True)
    if not all(isinstance(item, str) and item for item in surfaces):
        fail(f"{rel}: surfaces_inspected entries must be non-empty strings")

    if data.get("result") not in RESULTS:
        fail(f"{rel}: result is invalid")

    findings = require_list(data, "findings", rel)
    for idx, finding in enumerate(findings):
        if not isinstance(finding, dict):
            fail(f"{rel}: findings[{idx}] must be an object")
        for key in ("id", "surface", "message", "remediation"):
            require_str(finding, key, rel)
        if finding.get("severity") not in SEVERITIES:
            fail(f"{rel}: findings[{idx}].severity is invalid")
        if not isinstance(finding.get("restricted"), bool):
            fail(f"{rel}: findings[{idx}].restricted must be boolean")

    boundaries = require_obj(data, "trust_boundaries", rel)
    require_list(boundaries, "found", rel)
    require_list(boundaries, "missing", rel)

    evidence = require_obj(data, "evidence", rel)
    require_list(evidence, "accepted", rel)
    require_list(evidence, "missing", rel)

    decision = require_obj(data, "decision", rel)
    for key in ("merge", "release", "publish", "deploy"):
        if decision.get(key) not in DECISIONS:
            fail(f"{rel}: decision.{key} is invalid")
    if not isinstance(decision.get("restricted_handling_required"), bool):
        fail(f"{rel}: decision.restricted_handling_required must be boolean")

    backlog = require_list(data, "remediation_backlog", rel)
    for idx, item in enumerate(backlog):
        if not isinstance(item, dict):
            fail(f"{rel}: remediation_backlog[{idx}] must be an object")
        for key in ("id", "title", "priority", "owner", "status"):
            require_str(item, key, rel)
        if item["priority"] not in {"P0", "P1", "P2", "P3"}:
            fail(f"{rel}: remediation_backlog[{idx}].priority is invalid")
        if item["status"] not in {"open", "in_progress", "blocked", "done"}:
            fail(f"{rel}: remediation_backlog[{idx}].status is invalid")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Angel report JSON files.")
    parser.add_argument("reports", nargs="*", help="Report paths to validate.")
    args = parser.parse_args()

    reports = [Path(p) for p in args.reports] if args.reports else DEFAULT_REPORTS
    for report in reports:
        validate_report(report if report.is_absolute() else ROOT / report)
    print(json.dumps({"validated_angel_reports": [str(p) for p in reports]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
