#!/usr/bin/env python3
"""Validate the Workspace mesh release-readiness manifest.

The current safe state is prepared-but-not-deployed. Gate 0 may be complete;
all later deployment gates must remain not_started or blocked until explicit
promotion records exist.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "registry" / "workspace-mesh-release-readiness.v0.json"
DOC = ROOT / "docs" / "operations" / "workspace-mesh-release-readiness.md"

ALLOWED_CURRENT_GATE_STATUSES = {
    "gate-0-local-topology-proof": {"complete"},
    "gate-1-generated-artifact-review": {"not_started"},
    "gate-2-id-substitution-review": {"not_started"},
    "gate-3-apps-script-dry-run-rehearsal": {"not_started"},
    "gate-4-controlled-test-write": {"not_started"},
    "gate-5-scheduled-trigger-approval": {"blocked"},
    "gate-6-native-socioprophet-migration-review": {"blocked"},
}

FORBIDDEN_REQUIRED = {
    "tofu_apply_live_google_resources",
    "workspace_group_creation",
    "calendar_creation",
    "sheet_creation_by_iac",
    "apps_script_scheduled_triggers",
    "looker_studio_dashboard_creation",
    "production_data_processing",
    "native_socioprophet_migration",
}


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def main() -> None:
    if not MANIFEST.exists():
        fail(f"missing manifest: {MANIFEST.relative_to(ROOT)}")
    if not DOC.exists():
        fail(f"missing checklist doc: {DOC.relative_to(ROOT)}")

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    doc = DOC.read_text(encoding="utf-8")

    if manifest.get("status") != "prepared-but-not-deployed":
        fail("manifest status must remain prepared-but-not-deployed")
    if manifest.get("required_current_status") != "prepared-but-not-deployed":
        fail("required_current_status must remain prepared-but-not-deployed")

    gates = {gate.get("id"): gate for gate in manifest.get("gates", [])}
    for gate_id, allowed_statuses in ALLOWED_CURRENT_GATE_STATUSES.items():
        if gate_id not in gates:
            fail(f"missing gate: {gate_id}")
        status = gates[gate_id].get("status")
        if status not in allowed_statuses:
            fail(f"gate {gate_id} has status {status}, expected one of {sorted(allowed_statuses)}")

    forbidden = set(manifest.get("forbidden_until_promoted", []))
    missing_forbidden = FORBIDDEN_REQUIRED - forbidden
    if missing_forbidden:
        fail("missing forbidden-until-promoted items: " + ", ".join(sorted(missing_forbidden)))

    required_doc_phrases = [
        "prepared-but-not-deployed",
        "Gate 0 — Local topology proof",
        "Gate 1 — Generated artifact review",
        "Gate 2 — ID substitution review",
        "Gate 3 — Apps Script dry-run rehearsal",
        "Gate 4 — Controlled test write",
        "Gate 5 — Scheduled trigger approval",
        "Gate 6 — Native SocioProphet migration review",
        "Explicit non-authorization",
    ]
    for phrase in required_doc_phrases:
        if phrase not in doc:
            fail(f"checklist doc missing phrase: {phrase}")

    print("PASS: Workspace mesh release readiness remains prepared-but-not-deployed")
    print(f"gates={len(gates)}")
    print(f"forbidden_until_promoted={len(forbidden)}")


if __name__ == "__main__":
    main()
