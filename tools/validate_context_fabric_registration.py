#!/usr/bin/env python3
"""Validate Workspace Context Fabric registration staging.

This validator keeps the folded-registration path safe without requiring a
whole-file manifest rewrite through connector tooling. It verifies that the
registration fragment contains the expected repo entries and that the canonical
manifest does not contain duplicate repo names when the fragment is folded.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifest" / "workspace.toml"
FRAGMENT = ROOT / "manifest" / "context-fabric.registration.toml"
EXPECTED = {
    "prophet_workspace",
    "agent_registry",
    "memory_mesh",
    "socioprophet_agent_standards",
}

NAME_RE = re.compile(r'^name\s*=\s*"([^"]+)"\s*$', re.MULTILINE)


def names(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return NAME_RE.findall(text)


def main() -> int:
    manifest_names = names(MANIFEST)
    fragment_names = names(FRAGMENT)
    fragment_set = set(fragment_names)

    missing = sorted(EXPECTED - fragment_set)
    if missing:
        print("ERR: registration fragment missing expected repos: " + ", ".join(missing), file=sys.stderr)
        return 2

    extra_dupes = sorted(set(manifest_names) & EXPECTED)
    if extra_dupes:
        print(
            "ERR: expected fragment repos already appear in manifest/workspace.toml: "
            + ", ".join(extra_dupes),
            file=sys.stderr,
        )
        return 2

    combined = manifest_names + fragment_names
    dupes = sorted({name for name in combined if combined.count(name) > 1})
    if dupes:
        print("ERR: duplicate repo names after fold: " + ", ".join(dupes), file=sys.stderr)
        return 2

    print("OK: Context Fabric registration fragment is fold-safe")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
