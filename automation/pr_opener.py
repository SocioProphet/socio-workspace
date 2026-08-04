"""Open a recorded self-heal proposal as a real, human-reviewable fix PR.

The reasoned responder (automation/responder.py) DECIDES and, having no standing
credentials, only RECORDS a proposal (automation/executors.propose_pr). This module
is the credentialed other half: given such a proposal it creates a branch, writes the
proposed files, commits, pushes, and opens a pull request — for a human to review and
merge. It NEVER merges. That division is deliberate: the daemon cannot act on the world,
and the thing that can only ever *opens* a PR, so every self-healed change still passes a
human gate (and the CI-workflow / token review guardrail is never bypassed).

The subprocess runner is injected so the whole flow is testable without a real git/gh.
"""
from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Optional

# A runner takes an argv list and returns (returncode, stdout, stderr).
Runner = Callable[..., "RunResult"]


@dataclass(frozen=True)
class RunResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


def _subprocess_runner(argv, *, cwd: Optional[Path] = None) -> RunResult:
    proc = subprocess.run(
        argv, cwd=str(cwd) if cwd else None,
        capture_output=True, text=True,
    )
    return RunResult(proc.returncode, proc.stdout, proc.stderr)


def _valid(proposal: dict) -> bool:
    if not (isinstance(proposal, dict) and proposal.get("title") and proposal.get("branch")):
        return False
    # A proposal fixes forward (write files) OR reverts a bad commit — exactly one.
    has_files = isinstance(proposal.get("files"), dict) and len(proposal["files"]) > 0
    has_revert = isinstance(proposal.get("revert"), str) and bool(proposal.get("revert"))
    return has_files or has_revert


def open_pr(
    proposal: dict,
    *,
    repo_dir: Path,
    runner: Runner = _subprocess_runner,
) -> str:
    """Open (or reuse) a fix PR for *proposal* in the checkout at *repo_dir*; return its URL.

    Fail-closed: any git/gh non-zero exit raises RuntimeError with the captured stderr, so a
    partial push never masquerades as a success. Idempotent: if a PR for the branch already
    exists it is reused, and re-running writes the same files to the same branch.
    """
    if not _valid(proposal):
        raise ValueError("proposal must carry title, branch, and either file changes or a `revert` commit")

    repo_dir = Path(repo_dir)
    branch = proposal["branch"]
    base = proposal.get("base", "main")
    title = proposal["title"]
    body = proposal.get("body", "") or f"Automated self-heal fix.\n\nProposal: {branch}"
    repo = proposal.get("repo")  # owner/name; when absent, gh infers from the checkout

    def run(argv, *, allow_fail: bool = False) -> RunResult:
        res = runner(argv, cwd=repo_dir)
        if res.returncode != 0 and not allow_fail:
            raise RuntimeError(f"command failed ({res.returncode}): {shlex.join(argv)}\n{res.stderr.strip()}")
        return res

    # 1. Start the branch from the up-to-date base (idempotent: -B resets if it exists).
    run(["git", "fetch", "origin", base])
    run(["git", "checkout", "-B", branch, f"origin/{base}"])

    # 2. Produce the change — either revert a bad commit, or write forward-fix files.
    if proposal.get("revert"):
        # git revert creates its own commit; --no-edit keeps it non-interactive. A bad deploy
        # heals by reverting the offending commit, not by hand-patching over it.
        run(["git", "revert", "--no-edit", str(proposal["revert"])])
    else:
        changed = []
        for rel, content in proposal["files"].items():
            dest = repo_dir / rel
            if ".." in Path(rel).parts:
                raise ValueError(f"proposal file escapes the repo: {rel!r}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
            changed.append(rel)
        run(["git", "add", "--", *changed])
        # commit only if there is a delta (a re-run with identical content is a no-op).
        status = run(["git", "status", "--porcelain"])
        if status.stdout.strip():
            run(["git", "commit", "-m", title])

    # 4. Push the branch (safe: only ever this self-heal branch, never base).
    run(["git", "push", "--force-with-lease", "-u", "origin", branch])

    # 5. Reuse an existing PR if one is open for this branch, else open a new one.
    gh_repo = ["-R", repo] if repo else []
    existing = run(["gh", "pr", "list", *gh_repo, "--head", branch, "--state", "open",
                    "--json", "url", "--jq", ".[0].url // \"\""], allow_fail=True)
    url = existing.stdout.strip()
    if url:
        return url

    created = run(["gh", "pr", "create", *gh_repo, "--head", branch, "--base", base,
                   "--title", title, "--body", body])
    return created.stdout.strip()
