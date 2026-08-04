#!/usr/bin/env python3
"""Gitea is canonical now and no longer pulls. Detect divergence before it compounds.

Until 2026-08-04 every Gitea repo was a pull-mirror: GitHub was authoritative and Gitea
followed within 8 hours. After the cutover that link is GONE. Gitea is the source of
truth, nothing syncs it, and a commit merged on GitHub is invisible here forever.

That is the intended direction, but it converts a previously impossible failure into a
likely one. The mirrors could not drift because they were read-only; two writable copies
with no sync absolutely can, and nothing would say so. This says so.

Three states, not two, for the same reason every other check in this repo grew one: a
repo that could not be READ is not a repo that AGREES. Reporting an unreachable repo as
"in sync" is how the mirrors looked healthy while holding month-old code.

  in_sync     both sides reachable, same HEAD
  drifted     both sides reachable, HEADs differ  -> someone wrote to one side only
  unknown     one or both sides could not be read -> says nothing about agreement

Read-only. It never pushes, never force-syncs, and never picks a winner: deciding which
side is right when both have commits is a human call, and an automated resolver would
silently discard work.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

ORG = os.environ.get("SOCIOSPHERE_ORG", "SocioProphet")
GITEA_URL = os.environ.get("GITEA_URL", "http://localhost:3111").rstrip("/")
GITEA_TOKEN = os.environ.get("GITEA_TOKEN", "")


def _run(args: list[str]) -> tuple[int, str]:
    p = subprocess.run(args, capture_output=True, text=True)
    return p.returncode, (p.stdout if p.returncode == 0 else p.stderr).strip()


def github_head(repo: str, branch: str) -> tuple[str, str]:
    rc, out = _run(["gh", "api", f"repos/{ORG}/{repo}/commits/{branch}", "--jq", ".sha"])
    if rc != 0:
        return ("missing", "") if "not found" in out.lower() else ("error", out[:120])
    return "ok", out.strip()[:40]


def gitea_head(repo: str, branch: str) -> tuple[str, str]:
    if not GITEA_TOKEN:
        return "error", "GITEA_TOKEN unset — cannot read the canonical side"
    import urllib.error
    import urllib.request
    req = urllib.request.Request(
        f"{GITEA_URL}/api/v1/repos/{ORG}/{repo}/commits?limit=1&sha={branch}",
        headers={"Authorization": f"token {GITEA_TOKEN}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode())
            return ("ok", data[0]["sha"][:40]) if data else ("error", "no commits")
    except urllib.error.HTTPError as e:
        return ("missing", "") if e.code == 404 else ("error", f"http {e.code}")
    except Exception as e:
        return "error", str(e)[:120]


def compare(repos: list[str], branch: str) -> list[dict[str, str]]:
    rows = []
    for repo in repos:
        gh_s, gh_v = github_head(repo, branch)
        gt_s, gt_v = gitea_head(repo, branch)
        if gh_s != "ok" or gt_s != "ok":
            state = "unknown"
        elif gh_v == gt_v:
            state = "in_sync"
        else:
            state = "drifted"
        rows.append({"repo": repo, "state": state, "github": gh_v or gh_s,
                     "gitea": gt_v or gt_s})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("repos", nargs="*", help="repo names; default: sociosphere")
    ap.add_argument("--branch", default="main")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    rows = compare(args.repos or ["sociosphere"], args.branch)
    drifted = [r for r in rows if r["state"] == "drifted"]
    unknown = [r for r in rows if r["state"] == "unknown"]

    if args.json:
        print(json.dumps({"rows": rows, "drifted": len(drifted),
                          "unknown": len(unknown)}, indent=2))
    else:
        for r in rows:
            mark = {"in_sync": "  ", "drifted": "!!", "unknown": "??"}[r["state"]]
            print(f"{mark} {r['repo']:<28} github={r['github'][:10]:<12} "
                  f"gitea={r['gitea'][:10]}")
        if drifted:
            print(f"\n{len(drifted)} repo(s) DRIFTED. Gitea is canonical and does not "
                  "pull, so a GitHub-side commit stays invisible until someone syncs it:\n"
                  '  git --git-dir=<repo>.git fetch origin "+refs/heads/*:refs/heads/*"\n'
                  "Check which side has the work first — this tool does not choose.",
                  file=sys.stderr)
        if unknown:
            print(f"{len(unknown)} repo(s) UNKNOWN — could not be read on one side. "
                  "That is not agreement.", file=sys.stderr)
    return 1 if drifted else 0


if __name__ == "__main__":
    sys.exit(main())
