#!/usr/bin/env python3
"""Admitted is not governed: check that every admission fragment reached a shape.

``registry/admissions/*.canonical-repo.yaml`` is where estate detection deposits a
newly-discovered repository. That front end works -- ``noetica-impair`` was auto-admitted
the day it appeared, and the catalog ingested its assets. What did not happen is
everything after: it acquired no lane, no dependency edges and no propagation rule, so
every subsequent merge into it cascaded to nothing. It was a row in a list.

That is the failure this check exists to make impossible. An admission is a *claim that
a repository exists*, not a governance decision, and nothing downstream can act on it
until four further facts are recorded:

    shaped       the fragment itself carries role/status/tags -- what IS this
    laned        some registry/*-registration.yaml names it -- WHO governs it
    edged        dependency-graph.yaml or a *-dependency-edges.yaml pack names it,
                 so blast-radius traversal can reach it -- WHAT it touches
    propagating  change-propagation-rules.yaml names it as a trigger or a target,
                 so a merge into it actually cascades -- WHO hears about a change

The last one is the load-bearing one. ``change-propagation-rules.yaml`` keys every rule
on ``trigger.repo``, which means a repository must ALREADY be in that file for a change
to it to propagate. Nothing triggers on a repository *appearing*. So the first change to
a new repo -- the change that most needs to be heard -- is precisely the change that
cannot be. Detection without this check is a doorbell wired to nothing.

Newly admitted repos get a grace window before this is fatal, because admission is
automated and shaping is deliberate; a repo detected this morning should be visible in
the report, not blocking the build. Past the window it fails, which is the only way a
staging area stops being a place things go to be forgotten.

Debt that cannot be paid today goes in ``registry/unshaped-admission-backlog.yaml`` with a
``review_by`` date. That downgrades the failure to DEBT until the date and then fails
regardless of grace -- deliberately harder than an unfiled gap, because an expired
exception means someone promised to come back and did not.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "registry"
ADMISSIONS = REGISTRY / "admissions"
PROPAGATION = REGISTRY / "change-propagation-rules.yaml"
DEPENDENCY_GRAPH = REGISTRY / "dependency-graph.yaml"
BACKLOG = REGISTRY / "unshaped-admission-backlog.yaml"

#: Days after admission before an unshaped repo fails rather than warns.
GRACE_DAYS = 14

#: A repo may legitimately have no downstream consumers, but it must SAY so rather than
#: simply be absent -- silence and "nothing depends on this" are different facts.
NO_CONSUMERS_SENTINEL = "no_downstream_consumers"


def load_yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def admission_fragments() -> list[tuple[Path, dict[str, Any]]]:
    if not ADMISSIONS.is_dir():
        return []
    out = []
    for p in sorted(ADMISSIONS.glob("*.canonical-repo.yaml")):
        data = load_yaml(p)
        if isinstance(data, dict) and data.get("id"):
            out.append((p, data))
    return out


def backlog() -> dict[str, dict[str, Any]]:
    """Acknowledged debt, keyed by repo. Every entry expires; see the file's header."""
    data = load_yaml(BACKLOG)
    if not isinstance(data, dict):
        return {}
    return {e["repo"]: e for e in (data.get("entries") or [])
            if isinstance(e, dict) and e.get("repo")}


def admitted_on(fragment: dict[str, Any]) -> dt.date | None:
    """When was this admitted? The ``admitted`` field carries a trailing human note.

    Falls back to the date in ``source_ledger`` when ``admitted`` is absent. Several
    fragments from the same batch omit the field entirely, and treating them as undated
    put them past grace immediately -- flagging one-day-old repos as long-standing debt
    and burying the one repo that genuinely was. The ledger filename is real evidence of
    when the batch landed, so use it rather than guessing.
    """
    for field in ("admitted", "source_ledger"):
        m = re.search(r"(\d{4})-(\d{2})-(\d{2})", str(fragment.get(field, "")))
        if not m:
            continue
        try:
            return dt.date(int(m[1]), int(m[2]), int(m[3]))
        except ValueError:
            continue
    return None


# ── the four facts ───────────────────────────────────────────────────────────

def is_shaped(fragment: dict[str, Any]) -> tuple[bool, str]:
    missing = [k for k in ("role", "status", "description", "tags")
               if not fragment.get(k)]
    if missing:
        return False, f"fragment lacks {', '.join(missing)}"
    return True, f"role={fragment['role']}"


def _registration_files() -> list[Path]:
    return sorted(REGISTRY.glob("*-registration.yaml"))


def _edge_pack_files() -> list[Path]:
    packs = sorted(REGISTRY.glob("*-dependency-edges.yaml"))
    if DEPENDENCY_GRAPH.is_file():
        packs.append(DEPENDENCY_GRAPH)
    return packs


