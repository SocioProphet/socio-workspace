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

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

import yaml

from engines.mirror_drift_engine import (
    REGISTRY_PATH,
    STATUS_HEADER,
    STATUS_PATH,
    build_payload,
)

_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Generic reconciler: the reusable shape behind "a derived artifact drifted from
# its source of truth; regenerate it, then VERIFY, and roll back if that fails".
# resync_mirror_drift below is the in-process special case; new reconcilable
# artifacts (e.g. the vendored-artifact graph) register a Reconciler and reuse
# reconcile() rather than re-implementing verify+rollback.
# ---------------------------------------------------------------------------


@dataclass
class Reconciler:
    """A derived artifact that can be regenerated from a source and verified.

    check       : returns True iff the artifact is in sync. MAY RAISE when the source
                  of truth is un-assessable — reconcile() treats that as refuse-to-act.
    regenerate  : rebuild the derived artifact from the source. May raise.
    artifacts   : files to snapshot so a failed regeneration can be rolled back.
    """

    name: str
    check: Callable[[], bool]
    regenerate: Callable[[], None]
    artifacts: List[Path] = field(default_factory=list)


def _snapshot(paths: List[Path]) -> dict:
    return {Path(p): (Path(p).read_bytes() if Path(p).exists() else None) for p in paths}


def _restore(snapshot: dict) -> None:
    for path, prior in snapshot.items():
        if prior is not None:
            path.write_bytes(prior)
        elif path.exists():
            path.unlink()


def reconcile(r: Reconciler) -> dict:
    """Regenerate a drifted artifact and verify the fix, rolling back on failure.

    Returns {executor, action_taken ∈ {noop,regenerated,abort}, healed, rolled_back, [error]}.
    """
    result = {"executor": r.name, "action_taken": "none", "healed": False, "rolled_back": False}

    # 1. Idempotence + source readability. In sync -> nothing to do. Un-assessable -> abort.
    try:
        if r.check():
            result["action_taken"] = "noop"
            result["healed"] = True
            return result
    except Exception as exc:
        result["action_taken"] = "abort"
        result["error"] = f"cannot assess (source of truth unreadable): {exc}"
        return result

    # 2. Snapshot for rollback.
    snapshot = _snapshot(r.artifacts)

    # 3. Regenerate from the source of truth.
    try:
        r.regenerate()
        result["action_taken"] = "regenerated"
    except Exception as exc:
        _restore(snapshot)
        result["action_taken"] = "abort"
        result["rolled_back"] = True
        result["error"] = f"regeneration failed: {exc}"
        return result

    # 4. VERIFY the artifact (not the exit code). Roll back if the invariant does not hold.
    try:
        healed = bool(r.check())
    except Exception as exc:
        healed = False
        result["error"] = f"post-regeneration verification error: {exc}"

    if healed:
        result["healed"] = True
        return result

    _restore(snapshot)
    result["rolled_back"] = True
    result.setdefault("error", "post-regeneration verification failed; rolled back")
    return result


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


# ---------------------------------------------------------------------------
# Second reconcilable artifact: the vendored-artifact graph. Its invariant
# (tools/check_vendored_artifact_graph.py) is that the committed
# registry/neurosymbolic-repo-graph-reasoner/vendored-artifact.graph.ttl equals
# what tools/lift_vendor_freshness_to_graph.py regenerates from
# registry/vendor-freshness.yaml. The check and the lift are separate CLIs, so
# this reconciler drives them as subprocesses — and VERIFIES by re-running the
# check, never by trusting the lift's exit code.
# ---------------------------------------------------------------------------

_VG_CHECK = _ROOT / "tools" / "check_vendored_artifact_graph.py"
_VG_LIFT = _ROOT / "tools" / "lift_vendor_freshness_to_graph.py"
VENDORED_GRAPH_PATH = (
    _ROOT / "registry" / "neurosymbolic-repo-graph-reasoner" / "vendored-artifact.graph.ttl"
)


