#!/usr/bin/env python3
"""Review local generated Workspace mesh artifacts without promoting Gate 1.

This script reads generated artifacts from the fabric repo after the safe plan
has been generated. It does not mutate files, mark Gate 1 complete, or authorize
deployment.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

DEFAULT_FABRIC_REPO = Path.home() / "dev" / "prophet-platform-fabric-mlops-ts-suite"
GENERATED_RELATIVE = Path("infra/google-workspace-ops-mesh/generated/google-workspace-ops-mesh")
EXPECTED_ARTIFACTS = {
    "config.generated.json",
    "clasp.generated.json",
    "mesh-summary.generated.json",
    "operator-next-steps.md",
}
REQUIRED_METADATA_FIELDS = {
    "workstream",
    "meeting_type",
    "canonical_issue",
    "dashboard_key",
    "expected_outputs",
}
FORBIDDEN_MARKERS = [
    "-----BEGIN PRIVATE KEY-----",
    "client_secret",
    "refresh_token",
    "access_token",
]


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(f"missing generated artifact: {path}")
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON in {path}: {exc}")


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        fail(f"missing generated artifact: {path}")


def assert_no_forbidden_markers(path: Path, text: str) -> None:
    for marker in FORBIDDEN_MARKERS:
        if marker in text:
            fail(f"forbidden marker {marker!r} found in {path}")


def review_config(path: Path) -> None:
    text = read_text(path)
    assert_no_forbidden_markers(path, text)
    config = json.loads(text)

    if config.get("dryRun") is not True:
        fail("config.generated.json must keep dryRun=true")
    if config.get("spreadsheetId") != "TODO_GOOGLE_SHEET_ID":
        fail("config.generated.json must keep spreadsheetId placeholder before Gate 2")

    metadata_fields = set(config.get("requiredMetadataFields", []))
    missing = REQUIRED_METADATA_FIELDS - metadata_fields
    if missing:
        fail("config.generated.json missing metadata fields: " + ", ".join(sorted(missing)))

    calendars = config.get("calendars", [])
    if len(calendars) != 2:
        fail("config.generated.json must contain exactly two prototype calendars")
    for calendar in calendars:
        calendar_id = calendar.get("calendarId", "")
        if not calendar_id.startswith("TODO_"):
            fail("config.generated.json calendarId must remain placeholder before Gate 2")

    tabs = config.get("tabs", {})
    if tabs.get("Meetings") != "Meetings" or tabs.get("Automations") != "Automations":
        fail("config.generated.json tabs must map Meetings and Automations")


def review_clasp(path: Path) -> None:
    text = read_text(path)
    assert_no_forbidden_markers(path, text)
    clasp = json.loads(text)

    if clasp.get("scriptId") != "TODO_APPS_SCRIPT_PROJECT_ID":
        fail("clasp.generated.json must keep scriptId placeholder before Gate 2")
    if clasp.get("rootDir") != "apps-script/google-workspace-ops-prototype":
        fail("clasp.generated.json rootDir mismatch")

    expected_files = [
        "appsscript.json",
        "setup.gs",
        "sync-calendar-events-to-meetings.gs",
        "parser-test.gs",
        "seed-workspace-rows.gs",
        "seed-dashboard-rows.gs",
    ]
    if clasp.get("filePushOrder") != expected_files:
        fail("clasp.generated.json filePushOrder mismatch")


def review_mesh_summary(path: Path) -> None:
    text = read_text(path)
    assert_no_forbidden_markers(path, text)
    summary = json.loads(text)

    if summary.get("dry_run") is not True:
        fail("mesh-summary.generated.json must keep dry_run=true")
    if summary.get("project_services_enabled") is not False:
        fail("mesh-summary.generated.json must keep project_services_enabled=false")
    if summary.get("workspace_groups_enabled") is not False:
        fail("mesh-summary.generated.json must keep workspace_groups_enabled=false")
    for key in ["spreadsheet_id", "apps_script_project_id", "cloud_vendor_strategy_calendar_id", "launch_council_calendar_id"]:
        value = str(summary.get(key, ""))
        if not value.startswith("TODO_"):
            fail(f"mesh-summary.generated.json {key} must remain placeholder before Gate 2")


def review_operator_next_steps(path: Path) -> None:
    text = read_text(path)
    assert_no_forbidden_markers(path, text)

    required_phrases = [
        "Validate repository scaffold",
        "Review generated files",
        "reviewed before being copied",
        "Keep dry-run enabled",
        "does not create calendars, Sheets, Apps Script projects, dashboard objects, Workspace groups, or scheduled triggers by default",
    ]
    for phrase in required_phrases:
        if phrase not in text:
            fail(f"operator-next-steps.md missing phrase: {phrase}")

    forbidden_phrases = [
        "tofu apply",
        "clasp push",
        "enable triggers",
    ]
    for phrase in forbidden_phrases:
        if phrase in text:
            fail(f"operator-next-steps.md contains deployment instruction: {phrase}")


def main() -> None:
    fabric_repo = Path(os.environ.get("FABRIC_REPO", str(DEFAULT_FABRIC_REPO))).expanduser().resolve()
    generated_dir = fabric_repo / GENERATED_RELATIVE

    missing = [name for name in EXPECTED_ARTIFACTS if not (generated_dir / name).exists()]
    if missing:
        fail("missing generated artifacts. Run make terraform-workspace-mesh-plan-safe first. Missing: " + ", ".join(sorted(missing)))

    review_config(generated_dir / "config.generated.json")
    review_clasp(generated_dir / "clasp.generated.json")
    review_mesh_summary(generated_dir / "mesh-summary.generated.json")
    review_operator_next_steps(generated_dir / "operator-next-steps.md")

    print("PASS: Workspace mesh Gate 1 generated artifacts review clean")
    print(f"generated_dir={generated_dir}")
    print(f"artifacts={len(EXPECTED_ARTIFACTS)}")
    print("review_performed=false")
    print("promotion_authorized=false")


if __name__ == "__main__":
    main()
