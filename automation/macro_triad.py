"""The macro-triad quorum — the *map* half of the bridge, over the k3s master triad.

The "k3 regime" is the real k8s control plane: three k3s HA master (server) nodes, each the head
of one cluster in the mesh. Each master publishes a Lazerus Integrity Receipt (automation.lazerus)
committing to the state it is serving. This module is the macro quorum over those three receipts —
the thing that, per the design, "heals the one sick or infected cluster and amplifies the failback
to the last non-sick state":

  1. Lint every receipt fail-closed (a malformed receipt cannot vote).
  2. Group the well-formed, non-quarantined masters by the state they commit to (``state_root``).
  3. If a group reaches quorum (default 2-of-3), THAT is the canonical healthy state, and its
     ``commit`` is the failback target — the last state a master quorum stands behind.
  4. Any master outside that group — quarantined by a koe_id, diverged to another state_root, or
     malformed — is *sick*, and is named.

Fail-closed at the top: if NO state reaches quorum (a 1-1-1 split, or two of three sick), there is
no trusted state to fail anything back to, so ``quorum_ok`` is False and NO failback is proposed.
Naming a sick cluster is only safe when a healthy majority actually exists to name it against.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

from automation.lazerus import ClusterReceipt, lint_receipt


@dataclass(frozen=True)
class SickCluster:
    cluster: str
    reason: str
    head_commit: Optional[str] = None   # the (bad) commit this master is serving, when known
    koe_id: Optional[str] = None        # set when Lazerus had already fenced it


@dataclass(frozen=True)
class TriadAssessment:
    quorum_ok: bool                              # a state reached quorum -> a trusted target exists
    canonical_state_root: Optional[str] = None   # the state the healthy majority commits to
    canonical_commit: Optional[str] = None       # git sha of that state — the failback target
    healthy_clusters: tuple = ()                 # dids in the canonical group
    sick_clusters: tuple = ()                     # tuple[SickCluster]
    reasons: tuple = field(default=())           # human-readable trail (per-receipt lint/vote)

    @property
    def needs_failback(self) -> bool:
        """A trusted majority exists AND at least one master is sick against it."""
        return self.quorum_ok and bool(self.sick_clusters)


def assess_triad(receipts: list, *, quorum: int = 2) -> TriadAssessment:
    """Assess the k3s master triad from its members' Lazerus receipts.

    ``quorum`` is the number of agreeing masters required to declare a canonical state (2 of 3 for
    the standard triad — the same majority that keeps a 3-node etcd/k3s control plane live). The
    result is decidable and fail-closed: with no majority you get ``quorum_ok=False`` and no target,
    never a guess.
    """
    reasons: list = []
    healthy: list = []                   # (cluster_did, ClusterReceipt)
    sick: list = []                      # SickCluster
    by_state: dict = defaultdict(list)   # state_root -> [ClusterReceipt]

    for idx, raw in enumerate(receipts):
        res = lint_receipt(raw)
        if not res.ok:
            # A master whose receipt won't lint cannot vote and is presumed sick (fail-closed).
            cid = raw.get("cluster") if isinstance(raw, dict) else None
            sick.append(SickCluster(cluster=cid or f"<receipt[{idx}]>",
                                    reason="malformed receipt: " + "; ".join(res.errors)))
            reasons.append(f"receipt[{idx}] rejected ({cid or 'unknown'}): {'; '.join(res.errors)}")
            continue
        rec: ClusterReceipt = res.receipt
        if rec.koe_id is not None:
            # Lazerus already fenced this replica (path/peer disagreement) — sick by decree.
            sick.append(SickCluster(cluster=rec.cluster, reason="quarantined by Lazerus koe_id",
                                    head_commit=rec.commit, koe_id=rec.koe_id))
            reasons.append(f"{rec.cluster}: quarantined ({rec.koe_id})")
            continue
        by_state[rec.state_root].append(rec)

    # The winning state is the largest agreeing group that meets quorum. Ties are broken
    # deterministically by state_root so the same inputs always name the same canonical state.
    winner_root: Optional[str] = None
    if by_state:
        winner_root = max(sorted(by_state), key=lambda r: len(by_state[r]))
        if len(by_state[winner_root]) < quorum:
            winner_root = None

    if winner_root is None:
        # Split-brain: no state reached quorum. Every well-formed master is unreconciled (none is
        # canonical), so name them all sick — a caller can surface the split for a human even
        # though there is no trusted target to fail anything back to (quorum_ok stays False).
        for root, recs in sorted(by_state.items()):
            reasons.append(f"state {root[:19]}… has {len(recs)} vote(s) — short of quorum {quorum}")
            for rec in recs:
                sick.append(SickCluster(cluster=rec.cluster,
                                        reason=f"unreconciled: no quorum, committed to {root[:19]}…",
                                        head_commit=rec.commit))
        reasons.append(f"NO quorum: no state reached {quorum} agreeing masters — no trusted failback target")
        return TriadAssessment(quorum_ok=False, sick_clusters=tuple(sick), reasons=tuple(reasons))

    canonical = by_state[winner_root]
    canonical_commit = canonical[0].commit
    healthy = [r.cluster for r in canonical]
    reasons.append(f"quorum OK: {len(canonical)}/{len(receipts)} masters agree on {winner_root[:19]}… "
                   f"(commit {canonical_commit[:12]}) — canonical healthy state")

    # Any well-formed master that committed to a DIFFERENT state is a divergence (sick).
    for root, recs in by_state.items():
        if root == winner_root:
            continue
        for rec in recs:
            sick.append(SickCluster(cluster=rec.cluster,
                                    reason=f"diverged: committed to {root[:19]}… not the canonical state",
                                    head_commit=rec.commit))
            reasons.append(f"{rec.cluster}: diverged from canonical (serving {rec.commit[:12]})")

    return TriadAssessment(
        quorum_ok=True,
        canonical_state_root=winner_root,
        canonical_commit=canonical_commit,
        healthy_clusters=tuple(healthy),
        sick_clusters=tuple(sick),
        reasons=tuple(reasons),
    )
