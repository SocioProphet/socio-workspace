from __future__ import annotations

from dataclasses import asdict, dataclass

from .reconcile import ReconcileDecision


@dataclass(frozen=True)
class ResultLabel:
    surface_state: str
    freshness_class: str
    authority_state: str
    reconcile_state: str
    operator_message: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def label_for_stale_mirror(decision: ReconcileDecision) -> ResultLabel:
    if decision.action == "block_stale_mirror":
        return ResultLabel(
            surface_state="authoritative_local",
            freshness_class="fresh",
            authority_state="local_authoritative",
            reconcile_state="blocked",
            operator_message="Stale mirror blocked by policy.",
        )
    if decision.action == "metadata_only":
        return ResultLabel(
            surface_state="remote_metadata_only",
            freshness_class="bounded_stale",
            authority_state="local_authoritative",
            reconcile_state="degraded_read",
            operator_message="Mirror is stale; returning metadata only.",
        )
    if decision.action == "use_stale_mirror":
        return ResultLabel(
            surface_state="stale_mirror",
            freshness_class="bounded_stale",
            authority_state="remote_read_only",
            reconcile_state="allowed",
            operator_message="Using stale mirror per policy.",
        )
    if decision.action == "use_mirror":
        return ResultLabel(
            surface_state="stale_mirror",
            freshness_class="fresh",
            authority_state="remote_read_only",
            reconcile_state="allowed",
            operator_message="Mirror is fresh enough to use.",
        )
    return ResultLabel(
        surface_state="manual_resolution_required",
        freshness_class="unknown_stale",
        authority_state="none",
        reconcile_state="manual_reconcile_required",
        operator_message="Manual reconcile required before using mirror data.",
    )


def label_for_tombstone(decision: ReconcileDecision) -> ResultLabel:
    if decision.action == "apply_tombstone":
        return ResultLabel(
            surface_state="tombstoned",
            freshness_class="fresh",
            authority_state="remote_authoritative",
            reconcile_state="resolved",
            operator_message="Remote tombstone applied.",
        )
    if decision.action == "reject_tombstone":
        return ResultLabel(
            surface_state="authoritative_local",
            freshness_class="fresh",
            authority_state="local_authoritative",
            reconcile_state="rejected",
            operator_message="Unsigned tombstone rejected.",
        )
    return ResultLabel(
        surface_state="manual_resolution_required",
        freshness_class="unknown_stale",
        authority_state="none",
        reconcile_state="manual_reconcile_required",
        operator_message="Manual reconcile required before tombstone handling.",
    )


def label_for_authority_transition(decision: ReconcileDecision) -> ResultLabel:
    if decision.action == "promote_authority":
        authority = f"{decision.authoritative_side}_authoritative"
        return ResultLabel(
            surface_state="authority_transition_applied",
            freshness_class="fresh",
            authority_state=authority,
            reconcile_state="resolved",
            operator_message="Authority transition applied.",
        )
    if decision.action == "no_op":
        authority = f"{decision.authoritative_side}_authoritative"
        return ResultLabel(
            surface_state="authority_unchanged",
            freshness_class="fresh",
            authority_state=authority,
            reconcile_state="no_op",
            operator_message="Authority unchanged.",
        )
    authority = f"{decision.authoritative_side}_authoritative" if decision.authoritative_side != "none" else "none"
    return ResultLabel(
        surface_state="authority_transition_pending",
        freshness_class="unknown_stale",
        authority_state=authority,
        reconcile_state="manual_reconcile_required",
        operator_message="Manual reconcile required before authority transition.",
    )