def vendored_graph_in_sync() -> bool:
    """True iff the committed vendored-artifact graph matches the lift output."""
    proc = subprocess.run(
        [sys.executable, str(_VG_CHECK)], cwd=str(_ROOT), capture_output=True, text=True
    )
    return proc.returncode == 0


def _vendored_graph_regenerate() -> None:
    proc = subprocess.run(
        [sys.executable, str(_VG_LIFT), "--write"], cwd=str(_ROOT), capture_output=True, text=True
    )
    if proc.returncode != 0:
        raise RuntimeError(f"lift failed (rc={proc.returncode}): {proc.stderr.strip()[:200]}")


def vendored_graph_reconciler() -> Reconciler:
    return Reconciler(
        name="reconcile_vendored_graph",
        check=vendored_graph_in_sync,
        regenerate=_vendored_graph_regenerate,
        artifacts=[VENDORED_GRAPH_PATH],
    )


def reconcile_vendored_graph() -> dict:
    """Executor entry point for a vendored_graph_drift auto_fix decision."""
    return reconcile(vendored_graph_reconciler())


# ---------------------------------------------------------------------------
# propose_pr executor: for cross-repo / low-confidence decisions the responder
# caps at propose_pr (never auto-act). SAFE BY DEFAULT — the always-on daemon
# holds no GitHub write credentials, so it RECORDS a durable, reviewable proposal
# (branch, base, files, title, body, provenance) to state/proposals/ for a human
# or a credentialed CI job to open. When an `opener` is explicitly injected (a
# credentialed context), it opens the PR instead. It NEVER auto-applies to main.
# This keeps outward-facing action out of the autonomous loop (secrets minted in
# CI, not a standing PAT in a daemon).
# ---------------------------------------------------------------------------

import hashlib as _hashlib
import json as _json

from automation.durable_queue import DurableQueue, state_dir


def _proposal_id(proposal: dict) -> str:
    blob = _json.dumps(proposal, sort_keys=True, ensure_ascii=True).encode("utf-8")
    return _hashlib.sha256(blob).hexdigest()[:16]


def _valid_proposal(p) -> bool:
    """A proposal must name a branch, a title, and at least one file change."""
    return (
        isinstance(p, dict)
        and bool(p.get("title"))
        and bool(p.get("branch"))
        and isinstance(p.get("files"), dict)
        and len(p["files"]) > 0
    )


def propose_pr(*, beacon: dict, proposals_dir: Optional[Path] = None, opener=None) -> dict:
    """Record (default) or open (when a credentialed opener is injected) a PR proposal.

    Returns {executor, proposed, opened, [proposal_ref|pr_url|error]}. `proposed` True means
    the situation is resolved into a human-reviewable path; the responder does NOT escalate a
    successful proposal. A missing/invalid proposal or a failed open leaves proposed False, so
    the responder escalates to a human.
    """
    result = {"executor": "propose_pr", "proposed": False, "opened": False}

    proposal = beacon.get("proposal")
    if not _valid_proposal(proposal):
        result["error"] = "beacon carries no valid proposal (need title, branch, files)"
        return result

    proposal = {"base": "main", **proposal}  # default base branch
    pid = _proposal_id(proposal)
    result["proposal_ref"] = pid

    if opener is not None:
        # Credentialed context: actually open the PR. Never invoked by the default daemon.
        try:
            pr_url = opener(proposal)
        except Exception as exc:
            result["error"] = f"pr opener failed: {exc}"
            return result
        result["proposed"] = True
        result["opened"] = True
        result["pr_url"] = pr_url
        return result

    # Default: durably record the proposal; do not open (no standing creds in the daemon).
    directory = Path(proposals_dir) if proposals_dir is not None else state_dir() / "proposals"
    DurableQueue(directory).put(
        {
            "id": pid,
            "proposal": proposal,
            "beacon_kind": beacon.get("kind_class"),
            "system": beacon.get("system"),
            "evidence_ref": beacon.get("evidence_ref"),
        }
    )
    result["proposed"] = True
    return result


