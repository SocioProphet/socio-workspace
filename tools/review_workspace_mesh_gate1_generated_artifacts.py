#!/usr/bin/env python3
"""Review planned Workspace mesh artifacts without promoting Gate 1.

The default safe workflow runs `tofu plan -out` and `tofu show -json`; it does
not run `tofu apply`. Therefore the four local_file artifacts usually do not
exist on disk yet. This script prefers real generated files when present, but
falls back to the planned local_file contents in default-plan.json.

It does not mutate files, mark Gate 1 complete, or authorize deployment.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

DEFAULT_FABRIC_REPO = Path.home() / "dev" / "prophet-platform-fabric-mlops-ts-suite"
GENERATED_RELATIVE = Path("infra/google-workspace-ops-mesh/generated/google-workspace-ops-mesh")
PLAN_JSON_NAME = "default-plan.json"
EXPECTED_ARTIFACTS = {
    "config.generated.json",
    "clasp.generated.json",
    "mesh-summary.generated.json",
    "operator-next-steps.md",
}
RESOURCE_TO_ARTIFACT = {
    "local_file.apps_script_config[0]": "config.generated.json",
    "local_file.clasp_config[0]": "clasp.generated.json",
    "local_file.mesh_summary[0]": "mesh-summary.generated.json",
    "local_file.operator_next_steps[0]": "operator-next-steps.md",
}
REQUIRED_METADATA_FIELDS = {
    "workstream",
    "meeting_type",
    "canonical_issue",
    "dashboard_key",
    "expected_outputs",
}
PRIVATE_KEY_MARKER = "-----BEGIN " + "PRIVATE KEY-----"
FORBIDDEN_MARKERS = [
    PRIVATE_KEY_MARKER,
    "client_secret",
    "refresh_token",
    "access_token",
]


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        fail(f"missing artifact: {path}")


def parse_json_text(name: str, text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON for {name}: {exc}")


def assert_no_forbidden_markers(name: str, text: str) -> None:
    for marker in FORBIDDEN_MARKERS:
        if marker in text:
            fail(f"forbidden marker {marker!r} found in {name}")


def load_artifact_texts(generated_dir: Path) -> tuple[dict[str, str], str]:
    existing = {name: generated_dir / name for name in EXPECTED_ARTIFACTS if (generated_dir / name).exists()}
    if len(existing) == len(EXPECTED_ARTIFACTS):
        return {name: path.read_text(encoding="utf-8") for name, path in existing.items()}, "generated_files"

    plan_json_path = generated_dir / PLAN_JSON_NAME
    if not plan_json_path.exists():
        missing = sorted(EXPECTED_ARTIFACTS - set(existing))
        fail(
            "missing generated artifacts and plan JSON. Run make terraform-workspace-mesh-plan-safe first. "
            + "Missing artifacts: "
            + ", ".join(missing)
        )

    plan = parse_json_text(str(plan_json_path), plan_json_path.read_text(encoding="utf-8"))
    artifact_texts: dict[str, str] = {}
    for change in plan.get("resource_changes", []):
        address = change.get("address")
        artifact_name = RESOURCE_TO_ARTIFACT.get(address)
        if not artifact_name:
            continue
        actions = change.get("change", {}).get("actions", [])
        if actions not in (["create"], ["no-op"]):
            fail(f"unexpected plan action for {address}: {actions}")
        after = change.get("change", {}).get("after", {})
        content = after.get("content")
        if not isinstance(content, str):
            fail(f"plan JSON missing planned content for {address}")
        artifact_texts[artifact_name] = content

    missing_from_plan = EXPECTED_ARTIFACTS - set(artifact_texts)
    if missing_from_plan:
        fail("plan JSON missing expected local_file artifacts: " + ", ".join(sorted(missing_from_plan)))

    return artifact_texts, "plan_json"


def review_config(text: str) -> None:
    assert_no_forbidden_markers("config.generated.json", text)
    config = parse_json_text("config.generated.json", text)

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


def review_clasp(text: str) -> None:
    assert_no_forbidden_markers("clasp.generated.json", text)
    clasp = parse_json_text("clasp.generated.json", text)

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


def review_mesh_summary(text: str) -> None:
    assert_no_forbidden_markers("mesh-summary.generated.json", text)
    summary = parse_json_text("mesh-summary.generated.json", text)

    if summary.get("mesh_state") != "prepared-but-not-deployed":
        fail("mesh-summary.generated.json must keep mesh_state prepared-but-not-deployed")
    if summary.get("dry_run") is not True:
        fail("mesh-summary.generated.json must keep dry_run=true")
    if summary.get("exported_secrets") != []:
        fail("mesh-summary.generated.json must not export secrets")

    placeholders = summary.get("placeholders", {})
    expected_placeholder_values = {
        "spreadsheet_id": "TODO_GOOGLE_SHEET_ID",
        "apps_script_project_id": "TODO_APPS_SCRIPT_PROJECT_ID",
        "cloud_vendor_strategy_calendar_id": "TODO_SP_CLOUD_VENDOR_STRATEGY_CALENDAR_ID",
        "launch_council_calendar_id": "TODO_SP_LAUNCH_COUNCIL_CALENDAR_ID",
    }
    if placeholders != expected_placeholder_values:
        fail("mesh-summary.generated.json placeholders mismatch")


def review_operator_next_steps(text: str) -> None:
    assert_no_forbidden_markers("operator-next-steps.md", text)
    required_phrases = [
        "Do not paste sensitive IDs into committed files",
        "dry-run",
        "Gate 2",
        "review",
    ]
    for phrase in required_phrases:
        if phrase not in text:
            fail(f"operator-next-steps.md missing phrase: {phrase}")


def main() -> None:
    fabric_repo = Path(os.environ.get("FABRIC_REPO", DEFAULT_FABRIC_REPO)).expanduser()
    generated_dir = fabric_repo / GENERATED_RELATIVE
    artifact_texts, source = load_artifact_texts(generated_dir)

    review_config(artifact_texts["config.generated.json"])
    review_clasp(artifact_texts["clasp.generated.json"])
    review_mesh_summary(artifact_texts["mesh-summary.generated.json"])
    review_operator_next_steps(artifact_texts["operator-next-steps.md"])

    print("PASS: Workspace mesh Gate 1 generated artifacts review passed")
    print(f"fabric_repo={fabric_repo}")
    print(f"generated_dir={generated_dir}")
    print(f"source={source}")
    print(f"artifacts={len(EXPECTED_ARTIFACTS)}")
    print("dry_run=true")
    print("gate1_promoted=false")
    print("sensitive_values_printed=false")


if __name__ == "__main__":
    main()
