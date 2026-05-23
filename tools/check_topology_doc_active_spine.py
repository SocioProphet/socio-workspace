#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "TOPOLOGY.md"

REQUIRED = [
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
    "Legacy topology references that imply only `sociosphere` and `tritrpc` are core should be treated as stale.",
]

FORBIDDEN = [
    "## Core repos\n- **sociosphere**",
    "Directionality: `sociosphere -> tritrpc` allowed; `tritrpc -> sociosphere` forbidden.",
]


def main() -> int:
    text = DOC.read_text(encoding="utf-8")
    failed = False

    for needle in REQUIRED:
        if needle not in text:
            print(f"ERR: topology doc missing active-spine text: {needle}", file=sys.stderr)
            failed = True

    for needle in FORBIDDEN:
        if needle in text:
            print(f"ERR: topology doc still contains stale two-repo topology text: {needle}", file=sys.stderr)
            failed = True

    if failed:
        return 1

    print("OK: topology doc reflects active-spine model")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
