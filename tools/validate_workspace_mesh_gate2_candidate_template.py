#!/usr/bin/env python3
"""Validate the Gate 2 candidate mapping template.

The versioned template must contain placeholders only. Real local candidate
mapping files belong under ignored paths and must not be committed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "workspace-mesh" / "gate2-candidate-mapping.template.json"
GITIGNORE = ROOT / ".gitignore"

EXPECTED_PLACEHOLDERS = {
    "spreadsheet_id": "TODO_GOOGLE_SHEET_ID",
    "apps_script_project_id": "TODO_APPS_SCRIPT_PROJECT_ID",
    "cloud_vendor_strategy_calendar_id": "TODO_SP_CLOUD_VENDOR_STRATEGY_CALENDAR_ID",
    "launch_council_calendar_id": "TODO_SP_LAUNCH_COUNCIL_CALENDAR_ID",
}

REQUIRED_GITIGNORE = {
    ".workspace-mesh/",
    "**/gate2-candidate-mapping.local.json",
    "**/*.candidate.local.json",
}


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def main() -> None:
    if not TEMPLATE.exists():
        fail(f"missing template: {TEMPLATE.relative_to(ROOT)}")
    if not GITIGNORE.exists():
        fail("missing .gitignore")

    data = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    gitignore_text = GITIGNORE.read_text(encoding="utf-8")

    if data.get("status") != "template_only":
        fail("template status must be template_only")
    if data.get("mesh_state") != "prepared-but-not-deployed":
        fail("template mesh_state must be prepared-but-not-deployed")
    if data.get("gate_id") != "gate-2-id-substitution-review":
        fail("template gate_id mismatch")
    if data.get("dry_run_required") is not True:
        fail("template must require dry_run")

    candidate_values = data.get("candidate_values", {})
    if set(candidate_values) != set(EXPECTED_PLACEHOLDERS):
        fail("candidate_values keys mismatch")

    for key, placeholder in EXPECTED_PLACEHOLDERS.items():
        item = candidate_values.get(key, {})
        if item.get("placeholder") != placeholder:
            fail(f"placeholder mismatch for {key}")
        if item.get("candidate_value") != placeholder:
            fail(f"candidate_value must remain placeholder for {key}")
        if item.get("review_status") != "not_started":
            fail(f"review_status must remain not_started for {key}")
        source_evidence = str(item.get("source_evidence", ""))
        if not source_evidence.startswith("TODO_"):
            fail(f"source_evidence must remain TODO for {key}")

    text = TEMPLATE.read_text(encoding="utf-8")
    forbidden_markers = ["http://", "https://", "@", "BEGIN PRIVATE KEY", "client_secret", "access_token", "refresh_token"]
    for marker in forbidden_markers:
        if marker in text:
            fail(f"template contains forbidden marker: {marker}")

    missing_ignores = [entry for entry in sorted(REQUIRED_GITIGNORE) if entry not in gitignore_text]
    if missing_ignores:
        fail(".gitignore missing Gate 2 local mapping patterns: " + ", ".join(missing_ignores))

    print("PASS: Workspace mesh Gate 2 candidate mapping template is placeholder-only")
    print(f"placeholders={len(EXPECTED_PLACEHOLDERS)}")
    print("local_mapping_paths_ignored=true")


if __name__ == "__main__":
    main()
