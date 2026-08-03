#!/usr/bin/env python3
"""Compose code-derived self-documentation into the Boundary Atlas.

Self-documenting-estate, step 2 (COMPOSE). SocioSphere is the composition hub:
it does not hand-author repo documentation, it *derives* it from the code. This
tool reads the code-derived catalog (built by prophet-core-catalog's extractors
from the code itself) and the SocioSphere Boundary Atlas, and for every Atlas repo
that the catalog actually covers it emits:

  * a per-repo documentation RECORD grounded in real code assets
    (schemas / services / ADRs / agents / models / policies / vocab), the
    estate-graph provenance, and the repo's glossary terms;
  * a cross-repo LINK view (which repo's code references which) from the
    catalog's blast-radius / lineage edges.

Every field is derived from the catalog + estate-graph + Atlas. Nothing is typed
by hand, so nothing can rot: re-run and it re-derives. The drift canary
(`verify_self_documentation.py`) regenerates and byte-compares, so a stale
committed view fails CI.

Determinism: no timestamps in the composed records; all lists sorted; samples
capped. The only moving inputs are the pinned catalog + the Atlas, both hashed
into `catalog-pin.json`.

Outputs under --out (default artifacts/self-documentation/):
  catalog-pin.json            pinned catalog commit + sha256 of every consumed input
  index.json                  scope + per-repo summary (the composed manifest)
  repos/<short>.json          per-repo code-derived documentation record
  cross-repo-links.json       repo->repo reference graph (from catalog edges)

Usage:
  tools/compose_self_documentation.py --catalog PATH [--out DIR]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
ATLAS = ROOT / "catalog" / "boundaries.yaml"
DEFAULT_OUT = ROOT / "artifacts" / "self-documentation"

SAMPLE_ASSETS = 12          # capped per-repo asset sample
SAMPLE_TERMS = 20           # capped per-repo glossary terms
CATALOG_REPO = "SocioProphet/prophet-core-catalog"


def short(full_name: str) -> str:
    return full_name.split("/", 1)[-1].lower()


def github_repo_path(url: str) -> str | None:
    """'org/repo…' IFF url's host is exactly github.com, else None. A substring test
    (`"github.com/" in url`) matches `https://evil.example/github.com/x`
    (CodeQL py/incomplete-url-substring-sanitization) — parse and compare the host."""
    if not url:
        return None
    u = url.strip()
    if u.startswith("git@github.com:"):
        return u[len("git@github.com:"):].removesuffix(".git") or None
    if "://" not in u:
        u = "https://" + u
    parsed = urlparse(u)
    if (parsed.hostname or "").lower() != "github.com":
        return None
    return parsed.path.lstrip("/").removesuffix(".git") or None


def sha256_file(p: Path) -> str:
    return "sha256:" + hashlib.sha256(p.read_bytes()).hexdigest()


def load_jsonl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    out = []
    for line in p.read_text("utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def parse_estate_graph(ttl: Path) -> dict[str, dict]:
    """Parse catalog-entry blocks -> short-key -> provenance fields (stdlib only)."""
    if not ttl.exists():
        return {}
    text = ttl.read_text("utf-8")
    out = {}
    # blocks start with `ent:<name> a cat:CatalogEntry ;` and end at the next `.`
    for m in re.finditer(r"ent:([^\s]+)\s+a\s+cat:CatalogEntry\s*;(.*?)\.\s", text, re.S):
        body = m.group(2)

        def field(name):
            fm = re.search(rf'{name}\s+"([^"]*)"', body)
            return fm.group(1) if fm else None

        prov = field("cat:provenanceRef")
        prov_path = github_repo_path(prov) if prov else None
        key = short(prov_path) if prov_path else m.group(1).lower()
        out[key] = {
            "catalog_source_id": field("cat:catalogId"),
            "owner": field("cat:owner"),
            "status": field("cat:status"),
            "title": field("dct:title"),
            "license": field("dct:license"),
            "provenance_ref": prov,
        }
    return out


def catalog_commit(catalog: Path) -> str | None:
    r = subprocess.run(["git", "-C", str(catalog), "rev-parse", "HEAD"],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def resolve_repo(token: str, asset_repo: dict, known: set) -> str | None:
    """Resolve an edge endpoint to a repo short-key, if it is one."""
    if token in asset_repo:            # endpoint is an asset id
        return asset_repo[token]
    seg = token.split("/", 1)[0].lower()  # endpoint is "repo/file" or "repo"
    return seg if seg in known else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--catalog", required=True,
                    help="path to a prophet-core-catalog checkout (the code-derived catalog)")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    if not yaml:
        sys.exit("ERR: pyyaml required (pip install pyyaml)")
    catalog = Path(args.catalog).resolve()
    if not catalog.exists():
        sys.exit(f"ERR: catalog checkout not found: {catalog}")
    out = Path(args.out)

    idx_dir = catalog / "catalog-index"
    eg_dir = catalog / "datasets" / "estate-graph"
    inputs = {
        "atlas": ATLAS,
        "assets": idx_dir / "assets.jsonl",
        "edges": idx_dir / "edges.jsonl",
        "glossary": idx_dir / "glossary.jsonl",
        "index": idx_dir / "index.json",
        "estate_graph": eg_dir / "estate-graph.ttl",
        "estate_edges": eg_dir / "estate-edges.ttl",
    }
    for k, p in inputs.items():
        if not p.exists():
            sys.exit(f"ERR: required input missing: {k} -> {p}")

    atlas = yaml.safe_load(ATLAS.read_text("utf-8")) or {}
    entries = {short(e["repo"]): e for e in atlas.get("entries", []) if e.get("repo")}

    assets = load_jsonl(inputs["assets"])
    edges = load_jsonl(inputs["edges"])
    glossary = load_jsonl(inputs["glossary"])
    prov = parse_estate_graph(inputs["estate_graph"])

    # index assets by repo
    by_repo: dict[str, list[dict]] = defaultdict(list)
    asset_repo: dict[str, str] = {}
    for a in assets:
        r = a.get("repo")
        if isinstance(r, str) and r and r != "__union__":
            by_repo[r.lower()].append(a)
        if a.get("asset_id") and isinstance(r, str) and r:
            asset_repo[a["asset_id"]] = r.lower()
    known_repos = set(by_repo)

    # glossary terms by repo
    gloss_by_repo: dict[str, list[str]] = defaultdict(list)
    for g in glossary:
        for r in (g.get("repos") or []):
            if isinstance(r, str) and g.get("name"):
                gloss_by_repo[r.lower()].append(g["name"])

    # scope = Atlas repos the catalog actually covers (code-derived backing exists)
    scope = sorted(k for k in entries if by_repo.get(k))

    # ---- per-repo composed documentation records --------------------------
    repos_dir = out / "repos"
    repos_dir.mkdir(parents=True, exist_ok=True)
    # clear stale per-repo files so a removed repo cannot linger
    for old in repos_dir.glob("*.json"):
        old.unlink()

    summary = []
    for key in scope:
        e = entries[key]
        ras = by_repo[key]
        by_kind = Counter(a.get("kind") or a.get("dataset") for a in ras)
        datasets = sorted({a.get("dataset") for a in ras if a.get("dataset")})
        sample = sorted(
            ({"asset_id": a.get("asset_id"), "name": a.get("name"),
              "kind": a.get("kind"), "dataset": a.get("dataset"),
              "path": a.get("path")} for a in ras),
            key=lambda x: (str(x.get("dataset")), str(x.get("name"))))[:SAMPLE_ASSETS]
        terms = sorted(set(gloss_by_repo.get(key, [])))[:SAMPLE_TERMS]

        record = {
            "schema": "self-documentation-record/v0.1",
            "repo": e["repo"],
            "short": key,
            "atlas_backed": True,
            "boundary": {
                "boundary_class": e.get("boundary_class"),
                "jurisdiction": e.get("jurisdiction"),
                "maturity": e.get("maturity"),
                "claim_modes": e.get("claim_modes") or [],
                "current_status": e.get("current_status"),
                "owned_artifacts": e.get("owned_artifacts") or [],
            },
            "provenance": prov.get(key, {}),
            "catalog": {
                "asset_count": len(ras),
                "datasets": datasets,
                "by_kind": dict(sorted(by_kind.items(), key=lambda x: (-x[1], str(x[0])))),
                "glossary_term_count": len(set(gloss_by_repo.get(key, []))),
                "sample_assets": sample,
            },
            "glossary_terms": terms,
        }
        (repos_dir / f"{key}.json").write_text(
            json.dumps(record, indent=2, ensure_ascii=False, sort_keys=True) + "\n", "utf-8")
        summary.append({
            "short": key, "repo": e["repo"],
            "boundary_class": e.get("boundary_class"),
            "maturity": e.get("maturity"),
            "asset_count": len(ras),
            "datasets": len(datasets),
            "glossary_terms": record["catalog"]["glossary_term_count"],
        })

    # ---- cross-repo link view --------------------------------------------
    pair_counts: Counter = Counter()
    for ed in edges:
        fr = asset_repo.get(ed.get("from"))
        if not fr:
            continue
        to = resolve_repo(ed.get("to") or "", asset_repo, known_repos)
        if to and to != fr:
            pair_counts[(fr, to)] += 1
    scope_set = set(scope)
    links = sorted(
        ({"from": a, "to": b, "count": n}
         for (a, b), n in pair_counts.items()
         if a in scope_set or b in scope_set),
        key=lambda x: (x["from"], x["to"]))
    cross = {
        "schema": "cross-repo-link-view/v0.1",
        "scope": scope,
        "note": ("repo->repo edges derived from catalog blast-radius / lineage; "
                 "restricted to edges touching a Boundary-Atlas repo."),
        "link_count": len(links),
        "links": links,
    }
    (out / "cross-repo-links.json").write_text(
        json.dumps(cross, indent=2, ensure_ascii=False, sort_keys=True) + "\n", "utf-8")

    # ---- pin + manifest ---------------------------------------------------
    pin = {
        "schema": "catalog-pin/v0.1",
        "composed_by": "tools/compose_self_documentation.py",
        "catalog_repo": CATALOG_REPO,
        "catalog_commit": catalog_commit(catalog),
        "inputs": {k: sha256_file(p) for k, p in sorted(inputs.items())},
    }
    (out / "catalog-pin.json").write_text(
        json.dumps(pin, indent=2, ensure_ascii=False, sort_keys=True) + "\n", "utf-8")

    manifest = {
        "schema": "self-documentation-index/v0.1",
        "composed_by": "tools/compose_self_documentation.py",
        "catalog_repo": CATALOG_REPO,
        "catalog_commit": pin["catalog_commit"],
        "atlas_entries": len(entries),
        "scope_repos": len(scope),
        "cross_repo_links": len(links),
        "repos": sorted(summary, key=lambda x: x["short"]),
    }
    (out / "index.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n", "utf-8")

    print(f"OK composed: {len(scope)}/{len(entries)} atlas repos code-derived, "
          f"{len(links)} cross-repo links, catalog@{(pin['catalog_commit'] or '?')[:12]} "
          f"-> {out}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
