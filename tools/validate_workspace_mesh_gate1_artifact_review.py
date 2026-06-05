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
DOC = ROOT / "docs" / "operations" / "workspace-mesh-gate1-generated-artifact-review-template.md"

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


def main() -> None:
    if not MANIFEST.exists():
        fail(f"missing manifest: {MANIFEST.relative_to(ROOT)}")
    if not DOC.exists():
        fail(f"missing Gate 1 doc: {DOC.relative_to(ROOT)}")

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    doc = DOC.read_text(encoding="utf-8")

    if manifest.get("gate_id") != "gate-1-generated-artifact-review":
        fail("manifest gate_id mismatch")
    if manifest.get("status") != "not_started":
        fail("Gate 1 manifest status must remain not_started until a real review record exists")
    if manifest.get("current_mesh_state") != "prepared-but-not-deployed":
        fail("Gate 1 must remain tied to prepared-but-not-deployed state")
    if manifest.get("current_disposition") != "not_started":
        fail("Gate 1 disposition must remain not_started in the template manifest")

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

    print("PASS: Workspace mesh Gate 1 artifact-review template is valid and not started")
    print(f"artifacts={len(artifact_names)}")
    print(f"forbidden_by_this_gate={len(forbidden)}")


if __name__ == "__main__":
    main()
