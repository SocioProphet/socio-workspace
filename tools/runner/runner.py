#!/usr/bin/env python3
"""socio-workspace runner (v0.1)

Bootstrap runner for our manifest+lock workspace.

Commands:
  - list: show manifest repos + whether materialized
  - fetch: materialize missing repos (git clone) and checkout lock rev
  - run: run a task (build/test/lint/etc.) across selected components

Stdlib-only: no Python deps.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

try:
    import tomllib  # py>=3.11
except Exception as e:  # pragma: no cover
    print("ERROR: Python 3.11+ required (tomllib missing)", file=sys.stderr)
    raise

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "manifest" / "workspace.toml"
LOCK_PATH = ROOT / "manifest" / "workspace.lock.json"


@dataclass(frozen=True)
class Repo:
    name: str
    role: str
    local_path: Path
    url: str | None = None
    ref: str | None = None
    rev: str | None = None


def _run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=check)


def _capture(cmd: list[str], cwd: Path | None = None) -> str:
    return subprocess.check_output(cmd, cwd=str(cwd) if cwd else None, text=True).strip()


def load_manifest() -> list[Repo]:
    data = tomllib.loads(MANIFEST_PATH.read_text("utf-8"))
    repos: list[Repo] = []
    for r in data.get("repos", []):
        lp = ROOT / r["local_path"]
        repos.append(
            Repo(
                name=r["name"],
                role=r.get("role", "component"),
                local_path=lp,
                url=r.get("url"),
                ref=r.get("ref"),
                rev=r.get("rev"),
            )
        )
    return repos


def load_lock() -> dict[str, Any]:
    if not LOCK_PATH.exists():
        return {}
    return json.loads(LOCK_PATH.read_text("utf-8"))


def locked_rev(lock: dict[str, Any], name: str) -> str | None:
    for r in lock.get("repos", []):
        if r.get("name") == name:
            return r.get("rev")
    return None


def repo_is_git(p: Path) -> bool:
    return (p / ".git").exists()


def repo_head_rev(p: Path) -> str | None:
    if not repo_is_git(p):
        return None
    try:
        return _capture(["git", "rev-parse", "HEAD"], cwd=p)
    except Exception:
        return None


def cmd_list(args: argparse.Namespace) -> int:
    repos = load_manifest()
    lock = load_lock()

    for r in repos:
        exists = r.local_path.exists()
        head = repo_head_rev(r.local_path) if exists else None
        lrev = locked_rev(lock, r.name)
        status = "MISSING"
        if exists:
            status = "LOCAL"
            if repo_is_git(r.local_path):
                status = "GIT"
        drift = ""
        if lrev and head and head != lrev:
            drift = " (LOCK DRIFT)"
        print(f"- {r.name:28s} role={r.role:10s} status={status:7s} head={head or '-'} lock={lrev or '-'}{drift}")
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    repos = load_manifest()
    lock = load_lock()

    for r in repos:
        r.local_path.parent.mkdir(parents=True, exist_ok=True)

        if r.local_path.exists():
            # already materialized
            continue

        if not r.url:
            print(f"SKIP {r.name}: no url and path missing ({r.local_path})", file=sys.stderr)
            continue

        print(f"CLONE {r.name} -> {r.local_path}")
        _run(["git", "clone", r.url, str(r.local_path)])

        lrev = locked_rev(lock, r.name) or r.rev
        if lrev:
            print(f"CHECKOUT {r.name} @ {lrev}")
            _run(["git", "checkout", lrev], cwd=r.local_path)

    return 0


def detect_task_command(repo_path: Path, task: str) -> list[str] | None:
    """Return a command list for executing `task` inside `repo_path`."""

    if (repo_path / "Makefile").exists():
        return ["make", task]

    if (repo_path / "justfile").exists():
        return ["just", task]

    # Taskfile.yml (requires `task` binary)
    if (repo_path / "Taskfile.yml").exists() or (repo_path / "Taskfile.yaml").exists():
        return ["task", task]

    # scripts/ convention
    sh = repo_path / "scripts" / f"{task}.sh"
    py = repo_path / "scripts" / f"{task}.py"
    if sh.exists():
        return ["bash", str(sh)]
    if py.exists():
        return [sys.executable, str(py)]

    return None


def iter_targets(repos: Iterable[Repo], only: list[str] | None, role: str | None, all_components: bool) -> list[Repo]:
    out: list[Repo] = []

    if only:
        wanted = set(only)
        for r in repos:
            if r.name in wanted:
                out.append(r)
        return out

    if all_components:
        return [r for r in repos if r.role == "component"]

    if role:
        return [r for r in repos if r.role == role]

    return []


def cmd_run(args: argparse.Namespace) -> int:
    repos = load_manifest()
    targets = iter_targets(repos, args.only, args.role, args.all)

    if not targets:
        print("No targets selected. Use --all or --only <name> or --role <role>.", file=sys.stderr)
        return 2

    rc = 0
    for r in targets:
        if not r.local_path.exists():
            print(f"MISSING {r.name}: {r.local_path} (run fetch first)", file=sys.stderr)
            rc = 2
            continue

        cmd = detect_task_command(r.local_path, args.task)
        if not cmd:
            print(f"NO TASK CONTRACT for {r.name}: can't run '{args.task}'", file=sys.stderr)
            rc = 2
            continue

        print(f"\n== {r.name}: {args.task} ==")
        try:
            _run(cmd, cwd=r.local_path, check=True)
        except subprocess.CalledProcessError as e:
            print(f"FAIL {r.name}: exit {e.returncode}", file=sys.stderr)
            rc = e.returncode or 1

    return rc


def main() -> int:
    p = argparse.ArgumentParser(prog="runner")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("list", help="Show manifest repos and local status")
    sp.set_defaults(fn=cmd_list)

    sp = sub.add_parser("fetch", help="Materialize missing repos (git clone) + checkout lock")
    sp.set_defaults(fn=cmd_fetch)

    sp = sub.add_parser("run", help="Run a task across selected repos")
    sp.add_argument("task", help="Task name (build/test/lint/fmt/...) ")
    sp.add_argument("--all", action="store_true", help="Run against all repos with role=component")
    sp.add_argument("--only", action="append", help="Run only on named repo (repeatable)")
    sp.add_argument("--role", choices=["component", "adapter", "third_party", "tool"], help="Run on repos with this role")
    sp.set_defaults(fn=cmd_run)

    args = p.parse_args()
    return int(args.fn(args))


if __name__ == "__main__":
    raise SystemExit(main())
