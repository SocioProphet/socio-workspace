"""Executors — carry out the responder's decisions, with verify-and-rollback.

The responder DECIDES (auto_fix / canary_fix / propose_pr / ...); executors ACT. This is
the first real executor: the mirror-drift re-sync. Everything here obeys the estate maxims:

  - verify the ARTIFACT, not the exit code: after regenerating, we re-check the invariant
    actually holds. A fix that cannot be verified is not a fix.
  - a control that acts when nothing is wrong is suspect: if there is no drift, no-op.
  - never make it worse: if we cannot safely produce a verified fix, we roll back to the
    pre-existing artifact and report failure (which the responder escalates to a human).

The drift invariant (from engines/mirror_drift_engine.py):
    status/mirror-drift.yaml  ==  build_payload(registry/external-mirrors.yaml)
i.e. the derived artifact must equal what the registry (the source of truth) derives. The
re-sync regenerates the derived artifact from the registry, then verifies the invariant.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

from engines.mirror_drift_engine import (
    REGISTRY_PATH,
    STATUS_HEADER,
    STATUS_PATH,
    build_payload,
)


def _load(path: Path):
    return yaml.safe_load(Path(path).read_text("utf-8"))


def is_in_sync(registry_path: Path, status_path: Path) -> bool:
    """True iff the derived artifact equals build_payload(registry) — the drift invariant.

    Raises if the registry (source of truth) cannot be read or does not parse to a
    MAPPING: a registry that decodes to a non-mapping (e.g. YAML ``[]`` or a bare
    scalar) is un-assessable, not empty — treating it as ``{}`` would let a corrupted
    source silently overwrite a good artifact, so callers must refuse to act.

    A missing, unreadable, or non-mapping STATUS artifact simply means "out of sync"
    (return False): the artifact is derived, so it is safe to regenerate it from the
    readable source of truth rather than abort on a broken derivative.
    """
    status_path = Path(status_path)
    if not status_path.exists():
        return False
    registry = _load(registry_path)
    if not isinstance(registry, dict):
        raise ValueError(
            f"registry {registry_path} did not parse to a mapping "
            f"(got {type(registry).__name__}) — un-assessable, refusing to act"
        )
    expected = build_payload(registry)  # raises on malformed registry
    try:
        current = _load(status_path)
    except Exception:
        return False  # unreadable status ⇒ out of sync; regenerate from the source of truth
    if not isinstance(current, dict):
        return False  # non-mapping status ⇒ out of sync
    return current == expected


def _rollback(status_path: Path, had_prior: bool, prior: Optional[bytes]) -> None:
    status_path = Path(status_path)
    if had_prior and prior is not None:
        status_path.write_bytes(prior)
    elif status_path.exists():
        status_path.unlink()


def resync_mirror_drift(*, registry_path: Path = REGISTRY_PATH,
                        status_path: Path = STATUS_PATH) -> dict:
    """Re-sync the derived mirror-drift artifact to the registry source of truth.

    Returns a result dict: {executor, action_taken, healed, rolled_back, [error]}.
    action_taken ∈ {noop, regenerated, abort}.
    """
    registry_path = Path(registry_path)
    status_path = Path(status_path)
    result = {
        "executor": "resync_mirror_drift",
        "action_taken": "none",
        "healed": False,
        "rolled_back": False,
    }

    # 1. Idempotence + source-of-truth readability. If already in sync, do nothing.
    #    If the registry can't even be assessed, refuse to act (preserve the artifact).
    try:
        if is_in_sync(registry_path, status_path):
            result["action_taken"] = "noop"
            result["healed"] = True
            return result
    except Exception as exc:
        result["action_taken"] = "abort"
        result["error"] = f"cannot assess drift (source of truth unreadable): {exc}"
        return result

    # 2. Snapshot the existing artifact for rollback.
    had_prior = status_path.exists()
    prior = status_path.read_bytes() if had_prior else None

    # 3. Regenerate from the source of truth.
    try:
        registry = _load(registry_path) or {}
        payload = build_payload(registry)
        status_path.parent.mkdir(parents=True, exist_ok=True)
        body = yaml.safe_dump(payload, sort_keys=False, default_flow_style=False)
        status_path.write_text(STATUS_HEADER + body, encoding="utf-8")
        result["action_taken"] = "regenerated"
    except Exception as exc:
        _rollback(status_path, had_prior, prior)
        result["action_taken"] = "abort"
        result["rolled_back"] = True
        result["error"] = f"regeneration failed: {exc}"
        return result

    # 4. VERIFY the artifact (not the exit code). If the invariant does not now hold,
    #    roll back — we must never leave a worse artifact than we found.
    try:
        healed = is_in_sync(registry_path, status_path)
    except Exception as exc:
        healed = False
        result["error"] = f"post-write verification error: {exc}"

    if healed:
        result["healed"] = True
        return result

    _rollback(status_path, had_prior, prior)
    result["rolled_back"] = True
    result["healed"] = False
    result.setdefault("error", "post-write verification failed; rolled back")
    return result
