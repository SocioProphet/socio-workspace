#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "registry" / "spine-v0.txt"
OVERLAY = ROOT / "manifest" / "active-spine.repos.toml"
SOURCES = ROOT / "governance" / "CANONICAL_SOURCES.yaml"

REQUIRED = {
    "SocioProphet/prophet-platform": "prophet-platform",
    "SocioProphet/prophet-workspace": "prophet-workspace",
    "SocioProphet/hellgraph": "hellgraph",
    "SocioProphet/socioprophet-agent-standards": "socioprophet-agent-standards",
}

URL_RE = re.compile(r'^url\s*=\s*"https://github.com/([^"]+)"\s*$')
CANON_RE = re.compile(r'canonical_repo:\s*([^,}\s]+)')


def overlay_repos(text: str) -> set[str]:
    return {m.group(1) for line in text.splitlines() if (m := URL_RE.match(line.strip()))}


def canonical_repos(text: str) -> set[str]:
    return {m.group(1) for m in CANON_RE.finditer(text)}


def main() -> int:
    registry = REGISTRY.read_text(encoding="utf-8")
    overlay = OVERLAY.read_text(encoding="utf-8")
    sources = SOURCES.read_text(encoding="utf-8")

    overlay_set = overlay_repos(overlay)
    canonical_set = canonical_repos(sources)

    failed = False
    for full_name, repo_name in sorted(REQUIRED.items()):
        if full_name not in registry:
            print(f"ERR: missing from spine registry: {full_name}", file=sys.stderr)
            failed = True
        if full_name not in overlay_set:
            print(f"ERR: missing from active spine overlay: {full_name}", file=sys.stderr)
            failed = True
        if repo_name not in canonical_set:
            print(f"ERR: missing from canonical sources: {repo_name}", file=sys.stderr)
            failed = True

    if failed:
        return 1

    print("OK: active spine repos covered by registry, overlay, and canonical sources")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
