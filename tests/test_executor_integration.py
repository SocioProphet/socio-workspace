"""Live break -> heal / break -> abort proof for the first real executor.

The mirror-drift re-sync is the first place a responder decision becomes a real filesystem
effect. These tests induce a REAL break on real files (in a tmp dir) and prove teeth both
ways at the EXECUTOR level:

  - break the DERIVED artifact (stale status), registry valid  -> the executor HEALS it,
    and the fix is VERIFIED by re-checking the invariant (not by trusting an exit code).
  - break the SOURCE OF TRUTH (corrupt registry)              -> the executor ABORTS and
    the good artifact is preserved byte-for-byte (never make it worse).
  - no drift                                                  -> no-op (a control that acts
    when nothing is wrong is suspect).
  - verification failure after a write                        -> rollback restores the prior
    artifact.

Plus the wired path: responder.run_once(execute=True) drives the executor end-to-end.
"""

import textwrap

import pytest

from automation import executors
from engines.mirror_drift_engine import STATUS_HEADER, build_payload

import yaml


VALID_REGISTRY = textwrap.dedent(
    """\
    version: "1.0.0"
    updated_at: "2026-08-01"
    mirrors:
      - name: socios-installer
        org: SociOS-Linux
        url: https://github.com/SociOS-Linux/socios-installer
        upstream:
          url: https://github.com/coreos/coreos-installer
          ref: main
          head_sha: aaaa1111
          checked_at: "2026-08-01"
        mirror_head_sha: bbbb2222
        drift:
          status: behind
          note: "needs sync"
    """
)


def _write(path, text):
    path.write_text(text, encoding="utf-8")


def _correct_status_text(registry_path):
    registry = yaml.safe_load(registry_path.read_text("utf-8"))
    payload = build_payload(registry)
    return STATUS_HEADER + yaml.safe_dump(payload, sort_keys=False, default_flow_style=False)


@pytest.fixture
def files(tmp_path):
    reg = tmp_path / "external-mirrors.yaml"
    status = tmp_path / "mirror-drift.yaml"
    _write(reg, VALID_REGISTRY)
    return reg, status


# --- heal direction ---------------------------------------------------------

def test_resync_heals_drifted_derived_artifact(files):
    reg, status = files
    # BREAK: write a stale/wrong derived artifact.
    _write(status, STATUS_HEADER + "version: '0.0.0'\nmirrors: []\n")
    assert not executors.is_in_sync(reg, status)  # genuinely drifted

    result = executors.resync_mirror_drift(registry_path=reg, status_path=status)

    assert result["action_taken"] == "regenerated"
    assert result["healed"] is True
    # VERIFY THE ARTIFACT: the invariant now holds, independently re-derived.
    assert executors.is_in_sync(reg, status)
    assert status.read_text("utf-8") == _correct_status_text(reg)


def test_resync_is_noop_when_in_sync(files):
    reg, status = files
    _write(status, _correct_status_text(reg))
    before = status.read_bytes()

    result = executors.resync_mirror_drift(registry_path=reg, status_path=status)

    assert result["action_taken"] == "noop"
    assert result["healed"] is True
    assert status.read_bytes() == before  # did not churn a healthy artifact


def test_resync_generates_when_artifact_missing(files):
    reg, status = files  # status does not exist yet
    assert not status.exists()

    result = executors.resync_mirror_drift(registry_path=reg, status_path=status)

    assert result["action_taken"] == "regenerated"
    assert result["healed"] is True
    assert executors.is_in_sync(reg, status)


# --- abort direction (teeth) ------------------------------------------------

def test_resync_aborts_and_preserves_good_artifact_on_corrupt_source(files):
    reg, status = files
    good = _correct_status_text(reg)
    _write(status, good)
    # BREAK THE SOURCE OF TRUTH: corrupt the registry so it cannot be derived.
    _write(reg, "version: '1.0.0'\nmirrors: : : not a list\n  - broken")

    result = executors.resync_mirror_drift(registry_path=reg, status_path=status)

    assert result["healed"] is False
    assert result["action_taken"] == "abort"
    # NEVER MAKE IT WORSE: the good derived artifact is untouched.
    assert status.read_text("utf-8") == good


def test_resync_aborts_on_non_mapping_registry(files):
    reg, status = files
    good = _correct_status_text(reg)
    _write(status, good)
    _write(reg, "just a string, not a mapping")

    result = executors.resync_mirror_drift(registry_path=reg, status_path=status)

    assert result["healed"] is False
    assert result["action_taken"] == "abort"
    assert status.read_text("utf-8") == good


