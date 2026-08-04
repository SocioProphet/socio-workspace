#!/usr/bin/env python3
"""Discover SocioProphet org repos that are ABSENT from every registry surface.

Registration of a repo into the estate is manual, and the existing gates only
VALIDATE repos already in the register — nothing DISCOVERS a new org repo. This is
that missing half: it enumerates the live org via `gh`, loads the committed registry
surfaces, computes the set difference, and reports every repo the estate has not yet
registered. It is the drift detector for registration coverage.

It is deliberately the mirror image of `tools/enumerate_estate.py`: that tool writes
the authoritative roster and a coverage report; this one is a fail-closed GATE — it
exits non-zero when any unregistered repo exists, so CI (or a scheduled run) turns red
and says which repos need registering, instead of the gap staying invisible.

Registry surfaces treated as "registered" (a repo in ANY of these is covered):
  catalog/boundaries.yaml                                    Boundary Atlas entries
  catalog/proof-repo-roles.yaml                              proof role repositories
  registry/repo-governance-matrix-v0.yaml                    governance-class entries
  registry/canonical-repos.yaml                              canonical repo registry
  architecture/service-register/canonical-repo-estate.v1.0.csv  service-register estate
  .gitmodules                                                materialized submodules

Repos are matched by their canonical short key (lowercase repo name), so the same repo
counts as registered whether a surface names it `SocioProphet/Foo`, a git URL, or a bare
`foo`. Archived repos, forks, and an allowlist of repos governed elsewhere are excluded.

Enumeration needs the network + a `gh` token; it is a periodic/CI job, NOT part of the
drift canary. The `gh` runner is injectable so the discovery logic is unit-testable
without a live org.

Usage:
  tools/discover_unregistered_repos.py [--org ORG]... [--limit N]
                                       [--allow NAME]... [--json]
                                       [--out PATH] [--emit-register PATH]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path
from typing import Callable, Iterable, Optional
from urllib.parse import urlparse

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ORGS = ["SocioProphet"]

# Surfaces that constitute "registered". Missing files are tolerated (a surface may
# not exist in every checkout); each is parsed for the repo identifiers it carries.
BOUNDARIES = ROOT / "catalog" / "boundaries.yaml"
PROOF_ROLES = ROOT / "catalog" / "proof-repo-roles.yaml"
GOV_MATRIX = ROOT / "registry" / "repo-governance-matrix-v0.yaml"
CANONICAL_REPOS = ROOT / "registry" / "canonical-repos.yaml"
SERVICE_REGISTER_ESTATE = (
    ROOT / "architecture" / "service-register" / "canonical-repo-estate.v1.0.csv"
)
GITMODULES = ROOT / ".gitmodules"
ALLOWLIST = ROOT / "registry" / "discovery-allowlist.yaml"

# Runner takes an argv list and returns (returncode, stdout, stderr) — injectable so
# tests replay a recorded `gh` response instead of touching the network.
Runner = Callable[..., "RunResult"]


class RunResult:
    __slots__ = ("returncode", "stdout", "stderr")

    def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _subprocess_runner(argv) -> RunResult:
    proc = subprocess.run(argv, capture_output=True, text=True)
    return RunResult(proc.returncode, proc.stdout, proc.stderr)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def short(full_name: str) -> str:
    """`org/Repo`, a git URL, or a bare name -> canonical short key (lowercase name)."""
    s = (full_name or "").strip()
    if not s:
        return ""
    # scp-style ssh: git@host:org/repo.git (covers git@github.com and git@github-443)
    if "@" in s and ":" in s and "://" not in s:
        s = s.split(":", 1)[1]
    elif "://" in s:
        s = urlparse(s).path
    s = s.rstrip("/").removesuffix(".git")
    return s.split("/")[-1].lower()


def list_org_repos(org: str, *, limit: int = 500, runner: Runner = _subprocess_runner) -> list[dict]:
    """All repos for an org via `gh repo list --json name,url,isArchived,isFork`."""
    argv = [
        "gh", "repo", "list", org,
        "--limit", str(limit),
        "--json", "name,url,isArchived,isFork",
    ]
    res = runner(argv)
    if res.returncode != 0:
        raise RuntimeError(f"gh repo list failed for {org}: {res.stderr.strip()}")
    try:
        raw = json.loads(res.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"gh repo list returned non-JSON for {org}: {exc}")
    repos = []
    for r in raw:
        name = r.get("name") or ""
        repos.append({
            "full_name": f"{org}/{name}",
            "org": org,
            "name": name,
            "url": r.get("url") or f"https://github.com/{org}/{name}",
            "archived": bool(r.get("isArchived")),
            "fork": bool(r.get("isFork")),
        })
    return repos


def _load_yaml(path: Path):
    if not (path.exists() and yaml):
        return None
    return yaml.safe_load(path.read_text("utf-8"))


def load_registered_keys(root: Optional[Path] = None) -> set[str]:
    """Union of short keys named by every committed registry surface under *root*."""
    root = root or ROOT
    keys: set[str] = set()

    boundaries = _load_yaml(root / "catalog" / "boundaries.yaml") or {}
    for entry in boundaries.get("entries", []) or []:
        if entry.get("repo"):
            keys.add(short(entry["repo"]))

    proof_roles = _load_yaml(root / "catalog" / "proof-repo-roles.yaml") or {}
    for role in (proof_roles.get("roles") or {}).values():
        for repo in (role or {}).get("repositories", []) or []:
            keys.add(short(repo))

    matrix = _load_yaml(root / "registry" / "repo-governance-matrix-v0.yaml") or {}
    for repo in matrix.get("repositories", []) or []:
        if repo.get("name"):
            keys.add(short(repo["name"]))

    canonical = _load_yaml(root / "registry" / "canonical-repos.yaml") or {}
    for repo in canonical.get("repositories", []) or []:
        keys.add(short(repo.get("url") or repo.get("name") or ""))
    for repo in canonical.get("repos", []) or []:
        keys.add(short(repo.get("name") or ""))

    estate_csv = root / "architecture" / "service-register" / "canonical-repo-estate.v1.0.csv"
    if estate_csv.exists():
        import csv
        with estate_csv.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                if row.get("repo_full_name"):
                    keys.add(short(row["repo_full_name"]))

    gitmodules = root / ".gitmodules"
    if gitmodules.exists():
        for line in gitmodules.read_text("utf-8").splitlines():
            line = line.strip()
            if line.startswith("url"):
                keys.add(short(line.split("=", 1)[1]))

    keys.discard("")
    return keys


def load_allowlist(root: Optional[Path] = None, extra: Optional[Iterable[str]] = None) -> set[str]:
    """Short keys of repos deliberately governed elsewhere / out of registration scope."""
    root = root or ROOT
    allow: set[str] = set()
    data = _load_yaml(root / "registry" / "discovery-allowlist.yaml") or {}
    for name in data.get("allow", []) or []:
        allow.add(short(name))
    for name in extra or []:
        allow.add(short(name))
    allow.discard("")
    return allow


def compute_unregistered(
    org_repos: list[dict],
    registered: set[str],
    allowlist: Optional[set[str]] = None,
) -> list[dict]:
    """Repos that are live, not archived, not a fork, not registered, not allowlisted."""
    allowlist = allowlist or set()
    out = []
    for r in org_repos:
        if r.get("archived") or r.get("fork"):
            continue
        key = short(r.get("name") or r.get("full_name") or "")
        if not key or key in registered or key in allowlist:
            continue
        out.append(r)
    return sorted(out, key=lambda r: r["full_name"].lower())


def discover(
    orgs: Iterable[str],
    *,
    root: Optional[Path] = None,
    limit: int = 500,
    runner: Runner = _subprocess_runner,
    extra_allow: Optional[Iterable[str]] = None,
) -> dict:
    """Enumerate *orgs*, diff against the registry surfaces, and build a report dict."""
    root = root or ROOT
    orgs = list(orgs)
    registered = load_registered_keys(root)
    allowlist = load_allowlist(root, extra_allow)

    all_repos: list[dict] = []
    per_org: dict[str, int] = {}
    for org in orgs:
        repos = list_org_repos(org, limit=limit, runner=runner)
        per_org[org] = len(repos)
        all_repos.extend(repos)

    unregistered = compute_unregistered(all_repos, registered, allowlist)
    return {
        "generated_by": "tools/discover_unregistered_repos.py",
        "generated_at": now_iso(),
        "orgs": orgs,
        "counts": {
            "org_total": len(all_repos),
            "per_org": per_org,
            "registered_surface_keys": len(registered),
            "allowlisted": len(allowlist),
            "unregistered": len(unregistered),
        },
        "unregistered": [
            {"repo": r["full_name"], "url": r["url"]} for r in unregistered
        ],
    }


def build_register(report: dict) -> dict:
    """Machine-owned stub register: one entry per unregistered repo, for a human PR."""
    return {
        "schema_version": "0.1",
        "generated_by": report["generated_by"],
        "generated_at": report["generated_at"],
        "note": (
            "Auto-generated backlog of SocioProphet org repos absent from every "
            "registry surface. Each entry is a stub to be promoted into the Boundary "
            "Atlas (catalog/boundaries.yaml), the governance matrix "
            "(registry/repo-governance-matrix-v0.yaml), and — via SocioProphet/"
            "workspace-inventory upstream — the service-register estate."
        ),
        "orgs": report["orgs"],
        "repos": [
            {
                "repo": u["repo"],
                "url": u["url"],
                "status": "unregistered",
                "discovered_at": report["generated_at"],
                "proposed_surfaces": [
                    "catalog/boundaries.yaml",
                    "registry/repo-governance-matrix-v0.yaml",
                    "SocioProphet/workspace-inventory (service-register upstream)",
                ],
            }
            for u in report["unregistered"]
        ],
    }


def render_text(report: dict) -> str:
    c = report["counts"]
    lines = [
        f"discover-unregistered-repos: {c['org_total']} org repos across "
        f"{len(report['orgs'])} orgs "
        f"({', '.join(f'{o}={n}' for o, n in c['per_org'].items())}); "
        f"registered_surface_keys={c['registered_surface_keys']} "
        f"allowlisted={c['allowlisted']}",
    ]
    if report["unregistered"]:
        lines.append(f"UNREGISTERED ({c['unregistered']}):")
        lines.extend(f"  - {u['repo']}  {u['url']}" for u in report["unregistered"])
    else:
        lines.append("OK: no unregistered repos — every org repo is on a registry surface")
    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--org", action="append", dest="orgs", default=None,
                    help=f"org to scan (repeatable; default {DEFAULT_ORGS})")
    ap.add_argument("--limit", type=int, default=500, help="max repos per org (gh --limit)")
    ap.add_argument("--allow", action="append", dest="allow", default=None,
                    help="extra repo to allowlist (repeatable)")
    ap.add_argument("--json", action="store_true", help="emit the report as JSON on stdout")
    ap.add_argument("--out", default=None, help="write the JSON report to PATH")
    ap.add_argument("--emit-register", default=None,
                    help="write the machine-owned stub register (YAML) to PATH")
    args = ap.parse_args(argv)

    orgs = args.orgs or DEFAULT_ORGS
    try:
        report = discover(orgs, limit=args.limit, extra_allow=args.allow)
    except RuntimeError as exc:
        print(f"discover-unregistered-repos: ERROR: {exc}", file=sys.stderr)
        return 2

    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", "utf-8")
    if args.emit_register:
        if not yaml:  # pragma: no cover
            print("discover-unregistered-repos: ERROR: pyyaml required for --emit-register", file=sys.stderr)
            return 2
        Path(args.emit_register).write_text(
            yaml.safe_dump(build_register(report), sort_keys=False, allow_unicode=True), "utf-8")

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(render_text(report))

    # Fail-closed: any unregistered repo is drift the estate must act on.
    return 1 if report["unregistered"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
