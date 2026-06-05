#!/usr/bin/env python3
"""Create a local-only Gate 2 candidate mapping file from the placeholder template.

The generated file is written under .workspace-mesh/ and is expected to be
ignored by Git. This helper copies placeholders only; it does not substitute
identifier values.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "workspace-mesh" / "gate2-candidate-mapping.template.json"
LOCAL_DIR = ROOT / ".workspace-mesh"
LOCAL_FILE = LOCAL_DIR / "gate2-candidate-mapping.local.json"
EXPECTED_PLACEHOLDERS = {
    "spreadsheet_id": "TODO_GOOGLE_SHEET_ID",
    "apps_script_project_id": "TODO_APPS_SCRIPT_PROJECT_ID",
    "cloud_vendor_strategy_calendar_id": "TODO_SP_CLOUD_VENDOR_STRATEGY_CALENDAR_ID",
    "launch_council_calendar_id": "TODO_SP_LAUNCH_COUNCIL_CALENDAR_ID",
}


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(f"missing file: {path.relative_to(ROOT)}")
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON in {path.relative_to(ROOT)}: {exc}")


def assert_placeholder_only(path: Path) -> None:
    data = load_json(path)
    if data.get("status") not in {"template_only", "local_candidate_placeholder_copy"}:
        fail(f"unexpected status in {path.relative_to(ROOT)}")
    if data.get("mesh_state") != "prepared-but-not-deployed":
        fail(f"mesh_state mismatch in {path.relative_to(ROOT)}")
    if data.get("dry_run_required") is not True:
        fail(f"dry_run_required must be true in {path.relative_to(ROOT)}")

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
    parser = argparse.ArgumentParser(description="Create local-only Gate 2 candidate mapping file.")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing local candidate mapping file.")
    args = parser.parse_args()

    if not TEMPLATE.exists():
        fail(f"missing template: {TEMPLATE.relative_to(ROOT)}")
    assert_placeholder_only(TEMPLATE)

    LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    if LOCAL_FILE.exists() and not args.force:
        fail(f"local candidate mapping already exists: {LOCAL_FILE.relative_to(ROOT)}; rerun with --force to replace it")

    shutil.copyfile(TEMPLATE, LOCAL_FILE)

    data = load_json(LOCAL_FILE)
    data["status"] = "local_candidate_placeholder_copy"
    data["local_file_note"] = "This file is local-only and ignored by Git. Replace placeholders only under a separate Gate 2 review record."
    LOCAL_FILE.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    assert_placeholder_only(LOCAL_FILE)
    assert_git_ignored(LOCAL_FILE)

    print("PASS: Workspace mesh Gate 2 local candidate mapping file created")
    print(f"local_file={LOCAL_FILE.relative_to(ROOT)}")
    print("placeholder_copy=true")
    print("git_ignored=true")
    print("ids_substituted=false")


if __name__ == "__main__":
    main()
