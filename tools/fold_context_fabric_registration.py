#!/usr/bin/env python3
"""Fold the Workspace Context Fabric registration fragment into workspace.toml.

This helper avoids hand-editing the large canonical manifest. It appends the
entries from `manifest/context-fabric.registration.toml` to
`manifest/workspace.toml` only when those repo names are not already present.

Usage:

  python3 tools/fold_context_fabric_registration.py --check
  python3 tools/fold_context_fabric_registration.py --write

The default mode is `--check`.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifest" / "workspace.toml"
FRAGMENT = ROOT / "manifest" / "context-fabric.registration.toml"

NAME_RE = re.compile(r'^name\s*=\s*"([^"]+)"\s*$', re.MULTILINE)
EXPECTED = {
    "prophet_workspace",
    "agent_registry",
    "memory_mesh",
    "socioprophet_agent_standards",
}


def repo_names(text: str) -> list[str]:
    return NAME_RE.findall(text)


def fold(manifest_text: str, fragment_text: str) -> tuple[str, list[str], list[str]]:
    manifest_names = set(repo_names(manifest_text))
    fragment_names = repo_names(fragment_text)
    fragment_set = set(fragment_names)

    missing_from_fragment = sorted(EXPECTED - fragment_set)
    if missing_from_fragment:
        raise ValueError("fragment missing expected repo names: " + ", ".join(missing_from_fragment))

    already_present = [name for name in fragment_names if name in manifest_names]
    missing = [name for name in fragment_names if name not in manifest_names]

    if not missing:
        return manifest_text, already_present, missing

    text = manifest_text.rstrip() + "\n\n# ── Workspace Context Fabric ─────────────────────────────────────────────────\n\n"
    text += fragment_text.rstrip() + "\n"
    combined = repo_names(text)
    duplicates = sorted({name for name in combined if combined.count(name) > 1})
    if duplicates:
        raise ValueError("fold would create duplicate repo names: " + ", ".join(duplicates))
    return text, already_present, missing


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="write folded manifest")
    parser.add_argument("--check", action="store_true", help="check fold state without writing")
    args = parser.parse_args(argv)

    manifest_text = MANIFEST.read_text(encoding="utf-8")
    fragment_text = FRAGMENT.read_text(encoding="utf-8")

    try:
        folded, already_present, missing = fold(manifest_text, fragment_text)
    except ValueError as exc:
        print(f"ERR: {exc}", file=sys.stderr)
        return 2

    if args.write:
        MANIFEST.write_text(folded, encoding="utf-8")
        print("OK: folded Context Fabric registration into manifest/workspace.toml")
        if already_present:
            print("already present: " + ", ".join(already_present))
        if missing:
            print("added: " + ", ".join(missing))
        return 0

    if missing:
        print("PENDING: Context Fabric registration entries not yet folded: " + ", ".join(missing))
        return 1

    print("OK: Context Fabric registration entries already folded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
