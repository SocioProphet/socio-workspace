"""Produce the per-vantage reports the adaptive threat detector consumes — the sensor half.

The adaptive loop's other three parts are shipped: the controller (mesh_threat, #596), the live
detector that applies it (detect_mesh_threat, #601), and the placement it selects (#595). This is
the missing sensor: each mesh node observes its OWN partial, possibly-wrong view and emits a
report; a collector fans those in and writes the single file the detector reads. Symmetric to the
triad-receipt collector (#589): nodes write their own reports (a node cannot write another's), the
collector validates fail-closed, and a malformed/duplicate report is dropped and recorded rather
than trusted — so the holographic quorum sees a smaller vantage set, never a forged one.

build_report computes the honest local signal (the fraction of peers this node cannot reach) and
derives partition_suspected from it (a node that cannot see a majority of its peers is, from its
own vantage, partitioned) — the detector then resolves the mesh-wide truth from a QUORUM of these,
so one partitioned node's "everything is down" cannot move the posture alone.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Sequence


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_report(vantage: str, *, peers_total: int, peers_unreachable: int,
                 anomalies_seen: int = 0, partition_suspected: Optional[bool] = None) -> dict:
    """One node's honest local observation, shaped for the collector/detector.

    ``unreachable_fraction`` = peers_unreachable / peers_total, clamped to [0, 1]. When
    ``partition_suspected`` is not given it is derived: a node that cannot reach a strict majority
    of its peers suspects a partition (its own vantage has lost quorum). A node with no peers to
    probe (peers_total == 0) reports 0 unreachable and no partition — it can see nothing, and the
    detector treats a shortfall of vantages as blindness at the mesh level, not here.
    """
    if peers_total < 0 or peers_unreachable < 0 or anomalies_seen < 0:
        raise ValueError("counts must be non-negative")
    if peers_unreachable > peers_total:
        raise ValueError("peers_unreachable cannot exceed peers_total")
    frac = (peers_unreachable / peers_total) if peers_total else 0.0
    if partition_suspected is None:
        partition_suspected = peers_unreachable > (peers_total // 2) if peers_total else False
    return {
        "vantage": str(vantage),
        "unreachable_fraction": round(frac, 6),
        "anomalies_seen": int(anomalies_seen),
        "partition_suspected": bool(partition_suspected),
        "observed_at": _now(),
    }


def probe_and_report(vantage: str, peers: Sequence[str], *, reach: Callable[[str], bool],
                     anomalies_seen: int = 0) -> dict:
    """Probe each peer for reachability and emit this node's report.

    ``reach(peer) -> bool`` is INJECTED — the live implementation (a TCP dial, a health-endpoint
    GET, a gossip heartbeat) is node-runtime and environment-specific, so the library takes it as a
    seam and stays fully testable with a fake prober. A peer whose probe RAISES is treated as
    unreachable (fail-closed: an errored probe is not evidence of health). The count feeds
    build_report, which derives ``unreachable_fraction`` and ``partition_suspected``.
    """
    unreachable = 0
    for peer in peers:
        try:
            ok = reach(peer)
        except Exception:  # noqa: BLE001 — an errored probe counts as unreachable, never as healthy
            ok = False
        if not ok:
            unreachable += 1
    return build_report(vantage, peers_total=len(peers), peers_unreachable=unreachable,
                        anomalies_seen=anomalies_seen)


def _valid_report(r: object) -> Optional[str]:
    """Return an error string if the report is malformed, else None."""
    if not isinstance(r, dict):
        return f"not an object ({type(r).__name__})"
    if not isinstance(r.get("vantage"), str) or not r["vantage"]:
        return "vantage: missing or not a string"
    uf = r.get("unreachable_fraction")
    if not isinstance(uf, (int, float)) or isinstance(uf, bool) or not (0.0 <= float(uf) <= 1.0):
        return f"unreachable_fraction: {uf!r} not a number in [0,1]"
    an = r.get("anomalies_seen", 0)
    if not isinstance(an, int) or isinstance(an, bool) or an < 0:
        return f"anomalies_seen: {an!r} not a non-negative int"
    if not isinstance(r.get("partition_suspected", False), bool):
        return "partition_suspected: not a bool"
    return None


def collect_reports(node_report_paths: Iterable[Path], *, quorum: int = 3,
                    out_path: Optional[Path] = None) -> dict:
    """Fan in per-node report files -> the single document detect_mesh_threat reads.

    Reads each path as one node's report, validates it, and keeps the well-formed ones (deduped by
    ``vantage`` — a node reports once per round). Returns ``{quorum, reports, rejected, collected_at}``;
    when ``out_path`` is given it is written there atomically (temp + replace) so the detector never
    reads a half-written file. Fail-closed: an unreadable/malformed/duplicate report is dropped and
    recorded under ``rejected``, never counted as a vantage.
    """
    reports: List[dict] = []
    rejected: List[dict] = []
    seen: set = set()
    for p in node_report_paths:
        p = Path(p)
        try:
            raw = json.loads(p.read_text("utf-8"))
        except (FileNotFoundError, ValueError) as exc:
            rejected.append({"path": str(p), "reason": f"unreadable: {exc}"})
            continue
        err = _valid_report(raw)
        if err:
            rejected.append({"path": str(p), "reason": err})
            continue
        if raw["vantage"] in seen:
            rejected.append({"path": str(p), "vantage": raw["vantage"], "reason": "duplicate vantage this round"})
            continue
        seen.add(raw["vantage"])
        reports.append(raw)

    doc = {"quorum": quorum, "reports": reports, "rejected": rejected, "collected_at": _now()}
    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = out_path.with_suffix(out_path.suffix + ".tmp")
        tmp.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(out_path)
    return doc
