#!/usr/bin/env python3
"""Close the loop: monitor propagation, detect drift, alert. The pink arrow.

A delivery pipeline that runs dev -> pre-prod -> prod and stops is not a pipeline, it is
a chute. What makes the MLOps shape work is the return path: monitor what was deployed,
detect drift, alert, and feed that back into the next cycle. Propagation had no such
path. metrics/propagation-log.jsonl was written by the engine and read by nobody -- the
same defect this whole effort exists to remove, reproduced one level down.

Four signals, each of which was previously invisible:

  DECLARED-vs-ACTUATED DRIFT   the real drift metric. The hypergraph says who is a
        co-party to a change (lane membership + edges); the rules say who actually gets
        told. Divergence between them is a governance relationship that exists on paper
        and does not fire. This is the analogue of model drift: the world moved, the
        deployed artifact did not.

  DEAD RULES                   a rule that has never fired. Either its trigger repo is
        dormant, or the rule is mis-keyed and cannot match -- and the second is exactly
        how the whole estate sat inert while reporting success.

  FAILED DISPATCHES            an action the engine attempted and could not complete.

  NO-RULE MERGES               a repo merged and no rule matched. Recorded by the engine
        as status `no_rule`; if these accumulate for one repo, that repo is a sink.

Read-only. It alerts; it does not remediate, and it never edits a rule to make itself
green -- a monitor that can silence its own signal is not a monitor.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engines"))

RULES = ROOT / "registry" / "change-propagation-rules.yaml"
LOG = ROOT / "metrics" / "propagation-log.jsonl"

#: Fraction of a source's HYPEREDGE peers (cycle-1 reach) that its rules notify.
#: Below this the relation is mostly declared and barely actuated.
MIN_COVERAGE = 0.5


def load_rules() -> list[dict[str, Any]]:
    data = yaml.safe_load(RULES.read_text(encoding="utf-8")) or {}
    return [r for r in (data.get("rules") or []) if isinstance(r, dict)]


def load_log() -> list[dict[str, Any]]:
    if not LOG.is_file():
        return []
    out = []
    for line in LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def coverage() -> list[dict[str, Any]]:
    """Declared reach (hypergraph) vs actuated reach (rules), per trigger repo."""
    from gossip_beacon import Hypergraph, norm

    g = Hypergraph().load()
    rules = load_rules()
    by_trigger: dict[str, set[str]] = defaultdict(set)
    for r in rules:
        src = norm((r.get("trigger") or {}).get("repo"))
        if not src:
            continue
        for t in r.get("propagate_to") or []:
            if isinstance(t, dict) and (tgt := norm(t.get("repo"))):
                by_trigger[src].add(tgt)

    rows = []
    for src in sorted(by_trigger):
        res = g.converge(src)
        # The denominator is the HYPEREDGE, not the transitive closure.
        #
        # Convergence reach is everything eventually reachable -- 21 of ~22 nodes for
        # any well-connected repo, including the unrelated maths repos behind the
        # sociosphere hub. Scoring notification against that makes every repo look
        # catastrophically uncovered and measures connectedness rather than governance.
        # "Co-party to the relation" means cycle 1: lane siblings plus repos on a direct
        # edge. That is the set a change genuinely concerns.
        peers = {h["repo"] for h in g.emit(src, ttl=1)} - {src}
        actuated = by_trigger[src]
        missed = sorted(peers - actuated)
        # A trigger repo with NO peers is not fully covered, it is unplaced: it has a
        # rule but no lane and no edges, so nothing can be said about who its change
        # concerns. Scoring that 100% (as dividing by zero into 1.0 did) gives the worst
        # cases a clean bill -- the precise failure this monitor exists to catch.
        rows.append({
            "repo": src,
            "converged": res["converged"],
            "cycles": res["cycles"],
            "peers": len(peers),
            "actuated": len(actuated & peers),
            "coverage": round(len(actuated & peers) / len(peers), 3) if peers else None,
            "unplaced": not peers,
            "unreached": missed,
        })
    return rows


def evaluate() -> tuple[dict[str, Any], list[str]]:
    rules = load_rules()
    log = load_log()
    alerts: list[str] = []

    fired = Counter()
    failures: list[dict[str, Any]] = []
    no_rule: Counter = Counter()
    for ev in log:
        repo = ev.get("repo")
        status = ev.get("status")
        if status == "no_rule":
            no_rule[repo] += 1
        for act in ev.get("actions_triggered") or []:
            if act.get("rule"):
                fired[act["rule"]] += 1
            if act.get("status") == "failed":
                failures.append({"repo": act.get("repo"), "rule": act.get("rule"),
                                 "error": act.get("error", "")})

    dead = sorted({r["id"] for r in rules if r.get("id")} - set(fired))
    cov = coverage()

    if not log:
        # Distinguish "healthy" from "never observed". An empty log after wiring the
        # engine means nothing has run yet, which is not the same as nothing is wrong.
        alerts.append("propagation log is empty: no run has been observed yet, so "
                      "dead-rule and failure signals are UNKNOWN, not clean")
    for f in failures:
        alerts.append(f"dispatch failed: {f['rule']} -> {f['repo']} ({f['error']})")
    for repo, n in no_rule.most_common():
        alerts.append(f"{repo} merged {n}x with no matching rule — it is a sink")
    for row in cov:
        if not row["converged"]:
            alerts.append(f"{row['repo']}: beacon did not converge; reach is truncated")
        if row["unplaced"]:
            alerts.append(
                f"{row['repo']}: has a propagation rule but NO lane and no edges — "
                "nothing can be said about who its changes concern")
            continue
        if row["coverage"] < MIN_COVERAGE:
            alerts.append(
                f"{row['repo']}: coverage {row['coverage']:.0%} — {len(row['unreached'])} "
                f"co-part{'y' if len(row['unreached'])==1 else 'ies'} to its relation "
                f"get no notification ({', '.join(row['unreached'][:4])}"
                + (", …" if len(row['unreached']) > 4 else "") + ")")

    return {"rules": len(rules), "log_events": len(log), "dead_rules": dead,
            "failures": failures, "no_rule": dict(no_rule), "coverage": cov}, alerts


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true",
                    help="exit non-zero on any alert (default: only on failures)")
    args = ap.parse_args()

    report, alerts = evaluate()

    if args.json:
        print(json.dumps({**report, "alerts": alerts}, indent=2))
    else:
        print(f"propagation feedback: {report['rules']} rule(s), "
              f"{report['log_events']} logged event(s)\n")
        print("declared reach vs actuated reach")
        for row in report["coverage"]:
            if row["unplaced"]:
                print(f" ? {row['repo']:<34} UNPLACED — rule exists, no lane, no edges")
                continue
            bar = "!" if row["coverage"] < MIN_COVERAGE else " "
            print(f" {bar} {row['repo']:<34} cycles={row['cycles']} "
                  f"peers={row['peers']:<3} notified={row['actuated']:<3} "
                  f"coverage={row['coverage']:.0%}")
        if report["dead_rules"]:
            print(f"\ndead rules (never fired in the observed log): "
                  f"{len(report['dead_rules'])}")
            for r in report["dead_rules"]:
                print(f"    {r}")
        if alerts:
            print("\nalerts:")
            for a in alerts:
                print(f"  ! {a}")
        else:
            print("\nno alerts")

    if report["failures"]:
        return 1
    return 1 if (args.strict and alerts) else 0


if __name__ == "__main__":
    sys.exit(main())
