#!/usr/bin/env python3
"""Validate Gate 2 planning-only posture for the Workspace mesh."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "registry" / "workspace-mesh-gate2-id-substitution-planning.v0.json"
DOC = ROOT / "docs" / "operations" / "workspace-mesh-gate2-id-substitution-planning.md"

EXPECTED_PLACEHOLDERS = {
    "TODO_GOOGLE_SHEET_ID",
    "TODO_APPS_SCRIPT_PROJECT_ID",
    "TODO_SP_CLOUD_VENDOR_STRATEGY_CALENDAR_ID",
    "TODO_SP_LAUNCH_COUNCIL_CALENDAR_ID",
}

REQUIRED_DOC_PHRASES = [
    "planning_only",
    "prepared-but-not-deployed",
    "reviewed_no_promotion",
    "not_started",
    "TODO_GOOGLE_SHEET_ID",
    "TODO_APPS_SCRIPT_PROJECT_ID",
    "TODO_SP_CLOUD_VENDOR_STRATEGY_CALENDAR_ID",
    "TODO_SP_LAUNCH_COUNCIL_CALENDAR_ID",
    "does not contain real IDs",
]


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def main() -> None:
    if not MANIFEST.exists():
        fail(f"missing manifest: {MANIFEST.relative_to(ROOT)}")
    if not DOC.exists():
        fail(f"missing doc: {DOC.relative_to(ROOT)}")

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    doc = DOC.read_text(encoding="utf-8")

    if manifest.get("gate_id") != "gate-2-id-substitution-review":
        fail("Gate 2 manifest gate_id mismatch")
    if manifest.get("status") != "planning_only":
        fail("Gate 2 must remain planning_only")
    if manifest.get("mesh_state") != "prepared-but-not-deployed":
        fail("Gate 2 must keep mesh prepared-but-not-deployed")
    if manifest.get("gate_1_disposition") != "reviewed_no_promotion":
        fail("Gate 1 disposition must be reviewed_no_promotion")
    if manifest.get("gate_2_disposition") != "not_started":
        fail("Gate 2 disposition must remain not_started")

    placeholders = {item.get("placeholder") for item in manifest.get("placeholder_fields", [])}
    if placeholders != EXPECTED_PLACEHOLDERS:
        fail("Gate 2 placeholder set mismatch")

    for item in manifest.get("placeholder_fields", []):
        placeholder = str(item.get("placeholder", ""))
        if not placeholder.startswith("TODO_"):
            fail(f"non-placeholder value found for {item.get('name')}")
        if not item.get("target_artifact"):
            fail(f"missing target_artifact for {item.get('name')}")

    if len(manifest.get("placeholder_fields", [])) != 4:
        fail("Gate 2 must define exactly four placeholder fields")

    forbidden = set(manifest.get("forbidden_in_planning_record", []))
    required_forbidden = {
        "real_identifier_values",
        "versioned_candidate_mapping",
        "workspace_asset_mutation",
        "script_execution",
        "scheduled_jobs",
        "promotion_beyond_planning",
    }
    missing_forbidden = required_forbidden - forbidden
    if missing_forbidden:
        fail("Gate 2 missing forbidden planning items: " + ", ".join(sorted(missing_forbidden)))

    for phrase in REQUIRED_DOC_PHRASES:
        if phrase not in doc:
            fail(f"Gate 2 doc missing phrase: {phrase}")

    print("PASS: Workspace mesh Gate 2 planning scaffold is valid")
    print("status=planning_only")
    print("gate_2_disposition=not_started")
    print(f"placeholders={len(placeholders)}")


if __name__ == "__main__":
    main()
