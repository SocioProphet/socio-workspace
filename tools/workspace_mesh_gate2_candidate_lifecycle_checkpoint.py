#!/usr/bin/env python3
"""Print a compact Gate 2 candidate lifecycle checkpoint.

This script reads only status/count information from the local candidate file and
never prints candidate values. The standalone Make lifecycle target runs schema
validation before this script; the final block records that contract.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL_FILE = ROOT / ".workspace-mesh" / "gate2-candidate-mapping.local.json"
SCHEMA = ROOT / "schemas" / "workspace-mesh" / "gate2-candidate-review.schema.json"
TEMPLATE = ROOT / "templates" / "workspace-mesh" / "gate2-candidate-mapping.template.json"
EXPECTED_FIELDS = {
    "spreadsheet_id",
    "apps_script_project_id",
    "cloud_vendor_strategy_calendar_id",
    "launch_council_calendar_id",
}


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def git_ignored(path: Path) -> bool:
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", str(path.relative_to(ROOT))],
        cwd=ROOT,
        check=False,
    )
    return result.returncode == 0


def load_json(path: Path) -> dict:
    if not path.exists():
        fail(f"missing file: {path.relative_to(ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    if not LOCAL_FILE.exists():
        fail(f"missing local candidate mapping: {LOCAL_FILE.relative_to(ROOT)}")

    schema = load_json(SCHEMA)
    template = load_json(TEMPLATE)
    data = load_json(LOCAL_FILE)

    schema_fields = set(schema["properties"]["candidate_values"]["properties"])
    if schema_fields != EXPECTED_FIELDS:
        fail("schema field set mismatch")
    template_fields = set(template.get("candidate_values", {}))
    if template_fields != EXPECTED_FIELDS:
        fail("template field set mismatch")

    candidate_values = data.get("candidate_values", {})
    if set(candidate_values) != EXPECTED_FIELDS:
        fail("candidate field set mismatch")

    placeholder_count = 0
    local_candidate_count = 0
    evidence_count = 0

    for field, item in candidate_values.items():
        placeholder = str(item.get("placeholder", ""))
        candidate_value = str(item.get("candidate_value", ""))
        source_evidence = str(item.get("source_evidence", ""))
        if not placeholder.startswith("TODO_"):
            fail(f"placeholder for {field} is not a TODO value")
        if candidate_value == placeholder:
            placeholder_count += 1
        else:
            local_candidate_count += 1
        if source_evidence and not source_evidence.startswith("TODO_"):
            evidence_count += 1

    mode = "placeholder_copy" if local_candidate_count == 0 else "local_candidate_review"

    print("Workspace Mesh Gate 2 Candidate Lifecycle Checkpoint")
    print("====================================================")
    print("mesh_state=prepared-but-not-deployed")
    print("gate_2=planning_only")
    print("schema_present=true")
    print("schema_template_compatible=true")
    print("schema_validation=passed_by_lifecycle_target")
    print(f"local_candidate_file={LOCAL_FILE.relative_to(ROOT)}")
    print(f"mode={mode}")
    print(f"fields={len(EXPECTED_FIELDS)}")
    print(f"placeholder_values={placeholder_count}")
    print(f"local_candidate_values={local_candidate_count}")
    print(f"source_evidence_records={evidence_count}")
    print(f"git_ignored={str(git_ignored(LOCAL_FILE)).lower()}")
    print("candidate_values_printed=false")
    print("live_execution=false")
    print("next_allowed_action=local_candidate_review_only")


if __name__ == "__main__":
    main()
