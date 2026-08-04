#!/usr/bin/env python3
"""Find which trigger repos have merged to main recently, so propagation can fire.

This is the half that was missing. `propagate()` knows how to fan a merge out, but
nothing told it a merge had happened: the rules describe a signal that never arrived.

The obvious wiring -- a workflow in every trigger repo that dispatches to sociosphere --
needs a token with write access to *this* repo held in *those* repos. That means a PAT
or an App installation in 14 repositories, and the estate rule is that secrets are
minted in CI rather than carried as PATs. So the direction is inverted: sociosphere,
which owns the registry, also owns the trigger, and asks.

It is deliberately STATELESS. There is no watermark file to commit back, no cache to
warm and no artifact to expire -- it asks each trigger repo for commits on main inside a
lookback window and reports those. Correctness under double-fire comes from the
issue-title deduplication in the dispatcher, not from bookkeeping here. A stateless
poller that can safely repeat beats a stateful one whose state can be lost, and losing
the state of a governance signal is how the signal stops being trusted.

The window must exceed the poll interval or merges fall between runs; --window defaults
comfortably above the scheduled cadence, and overlap is harmless by construction.

`trigger.paths` is honoured where a rule declares it. Without that the schema rule would
fire on every commit to superconscious including README edits, and a notification that
arrives when nothing relevant changed teaches people to ignore notifications.
"""
from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "registry" / "change-propagation-rules.yaml"
ORG = os.environ.get("SOCIOSPHERE_ORG", "SocioProphet")

#: Must exceed the schedule interval in propagation-poll.yml, with margin for a slow or
#: retried run. Overlap re-reports a merge, which the dispatcher deduplicates.
DEFAULT_WINDOW_MINUTES = 90


def gh_json(path: str) -> Any:
    proc = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def trigger_rules() -> list[dict[str, Any]]:
    data = yaml.safe_load(RULES.read_text(encoding="utf-8")) or {}
    out = []
    for rule in data.get("rules") or []:
        repo = (rule.get("trigger") or {}).get("repo")
        if repo:
            out.append(rule)
    return out


def _matches_paths(files: list[str], patterns: list[str]) -> bool:
    for f in files:
        for pat in patterns:
            # fnmatch has no ** semantics; 'a/**' should match anything under a/.
            if fnmatch.fnmatch(f, pat) or (
                pat.endswith("/**") and f.startswith(pat[:-2])
            ):
                return True
    return False


def recent_commits(repo: str, since: dt.datetime, branch: str) -> list[dict[str, Any]]:
    data = gh_json(
        f"repos/{ORG}/{repo}/commits?sha={branch}&since={since.isoformat()}"
    )
    return data if isinstance(data, list) else []


def changed_files(repo: str, sha: str) -> list[str]:
    data = gh_json(f"repos/{ORG}/{repo}/commits/{sha}")
    if not isinstance(data, dict):
        return []
    return [f.get("filename", "") for f in data.get("files") or []]


def detect(window_minutes: int, branch: str, now: dt.datetime) -> list[dict[str, Any]]:
    since = now - dt.timedelta(minutes=window_minutes)
    fired: list[dict[str, Any]] = []

    for rule in trigger_rules():
        trig = rule["trigger"]
        repo = trig["repo"]
        commits = recent_commits(repo, since, branch)
        if not commits:
            continue

        patterns = trig.get("paths") or []
        matched_sha = commits[0].get("sha", "")
        if patterns:
            # Only inspect files when a rule actually constrains them -- one extra API
            # call per commit, and most rules do not need it.
            hit = None
            for c in commits:
                sha = c.get("sha", "")
                if _matches_paths(changed_files(repo, sha), patterns):
                    hit = sha
                    break
            if hit is None:
                continue
            matched_sha = hit

        fired.append({
            "repo": repo,
            "rule": rule.get("id"),
            "commits": len(commits),
            "sha": matched_sha,
            "path_filtered": bool(patterns),
        })
    return fired


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--window", type=int, default=DEFAULT_WINDOW_MINUTES,
                    help="lookback in minutes; must exceed the poll interval")
    ap.add_argument("--branch", default="main")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--now", help="override now (ISO) for tests")
    args = ap.parse_args()

    now = (dt.datetime.fromisoformat(args.now) if args.now
           else dt.datetime.now(tz=dt.timezone.utc))
    fired = detect(args.window, args.branch, now)

    if args.json:
        print(json.dumps({"window_minutes": args.window, "fired": fired}, indent=2))
        return 0

    if not fired:
        print(f"no trigger repo merged to {args.branch} in the last {args.window}m")
        return 0
    print(f"{len(fired)} trigger repo(s) merged in the last {args.window}m:")
    for f in fired:
        note = " (path-filtered)" if f["path_filtered"] else ""
        print(f"  {f['repo']}  rule={f['rule']}  {f['commits']} commit(s){note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
