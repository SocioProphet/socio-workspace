#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SPINE = ROOT / "registry" / "spine-v0.txt"
SOURCES = ROOT / "governance" / "CANONICAL_SOURCES.yaml"

REQUIRED_CANONICAL_SOURCE_REPOS = {
    "SocioProphet/prophet-platform": "prophet-platform",
    "SocioProphet/TriTRPC": "TriTRPC",
    "SocioProphet/socioprophet-standards-storage": "socioprophet-standards-storage",
    "SocioProphet/socioprophet-standards-knowledge": "socioprophet-standards-knowledge",
    "SocioProphet/prophet-platform-standards": "prophet-platform-standards",
    "SocioProphet/socioprophet-agent-standards": "socioprophet-agent-standards",
    "SocioProphet/prophet-workspace": "prophet-workspace",
    "SocioProphet/hellgraph": "hellgraph",
    "SourceOS-Linux/sourceos-spec": "sourceos-spec",
}

CANON_RE = re.compile(r"canonical_repo:\s*([^,}\s]+)")


def canonical_repos(text: str) -> set[str]:
    return {match.group(1) for match in CANON_RE.finditer(text)}


def main() -> int:
    spine = SPINE.read_text(encoding="utf-8")
    sources = SOURCES.read_text(encoding="utf-8")
    canonical = canonical_repos(sources)

    failed = False
    for full_name, repo_name in sorted(REQUIRED_CANONICAL_SOURCE_REPOS.items()):
        if full_name not in spine:
            print(f"ERR: required repo missing from spine registry: {full_name}", file=sys.stderr)
            failed = True
        if repo_name not in canonical:
            print(f"ERR: required repo missing from canonical sources: {repo_name}", file=sys.stderr)
            failed = True

    if failed:
        return 1

    print("OK: active spine canonical-source coverage is present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
