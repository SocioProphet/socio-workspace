#!/usr/bin/env python3
"""Validate Workspace mesh Make integration surfaces.

The canonical local operator entrypoint is workspace-mesh-local-checkpoint.mk.
This validator ensures it delegates to the expected standalone make fragments
without requiring risky root GNUmakefile edits.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT_MK = ROOT / "workspace-mesh-local-checkpoint.mk"
EXPECTED_MAKEFILES = {
    "workspace-mesh-gate2-candidate.mk",
    "workspace-mesh-gate2-promotion.mk",
    "workspace-mesh-current-state.mk",
}
EXPECTED_COMMANDS = {
    "workspace-mesh-operator-checkpoint",
    "workspace-mesh-gate2-candidate-lifecycle-checkpoint",
    "workspace-mesh-gate2-promotion-blocker-validate",
    "workspace-mesh-current-state-validate",
    "tools/workspace_mesh_local_checkpoint.py",
}
FORBIDDEN_ROOT_DEPENDENCIES = {
    "tofu apply",
    "clasp push",
    "workspace-mesh-gate3-start",
}


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def main() -> None:
    if not CHECKPOINT_MK.exists():
        fail("missing workspace-mesh-local-checkpoint.mk")
    checkpoint_text = CHECKPOINT_MK.read_text(encoding="utf-8")

    for makefile in sorted(EXPECTED_MAKEFILES):
        if not (ROOT / makefile).exists():
            fail(f"missing expected make fragment: {makefile}")
        if makefile not in checkpoint_text:
            fail(f"checkpoint does not reference make fragment: {makefile}")

    for command in sorted(EXPECTED_COMMANDS):
        if command not in checkpoint_text:
            fail(f"checkpoint missing expected command: {command}")

    for marker in sorted(FORBIDDEN_ROOT_DEPENDENCIES):
        if marker in checkpoint_text:
            fail(f"checkpoint contains forbidden marker: {marker}")

    if "workspace-mesh-local-checkpoint" not in checkpoint_text:
        fail("checkpoint target missing")

    print("PASS: Workspace mesh Make integration is reconciled")
    print("canonical_entrypoint=workspace-mesh-local-checkpoint.mk")
    print(f"standalone_fragments={len(EXPECTED_MAKEFILES)}")
    print("root_gnumakefile_edit_required=false")
    print("gate3_start_referenced=false")
    print("live_execution=false")


if __name__ == "__main__":
    main()
