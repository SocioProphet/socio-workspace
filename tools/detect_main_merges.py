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


def gh_json(path: str) -> tuple[str, Any]:
    """Returns (status, data) where status is ok | not_found | error.

    This used to return None for every failure, and the caller turned that into an
    empty commit list -- so a repository that DOES NOT EXIST was indistinguishable from
    one that simply had no merges in the window. Six of the fourteen trigger repos in
    change-propagation-rules.yaml are 404s, and the poller would have reported all of
    them as quiet, forever, with no signal that the rules point at nothing.

    Collapsing "I could not look" into "there was nothing" is the defect this whole
    effort keeps finding. Here it is again, so it gets a third state again.
    """
    proc = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    if proc.returncode != 0:
        err = proc.stderr.lower()
        if "not found" in err or "404" in err:
            return "not_found", None
        return "error", proc.stderr.strip()[:200]
    try:
        return "ok", json.loads(proc.stdout)
    except json.JSONDecodeError:
        return "error", "unparseable response"


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


def recent_commits(repo: str, since: dt.datetime,
                   branch: str) -> tuple[str, list[dict[str, Any]]]:
    status, data = gh_json(
        f"repos/{ORG}/{repo}/commits?sha={branch}&since={since.isoformat()}"
    )
    return status, (data if isinstance(data, list) else [])


def changed_files(repo: str, sha: str) -> list[str]:
    _, data = gh_json(f"repos/{ORG}/{repo}/commits/{sha}")
    if not isinstance(data, dict):
        return []
    return [f.get("filename", "") for f in data.get("files") or []]


def detect(window_minutes: int, branch: str,
           now: dt.datetime) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    since = now - dt.timedelta(minutes=window_minutes)
    fired: list[dict[str, Any]] = []
    #: Trigger repos that could not be observed at all. A rule keyed on a repository
    #: that does not exist is not dormant, it is broken, and it must not read as quiet.
    unobservable: list[dict[str, str]] = []

    for rule in trigger_rules():
        trig = rule["trigger"]
        repo = trig["repo"]
        status, commits = recent_commits(repo, since, branch)
        if status != "ok":
            # A 404 on the COMMITS endpoint has two very different causes: the repo does
            # not exist, or it exists without the branch we asked for. design-system is
            # the second -- a 2021-era repo whose default branch is not `main`. Labelling
            # it "does not exist" would be a false claim about a real repository, and the
            # fixes differ: delete the rule vs point it at the right branch.
            if status == "not_found":
                repo_status, _ = gh_json(f"repos/{ORG}/{repo}")
                status = "no_repo" if repo_status == "not_found" else "no_branch"
            unobservable.append({"repo": repo, "rule": rule.get("id", "?"),
                                 "status": status})
            continue
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
    return fired, unobservable


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
    fired, unobservable = detect(args.window, args.branch, now)

    if args.json:
        print(json.dumps({"window_minutes": args.window, "fired": fired,
                          "unobservable": unobservable}, indent=2))
        return 1 if unobservable else 0

    if fired:
        print(f"{len(fired)} trigger repo(s) merged in the last {args.window}m:")
        for f in fired:
            note = " (path-filtered)" if f["path_filtered"] else ""
            print(f"  {f['repo']}  rule={f['rule']}  {f['commits']} commit(s){note}")
    else:
        print(f"no trigger repo merged to {args.branch} in the last {args.window}m")

    if unobservable:
        missing = [u for u in unobservable if u["status"] == "no_repo"]
        nobranch = [u for u in unobservable if u["status"] == "no_branch"]
        errored = [u for u in unobservable
                   if u["status"] not in ("no_repo", "no_branch")]
        print(f"\n{len(unobservable)} trigger repo(s) COULD NOT BE OBSERVED — these did "
              "not report 'no merges', they reported nothing at all:", file=sys.stderr)
        for u in missing:
            print(f"  NO SUCH REPO    {u['repo']:<34} (rule {u['rule']})", file=sys.stderr)
        for u in nobranch:
            print(f"  no '{args.branch}' branch {u['repo']:<28} (rule {u['rule']}) "
                  "— repo exists; the rule targets a branch it does not have",
                  file=sys.stderr)
        for u in errored:
            print(f"  unreadable      {u['repo']:<34} (rule {u['rule']})", file=sys.stderr)
        if missing:
            print("\nA rule keyed on a repository that does not exist can never fire. "
                  "Either the repo was renamed or never created, or the rule is stale — "
                  "fix change-propagation-rules.yaml.", file=sys.stderr)
        if nobranch:
            print("A rule targeting a branch the repo does not have can never fire "
                  "either, but the repo is real — correct the branch, do not delete "
                  "the rule.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
