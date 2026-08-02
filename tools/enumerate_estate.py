#!/usr/bin/env python3
"""Enumerate the cross-org SocioProphet estate — the authoritative repo roster.

Self-documenting-estate, step 1 (ENUMERATE). Lists every repository across the
three estate orgs via the GitHub API (`gh api`), annotates each with any role /
jurisdiction we can already infer from committed governance surfaces (the Boundary
Atlas `catalog/boundaries.yaml`, the workspace manifest `manifest/workspace.toml`,
and — when a catalog checkout is provided — the code-derived catalog `sources/`),
and reconciles the three views so *coverage gaps* (a repo in one surface but not
another) become data, not surprises.

Outputs (committed):
  registry/estate-roster.json           authoritative cross-org repo list
  registry/estate-roster.coverage.json  reconciliation / coverage-gap report

Enumeration needs the network + a `gh` token; it is a periodic job, NOT part of
the drift canary. Deterministic given a fixed API response (repos sorted by
full_name; the only non-deterministic field is `generated_at`).

Usage:
  tools/enumerate_estate.py [--catalog PATH] [--orgs org[,org...]]
                            [--out-roster PATH] [--out-coverage PATH]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

try:
    import tomllib  # py3.11+
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ORGS = ["SocioProphet", "SourceOS-Linux", "SociOS-Linux"]
ATLAS = ROOT / "catalog" / "boundaries.yaml"
WORKSPACE = ROOT / "manifest" / "workspace.toml"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def short(full_name: str) -> str:
    """org/Repo -> canonical short key (lowercase repo name)."""
    return full_name.split("/", 1)[-1].lower()


def gh_repos(org: str) -> list[dict]:
    """All repos for an org via `gh api --paginate`. One object per line."""
    cmd = [
        "gh", "api", "--paginate",
        f"orgs/{org}/repos?per_page=100&type=all",
        "--jq",
        ".[] | {full_name,name,private,archived,fork,visibility,"
        "default_branch,pushed_at,description,license:(.license.spdx_id)}",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"ERR: gh api failed for org {org}: {r.stderr.strip()}")
    out = []
    for line in r.stdout.splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def load_atlas() -> dict[str, dict]:
    """short-key -> {boundary_class, jurisdiction, maturity} from the Boundary Atlas."""
    if not (ATLAS.exists() and yaml):
        return {}
    data = yaml.safe_load(ATLAS.read_text("utf-8")) or {}
    out = {}
    for e in data.get("entries", []):
        repo = e.get("repo")
        if not repo:
            continue
        out[short(repo)] = {
            "boundary_class": e.get("boundary_class"),
            "jurisdiction": e.get("jurisdiction"),
            "maturity": e.get("maturity"),
        }
    return out


def load_workspace_roles() -> dict[str, str]:
    """short-key -> role from the workspace manifest."""
    if not (WORKSPACE.exists() and tomllib):
        return {}
    data = tomllib.loads(WORKSPACE.read_text("utf-8"))
    out = {}
    for r in data.get("repos", []):
        url = r.get("url") or ""
        if "github.com/" in url:
            out[short(url.split("github.com/", 1)[1])] = r.get("role")
    return out


def load_catalog_sources(catalog: Path | None) -> dict[str, str]:
    """short-key -> catalog source id, from a catalog checkout's sources/."""
    if not catalog:
        return {}
    out = {}
    for sf in sorted((catalog / "sources").glob("src.*.json")):
        try:
            s = json.loads(sf.read_text("utf-8"))
        except json.JSONDecodeError:
            continue
        prov = s.get("provider") or ""
        if "/" in prov:
            out[short(prov)] = s.get("id")
    return out


