#!/usr/bin/env python3
"""Validate Sociosphere's Workspace mesh proxy surface.

Sociosphere should expose operator-friendly proxy targets while preserving
prophet-platform-fabric-mlops-ts-suite as the mesh implementation authority.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GNUMAKEFILE = ROOT / "GNUmakefile"
DOC = ROOT / "docs" / "operations" / "workspace-mesh-proxy.md"

REQUIRED_TARGETS = [
    "fabric-repo-check",
    "doctor-workspace-ops",
    "validate-workspace-prototype",
    "validate-workspace-mesh",
    "validate-workspace-all",
    "terraform-workspace-mesh-init",
    "terraform-workspace-mesh-fmt",
    "terraform-workspace-mesh-validate",
    "terraform-workspace-mesh-plan",
    "terraform-workspace-mesh-plan-out",
    "terraform-workspace-mesh-plan-json",
    "validate-workspace-mesh-plan-json",
    "terraform-workspace-mesh-plan-safe",
    "tofu-workspace-mesh-plan-safe",
]

REQUIRED_NEEDLES = [
    "include Makefile",
    "FABRIC_REPO ?= $(HOME)/dev/prophet-platform-fabric-mlops-ts-suite",
    "FABRIC_MAKE ?= make -C $(FABRIC_REPO)",
    "terraform-workspace-mesh-plan-safe: fabric-repo-check",
    "$(FABRIC_MAKE) terraform-workspace-mesh-plan-safe",
]


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def read(path: Path) -> str:
    if not path.exists():
        fail(f"missing file: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def main() -> None:
    make_text = read(GNUMAKEFILE)
    doc_text = read(DOC)

    for needle in REQUIRED_NEEDLES:
        if needle not in make_text:
            fail(f"GNUmakefile missing required content: {needle}")

    for target in REQUIRED_TARGETS:
        if f"{target}:" not in make_text:
            fail(f"GNUmakefile missing target: {target}")
        if target not in doc_text:
            fail(f"workspace-mesh-proxy.md missing target documentation: {target}")

    print("PASS: Sociosphere Workspace mesh proxy is valid")
    print(f"targets={len(REQUIRED_TARGETS)}")


if __name__ == "__main__":
    main()
