#!/usr/bin/env python3
"""Guard: every hellgraph dependency must point at the ONE canonical hellgraph,
pinned to an immutable ref — no local path deps, no moving branches.

"One graph, not many divergent branches with discontinuity" as a property of the
build rather than a note in a comment. Scans the repo for hellgraph consumption:

  * Rust (Cargo.toml): the hellgraph crates (hg_analytics / hg_core / hg_kernel /
    hg_napi) MUST be a git dep pinned by `rev = "<sha>"`. A `path = …` dep (points at
    a local checkout that drifts/forks) or a git dep without `rev` (branch/tag moves)
    is a violation.
  * JS (package.json): a `@socioprophet/hellgraph` (or "hellgraph") dep MUST be EITHER
    a vendored tarball (`file:vendor/socioprophet-hellgraph-X.Y.Z.tgz` — the pattern
    already used by prophet-platform's hellgraph-service/lifecycle-warden, see
    docs/architecture/hellgraph-consumption-policy.md) OR pinned to a tag (`#v1.2.3`)
    or a commit SHA (`#<40-hex>`) for a git-sourced dep. A bare local `file:` path
    outside `vendor/` (drifts/forks with whatever's on that one machine), a missing
    ref, or a moving branch (main/master/HEAD/develop) is a violation.

stdlib-only. Exit 0 if clean; 1 (with the offenders) otherwise.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", "node_modules", "target", "vendor", "dist", "__pycache__", ".venv"}

RUST_CRATES = ("hg_analytics", "hg_core", "hg_kernel", "hg_napi")
_SHA_RE = re.compile(r'rev\s*=\s*"[0-9a-fA-F]{7,40}"')
_JS_SHA = re.compile(r"^[0-9a-fA-F]{7,40}$")
_JS_TAG = re.compile(r"^v?\d+\.\d+")
_MOVING = {"main", "master", "head", "develop", "dev", ""}
_VENDORED_TGZ = re.compile(r"^file:vendor/socioprophet-hellgraph-\d+\.\d+\.\d+\.tgz$")

violations: list[str] = []


def _walk(suffix: str):
    for p in ROOT.rglob(f"*{suffix}"):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        yield p


def check_cargo(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    for crate in RUST_CRATES:
        # capture `crate = "…"` or `crate = { … }` (non-nested inline table, single/multi-line)
        for m in re.finditer(rf'(?m)^\s*{re.escape(crate)}\s*=\s*(\{{[^}}]*\}}|"[^"]*"|[^\n#]*)', text):
            spec = m.group(1).strip()
            rel = path.relative_to(ROOT)
            if "path" in spec and re.search(r'\bpath\s*=', spec):
                violations.append(f"{rel}: `{crate}` uses a local PATH dep — pin to the canonical hellgraph git rev instead:\n      {spec}")
            elif re.search(r'\bgit\s*=', spec):
                if not _SHA_RE.search(spec):
                    violations.append(f"{rel}: `{crate}` git dep has no immutable `rev` (branch/tag moves):\n      {spec}")
            else:
                violations.append(f"{rel}: `{crate}` must be a git dep pinned by `rev`, got:\n      {spec}")


def check_package_json(path: Path) -> None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return
    rel = path.relative_to(ROOT)
    for section in ("dependencies", "devDependencies", "optionalDependencies"):
        for name, val in (data.get(section) or {}).items():
            if "hellgraph" not in name.lower():
                continue
            if not isinstance(val, str):
                violations.append(f"{rel}: `{name}` = {val!r} is not pinned (needs a vendored tarball or `#<tag-or-sha>`)")
                continue
            if _VENDORED_TGZ.match(val):
                continue
            if "#" not in val:
                violations.append(f"{rel}: `{name}` = {val!r} is not pinned (needs `file:vendor/socioprophet-hellgraph-X.Y.Z.tgz` or `#<tag-or-sha>`)")
                continue
            ref = val.rsplit("#", 1)[1]
            if ref.lower() in _MOVING or not (_JS_SHA.match(ref) or _JS_TAG.match(ref)):
                violations.append(f"{rel}: `{name}` pinned to a moving/unrecognized ref '#{ref}' (use a tag `#vX.Y.Z` or a SHA)")


def main() -> int:
    cargo = list(_walk("Cargo.toml"))
    pkgs = list(_walk("package.json"))
    for p in cargo:
        check_cargo(p)
    for p in pkgs:
        check_package_json(p)
    print(f"scanned {len(cargo)} Cargo.toml + {len(pkgs)} package.json for hellgraph pins")
    if violations:
        print(f"\nFAIL — {len(violations)} unpinned/divergent hellgraph dependency(ies):")
        for v in violations:
            print(f"  - {v}")
        print("\nOne graph: pin to SocioProphet/hellgraph @ <rev>. See docs/architecture/hellgraph-consumption-policy.md")
        return 1
    print("PASS — every hellgraph dependency is pinned to the one canonical graph")
    return 0


if __name__ == "__main__":
    sys.exit(main())
