from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from .events import EventSink
from .integration_common import run_mount_and_connector_flow
from .connectors.s3 import S3Executor
from .connectors.hyper import HyperExecutor
from .reconcile import decide_authority_transition, decide_tombstone_action
from .result_labels import label_for_authority_transition, label_for_tombstone
from .types import EvidenceEvent


def _event_id(prefix: str, suffix: str) -> str:
    return f"{prefix}:{suffix}"


def _load_event_count(path: Path) -> int:
    if not path.exists():
        return 0
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    return len([line for line in lines if line])


def run_tombstone_propagation_flow(
    root: Path,
    *,
    signed_tombstone: bool,
    local_dirty: bool,
    authority_mode: str = "local_first",
) -> dict[str, Any]:
    result = run_mount_and_connector_flow(
        root,
        executor_cls=S3Executor,
        connector_id="s3",
        dataset_ref="ds/tombstone",
        mount_name="demo-tombstone",
        capacity_bytes=2048,
    )
    events_path = root / "events.ndjson"
    sink = EventSink(events_path)
    decision = decide_tombstone_action(
        signed_tombstone=signed_tombstone,
        local_dirty=local_dirty,
        authority_mode=authority_mode,
    )
    label = label_for_tombstone(decision)
    sink.emit(
        EvidenceEvent(
            event_id=_event_id("reconcile", "tombstone"),
            event_type="reconcile.tombstone.evaluated",
            occurred_at="2026-04-17T00:00:00Z",
            actor_ref="tester",
            workspace_ref="ws/demo",
            dataset_ref="ds/tombstone",
            policy_bundle_ref="policy/default",
            correlation_id="tombstone-flow",
            payload={
                "decision": asdict(decision),
                "result_label": label.to_dict(),
                "signed_tombstone": signed_tombstone,
                "local_dirty": local_dirty,
                "authority_mode": authority_mode,
            },
        )
    )
    result["reconcile_decision"] = asdict(decision)
    result["result_label"] = label.to_dict()
    result["event_count"] = _load_event_count(events_path)
    return result


def run_authority_transition_flow(
    root: Path,
    *,
    current_authority: str,
    requested_authority: str,
    quorum_granted: bool,
) -> dict[str, Any]:
    result = run_mount_and_connector_flow(
        root,
        executor_cls=HyperExecutor,
        connector_id="hyper",
        dataset_ref="ds/authority",
        mount_name="demo-authority",
        capacity_bytes=4096,
    )
    events_path = root / "events.ndjson"
    sink = EventSink(events_path)
    decision = decide_authority_transition(
        current_authority=current_authority,
        requested_authority=requested_authority,
        quorum_granted=quorum_granted,
    )
    label = label_for_authority_transition(decision)
    sink.emit(
        EvidenceEvent(
            event_id=_event_id("reconcile", "authority"),
            event_type="reconcile.authority_transition.evaluated",
            occurred_at="2026-04-17T00:00:00Z",
            actor_ref="tester",
            workspace_ref="ws/demo",
            dataset_ref="ds/authority",
            policy_bundle_ref="policy/default",
            correlation_id="authority-flow",
            payload={
                "decision": asdict(decision),
                "result_label": label.to_dict(),
                "current_authority": current_authority,
                "requested_authority": requested_authority,
                "quorum_granted": quorum_granted,
            },
        )
    )
    result["reconcile_decision"] = asdict(decision)
    result["result_label"] = label.to_dict()
    result["event_count"] = _load_event_count(events_path)
    return result
