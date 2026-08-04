"""Telemetry + alerting: make the self-heal loop observable.

The loop writes durable receipts (state/decisions), proposals (state/proposals) and quarantine
markers (state/quarantine), but nothing read them — so the estate could heal (or fail to) with
no signal a human could see. This aggregates those receipts into Prometheus-format metrics and
into SRE ALERTS: an alert fires when something genuinely needs attention (a policy breach was
quarantined; escalations pile up; a healing attempt failed to resolve).

Reads are non-destructive (`DurableQueue.peek_all`), so scraping never drains the queues.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from automation.durable_queue import DurableQueue, state_dir

# Default alert thresholds (overridable by the caller / scheduler job).
DEFAULT_ESCALATION_ALERT_THRESHOLD = 5


def collect(state: Optional[Path] = None) -> dict:
    """Aggregate self-heal receipts into a metrics dict. Non-destructive."""
    root = Path(state) if state is not None else state_dir()
    decisions = DurableQueue(root / "decisions").peek_all()

    by_action: Dict[str, int] = {}
    by_kind: Dict[str, int] = {}
    by_verdict: Dict[str, int] = {}
    heals = proposals = quarantines = escalations = healing_failures = 0

    for r in decisions:
        action = str(r.get("action", "unknown"))
        by_action[action] = by_action.get(action, 0) + 1
        by_kind[str(r.get("beacon_kind", "unknown"))] = by_kind.get(str(r.get("beacon_kind", "unknown")), 0) + 1
        by_verdict[str(r.get("verdict", "unknown"))] = by_verdict.get(str(r.get("verdict", "unknown")), 0) + 1
        if action == "escalate_human":
            escalations += 1
        ex = r.get("execution") or {}
        if ex.get("healed"):
            heals += 1
        if ex.get("proposed"):
            proposals += 1
        if ex.get("quarantined"):
            quarantines += 1
        # an executor ran but did not resolve (healed/proposed/quarantined all falsey)
        if ex and not (ex.get("healed") or ex.get("proposed") or ex.get("quarantined")):
            healing_failures += 1

    return {
        "decisions_total": len(decisions),
        "by_action": by_action,
        "by_kind": by_kind,
        "by_verdict": by_verdict,
        "heals_total": heals,
        "proposals_total": proposals,
        "quarantines_total": quarantines,
        "escalations_total": escalations,
        "healing_failures_total": healing_failures,
        "queue_depth": {
            "beacons": DurableQueue(root / "beacons").qsize(),
            "decisions": len(decisions),
            "proposals": DurableQueue(root / "proposals").qsize(),
            "quarantine": DurableQueue(root / "quarantine").qsize(),
        },
    }


def _fmt_labeled(name: str, help_text: str, values: Dict[str, int], label: str) -> List[str]:
    lines = [f"# HELP {name} {help_text}", f"# TYPE {name} gauge"]
    for key, count in sorted(values.items()):
        safe = str(key).replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'{name}{{{label}="{safe}"}} {count}')
    return lines


def render_prometheus(metrics: dict) -> str:
    """Render metrics in Prometheus text exposition format."""
    P = "sociosphere_selfheal"
    lines: List[str] = []
    for name, help_text, key in [
        (f"{P}_heals_total", "Artifacts healed by an executor", "heals_total"),
        (f"{P}_proposals_total", "Reviewable proposals recorded", "proposals_total"),
        (f"{P}_quarantines_total", "Subjects quarantined", "quarantines_total"),
        (f"{P}_escalations_total", "Decisions escalated to a human", "escalations_total"),
        (f"{P}_healing_failures_total", "Executor ran but did not resolve", "healing_failures_total"),
        (f"{P}_decisions_total", "Total decisions recorded", "decisions_total"),
    ]:
        lines += [f"# HELP {name} {help_text}", f"# TYPE {name} counter", f"{name} {metrics.get(key, 0)}"]
    lines += _fmt_labeled(f"{P}_decisions_by_action", "Decisions by action", metrics.get("by_action", {}), "action")
    lines += _fmt_labeled(f"{P}_decisions_by_kind", "Decisions by failure class", metrics.get("by_kind", {}), "kind")
    lines += _fmt_labeled(f"{P}_queue_depth", "Pending items per queue", metrics.get("queue_depth", {}), "queue")
    return "\n".join(lines) + "\n"


def alerts(metrics: dict, *, escalation_threshold: int = DEFAULT_ESCALATION_ALERT_THRESHOLD) -> List[dict]:
    """SRE alerts: conditions a human should act on. Empty list == all clear."""
    out: List[dict] = []
    if metrics.get("quarantines_total", 0) > 0:
        out.append({"severity": "warning", "kind": "quarantine",
                    "message": f"{metrics['quarantines_total']} subject(s) quarantined — review the policy breach"})
    if metrics.get("healing_failures_total", 0) > 0:
        out.append({"severity": "warning", "kind": "healing_failure",
                    "message": f"{metrics['healing_failures_total']} executor run(s) did not resolve"})
    if metrics.get("escalations_total", 0) >= escalation_threshold:
        out.append({"severity": "warning", "kind": "escalation_backlog",
                    "message": f"{metrics['escalations_total']} escalations pending (>= {escalation_threshold})"})
    return out


def write_metrics_file(text: str, path: Optional[Path] = None) -> Path:
    """Atomically write Prometheus text where a textfile-collector / sidecar can scrape it."""
    target = Path(path) if path is not None else state_dir() / "metrics.prom"
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(target.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, target)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return target


def main(argv: Optional[List[str]] = None) -> int:
    """CLI: print Prometheus metrics; with --alerts, print alerts and exit 1 if any fire."""
    import sys

    argv = sys.argv[1:] if argv is None else argv
    metrics = collect()
    if "--alerts" in argv:
        firing = alerts(metrics)
        for a in firing:
            print(f"[{a['severity']}] {a['kind']}: {a['message']}")
        return 1 if firing else 0
    print(render_prometheus(metrics), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
