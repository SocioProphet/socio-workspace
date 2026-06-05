#!/usr/bin/env python3
"""Verify an existing local-only Gate 2 candidate mapping file.

This verifier is read-only. It checks that the local file exists, is ignored by
Git, preserves dry-run posture, and contains the expected Gate 2 fields. It does
not print candidate values.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL_FILE = ROOT / ".workspace-mesh" / "gate2-candidate-mapping.local.json"
EXPECTED_PLACEHOLDERS = {
    "spreadsheet_id": "TODO_GOOGLE_SHEET_ID",
    "apps_script_project_id": "TODO_APPS_SCRIPT_PROJECT_ID",
    "cloud_vendor_strategy_calendar_id": "TODO_SP_CLOUD_VENDOR_STRATEGY_CALENDAR_ID",
    "launch_council_calendar_id": "TODO_SP_LAUNCH_COUNCIL_CALENDAR_ID",
}
ALLOWED_REVIEW_STATUSES = {
    "not_started",
    "candidate_recorded_local_only",
    "source_evidence_recorded",
    "reviewed_local_only",
    "rejected_local_only",
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
        fail(f"missing local candidate mapping: {path.relative_to(ROOT)}")
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON in {path.relative_to(ROOT)}: {exc}")


def assert_git_ignored(path: Path) -> None:
    try:
        result = subprocess.run(
            ["git", "check-ignore", "--quiet", str(path.relative_to(ROOT))],
            cwd=ROOT,
            check=False,
        )
    except FileNotFoundError:
        fail("git command not found; cannot verify ignore status")
    if result.returncode != 0:
        fail(f"local candidate file is not ignored by Git: {path.relative_to(ROOT)}")


def main() -> None:
    text = LOCAL_FILE.read_text(encoding="utf-8") if LOCAL_FILE.exists() else ""
    for marker in FORBIDDEN_MARKERS:
        if marker in text:
            fail(f"forbidden marker found in local candidate mapping: {marker}")

    data = load_json(LOCAL_FILE)
    assert_git_ignored(LOCAL_FILE)

    if data.get("mesh_state") != "prepared-but-not-deployed":
        fail("mesh_state must remain prepared-but-not-deployed")
    if data.get("gate_id") != "gate-2-id-substitution-review":
        fail("gate_id mismatch")
    if data.get("dry_run_required") is not True:
        fail("dry_run_required must remain true")

    candidate_values = data.get("candidate_values", {})
    if set(candidate_values) != set(EXPECTED_PLACEHOLDERS):
        fail("candidate_values keys mismatch")

    placeholder_count = 0
    local_candidate_count = 0
    evidence_count = 0

    for key, placeholder in EXPECTED_PLACEHOLDERS.items():
        item = candidate_values.get(key, {})
        if item.get("placeholder") != placeholder:
            fail(f"placeholder mismatch for {key}")

        review_status = item.get("review_status")
        if review_status not in ALLOWED_REVIEW_STATUSES:
            fail(f"unsupported review_status for {key}: {review_status}")

        candidate_value = str(item.get("candidate_value", ""))
        if not candidate_value:
            fail(f"candidate_value missing for {key}")
        if candidate_value == placeholder:
            placeholder_count += 1
        else:
            local_candidate_count += 1

        source_evidence = str(item.get("source_evidence", ""))
        if source_evidence and not source_evidence.startswith("TODO_"):
            evidence_count += 1

    mode = "placeholder_copy" if local_candidate_count == 0 else "local_candidate_review"

    print("PASS: Workspace mesh Gate 2 local candidate mapping verifies clean")
    print(f"local_file={LOCAL_FILE.relative_to(ROOT)}")
    print(f"mode={mode}")
    print(f"fields={len(EXPECTED_PLACEHOLDERS)}")
    print(f"placeholder_values={placeholder_count}")
    print(f"local_candidate_values={local_candidate_count}")
    print(f"source_evidence_records={evidence_count}")
    print("git_ignored=true")
    print("dry_run_required=true")
    print("candidate_values_printed=false")


if __name__ == "__main__":
    main()
