#!/usr/bin/env python3
"""Validate the Gate 2 candidate review schema and template compatibility."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "workspace-mesh" / "gate2-candidate-review.schema.json"
TEMPLATE = ROOT / "templates" / "workspace-mesh" / "gate2-candidate-mapping.template.json"

EXPECTED_FIELDS = {
    "spreadsheet_id",
    "apps_script_project_id",
    "cloud_vendor_strategy_calendar_id",
    "launch_council_calendar_id",
}
EXPECTED_REVIEW_STATUSES = {
    "not_started",
    "candidate_recorded_local_only",
    "source_evidence_recorded",
    "reviewed_local_only",
    "rejected_local_only",
}


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def load_json(path: Path) -> dict:
    if not path.exists():
        fail(f"missing file: {path.relative_to(ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    schema = load_json(SCHEMA)
    template = load_json(TEMPLATE)

    if schema.get("title") != "Workspace Mesh Gate 2 Candidate Review Schema":
        fail("schema title mismatch")
    if schema.get("properties", {}).get("mesh_state", {}).get("const") != "prepared-but-not-deployed":
        fail("schema must require prepared-but-not-deployed")
    if schema.get("properties", {}).get("gate_id", {}).get("const") != "gate-2-id-substitution-review":
        fail("schema gate_id mismatch")

    candidate_properties = schema["properties"]["candidate_values"]["properties"]
    if set(candidate_properties) != EXPECTED_FIELDS:
        fail("schema candidate field set mismatch")

    review_statuses = set(schema["$defs"]["candidateField"]["properties"]["review_status"]["enum"])
    if review_statuses != EXPECTED_REVIEW_STATUSES:
        fail("schema review_status enum mismatch")

    review_controls = schema["properties"]["review_controls"]["properties"]
    expected_control_consts = {
        "candidate_values_printed": False,
        "live_execution": False,
        "git_ignored_required": True,
        "versioned_candidate_values_allowed": False,
    }
    for key, expected in expected_control_consts.items():
        if review_controls.get(key, {}).get("const") is not expected:
            fail(f"review control {key} const mismatch")

    template_values = template.get("candidate_values", {})
    if set(template_values) != EXPECTED_FIELDS:
        fail("template candidate field set mismatch")
    for field, item in template_values.items():
        placeholder = str(item.get("placeholder", ""))
        candidate_value = str(item.get("candidate_value", ""))
        if not placeholder.startswith("TODO_"):
            fail(f"template placeholder for {field} must start with TODO_")
        if candidate_value != placeholder:
            fail(f"template candidate_value for {field} must equal placeholder")
        if item.get("review_status") != "not_started":
            fail(f"template review_status for {field} must remain not_started")

    print("PASS: Workspace mesh Gate 2 candidate review schema is valid")
    print(f"fields={len(EXPECTED_FIELDS)}")
    print(f"review_statuses={len(EXPECTED_REVIEW_STATUSES)}")
    print("template_compatible=true")
    print("candidate_values_printed=false")


if __name__ == "__main__":
    main()
