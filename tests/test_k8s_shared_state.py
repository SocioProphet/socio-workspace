"""The k8s manifest wires one SHARED RWX state volume across producer, consumer, and reader.

Without this, webhook pods (event producers) wrote to a per-pod temp dir the scheduler never
saw, and RWO PVCs cannot be shared across pods/nodes — so events and proposals never flowed.
This asserts the automation-state PVC is ReadWriteMany and that every workload touching the
self-heal state mounts it at /app/state with SOCIOSPHERE_STATE_DIR pointed there.
"""

from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

MANIFEST = Path(__file__).resolve().parent.parent / "deployment" / "kubernetes.yaml"
SHARED = "automation-state"
MOUNT = "/app/state"


def _docs():
    return [d for d in yaml.safe_load_all(MANIFEST.read_text("utf-8")) if d]


def _pod_spec(doc):
    """The pod spec for a Deployment or a CronJob."""
    if doc["kind"] == "Deployment":
        return doc["spec"]["template"]["spec"]
    if doc["kind"] == "CronJob":
        return doc["spec"]["jobTemplate"]["spec"]["template"]["spec"]
    raise AssertionError(doc["kind"])


def _by(kind, name):
    for d in _docs():
        if d.get("kind") == kind and d.get("metadata", {}).get("name") == name:
            return d
    raise AssertionError(f"{kind}/{name} not found")


def test_shared_state_pvc_is_read_write_many():
    pvc = _by("PersistentVolumeClaim", SHARED)
    assert "ReadWriteMany" in pvc["spec"]["accessModes"]


@pytest.mark.parametrize("kind,name", [
    ("Deployment", "webhooks"),
    ("Deployment", "scheduler"),
    ("CronJob", "proposal-opener"),
])
def test_workload_shares_state_volume(kind, name):
    spec = _pod_spec(_by(kind, name))

    # the pod declares the shared PVC volume
    vols = {v["name"]: v for v in spec.get("volumes", [])}
    assert SHARED in vols, f"{name} does not declare the {SHARED} volume"
    assert vols[SHARED]["persistentVolumeClaim"]["claimName"] == SHARED

    container = spec["containers"][0]
    # mounts it at the common path
    mounts = {m["name"]: m["mountPath"] for m in container.get("volumeMounts", [])}
    assert mounts.get(SHARED) == MOUNT, f"{name} must mount {SHARED} at {MOUNT}"

    # and points SOCIOSPHERE_STATE_DIR at it, so all three read/write one queue
    env = {e["name"]: e.get("value") for e in container.get("env", [])}
    assert env.get("SOCIOSPHERE_STATE_DIR") == MOUNT, f"{name} SOCIOSPHERE_STATE_DIR must be {MOUNT}"


def test_manifest_parses_and_has_all_workloads():
    kinds = [(d["kind"], d["metadata"]["name"]) for d in _docs() if "metadata" in d]
    for expected in [("Deployment", "webhooks"), ("Deployment", "scheduler"),
                     ("CronJob", "proposal-opener"), ("PersistentVolumeClaim", SHARED)]:
        assert expected in kinds
