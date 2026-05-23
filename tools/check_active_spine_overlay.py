#!/usr/bin/env python3
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "registry" / "spine-v0.txt"
OVERLAY = ROOT / "manifest" / "active-spine.repos.toml"

REQUIRED_OVERLAY = {
    "SocioProphet/prophet-platform",
    "SocioProphet/prophet-workspace",
    "SocioProphet/hellgraph",
    "SocioProphet/socioprophet-agent-standards",
}

URL_RE = re.compile(r'^url\s*=\s*"https://github.com/([^"]+)"\s*$')


def urls_in_overlay(text: str) -> set[str]:
    return {m.group(1) for line in text.splitlines() if (m := URL_RE.match(line.strip()))}


def main() -> int:
    registry = REGISTRY.read_text(encoding="utf-8")
    overlay = OVERLAY.read_text(encoding="utf-8")
    overlay_repos = urls_in_overlay(overlay)

    missing_from_registry = sorted(repo for repo in REQUIRED_OVERLAY if repo not in registry)
    missing_from_overlay = sorted(REQUIRED_OVERLAY - overlay_repos)
    unexpected_overlay = sorted(overlay_repos - REQUIRED_OVERLAY)

    if missing_from_registry or missing_from_overlay or unexpected_overlay:
        for repo in missing_from_registry:
            print(f"ERR: required overlay repo missing from registry: {repo}", file=sys.stderr)
        for repo in missing_from_overlay:
            print(f"ERR: required overlay repo missing from manifest overlay: {repo}", file=sys.stderr)
        for repo in unexpected_overlay:
            print(f"ERR: unexpected repo in manifest overlay: {repo}", file=sys.stderr)
        return 1

    print("OK: active spine manifest overlay matches registry subset")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