def load_catalog_asset_counts(catalog: Path | None) -> dict[str, int]:
    """short-key -> number of code-derived catalog assets for that repo."""
    if not catalog:
        return {}
    idx = catalog / "catalog-index" / "assets.jsonl"
    if not idx.exists():
        return {}
    counts: dict[str, int] = {}
    for line in idx.read_text("utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            a = json.loads(line)
        except json.JSONDecodeError:
            continue
        repo = a.get("repo")
        if isinstance(repo, str) and repo and repo != "__union__":
            counts[repo.lower()] = counts.get(repo.lower(), 0) + 1
    return counts


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--orgs", default=",".join(DEFAULT_ORGS))
    ap.add_argument("--catalog", default=None,
                    help="path to a prophet-core-catalog checkout for reconciliation")
    ap.add_argument("--out-roster", default=str(ROOT / "registry" / "estate-roster.json"))
    ap.add_argument("--out-coverage",
                    default=str(ROOT / "registry" / "estate-roster.coverage.json"))
    args = ap.parse_args()

    orgs = [o.strip() for o in args.orgs.split(",") if o.strip()]
    catalog = Path(args.catalog).resolve() if args.catalog else None

    atlas = load_atlas()
    ws_roles = load_workspace_roles()
    cat_sources = load_catalog_sources(catalog)
    cat_assets = load_catalog_asset_counts(catalog)

    repos = []
    per_org = {}
    for org in orgs:
        raw = gh_repos(org)
        per_org[org] = len(raw)
        for r in raw:
            key = short(r["full_name"])
            a = atlas.get(key, {})
            repos.append({
                "full_name": r["full_name"],
                "org": org,
                "name": r.get("name"),
                "private": bool(r.get("private")),
                "archived": bool(r.get("archived")),
                "fork": bool(r.get("fork")),
                "visibility": r.get("visibility"),
                "default_branch": r.get("default_branch"),
                "pushed_at": r.get("pushed_at"),
                "description": r.get("description"),
                "license": r.get("license"),
                # inferred jurisdiction / role from governance surfaces
                "role": ws_roles.get(key) or a.get("boundary_class"),
                "boundary_class": a.get("boundary_class"),
                "jurisdiction": a.get("jurisdiction"),
                "maturity": a.get("maturity"),
                "in_boundary_atlas": key in atlas,
                "in_workspace_manifest": key in ws_roles,
                "in_catalog_sources": key in cat_sources,
                "catalog_source_id": cat_sources.get(key),
                "catalog_asset_count": cat_assets.get(key, 0),
            })
    repos.sort(key=lambda x: x["full_name"].lower())

    roster = {
        "generated_by": "tools/enumerate_estate.py",
        "generated_at": now_iso(),
        "orgs": orgs,
        "catalog_reconciled": catalog is not None,
        "counts": {
            "total": len(repos),
            "per_org": per_org,
            "in_boundary_atlas": sum(r["in_boundary_atlas"] for r in repos),
            "in_workspace_manifest": sum(r["in_workspace_manifest"] for r in repos),
            "in_catalog_sources": sum(r["in_catalog_sources"] for r in repos),
            "cataloged_with_assets": sum(r["catalog_asset_count"] > 0 for r in repos),
        },
        "repos": repos,
    }

    roster_keys = {short(r["full_name"]) for r in repos}
    coverage = {
        "generated_by": "tools/enumerate_estate.py",
        "generated_at": roster["generated_at"],
        "orgs": orgs,
        "totals": roster["counts"],
        "gaps": {
            # governance surfaces should be a subset of the live estate
            "workspace_manifest_not_in_roster": sorted(k for k in ws_roles if k not in roster_keys),
            "boundary_atlas_not_in_roster": sorted(k for k in atlas if k not in roster_keys),
            "catalog_sources_not_in_roster": sorted(k for k in cat_sources if k not in roster_keys),
            # Atlas repos with a jurisdiction claim but no code-derived catalog assets yet
            "atlas_without_catalog_coverage": sorted(
                k for k in atlas if cat_assets.get(k, 0) == 0),
            # the long tail: live repos the code-catalog has not yet harvested
            "roster_not_in_catalog_sources_count":
                sum(1 for k in roster_keys if k not in cat_sources),
        },
    }
    # bounded sample of the long tail so the report stays reviewable
    tail = sorted(k for k in roster_keys if k not in cat_sources)
    coverage["gaps"]["roster_not_in_catalog_sources_sample"] = tail[:50]

    Path(args.out_roster).write_text(
        json.dumps(roster, indent=2, ensure_ascii=False) + "\n", "utf-8")
    Path(args.out_coverage).write_text(
        json.dumps(coverage, indent=2, ensure_ascii=False) + "\n", "utf-8")

    c = roster["counts"]
    print(f"OK roster: {c['total']} repos across {len(orgs)} orgs "
          f"({', '.join(f'{o}={n}' for o, n in per_org.items())}); "
          f"atlas={c['in_boundary_atlas']} manifest={c['in_workspace_manifest']} "
          f"catalog_sources={c['in_catalog_sources']} cataloged_with_assets="
          f"{c['cataloged_with_assets']}")
    print(f"   coverage gaps -> {args.out_coverage}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
