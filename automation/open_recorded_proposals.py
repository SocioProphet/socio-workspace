"""Drain recorded self-heal proposals and open them as fix PRs (credentialed context).

The daemon records proposals with no credentials; this runs where credentials exist (a
gated CI job) and opens each recorded proposal as a human-reviewable PR via
:func:`automation.pr_opener.open_pr`. It is the bridge that makes "the next red opens its
own fix PR" true without giving the always-on daemon any power to act.

Fail-closed and bounded: a proposal that fails to open is re-queued for the next run so a
transient credential/network blip self-corrects — but after ``MAX_ATTEMPTS`` it is moved to
a dead-letter queue and the run fails loudly. Silent infinite retry is exactly the
"retry masquerades as a fix" trap this whole effort exists to kill.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, List, Optional

from automation.durable_queue import DurableQueue, state_dir
from automation.pr_opener import open_pr
from automation.self_heal import remediate_via_pr

MAX_ATTEMPTS = 3


def _repo_toplevel() -> Path:
    proc = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return Path(proc.stdout.strip()) if proc.returncode == 0 else Path.cwd()


def clone_target(repo: str, workdir: Path) -> Path:
    """Clone ``owner/name`` into *workdir* using GITHUB_TOKEN; return the checkout path.

    A proposal can target any estate repo, so the opener needs that repo's checkout —
    not the automation image the drainer runs in. Token is passed via the URL only for
    the clone and never written to disk (git stores no credential from an https URL).
    """
    token = os.environ.get("GITHUB_TOKEN", "")
    auth = f"x-access-token:{token}@" if token else ""
    url = f"https://{auth}github.com/{repo}.git"
    dest = workdir / repo.replace("/", "__")
    proc = subprocess.run(["git", "clone", "--depth", "1", url, str(dest)],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"clone {repo} failed: {proc.stderr.strip()}")
    return dest


def drain_and_open(
    *,
    proposals_dir: Optional[Path] = None,
    dead_letter_dir: Optional[Path] = None,
    repo_dir: Optional[Path] = None,
    opener: Callable = open_pr,
    checkout: Optional[Callable] = None,
    runner=None,
    limit: Optional[int] = None,
) -> List[dict]:
    """Open every recorded proposal; return one result dict per item processed.

    Result: {id, kind, opened: bool, pr_url|error, attempts}. Failures are re-queued (or
    dead-lettered past MAX_ATTEMPTS); successes are consumed. When a proposal names a
    ``repo`` and *checkout* is provided, that repo is checked out and the PR is opened
    there; otherwise the PR is opened in *repo_dir* (the local checkout).
    """
    checkout = checkout if checkout is not None else clone_target
    proposals = DurableQueue(proposals_dir if proposals_dir is not None else state_dir() / "proposals")
    dead = DurableQueue(dead_letter_dir if dead_letter_dir is not None else state_dir() / "proposals-dead")
    repo_dir = Path(repo_dir) if repo_dir is not None else _repo_toplevel()

    # Snapshot the current queue into a batch FIRST, then process. A failure re-queued
    # below must wait for the NEXT run, not be re-consumed (and burn all its attempts) in
    # this one — draining up front makes each run cost each proposal exactly one attempt.
    batch: List[dict] = []
    while not proposals.empty():
        if limit is not None and len(batch) >= limit:
            break
        try:
            batch.append(proposals.get_nowait())
        except Exception:
            break

    results: List[dict] = []
    for entry in batch:
        attempts = int(entry.get("attempts", 0)) + 1
        proposal = entry.get("proposal") or {}
        rid = entry.get("id", "?")
        base = {"id": rid, "kind": entry.get("beacon_kind"), "attempts": attempts}
        # Each proposal is remediated as a ControlLoop: opening a reviewable PR IS
        # convergence, and the sealed result (trace_hash) is the provenance. Within-run
        # bounded retry lives in the loop; the dead-letter below is the ORTHOGONAL
        # cross-run bound for transient infra (a clone/credential blip between runs).
        try:
            with tempfile.TemporaryDirectory(prefix="self-heal-open-") as tmp:
                target = checkout(proposal["repo"], Path(tmp)) if proposal.get("repo") else repo_dir
                sealed = remediate_via_pr(proposal, opener=opener, repo_dir=target, runner=runner)
        except Exception as exc:  # checkout (clone) failure — never opened a PR
            sealed = {"converged": False, "pr_url": None, "trace_hash": None,
                      "error": f"checkout failed: {exc}"}

        if sealed.get("converged"):
            results.append({**base, "opened": True, "pr_url": sealed.get("pr_url"),
                            "trace_hash": sealed.get("trace_hash")})
            continue

        entry["attempts"] = attempts
        entry["last_error"] = sealed.get("error") or sealed.get("reason")
        rec = {**base, "opened": False, "error": entry["last_error"],
               "pr_url": sealed.get("pr_url"), "trace_hash": sealed.get("trace_hash")}
        if attempts >= MAX_ATTEMPTS:
            dead.put(entry)          # give up loudly instead of retrying forever
            rec["dead_lettered"] = True
        else:
            proposals.put(entry)     # transient — let the next run retry
        results.append(rec)
    return results


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Open recorded self-heal proposals as fix PRs.")
    ap.add_argument("--limit", type=int, default=None, help="max proposals to process this run")
    ap.add_argument("--repo-dir", type=Path, default=None, help="checkout to open PRs in")
    args = ap.parse_args(argv)

    results = drain_and_open(limit=args.limit, repo_dir=args.repo_dir)
    opened = [r for r in results if r.get("opened")]
    failed = [r for r in results if not r.get("opened")]
    dead = [r for r in failed if r.get("dead_lettered")]

    print(json.dumps({"processed": len(results), "opened": len(opened),
                      "failed": len(failed), "dead_lettered": len(dead),
                      "results": results}, indent=2))
    for r in opened:
        print(f"  opened {r['pr_url']}  ({r.get('kind')})", file=sys.stderr)
    for r in failed:
        tag = "DEAD-LETTER" if r.get("dead_lettered") else f"attempt {r['attempts']}/{MAX_ATTEMPTS}"
        print(f"  FAILED [{tag}] {r['id']}: {r.get('error')}", file=sys.stderr)

    # Fail the run if anything gave up permanently; a transient re-queue is not a failure.
    return 1 if dead else 0


if __name__ == "__main__":
    raise SystemExit(main())