def test_resync_aborts_on_falsey_non_mapping_registry(files):
    # A registry that decodes to a FALSEY non-mapping (YAML `[]`) must be treated as
    # un-assessable, not as an empty mapping — otherwise a corrupted source could
    # silently overwrite a good artifact. This is the case the old `_load() or {}` masked.
    reg, status = files
    good = _correct_status_text(reg)
    _write(status, good)
    _write(reg, "[]\n")

    result = executors.resync_mirror_drift(registry_path=reg, status_path=status)

    assert result["healed"] is False
    assert result["action_taken"] == "abort"
    assert status.read_text("utf-8") == good  # good artifact preserved


def test_resync_regenerates_when_status_is_unreadable(files):
    # The registry is readable (source of truth intact) but the DERIVED status
    # artifact is corrupt YAML — that just means out of sync, so regenerate it.
    reg, status = files
    _write(status, "this: : : is not valid yaml\n  - broken")

    assert executors.is_in_sync(reg, status) is False
    result = executors.resync_mirror_drift(registry_path=reg, status_path=status)

    assert result["healed"] is True
    assert result["action_taken"] == "regenerated"
    assert executors.is_in_sync(reg, status)


def test_verification_failure_after_write_rolls_back(files, monkeypatch):
    """If regeneration writes but the post-write verification fails, restore the prior file.

    We force the branch by making build_payload succeed for the drift assessment and the
    write, then fail the post-write verification — proving the rollback path is real.
    """
    reg, status = files
    prior = STATUS_HEADER + "version: '9.9.9'\nmirrors: []\n"
    _write(status, prior)

    real_build = executors.build_payload
    calls = {"n": 0}

    def flaky(registry):
        calls["n"] += 1
        # calls 1 (assess) and 2 (write) succeed; call 3 (post-write verify) raises.
        if calls["n"] >= 3:
            raise RuntimeError("injected verification failure")
        return real_build(registry)

    monkeypatch.setattr(executors, "build_payload", flaky)

    result = executors.resync_mirror_drift(registry_path=reg, status_path=status)

    assert result["healed"] is False
    assert result["rolled_back"] is True
    assert status.read_text("utf-8") == prior  # prior artifact restored


# --- wired path: responder.run_once(execute=True) drives the executor -------

def test_run_once_execute_drives_resync_end_to_end(tmp_path, monkeypatch):
    from automation.durable_queue import DurableQueue, state_dir
    from automation import responder

    monkeypatch.setenv("SOCIOSPHERE_STATE_DIR", str(tmp_path / "state"))
    reg = tmp_path / "external-mirrors.yaml"
    status = tmp_path / "mirror-drift.yaml"
    _write(reg, VALID_REGISTRY)
    _write(status, STATUS_HEADER + "version: '0.0.0'\nmirrors: []\n")  # drifted

    inbox = DurableQueue(state_dir() / "beacons")
    decisions = DurableQueue(state_dir() / "decisions")
    inbox.put({
        "kind_class": "mirror_drift",
        "system": "external-mirrors",
        "evidence": {"detector": "mirror_drift_engine", "reproducible": True, "stale": False},
        "evidence_ref": "ev://drift",
    })

    out = responder.run_once(
        inbox=inbox, decisions=decisions, execute=True,
        executor_paths={"registry_path": reg, "status_path": status},
    )

    assert len(out) == 1
    r = out[0]
    assert r["action"] == "auto_fix"           # decided auto_fix
    assert r["execution"]["healed"] is True    # and actually healed
    assert executors.is_in_sync(reg, status)   # verified on disk


def test_run_once_execute_escalates_when_executor_cannot_heal(tmp_path, monkeypatch):
    from automation.durable_queue import DurableQueue, state_dir
    from automation import responder

    monkeypatch.setenv("SOCIOSPHERE_STATE_DIR", str(tmp_path / "state"))
    reg = tmp_path / "external-mirrors.yaml"
    status = tmp_path / "mirror-drift.yaml"
    _write(status, STATUS_HEADER + "version: '1.2.3'\nmirrors: []\n")
    _write(reg, "mirrors: : : broken")  # corrupt source -> executor aborts

    inbox = DurableQueue(state_dir() / "beacons")
    decisions = DurableQueue(state_dir() / "decisions")
    inbox.put({
        "kind_class": "mirror_drift", "system": "external-mirrors",
        "evidence": {"detector": "mirror_drift_engine", "reproducible": True, "stale": False},
    })

    out = responder.run_once(
        inbox=inbox, decisions=decisions, execute=True,
        executor_paths={"registry_path": reg, "status_path": status},
    )

    r = out[0]
    assert r["execution"]["healed"] is False
    # a decision that could not be verified becomes a human escalation
    assert r["action"] == "escalate_human"
