"""SENSE-stage proof, and the first FULL vertical slice end-to-end.

detect -> beacon(evidence) -> decide -> execute(resync) -> verify -> receipt.

The headline test induces REAL drift on real files (tmp) and drives the whole spine: a
detector emits an evidence-bearing mirror_drift beacon, the responder decides auto_fix, the
executor re-syncs, and the artifact is VERIFIED healed on disk. This is the difference
between "can heal in a unit test" and "does heal end-to-end".

Teeth both ways: a corrupt SOURCE OF TRUTH yields a warrantless beacon that the responder
escalates to a human, and the good artifact is preserved.
"""

import textwrap

import pytest
import yaml

from automation import detectors, executors, responder
from automation.durable_queue import DurableQueue, state_dir
from engines.mirror_drift_engine import STATUS_HEADER, build_payload


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

STALE_STATUS = STATUS_HEADER + "version: '0.0.0'\nmirrors: []\n"


def _write(path, text):
    path.write_text(text, encoding="utf-8")


def _correct_status_text(reg):
    payload = build_payload(yaml.safe_load(reg.read_text("utf-8")))
    return STATUS_HEADER + yaml.safe_dump(payload, sort_keys=False, default_flow_style=False)


@pytest.fixture
def files(tmp_path):
    reg = tmp_path / "external-mirrors.yaml"
    status = tmp_path / "mirror-drift.yaml"
    _write(reg, VALID_REGISTRY)
    return reg, status


# --- the detector in isolation ---------------------------------------------

def test_detects_drift_and_emits_evidence_beacon(files):
    reg, status = files
    _write(status, STALE_STATUS)  # BREAK: derived artifact drifted

    beacon = detectors.detect_mirror_drift(registry_path=reg, status_path=status)

    assert beacon is not None
    assert beacon["kind_class"] == "mirror_drift"
    assert beacon["evidence"]["detector"] == "mirror_drift_engine.check"
    assert beacon["evidence"]["reproducible"] is True
    assert beacon["evidence"]["stale"] is False


def test_no_beacon_when_in_sync(files):
    reg, status = files
    _write(status, _correct_status_text(reg))
    # a control that fires when nothing is wrong is suspect
    assert detectors.detect_mirror_drift(registry_path=reg, status_path=status) is None


def test_unreadable_source_emits_warrantless_beacon(files):
    reg, status = files
    _write(status, _correct_status_text(reg))
    _write(reg, "[]\n")  # source of truth un-assessable (falsey non-mapping)

    beacon = detectors.detect_mirror_drift(registry_path=reg, status_path=status)

    assert beacon is not None
    assert beacon["kind_class"] == "mirror_drift"
    assert "evidence" not in beacon           # no warrant -> responder will escalate
    assert beacon["detail"]["assessable"] is False


def test_run_detectors_enqueues_beacon(files, tmp_path, monkeypatch):
    reg, status = files
    _write(status, STALE_STATUS)
    monkeypatch.setenv("SOCIOSPHERE_STATE_DIR", str(tmp_path / "state"))
    inbox = DurableQueue(state_dir() / "beacons")

    emitted = detectors.run_detectors(
        inbox=inbox, detector_paths={"registry_path": reg, "status_path": status},
        detectors=[detectors.detect_mirror_drift],
    )

    assert len(emitted) == 1
    assert inbox.qsize() == 1


# --- the full vertical slice, end to end -----------------------------------

def test_full_loop_detect_decide_heal_verify(files, tmp_path, monkeypatch):
    reg, status = files
    _write(status, STALE_STATUS)  # real drift
    assert not executors.is_in_sync(reg, status)

    monkeypatch.setenv("SOCIOSPHERE_STATE_DIR", str(tmp_path / "state"))
    inbox = DurableQueue(state_dir() / "beacons")
    decisions = DurableQueue(state_dir() / "decisions")
    paths = {"registry_path": reg, "status_path": status}

    # SENSE
    detectors.run_detectors(inbox=inbox, detector_paths=paths, detectors=[detectors.detect_mirror_drift])
    # DECIDE + ACT + VERIFY
    out = responder.run_once(inbox=inbox, decisions=decisions, execute=True, executor_paths=paths)

    assert len(out) == 1
    r = out[0]
    assert r["action"] == "auto_fix"
    assert r["execution"]["healed"] is True
    # the ARTIFACT is actually healed on disk — verified, not asserted from an exit code
    assert executors.is_in_sync(reg, status)
    assert status.read_text("utf-8") == _correct_status_text(reg)


def test_full_loop_corrupt_source_escalates_and_preserves(files, tmp_path, monkeypatch):
    reg, status = files
    good = _correct_status_text(reg)
    _write(status, good)
    _write(reg, "mirrors: : : broken")  # corrupt source of truth

    monkeypatch.setenv("SOCIOSPHERE_STATE_DIR", str(tmp_path / "state"))
    inbox = DurableQueue(state_dir() / "beacons")
    decisions = DurableQueue(state_dir() / "decisions")
    paths = {"registry_path": reg, "status_path": status}

    detectors.run_detectors(inbox=inbox, detector_paths=paths, detectors=[detectors.detect_mirror_drift])
    out = responder.run_once(inbox=inbox, decisions=decisions, execute=True, executor_paths=paths)

    assert len(out) == 1
    assert out[0]["action"] == "escalate_human"   # no warrant -> human, never auto-acts
    assert status.read_text("utf-8") == good        # good artifact preserved
