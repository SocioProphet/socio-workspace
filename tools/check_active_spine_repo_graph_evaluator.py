#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
EVALUATOR = ROOT / "tools" / "evaluate_active_spine_repo_graph.py"

REQUIRED_FINDING_KINDS = {
    "promotion-ready",
    "missing-surface",
    "stale-pin",
    "policy-review-required",
    "blocked-non-actionable",
}

REQUIRED_PROMOTION_READY = {
    "SocioProphet/socioprophet-agent-standards",
    "SocioProphet/prophet-workspace",
    "SocioProphet/hellgraph",
}

REQUIRED_POLICY_REVIEW = {
    "SocioProphet/sociosphere",
    "SocioProphet/TriTRPC",
    "SocioProphet/socioprophet-standards-storage",
    "SocioProphet/socioprophet-standards-knowledge",
}


def fail(msg: str) -> None:
    print(f"ERR: {msg}", file=sys.stderr)


def load_evaluator():
    spec = importlib.util.spec_from_file_location("evaluate_active_spine_repo_graph", EVALUATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load evaluator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    failed = False
    evaluator = load_evaluator()
    result = evaluator.evaluate()
    findings = result.get("findings", [])
    kinds = {item.get("kind") for item in findings}
    if not REQUIRED_FINDING_KINDS <= kinds:
        fail(f"missing finding kinds: {sorted(REQUIRED_FINDING_KINDS - kinds)}")
        failed = True

    promotion_ready = {item["repository"] for item in findings if item.get("kind") == "promotion-ready"}
    if not REQUIRED_PROMOTION_READY <= promotion_ready:
        fail(f"missing promotion-ready findings: {sorted(REQUIRED_PROMOTION_READY - promotion_ready)}")
        failed = True

    policy_review = {item["repository"] for item in findings if item.get("kind") == "policy-review-required"}
    if not REQUIRED_POLICY_REVIEW <= policy_review:
        fail(f"missing policy-review-required findings: {sorted(REQUIRED_POLICY_REVIEW - policy_review)}")
        failed = True

    adjacency = [item for item in findings if item.get("kind") == "blocked-non-actionable"]
    if not any(item.get("repository") == "SourceOS-Linux/sourceos-spec" and item.get("actionable") is False for item in adjacency):
        fail("missing non-actionable SourceOS adjacency finding")
        failed = True

    stale = [item for item in findings if item.get("kind") == "stale-pin"]
    if not any(item.get("repository") == "watson-cyc-semantic-web-chronos-v1" for item in stale):
        fail("missing stale-pin corpus-loop review finding")
        failed = True

    if failed:
        return 1

    print(f"OK: active spine repo graph evaluator produced {len(findings)} governed findings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