# ---------------------------------------------------------------------------
# quarantine executor: for a policy_violation (verdict quarantine) the responder
# must ISOLATE, never auto-fix. This records a durable quarantine marker for the
# subject so it is contained and visible (a human, and downstream tooling, can see
# it is quarantined) — the honest "isolate, don't fix, don't ignore" action.
# ---------------------------------------------------------------------------

from datetime import datetime as _dt, timezone as _tz


def quarantine(*, beacon: dict, quarantine_dir: Optional[Path] = None) -> dict:
    """Isolate a subject by recording a durable quarantine marker. Returns {quarantined}."""
    result = {"executor": "quarantine", "quarantined": False}
    subject = beacon.get("system")
    if not subject:
        result["error"] = "beacon has no subject (system) to quarantine"
        return result
    directory = Path(quarantine_dir) if quarantine_dir is not None else state_dir() / "quarantine"
    DurableQueue(directory).put({
        "subject": subject,
        "kind_class": beacon.get("kind_class"),
        "reason": (beacon.get("detail") or {}).get("reason") or beacon.get("reason"),
        "evidence_ref": beacon.get("evidence_ref"),
        "quarantined_at": _dt.now(_tz.utc).isoformat(),
    })
    result["quarantined"] = True
    result["subject"] = subject
    return result


# ---------------------------------------------------------------------------
# canary_fix executor: "prove the fix mechanism on a canary, then apply". Before
# touching the real artifact at probable (not sealed) confidence, run the SAME fix
# against a synthetic guaranteed-input -> provable-output case. If the canary heals
# as expected, the mechanism is trusted and we apply to the real target (with the
# executor's own verify + rollback). If the canary fails, the mechanism itself is
# suspect: we do NOT touch the real artifact and the responder escalates.
# Only classes with a clean isolated canary are registered; others escalate.
# ---------------------------------------------------------------------------

_CANARY_REGISTRY = """version: "1.0.0"
updated_at: "2026-01-01"
mirrors:
  - name: canary
    org: Canary
    url: https://example.invalid/canary
    upstream:
      url: https://example.invalid/upstream
      ref: main
      head_sha: deadbeefdeadbeefdeadbeefdeadbeefdeadbeef
      checked_at: "2026-01-01"
    mirror_head_sha: cafebabecafebabecafebabecafebabecafebabe
    drift:
      status: behind
      note: canary
"""


def _mirror_drift_canary() -> bool:
    """Guaranteed input -> provable output: resync must heal a synthetic drift on disk."""
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        reg = Path(d) / "registry.yaml"
        status = Path(d) / "status.yaml"
        reg.write_text(_CANARY_REGISTRY, encoding="utf-8")
        # induce drift: no status artifact -> a working resync must create the correct one
        res = resync_mirror_drift(registry_path=reg, status_path=status)
        return bool(res.get("healed")) and is_in_sync(reg, status)


# kind_class -> (canary_fn, apply_fn). apply_fn receives the executor_paths kwargs.
_CANARY_FIX = {
    "mirror_drift": (_mirror_drift_canary, resync_mirror_drift),
}


def canary_fix(*, beacon: dict, **apply_kwargs) -> dict:
    """Canary the fix mechanism, then apply to the real artifact; escalate if unproven."""
    kind = beacon.get("kind_class")
    entry = _CANARY_FIX.get(kind)
    if entry is None:
        return {"executor": "canary_fix", "healed": False, "canary_passed": False,
                "error": f"no canary mechanism for class {kind!r} — cannot prove a fix"}
    canary_fn, apply_fn = entry
    try:
        passed = bool(canary_fn())
    except Exception as exc:  # pragma: no cover - defensive
        return {"executor": "canary_fix", "healed": False, "canary_passed": False,
                "error": f"canary raised: {exc}"}
    if not passed:
        return {"executor": "canary_fix", "healed": False, "canary_passed": False,
                "error": "canary failed: fix mechanism not trusted, real artifact untouched"}
    result = apply_fn(**apply_kwargs)
    result["canary_passed"] = True
    return result
