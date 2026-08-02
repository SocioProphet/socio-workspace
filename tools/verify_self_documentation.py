#!/usr/bin/env python3
"""Drift canary for the self-documenting estate — effect over artifact.

Self-documenting-estate, step 3 (CANARY). A control that cannot fail is suspect.
This one CAN fail, and does, the moment the committed self-documentation stops
matching the code it claims to describe. It is fail-closed: no catalog, a moved
catalog, a hand-edited composed record, a repo with no code-derived backing, or a
composed repo missing from the roster all turn the build RED.

Teeth (each is an independent way to go red):
  A  MISSING     — a code-derived doc that a fresh regenerate produces is absent
                   from the committed view (a covered repo silently undocumented).
  B  UNBACKED    — a committed per-repo doc that is not backed by real catalog
                   assets (an Atlas claim with no code behind it).
  C  STALE/DRIFT — the committed composed view is not byte-identical to a fresh
                   regenerate from the pinned catalog (docs drifted from code).
  D  PIN         — the catalog is absent, or its consumed inputs no longer hash
                   to the committed `catalog-pin.json` (docs describe a catalog
                   that no longer exists as pinned).
  E  ROSTER      — a composed repo is not present in the committed estate-roster.

Exit 0 only if every tooth passes.

Usage:
  tools/verify_self_documentation.py [--catalog PATH]
  (falls back to $PROPHET_CORE_CATALOG, then ../prophet-core-catalog)
"""
from __future__ import annotations

import argparse
import filecmp
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SELFDOC = ROOT / "artifacts" / "self-documentation"
ROSTER = ROOT / "registry" / "estate-roster.json"
COMPOSE = ROOT / "tools" / "compose_self_documentation.py"


def fail(msg: str):
    print(f"SELF-DOC DRIFT FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def find_catalog(explicit: str | None) -> Path:
    for cand in (explicit, os.environ.get("PROPHET_CORE_CATALOG"),
                 str(ROOT.parent / "prophet-core-catalog")):
        if cand and Path(cand).exists():
            return Path(cand).resolve()
    fail("no catalog checkout found (pass --catalog, set $PROPHET_CORE_CATALOG, "
         "or place prophet-core-catalog alongside sociosphere) — fail-closed")


def rel_files(base: Path) -> set[str]:
    return {str(p.relative_to(base)) for p in base.rglob("*") if p.is_file()}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--catalog", default=None)
    args = ap.parse_args()

    if not SELFDOC.exists():
        fail(f"no committed self-documentation at {SELFDOC} — run compose first")
    pin_path = SELFDOC / "catalog-pin.json"
    if not pin_path.exists():
        fail("catalog-pin.json missing — cannot verify what the docs were derived from")
    pin = json.loads(pin_path.read_text("utf-8"))

    catalog = find_catalog(args.catalog)

    # ---- Tooth D: pin integrity (fail-closed) ----------------------------
    # Recompute compose's own input hashes by regenerating and comparing the pin.
    # First, a cheap direct hash check of the consumed inputs.
    import hashlib
    idx = catalog / "catalog-index"
    eg = catalog / "datasets" / "estate-graph"
    input_paths = {
        "atlas": ROOT / "catalog" / "boundaries.yaml",
        "assets": idx / "assets.jsonl", "edges": idx / "edges.jsonl",
        "glossary": idx / "glossary.jsonl", "index": idx / "index.json",
        "estate_graph": eg / "estate-graph.ttl", "estate_edges": eg / "estate-edges.ttl",
    }
    for name, want in pin.get("inputs", {}).items():
        p = input_paths.get(name)
        if not p or not p.exists():
            fail(f"pinned input '{name}' not present in this checkout ({p}) — fail-closed")
        got = "sha256:" + hashlib.sha256(p.read_bytes()).hexdigest()
        if got != want:
            fail(f"pinned input '{name}' hash mismatch: docs were derived from a "
                 f"different catalog/atlas state (pin={want[:19]}.. now={got[:19]}..). "
                 f"Recompose to refresh, or restore the pinned catalog.")

    # ---- Teeth A + C: regenerate and byte-compare ------------------------
    with tempfile.TemporaryDirectory() as td:
        r = subprocess.run(
            [sys.executable, str(COMPOSE), "--catalog", str(catalog), "--out", td],
            capture_output=True, text=True)
        if r.returncode != 0:
            fail(f"regenerate failed: {r.stderr.strip() or r.stdout.strip()}")
        fresh = Path(td)
        committed_files = rel_files(SELFDOC)
        fresh_files = rel_files(fresh)
        missing = fresh_files - committed_files      # tooth A
        extra = committed_files - fresh_files
        if missing:
            fail(f"committed view is MISSING code-derived docs a fresh regenerate "
                 f"produces (covered repos left undocumented): {sorted(missing)}")
        if extra:
            fail(f"committed view has STALE files a fresh regenerate does not "
                 f"produce (removed/renamed repos still documented): {sorted(extra)}")
        differ = [f for f in sorted(fresh_files)
                  if not filecmp.cmp(fresh / f, SELFDOC / f, shallow=False)]
        if differ:
            fail(f"committed self-documentation DRIFTED from the code/catalog "
                 f"(not byte-identical to fresh regenerate): {differ}. Recompose.")

    # ---- Tooth B: every committed per-repo doc is catalog-backed ---------
    for rec_path in sorted((SELFDOC / "repos").glob("*.json")):
        rec = json.loads(rec_path.read_text("utf-8"))
        if not rec.get("atlas_backed") or rec.get("catalog", {}).get("asset_count", 0) <= 0:
            fail(f"{rec_path.name}: composed doc is not backed by catalog assets "
                 f"(atlas claim with no code behind it)")

    # ---- Tooth E: composed scope is present in the roster ----------------
    if not ROSTER.exists():
        fail(f"estate roster missing at {ROSTER} — cannot cross-check composed scope")
    roster = json.loads(ROSTER.read_text("utf-8"))
    roster_keys = {r["full_name"].split("/", 1)[-1].lower() for r in roster.get("repos", [])}
    manifest = json.loads((SELFDOC / "index.json").read_text("utf-8"))
    scope = [r["short"] for r in manifest.get("repos", [])]
    not_in_roster = sorted(s for s in scope if s not in roster_keys)
    if not_in_roster:
        fail(f"composed repos absent from the cross-org roster (roster/self-doc "
             f"disagree): {not_in_roster} — re-run enumerate_estate.py")

    print(f"OK self-documentation: {len(scope)} atlas repos code-derived and "
          f"byte-identical to a fresh regenerate from catalog@"
          f"{(pin.get('catalog_commit') or '?')[:12]}; all catalog-backed; all in roster.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
