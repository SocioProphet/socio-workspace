#!/usr/bin/env python3
"""Heal GitHub -> Gitea drift — the actuation half of SCM sovereignty.

`check_scm_drift.py` (sociosphere#624) DETECTS that Gitea (canonical, no longer pulls) has fallen
behind GitHub. But detection is not repair: Gitea stays wrong until something pushes the missing
commits. This is that something — and it is deliberately SAFE:

  * IN SYNC            -> nothing to do.
  * BEHIND (fast-fwd)  -> Gitea's head is an ancestor of GitHub's -> push GitHub's branch to Gitea.
                          A pure fast-forward: it only ADDS the commits Gitea was missing.
  * DIVERGED (conflict) -> the heads are unrelated (someone wrote to Gitea directly) -> STOP and
                          escalate. Never force-overwrite the golden repo; a real fork is a human call.
  * GITEA MISSING repo  -> report, don't auto-create (repo creation on the canonical host is a human
                          decision).
  * UNREADABLE (no token) -> SKIP CLEAN, exit 0. Unconfigured is not a failure — it must not turn the
                          gate red; it just means "not wired here yet".

Pairs with #624: detect finds it, this fixes it, and running it on every merge PREVENTS drift.
Env: GITEA_URL, GITEA_TOKEN (write scope), ORG (default SocioProphet). Read from CI-minted secrets.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from typing import Callable, Optional, Tuple

GITEA_URL = os.environ.get("GITEA_URL", "").rstrip("/")
GITEA_TOKEN = os.environ.get("GITEA_TOKEN", "")
ORG = os.environ.get("ORG", "SocioProphet")

Run = Callable[[list], Tuple[int, str]]

IN_SYNC, BEHIND_FF, DIVERGED, GITEA_MISSING, UNKNOWN, HEALED, PUSH_FAILED = (
    "in_sync", "behind_ff", "diverged_conflict", "gitea_missing", "unknown", "healed", "push_failed")


def _run(args: list) -> Tuple[int, str]:
    p = subprocess.run(args, capture_output=True, text=True)
    return p.returncode, (p.stdout or p.stderr).strip()


def github_head(repo: str, branch: str, *, run: Run = _run) -> Optional[str]:
    rc, out = run(["gh", "api", f"repos/{ORG}/{repo}/commits/{branch}", "--jq", ".sha"])
    return out if rc == 0 and out else None


def gitea_head(repo: str, branch: str) -> Tuple[Optional[str], str]:
    """(sha, status) — status is one of ok / missing / unauth / error."""
    if not GITEA_TOKEN or not GITEA_URL:
        return None, "unauth"
    req = urllib.request.Request(
        f"{GITEA_URL}/api/v1/repos/{ORG}/{repo}/commits?limit=1&sha={branch}",
        headers={"Authorization": f"token {GITEA_TOKEN}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
            return (data[0]["sha"] if data else None), "ok"
    except urllib.error.HTTPError as e:
        return None, "missing" if e.code == 404 else f"http{e.code}"
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None, "error"


def classify(gh: Optional[str], gt: Optional[str], gt_status: str, ff_safe: bool) -> str:
    """Pure decision: what to do given the two heads. ``ff_safe`` = is Gitea's head an ancestor of
    GitHub's (so a fast-forward is safe)? Only meaningful when both heads exist and differ."""
    if gt_status in ("unauth", "error"):
        return UNKNOWN
    if gt_status == "missing" or gt is None:
        return GITEA_MISSING
    if gh is None:
        return UNKNOWN
    if gh == gt:
        return IN_SYNC
    return BEHIND_FF if ff_safe else DIVERGED


def reconcile_repo(repo: str, branch: str = "main", *, run: Run = _run,
                   gh: Optional[str] = None, gt: Optional[str] = None,
                   gt_status: Optional[str] = None) -> str:
    """Reconcile one repo. Returns a status: healed / in_sync / diverged_conflict / gitea_missing /
    unknown / push_failed. Fast-forward only — never force. Injectables let tests skip real git."""
    if gh is None:
        gh = github_head(repo, branch, run=run)
    if gt_status is None:
        gt, gt_status = gitea_head(repo, branch)
    if gh is not None and gt is not None and gh != gt:
        # need history to decide ff vs conflict: clone GitHub, fetch the Gitea head, test ancestry.
        work = tempfile.mkdtemp()
        gh_url = f"https://github.com/{ORG}/{repo}.git"
        gt_url = f"{GITEA_URL.replace('https://', f'https://token:{GITEA_TOKEN}@')}/{ORG}/{repo}.git"
        run(["git", "clone", "--quiet", gh_url, work])
        run(["git", "-C", work, "fetch", "--quiet", gt_url, gt])
        rc, _ = run(["git", "-C", work, "merge-base", "--is-ancestor", gt, gh])
        ff_safe = (rc == 0)
        state = classify(gh, gt, gt_status, ff_safe)
        if state == BEHIND_FF:
            prc, _ = run(["git", "-C", work, "push", gt_url, f"{gh}:refs/heads/{branch}"])
            return HEALED if prc == 0 else PUSH_FAILED
        return state
    return classify(gh, gt, gt_status or "ok", ff_safe=False)


def main() -> int:
    ap = argparse.ArgumentParser(description="Heal GitHub->Gitea drift (fast-forward only).")
    ap.add_argument("repos", nargs="*", default=["sociosphere"], help="repo names")
    ap.add_argument("--branch", default="main")
    args = ap.parse_args()

    if not GITEA_TOKEN or not GITEA_URL:
        print("GITEA_URL/GITEA_TOKEN unset — SKIP CLEAN (reconcile not wired here). exit 0")
        return 0  # unconfigured is not a failure; do not turn the gate red

    conflicts = 0
    for repo in (args.repos or ["sociosphere"]):
        st = reconcile_repo(repo, args.branch)
        mark = {"healed": "HEALED", "in_sync": "in sync", "diverged_conflict": "CONFLICT",
                "gitea_missing": "gitea missing repo", "unknown": "unreadable",
                "push_failed": "PUSH FAILED"}.get(st, st)
        print(f"  {ORG}/{repo}@{args.branch}: {mark}")
        if st in (DIVERGED, PUSH_FAILED):
            conflicts += 1
    if conflicts:
        print(f"\n{conflicts} repo(s) need a human — a true divergence/failure is never auto-forced.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
