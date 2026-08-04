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

import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, List, Optional, Union

import yaml

from automation.beacon_producers import propose_state_failback
from automation.durable_queue import DurableQueue, state_dir
from automation.executors import is_in_sync, vendored_graph_in_sync
from automation.macro_triad import assess_triad
from engines.mirror_drift_engine import REGISTRY_PATH, STATUS_PATH

_ROOT = Path(__file__).resolve().parents[1]
_VENDOR_REGISTER = _ROOT / "registry" / "vendor-freshness.yaml"
_VENDOR_VALIDATOR = _ROOT / "tools" / "validate_vendor_freshness.py"
_vendor_mod = None


def _vendor_compute_state():
    """Load and cache validate_vendor_freshness.compute_state (the register's own logic)."""
    global _vendor_mod
    if _vendor_mod is None:
        spec = importlib.util.spec_from_file_location("_vf_validator", _VENDOR_VALIDATOR)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _vendor_mod = mod
    return _vendor_mod.compute_state


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


def detect_stale_vendors(*, register_path: Optional[Path] = None) -> List[dict]:
    """Emit a stale_vendor beacon for each vendored artifact that is behind upstream.

    Uses the register's OWN logic (validate_vendor_freshness.compute_state) so the detector
    and the gate can never disagree. The real fix is a cross-repo re-vendor, which is not
    locally computable — so the beacon carries NO proposal: the responder caps stale_vendor at
    propose_pr and, with nothing to file, escalates to a human with the staleness report.
    `waived` artifacts (deliberately accepted staleness) are not flagged.
    """
    reg = Path(register_path) if register_path is not None else _VENDOR_REGISTER
    data = yaml.safe_load(reg.read_text("utf-8")) or {}
    sources = {
        s.get("source_id"): s
        for s in (data.get("sources") or [])
        if isinstance(s, dict) and s.get("source_id")
    }
    compute_state = _vendor_compute_state()

    beacons: List[dict] = []
    for art in (data.get("artifacts") or []):
        if not isinstance(art, dict):
            continue
        source = sources.get(art.get("source_id"))
        if not source:
            continue  # dangling source ref is the validator's problem, not ours
        state, reason = compute_state(art, source)
        if state != "stale":
            continue
        if art.get("disposition") == "waived":
            continue  # deliberately accepted staleness — don't nag
        # Carry the SCHEME-APPROPRIATE identity in typed fields, not just the prose reason:
        # a commit/digest-scheme vendor has a null vendored_version, so hardcoding the semver
        # fields left a machine reading detail.vendored_ref blind. Pick by version_scheme.
        _v, _u = {
            "semver": ("vendored_version", "upstream_latest_version"),
            "digest": ("vendored_digest", "upstream_latest_digest"),
            "commit": ("vendored_commit", "upstream_latest_commit"),
        }.get(source.get("version_scheme"), ("vendored_version", "upstream_latest_version"))
        beacons.append({
            "kind_class": "stale_vendor",
            "system": f"vendored:{art.get('artifact_id')}",
            "evidence": {
                "detector": "vendor_freshness.compute_state",
                "reproducible": True,
                "stale": False,  # the DETECTION is fresh; the SUBJECT is what's stale
            },
            "evidence_ref": "file://registry/vendor-freshness.yaml",
            "detail": {
                "artifact_id": art.get("artifact_id"),
                "source_id": art.get("source_id"),
                "consumer_repo": art.get("consumer_repo"),
                "version_scheme": source.get("version_scheme"),
                "vendored_ref": art.get(_v),
                "upstream_ref": source.get(_u),
                "disposition": art.get("disposition"),
                "state": state,
                "reason": reason,
                "remediation": "cross-repo re-vendor required (not locally computable) — human action",
            },
            "observed_at": _now(),
        })
    return beacons


_WSLOCK_TOOL = _ROOT / "tools" / "generate_workspace_resolved_lock.py"
_WSLOCK_ARTIFACT = _ROOT / "manifest" / "workspace.resolved.lock.json"


def _lock_identity(text: str) -> str:
    """Content identity of a resolved lock, ignoring the volatile generated_at timestamp."""
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return text
    if isinstance(data, dict):
        data.pop("generated_at", None)
    return json.dumps(data, sort_keys=True)


