"""Detectors — the SENSE stage: turn a real failure into an evidence-bearing beacon.

This closes the hole at the front of the self-heal spine. Until now the only beacon
emitter was `observe_and_beacon`, which produced a warrantless beacon (no kind_class, no
evidence) — so every real signal decided to BOTTOM -> human, and the decide/act/verify
machinery never fired. A detector observes a specific failure class and emits a beacon
carrying a WARRANT (what was checked, whether it reproduces), which the responder can
actually reason about.

First detector: mirror drift. The invariant (engines/mirror_drift_engine.py) is
    status/mirror-drift.yaml == build_payload(registry/external-mirrors.yaml)
A detector must be honest three ways:
  - in sync            -> emit NOTHING (a control that fires when nothing is wrong is suspect)
  - drift, source OK   -> emit a mirror_drift beacon WITH evidence (detector auto-heals it)
  - source unreadable  -> emit a mirror_drift beacon WITHOUT evidence (we see trouble but
                          cannot warrant a fix -> the responder routes it to a human)
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, List, Optional

from automation.durable_queue import DurableQueue, state_dir
from automation.executors import is_in_sync, vendored_graph_in_sync
from engines.mirror_drift_engine import REGISTRY_PATH, STATUS_PATH


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def detect_mirror_drift(*, registry_path: Path = REGISTRY_PATH,
                        status_path: Path = STATUS_PATH) -> Optional[dict]:
    """Return a mirror_drift beacon if drift is detected, else None.

    Evidence is claimed only when it is honest: `is_in_sync` is a pure, deterministic
    function of the two files, so a drift verdict reproduces on re-read — we assert it by
    reading twice and only claiming `reproducible` when the two reads agree.
    """
    try:
        first = is_in_sync(registry_path, status_path)
        second = is_in_sync(registry_path, status_path)
    except Exception as exc:
        # The source of truth cannot be assessed. We can see something is wrong but cannot
        # warrant an automatic fix — emit a warrantless beacon so the responder escalates.
        return {
            "kind_class": "mirror_drift",
            "system": "external-mirrors",
            "detail": {"assessable": False, "error": str(exc)},
            "observed_at": _now(),
        }

    if first:
        return None  # in sync — nothing to heal, nothing to beacon

    reproducible = (first == second)
    return {
        "kind_class": "mirror_drift",
        "system": "external-mirrors",
        "evidence": {
            "detector": "mirror_drift_engine.check",
            "reproducible": reproducible,
            "stale": False,
        },
        "evidence_ref": f"file://{Path(status_path)}",
        "detail": {
            "invariant": "status/mirror-drift.yaml == build_payload(registry/external-mirrors.yaml)",
            "in_sync": False,
        },
        "observed_at": _now(),
    }


def detect_vendored_graph_drift() -> Optional[dict]:
    """Return a vendored_graph_drift beacon if the committed graph has drifted, else None.

    Invariant (tools/check_vendored_artifact_graph.py): the committed
    registry/.../vendored-artifact.graph.ttl equals what the lift regenerates from
    registry/vendor-freshness.yaml. `vendored_graph_in_sync` is deterministic, so a drift
    verdict reproduces on re-check — claimed via a double check.
    """
    first = vendored_graph_in_sync()
    second = vendored_graph_in_sync()
    if first:
        return None
    return {
        "kind_class": "vendored_graph_drift",
        "system": "vendored-artifact-graph",
        "evidence": {
            "detector": "check_vendored_artifact_graph",
            "reproducible": (first == second),
            "stale": False,
        },
        "evidence_ref": "file://registry/neurosymbolic-repo-graph-reasoner/vendored-artifact.graph.ttl",
        "detail": {
            "invariant": "vendored-artifact.graph.ttl == lift(registry/vendor-freshness.yaml)",
            "in_sync": False,
        },
        "observed_at": _now(),
    }


# Registered detectors: each is a zero/keyword-arg callable returning Optional[beacon].
DETECTORS: List[Callable[..., Optional[dict]]] = [detect_mirror_drift, detect_vendored_graph_drift]


def run_detectors(inbox: Optional[DurableQueue] = None,
                  detector_paths: Optional[dict] = None,
                  detectors: Optional[List[Callable[..., Optional[dict]]]] = None) -> List[dict]:
    """Run each registered detector; enqueue every emitted beacon. Returns the beacons.

    `detector_paths` is forwarded to detectors that accept them (a detector that does not is
    called with no arguments). `detectors` overrides the default registry — used by tests to
    run one detector in isolation so an unrelated real-tree detector is not triggered.
    """
    inbox = inbox if inbox is not None else DurableQueue(state_dir() / "beacons")
    emitted: List[dict] = []
    for detector in (detectors if detectors is not None else DETECTORS):
        try:
            beacon = detector(**(detector_paths or {}))
        except TypeError:
            beacon = detector()
        if beacon is not None:
            inbox.put(beacon)
            emitted.append(beacon)
    return emitted
