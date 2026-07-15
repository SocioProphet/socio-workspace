#!/usr/bin/env python3
"""Validate Workspace Context Fabric registration state.

The registration can be in either valid state:

1. pending fold: all expected repos are present in the registration fragment and
   absent from manifest/workspace.toml.
2. folded: all expected repos are present in manifest/workspace.toml.

Partial folds and duplicate repo names are rejected.
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

def _repo_names_from_toml(text: str) -> list[str] | None:
    """Repo names from [[repos]] only, via a real TOML parse.

    The regex below matches any `name = "..."` line, which also catches
    [workspace].name — the workspace's own identity, not a repo. That made
    `sociosphere` look like a duplicate of the legitimate [[repos]] entry of the
    same name. Returns None if the text isn't parseable TOML (e.g. a bare
    fragment), so callers can fall back to the regex.
    """
    try:
        import tomllib
    except ModuleNotFoundError:  # py<3.11
        return None
    try:
        data = tomllib.loads(text)
    except Exception:
        return None
    repos = data.get("repos")
    if repos is None:
        # Parsed cleanly and there are simply no [[repos]] — that is zero repos,
        # NOT a reason to fall back to the regex (which would then wrongly harvest
        # [workspace].name, the very bug this exists to prevent).
        return []
    if not isinstance(repos, list):
        return None
    return [r["name"] for r in repos if isinstance(r, dict) and isinstance(r.get("name"), str)]



def names(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    parsed = _repo_names_from_toml(text)
    return parsed if parsed is not None else NAME_RE.findall(text)


def duplicates(values: list[str]) -> list[str]:
    return sorted({value for value in values if values.count(value) > 1})


def main() -> int:
    manifest_names = names(MANIFEST)
    fragment_names = names(FRAGMENT)
    fragment_set = set(fragment_names)
    manifest_set = set(manifest_names)

    fragment_missing = sorted(EXPECTED - fragment_set)
    if fragment_missing:
        print(
            "ERR: registration fragment missing expected repos: "
            + ", ".join(fragment_missing),
            file=sys.stderr,
        )
        return 2

    manifest_dupes = duplicates(manifest_names)
    if manifest_dupes:
        print(
            "ERR: duplicate repo names in manifest/workspace.toml: "
            + ", ".join(manifest_dupes),
            file=sys.stderr,
        )
        return 2

    fragment_dupes = duplicates(fragment_names)
    if fragment_dupes:
        print(
            "ERR: duplicate repo names in registration fragment: "
            + ", ".join(fragment_dupes),
            file=sys.stderr,
        )
        return 2

    present = EXPECTED & manifest_set
    missing_from_manifest = EXPECTED - manifest_set

    if present and missing_from_manifest:
        print(
            "ERR: partial Context Fabric fold; present="
            + ", ".join(sorted(present))
            + " missing="
            + ", ".join(sorted(missing_from_manifest)),
            file=sys.stderr,
        )
        return 2

    if present == EXPECTED:
        print("OK: Context Fabric registration entries are folded into manifest/workspace.toml")
        return 0

    print("OK: Context Fabric registration fragment is pending fold and fold-safe")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
