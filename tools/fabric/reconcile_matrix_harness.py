from __future__ import annotations

from pathlib import Path
from typing import Any

from .reconcile import (
    decide_authority_transition,
    decide_stale_mirror_action,
    decide_tombstone_action,
)
from .reconcile_flow_harness import run_authority_transition_flow, run_tombstone_propagation_flow
from .result_labels import (
    label_for_authority_transition,
    label_for_stale_mirror,
    label_for_tombstone,
)
from .stale_mirror_flow_harness import run_stale_mirror_flow


def run_reconcile_matrix(root: Path) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)

    tombstone = run_tombstone_propagation_flow(
        root / "tombstone",
        signed_tombstone=True,
        local_dirty=False,
        authority_mode="provider_first",
    )
    stale = run_stale_mirror_flow(
        root / "stale",
        stale_generation_gap=3,
        policy_allow_stale=True,
        authority_mode="local_first",
    )
    authority = run_authority_transition_flow(
        root / "authority",
        current_authority="local",
        requested_authority="remote",
        quorum_granted=True,
    )

    tombstone_decision = decide_tombstone_action(
        signed_tombstone=True,
        local_dirty=False,
        authority_mode="provider_first",
    )
    stale_decision = decide_stale_mirror_action(
        stale_generation_gap=3,
        policy_allow_stale=True,
        authority_mode="local_first",
    )
    authority_decision = decide_authority_transition(
        current_authority="local",
        requested_authority="remote",
        quorum_granted=True,
    )

    direct_decisions = {
        "tombstone": tombstone_decision.__dict__,
        "stale_mirror": stale_decision.__dict__,
        "authority_transition": authority_decision.__dict__,
    }
    result_labels = {
        "tombstone": label_for_tombstone(tombstone_decision).to_dict(),
        "stale_mirror": label_for_stale_mirror(stale_decision).to_dict(),
        "authority_transition": label_for_authority_transition(authority_decision).to_dict(),
    }

    return {
        "tombstone": tombstone,
        "stale_mirror": stale,
        "authority_transition": authority,
        "direct_decisions": direct_decisions,
        "result_labels": result_labels,
    }
