from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReconcileDecision:
    action: str
    reason: str
    authoritative_side: str


def decide_reconcile_action(
    *,
    local_dirty: bool,
    remote_delete: bool,
    remote_newer: bool,
    authority_mode: str = "local_first",
    policy_allow_stale: bool = False,
) -> ReconcileDecision:
    if local_dirty and remote_delete:
        return ReconcileDecision(
            action="manual_reconcile",
            reason="local_dirty_remote_delete",
            authoritative_side="none",
        )

    if authority_mode == "local_first":
        if remote_newer and not policy_allow_stale:
            return ReconcileDecision(
                action="manual_reconcile",
                reason="remote_newer_but_local_authority",
                authoritative_side="local",
            )
        return ReconcileDecision(
            action="local_wins",
            reason="local_first_default",
            authoritative_side="local",
        )

    if authority_mode == "provider_first":
        if local_dirty and remote_newer:
            return ReconcileDecision(
                action="manual_reconcile",
                reason="provider_first_with_local_dirty_and_remote_newer",
                authoritative_side="remote",
            )
        return ReconcileDecision(
            action="remote_wins",
            reason="provider_first_default",
            authoritative_side="remote",
        )

    if authority_mode == "hybrid":
        if local_dirty or remote_delete or remote_newer:
            return ReconcileDecision(
                action="manual_reconcile",
                reason="hybrid_requires_explicit_resolution",
                authoritative_side="none",
            )
        return ReconcileDecision(
            action="no_op",
            reason="hybrid_no_change",
            authoritative_side="none",
        )

    return ReconcileDecision(
        action="manual_reconcile",
        reason="unknown_authority_mode",
        authoritative_side="none",
    )


def decide_tombstone_action(
    *,
    signed_tombstone: bool,
    local_dirty: bool,
    authority_mode: str = "local_first",
) -> ReconcileDecision:
    if local_dirty:
        return ReconcileDecision(
            action="manual_reconcile",
            reason="local_dirty_remote_tombstone",
            authoritative_side="none",
        )

    if not signed_tombstone:
        return ReconcileDecision(
            action="reject_tombstone",
            reason="unsigned_tombstone",
            authoritative_side="none",
        )

    if authority_mode == "provider_first":
        return ReconcileDecision(
            action="apply_tombstone",
            reason="provider_first_signed_tombstone",
            authoritative_side="remote",
        )

    if authority_mode == "local_first":
        return ReconcileDecision(
            action="manual_reconcile",
            reason="signed_tombstone_requires_policy_check",
            authoritative_side="local",
        )

    if authority_mode == "hybrid":
        return ReconcileDecision(
            action="manual_reconcile",
            reason="hybrid_tombstone_requires_resolution",
            authoritative_side="none",
        )

    return ReconcileDecision(
        action="manual_reconcile",
        reason="unknown_authority_mode",
        authoritative_side="none",
    )


def decide_stale_mirror_action(
    *,
    stale_generation_gap: int,
    policy_allow_stale: bool,
    authority_mode: str = "local_first",
) -> ReconcileDecision:
    if stale_generation_gap <= 0:
        return ReconcileDecision(
            action="use_mirror",
            reason="mirror_is_fresh",
            authoritative_side="remote",
        )

    if not policy_allow_stale:
        return ReconcileDecision(
            action="block_stale_mirror",
            reason="stale_not_allowed",
            authoritative_side="local",
        )

    if authority_mode == "local_first":
        return ReconcileDecision(
            action="metadata_only",
            reason="stale_mirror_local_first",
            authoritative_side="local",
        )

    if authority_mode == "provider_first":
        return ReconcileDecision(
            action="use_stale_mirror",
            reason="stale_mirror_provider_first",
            authoritative_side="remote",
        )

    if authority_mode == "hybrid":
        return ReconcileDecision(
            action="manual_reconcile",
            reason="stale_mirror_hybrid_requires_resolution",
            authoritative_side="none",
        )

    return ReconcileDecision(
        action="manual_reconcile",
        reason="unknown_authority_mode",
        authoritative_side="none",
    )


def decide_authority_transition(
    *,
    current_authority: str,
    requested_authority: str,
    quorum_granted: bool,
) -> ReconcileDecision:
    if current_authority == requested_authority:
        return ReconcileDecision(
            action="no_op",
            reason="same_authority",
            authoritative_side=current_authority,
        )

    if not quorum_granted:
        return ReconcileDecision(
            action="manual_reconcile",
            reason="quorum_required_for_authority_transition",
            authoritative_side=current_authority,
        )

    return ReconcileDecision(
        action="promote_authority",
        reason="authority_transition_granted",
        authoritative_side=requested_authority,
    )
