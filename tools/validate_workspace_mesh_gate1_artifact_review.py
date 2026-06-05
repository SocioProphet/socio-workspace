#!/usr/bin/env python3
"""Validate Gate 1 generated-artifact review posture.

Gate 1 is allowed to exist as a template/manifest while remaining not_started.
This validator ensures review criteria exist without promoting the mesh beyond
prepared-but-not-deployed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "registry" / "workspace-mesh-gate1-generated-artifact-review.v0.json"
STATUS_MANIFEST = ROOT / "registry" / "workspace-mesh-gate1-status.v0.json"
DOC = ROOT / "docs" / "operations" / "workspace-mesh-gate1-generated-artifact-review-template.md"
STATUS_DOC = ROOT / "docs" / "operations" / "workspace-mesh-gate1-status.md"

EXPECTED_ARTIFACTS = {
    "config.generated.json",
    "clasp.generated.json",
    "mesh-summary.generated.json",
    "operator-next-steps.md",
}

REQUIRED_FORBIDDEN = {
    "id_substitution",
    "tofu_apply",
    "clasp_push",
    "apps_script_execution",
    "scheduled_triggers",
    "live_calendar_access",
    "workspace_group_creation",
    "dashboard_creation",
    "production_data_processing",
    "native_socioprophet_migration",
}

REQUIRED_DOC_PHRASES = [
    "Gate 1 — Generated Artifact Review Template",
    "prepared-but-not-deployed",
    "config.generated.json",
    "clasp.generated.json",
    "mesh-summary.generated.json",
    "operator-next-steps.md",
    "dryRun",
    "TODO_GOOGLE_SHEET_ID",
    "TODO_APPS_SCRIPT_PROJECT_ID",
    "Explicit non-authorization",
]


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def load_json(path: Path) -> dict:
    if not path.exists():
        fail(f"missing JSON file: {path.relative_to(ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    if not MANIFEST.exists():
        fail(f"missing manifest: {MANIFEST.relative_to(ROOT)}")
    if not DOC.exists():
        fail(f"missing Gate 1 doc: {DOC.relative_to(ROOT)}")
    if not STATUS_DOC.exists():
        fail(f"missing Gate 1 status doc: {STATUS_DOC.relative_to(ROOT)}")

    manifest = load_json(MANIFEST)
    status_manifest = load_json(STATUS_MANIFEST)
    doc = DOC.read_text(encoding="utf-8")
    status_doc = STATUS_DOC.read_text(encoding="utf-8")

    if manifest.get("gate_id") != "gate-1-generated-artifact-review":
        fail("manifest gate_id mismatch")
    if manifest.get("status") != "not_started":
        fail("Gate 1 manifest status must remain not_started until a real review record exists")
    if manifest.get("current_mesh_state") != "prepared-but-not-deployed":
        fail("Gate 1 must remain tied to prepared-but-not-deployed state")
    if manifest.get("current_disposition") != "not_started":
        fail("Gate 1 disposition must remain not_started in the template manifest")

    if status_manifest.get("gate_id") != "gate-1-generated-artifact-review":
        fail("Gate 1 status manifest gate_id mismatch")
    if status_manifest.get("status") != "not_started":
        fail("Gate 1 status manifest must remain not_started")
    if status_manifest.get("mesh_state") != "prepared-but-not-deployed":
        fail("Gate 1 status manifest must remain prepared-but-not-deployed")
    if status_manifest.get("review_performed") is not False:
        fail("Gate 1 review_performed must remain false")
    if status_manifest.get("promotion_authorized") is not False:
        fail("Gate 1 promotion_authorized must remain false")

    artifact_names = {artifact.get("name") for artifact in manifest.get("artifacts", [])}
    missing_artifacts = EXPECTED_ARTIFACTS - artifact_names
    extra_artifacts = artifact_names - EXPECTED_ARTIFACTS
    if missing_artifacts:
        fail("Gate 1 manifest missing artifacts: " + ", ".join(sorted(missing_artifacts)))
    if extra_artifacts:
        fail("Gate 1 manifest has unexpected artifacts: " + ", ".join(sorted(extra_artifacts)))

    for artifact in manifest.get("artifacts", []):
        if not artifact.get("required_checks"):
            fail(f"artifact {artifact.get('name')} has no required_checks")

    forbidden = set(manifest.get("forbidden_by_this_gate", []))
    missing_forbidden = REQUIRED_FORBIDDEN - forbidden
    if missing_forbidden:
        fail("Gate 1 missing forbidden actions: " + ", ".join(sorted(missing_forbidden)))

    for phrase in REQUIRED_DOC_PHRASES:
        if phrase not in doc:
            fail(f"Gate 1 doc missing phrase: {phrase}")

    for phrase in ["Status: `not_started`", "prepared-but-not-deployed", "promotion_authorized", "review_performed"]:
        if phrase not in status_doc:
            fail(f"Gate 1 status doc missing phrase: {phrase}")

    print("PASS: Workspace mesh Gate 1 artifact-review template is valid and not started")
    print(f"artifacts={len(artifact_names)}")
    print(f"forbidden_by_this_gate={len(forbidden)}")


if __name__ == "__main__":
    main()