def detect_workspace_lock_drift(*, resolver_args: Optional[List[str]] = None,
                                lock_path: Optional[Path] = None) -> Optional[dict]:
    """Network-gated: propose a refresh when the committed resolved lock drifts from resolution.

    A resolved lock pins repo refs to SHAs; regenerating it tracks LIVE upstream, so it must
    NOT be silently auto-applied — the responder caps `workspace_lock_drift` at propose_pr and
    the beacon carries a computed proposal (the freshly resolved lock as the file change) for
    review. Resolution needs a resolver: `--live` (network + token) in the daemon, or a
    `--fixture-map` offline. If the resolver is unavailable, we cannot assess — emit nothing.
    """
    resolver = resolver_args if resolver_args is not None else ["--live"]
    lock = Path(lock_path) if lock_path is not None else _WSLOCK_ARTIFACT
    proc = subprocess.run(
        [sys.executable, str(_WSLOCK_TOOL), *resolver],
        cwd=str(_ROOT), capture_output=True, text=True,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        return None  # cannot resolve (network-gated) -> cannot assess -> no beacon
    fresh = proc.stdout
    try:
        committed = lock.read_text("utf-8")
    except FileNotFoundError:
        committed = ""
    if _lock_identity(fresh) == _lock_identity(committed):
        return None  # in sync (ignoring the timestamp)
    return {
        "kind_class": "workspace_lock_drift",
        "system": "workspace-resolved-lock",
        "evidence": {
            "detector": "generate_workspace_resolved_lock",
            "reproducible": True,
            "stale": False,
        },
        "evidence_ref": "file://manifest/workspace.resolved.lock.json",
        "proposal": {
            "branch": "auto/workspace-resolved-lock-refresh",
            "title": "Refresh workspace.resolved.lock.json from resolved refs",
            "body": (
                "Automated proposal: the committed resolved lock differs from a fresh "
                "resolution. This bumps pinned refs, so review the changes before merging."
            ),
            "files": {"manifest/workspace.resolved.lock.json": fresh},
        },
        "detail": {
            "artifact": "manifest/workspace.resolved.lock.json",
            "drift": "committed lock != freshly resolved lock (excluding generated_at)",
        },
        "observed_at": _now(),
    }


_SOURCE_EXPOSURE_REPORT = _ROOT / "artifacts" / "source-exposure" / "source-exposure-report.json"


def detect_policy_violations(*, report_path: Optional[Path] = None) -> List[dict]:
    """Emit a policy_violation beacon when the source-exposure gate reports a blocking finding.

    Reads the gate's committed report (block count) rather than re-scanning every cycle — cheap
    and non-destructive. A violation is a policy breach: the responder caps policy_violation at
    quarantine (isolate + record), never a fix. No report -> cannot assess -> nothing.
    """
    path = Path(report_path) if report_path is not None else _SOURCE_EXPOSURE_REPORT
    try:
        report = json.loads(path.read_text("utf-8"))
    except (FileNotFoundError, ValueError):
        return []
    block = int(report.get("block", 0) or 0)
    if report.get("result") == "pass" and block == 0:
        return []
    return [{
        "kind_class": "policy_violation",
        "system": "policy:source-exposure",
        "evidence": {"detector": "check_source_exposure", "reproducible": True, "stale": False},
        "evidence_ref": f"file://{path}",
        "detail": {
            "check": "source-exposure",
            "result": report.get("result"),
            "block": block,
            "warn": report.get("warn"),
            "reason": f"source-exposure gate reports {block} blocking finding(s)",
        },
        "observed_at": _now(),
    }]


def _latest_failed_workflows_on_main() -> List[dict]:
    """Latest run per workflow on main, keeping only those whose newest run FAILED (via gh)."""
    proc = subprocess.run(
        ["gh", "run", "list", "--branch", "main", "--limit", "40",
         "--json", "name,conclusion,headSha,createdAt,url"],
        cwd=str(_ROOT), capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return []  # gh unavailable / no token -> network-gated -> no beacons
    try:
        runs = json.loads(proc.stdout or "[]")
    except ValueError:
        return []
    latest: dict = {}
    for run in sorted(runs, key=lambda r: r.get("createdAt", ""), reverse=True):
        name = run.get("name")
        if name and name not in latest:
            latest[name] = run
    return [r for r in latest.values() if r.get("conclusion") == "failure"]


def detect_build_failures(*, runs_source=None) -> List[dict]:
    """Emit a build_failure beacon per workflow whose latest run on main failed.

    Network-gated (default source queries `gh`). A build failure is not locally fixable, so it
    caps at canary_fix with no mechanism -> escalates to a human with the failing run.
    """
    runs = (runs_source or _latest_failed_workflows_on_main)()
    beacons: List[dict] = []
    for run in runs:
        name = run.get("name", "?")
        beacons.append({
            "kind_class": "build_failure",
            "system": f"ci:{name}",
            "evidence": {"detector": "gh_run_list", "reproducible": True, "stale": False},
            "evidence_ref": run.get("url"),
            "detail": {"workflow": name, "conclusion": "failure", "run_url": run.get("url")},
            "observed_at": _now(),
        })
    return beacons


_LAZERUS_TRIAD_RECEIPTS = _ROOT / "status" / "lazerus-triad-receipts.json"
_DEFAULT_INFRA_REPO = "SocioProphet/prophet-platform"


def detect_macro_triad_divergence(*, receipts_path: Optional[Path] = None) -> List[dict]:
    """SENSE the k3s master triad: emit a failback beacon when a master diverged from the quorum.

    Reads the masters' published Lazerus Integrity Receipts (a producer writes this file — the
    three k3s HA masters each attest the state they serve) and drives the macro-triad closure:

      - file absent / unreadable    -> emit NOTHING (no receipts published yet = cannot assess;
                                       producer-gated, exactly like the network-gated detectors)
      - healthy triad               -> propose_state_failback returns [] -> emit NOTHING
      - a master diverged + quorum   -> the quorum-gated failback beacon(s) (a reviewed revert of
                                       the sick master back to the last quorum-blessed state)
      - split-brain, NO quorum       -> a WARRANTLESS beacon (no evidence, no proposal): a real,
                                       serious condition we can SEE but cannot warrant a fix for
                                       (no quorum = no trusted target) -> responder escalates to a
                                       human. Fail-closed: we never guess a target.

    This is the piece that makes the #587 actuator actually fire in the live loop. Until a
    producer publishes the receipts file it is a safe no-op — wired and dormant, not inert.
    """
    path = Path(receipts_path) if receipts_path is not None else _LAZERUS_TRIAD_RECEIPTS
    try:
        doc = json.loads(path.read_text("utf-8"))
    except (FileNotFoundError, ValueError):
        return []  # no receipts published -> cannot assess -> nothing (producer-gated)
    if not isinstance(doc, dict):
        return []
    receipts = doc.get("receipts")
    if not isinstance(receipts, list) or not receipts:
        return []
    repo = doc.get("repo") or _DEFAULT_INFRA_REPO
    try:
        quorum = int(doc.get("quorum", 2) or 2)
    except (TypeError, ValueError):
        quorum = 2

    # ACTUATE: quorum-gated failback(s) for any master that diverged from the canonical state.
    beacons = propose_state_failback(receipts, repo=repo, quorum=quorum)
    if beacons:
        return beacons

    # No failback proposed. Either the triad is healthy (nothing to do) OR it is split-brain with
    # no quorum — a condition propose_state_failback correctly refuses to act on (no trusted
    # target). Surface the latter warrantlessly so a human is paged instead of silence.
    assessment = assess_triad(receipts, quorum=quorum)
    # Page a human only when enough masters reported that a quorum SHOULD have formed but did not
    # (a genuine split-brain), not when the report is merely incomplete (fewer than `quorum`
    # masters have checked in yet — a liveness/producer concern, handled elsewhere).
    if not assessment.quorum_ok and len(receipts) >= quorum:
        return [{
            "kind_class": "deploy_regression",
            "system": f"{repo}::macro-triad",
            # NO evidence + NO proposal on purpose: we see the split-brain but cannot warrant a
            # failback (no quorum) -> the responder routes this to a human, never auto-acts.
            "detail": {
                "condition": "split-brain: no k3s master quorum -> no trusted failback target",
                "sick": [s.cluster for s in assessment.sick_clusters],
                "reasons": list(assessment.reasons),
            },
            "observed_at": _now(),
        }]
    return []  # healthy triad — nothing to heal


# Registered detectors: each is a keyword-arg callable returning None, a beacon, or a list.
DETECTORS: List[Callable[..., Union[None, dict, List[dict]]]] = [
    detect_mirror_drift,
    detect_vendored_graph_drift,
    detect_stale_vendors,
    detect_workspace_lock_drift,
    detect_policy_violations,
    detect_build_failures,
    detect_macro_triad_divergence,
]


def run_detectors(inbox: Optional[DurableQueue] = None,
                  detector_paths: Optional[dict] = None,
                  detectors: Optional[List[Callable[..., Optional[dict]]]] = None) -> List[dict]:
    """Run each registered detector; enqueue every emitted beacon. Returns the beacons.

    `detector_paths` is forwarded to detectors that accept them (a detector that does not is
    called with no arguments). `detectors` overrides the default registry — used by tests to
    run one detector in isolation so an unrelated real-tree detector is not triggered.
    """
    from automation import envelope

    inbox = inbox if inbox is not None else DurableQueue(state_dir() / "beacons")
    emitted: List[dict] = []
    for detector in (detectors if detectors is not None else DETECTORS):
        try:
            result = detector(**(detector_paths or {}))
        except TypeError:
            result = detector()
        if result is None:
            continue
        for beacon in (result if isinstance(result, list) else [result]):
            beacon = envelope.stamp(beacon)  # canonical envelope: message_id/trace_id/span_id/...
            inbox.put(beacon)
            emitted.append(beacon)
    return emitted
