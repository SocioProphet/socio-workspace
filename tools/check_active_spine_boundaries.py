#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
BOUNDARIES = ROOT / "catalog" / "boundaries.yaml"

REQUIRED_REPOS = [
    "SocioProphet/sociosphere",
    "SocioProphet/prophet-platform",
    "SocioProphet/TriTRPC",
    "SocioProphet/prophet-platform-standards",
    "SocioProphet/socioprophet-standards-storage",
    "SocioProphet/socioprophet-standards-knowledge",
    "SocioProphet/socioprophet-agent-standards",
    "SocioProphet/prophet-workspace",
    "SocioProphet/hellgraph",
    "SourceOS-Linux/sourceos-spec",
]

REQUIRED_BOUNDARY_CLASSES = [
    "estate_registry",
    "runtime_verifier",
    "transport_protocol",
    "standards",
    "storage_standard",
    "knowledge_standard",
    "agent_profile_standard",
    "workspace_product",
    "proof_graph_runtime",
    "sourceos_spec_standard",
]

REPO_RE = re.compile(r"^\s*- repo:\s*(\S+)\s*$", re.MULTILINE)
CLASS_RE = re.compile(r"^\s*boundary_class:\s*(\S+)\s*$", re.MULTILINE)


def main() -> int:
    text = BOUNDARIES.read_text(encoding="utf-8")
    repos = set(REPO_RE.findall(text))
    classes = set(CLASS_RE.findall(text))
    failed = False

    for repo in REQUIRED_REPOS:
        if repo not in repos:
            print(f"ERR: active-spine boundary missing repo: {repo}", file=sys.stderr)
            failed = True

    for boundary_class in REQUIRED_BOUNDARY_CLASSES:
        if boundary_class not in classes:
            print(f"ERR: active-spine boundary class missing: {boundary_class}", file=sys.stderr)
            failed = True

    if failed:
        return 1

    print("OK: active-spine boundary coverage is present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
