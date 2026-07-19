from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from .events import EventSink
from .integration_common import run_mount_and_connector_flow
from .connectors.s3 import S3Executor
from .reconcile import decide_stale_mirror_action
from .result_labels import label_for_stale_mirror
from .types import EvidenceEvent


def run_stale_mirror_flow(
    root: Path,
    *,
    stale_generation_gap: int,
    policy_allow_stale: bool,
    authority_mode: str = "local_first",
) -> dict[str, Any]:
    result = run_mount_and_connector_flow(
        root,
        executor_cls=S3Executor,
        connector_id="s3",
        dataset_ref="ds/stale-mirror",
        mount_name="demo-stale-mirror",
        capacity_bytes=2048,
    )
    events_path = root / "events.ndjson"
    sink = EventSink(events_path)
    decision = decide_stale_mirror_action(
        stale_generation_gap=stale_generation_gap,
        policy_allow_stale=policy_allow_stale,
        authority_mode=authority_mode,
    )
    label = label_for_stale_mirror(decision)
    sink.emit(
        EvidenceEvent(
            event_id="reconcile:stale-mirror",
            event_type="reconcile.stale_mirror.evaluated",
            occurred_at="2026-04-17T00:00:00Z",
            actor_ref="tester",
            workspace_ref="ws/demo",
            dataset_ref="ds/stale-mirror",
            policy_bundle_ref="policy/default",
            correlation_id="stale-mirror-flow",
            payload={
                "decision": asdict(decision),
                "result_label": label.to_dict(),
                "stale_generation_gap": stale_generation_gap,
                "policy_allow_stale": policy_allow_stale,
                "authority_mode": authority_mode,
            },
        )
    )
    event_lines = events_path.read_text(encoding="utf-8").strip().splitlines()
    result["reconcile_decision"] = asdict(decision)
    result["result_label"] = label.to_dict()
    result["event_count"] = len([line for line in event_lines if line])
    return result