def _names_repo(path: Path, repo_id: str) -> bool:
    """Does this registry file mention the repo as a token, not a substring?

    Substring matching would let ``noetica`` satisfy a check for ``noetica-impair``
    and vice versa -- the exact class of false pass that makes a governance check
    worse than no check.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    return re.search(rf"(?<![\w-]){re.escape(repo_id)}(?![\w-])", text) is not None


def is_laned(repo_id: str) -> tuple[bool, str]:
    hits = [p.name for p in _registration_files() if _names_repo(p, repo_id)]
    if hits:
        return True, f"lane: {', '.join(hits)}"
    return False, "no registry/*-registration.yaml names it -- ungoverned"


def is_edged(repo_id: str) -> tuple[bool, str]:
    hits = [p.name for p in _edge_pack_files() if _names_repo(p, repo_id)]
    if hits:
        return True, f"edges in {', '.join(hits)}"
    return False, "absent from every dependency edge pack -- invisible to blast radius"


def propagation_role(repo_id: str) -> tuple[bool, str]:
    """Is the repo a trigger, a target, or neither, in the propagation rules?"""
    data = load_yaml(PROPAGATION)
    if not isinstance(data, dict):
        return False, "change-propagation-rules.yaml unreadable"
    triggers, targets = [], []
    for rule in data.get("rules") or []:
        if not isinstance(rule, dict):
            continue
        rid = rule.get("id", "?")
        if (rule.get("trigger") or {}).get("repo") == repo_id:
            triggers.append(rid)
        for tgt in rule.get("propagate_to") or []:
            if isinstance(tgt, dict) and tgt.get("repo") == repo_id:
                targets.append(rid)
    if triggers:
        return True, f"triggers {', '.join(triggers)}" + (
            f"; target of {', '.join(targets)}" if targets else "")
    if targets:
        return False, (
            f"only ever a TARGET ({', '.join(targets)}) -- changes to it reach no one. "
            "A repo that receives notifications but emits none is a sink, and a sink is "
            "where percolation stops"
        )
    return False, "no rule triggers on it -- merges into it cascade nowhere"


# ── report ───────────────────────────────────────────────────────────────────

def evaluate(today: dt.date) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    failures = 0
    known = backlog()
    for path, frag in admission_fragments():
        repo_id = frag["id"]
        checks = {
            "shaped": is_shaped(frag),
            "laned": is_laned(repo_id),
            "edged": is_edged(repo_id),
            "propagating": propagation_role(repo_id),
        }
        unmet = [k for k, (ok, _) in checks.items() if not ok]
        admitted = admitted_on(frag)
        age = (today - admitted).days if admitted else None
        in_grace = age is not None and age < GRACE_DAYS

        # An acknowledged entry holds the failure open until its review date, and then
        # fails harder than an unacknowledged one: an expired exception is worse than
        # never having filed it, because someone promised to come back.
        entry = known.get(repo_id)
        expired = False
        if entry:
            try:
                expired = today > dt.date.fromisoformat(str(entry.get("review_by")))
            except (TypeError, ValueError):
                expired = True

        if not unmet:
            status = "OK"
        elif entry and expired:
            status = "FAIL"
            failures += 1
        elif entry:
            status = "DEBT"
        elif in_grace:
            status = "WARN"
        else:
            status = "FAIL"
            failures += 1
        rows.append({
            "repo": repo_id, "fragment": path.name, "status": status,
            "age_days": age, "in_grace": in_grace, "unmet": unmet,
            "acknowledged": bool(entry),
            "review_by": entry.get("review_by") if entry else None,
            "detail": {k: v[1] for k, v in checks.items()},
        })
    return rows, failures


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="emit machine-readable output")
    ap.add_argument("--today", help="override today's date (YYYY-MM-DD) for tests")
    args = ap.parse_args()

    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    rows, failures = evaluate(today)

    if args.json:
        print(json.dumps({"grace_days": GRACE_DAYS, "failures": failures,
                          "admissions": rows}, indent=2))
        return 1 if failures else 0

    if not rows:
        print("no admission fragments found")
        return 0

    print(f"admission governance shape ({len(rows)} fragment(s), "
          f"grace {GRACE_DAYS}d)\n")
    for r in sorted(rows, key=lambda x: (x["status"] != "FAIL", x["repo"])):
        age = f"{r['age_days']}d" if r["age_days"] is not None else "age?"
        print(f"  [{r['status']:<4}] {r['repo']}  ({age})")
        for key in ("shaped", "laned", "edged", "propagating"):
            mark = "✗" if key in r["unmet"] else "✓"
            print(f"        {mark} {key:<12} {r['detail'][key]}")
    if failures:
        print(f"\n{failures} admitted repo(s) never reached a governed shape. Admission "
              "records that a repository exists; it does not tell the estate what the "
              "repository IS, what it touches, or who to wake when it changes. Add a "
              "lane, dependency edges and a propagation rule.")
        return 1
    warned = sum(1 for r in rows if r["status"] == "WARN")
    print(f"\nall admissions governed"
          + (f" ({warned} still inside the grace window)" if warned else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
