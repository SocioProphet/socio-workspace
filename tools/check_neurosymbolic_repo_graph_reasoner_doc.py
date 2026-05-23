#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "governance" / "neurosymbolic-repo-graph-reasoner.md"

REQUIRED = [
    "watson-cyc-semantic-web-chronos-v1",
    "registry/corpus-loop-v1/valid.watson-cyc-chronos.pinned.json",
    "SocioProphet/sherlock-search",
    "SocioProphet/ontogenesis",
    "SocioProphet/policy-fabric",
    "SocioProphet/agentplane",
    "SocioProphet/model-governance-ledger",
    "Platform/corpus-event-semantics.ttl",
    "shapes/corpus-event-semantics.shacl.ttl",
    "Chronos-style transition reasoning",
    "Watson/Cyc-style semantic reasoning",
    "SHACL as promotion gate",
    "governed-action-policy-decision.v0",
    "bounded-action-loop.v0",
    "governance-audit-record.v0",
    "Do not implement this as generic Pellet-only reasoning.",
    "Do not treat OWL class inference as sufficient for governance action.",
]

FORBIDDEN = [
    "standalone OWL-only reasoner model",
    "generic Pellet-only reasoning"  # allowed only in explicit non-goal context, checked below
]


def main() -> int:
    text = DOC.read_text(encoding="utf-8")
    failed = False

    for needle in REQUIRED:
        if needle not in text:
            print(f"ERR: neurosymbolic repo graph reasoner doc missing: {needle}", file=sys.stderr)
            failed = True

    if "rather than a standalone OWL-only reasoner model" not in text:
        print("ERR: doc must reject standalone OWL-only reasoner framing", file=sys.stderr)
        failed = True

    if "Do not implement this as generic Pellet-only reasoning." not in text:
        print("ERR: doc must explicitly reject Pellet-only implementation", file=sys.stderr)
        failed = True

    return 1 if failed else _ok()


def _ok() -> int:
    print("OK: neurosymbolic repo graph reasoner doc is anchored to Watson/Cyc/Chronos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
