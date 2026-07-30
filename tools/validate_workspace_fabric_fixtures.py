#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / "protocol" / "workspace-fabric" / "v0"
FIX = WF / "fixtures"
ADP = FIX / "adapters"

REQUEST = FIX / "mount-registration-request.example.json"
LEASE = FIX / "mount-registration-lease.example.json"
EVENT = FIX / "evidence-event.example.json"
RENEWAL = FIX / "lease-renewal-request.example.json"
REVOCATION = FIX / "lease-revocation-request.example.json"
AUTH_REQ = FIX / "authority-transition-request.example.json"
AUTH_DEC = FIX / "authority-transition-decision.example.json"
POLICY_DEC = FIX / "policy-decision.example.json"
QUORUM_DEC = FIX / "quorum-decision.example.json"
TOMBSTONE = FIX / "tombstone-decision.example.json"
RECONCILE = FIX / "reconcile-required.example.json"
TRANSITION = FIX / "transition.example.json"
STATE_MACHINE = FIX / "state-machine.example.json"

REQ_SCHEMA = WF / "mount-registration-request.schema.json"
LEASE_SCHEMA = WF / "mount-registration-lease.schema.json"
EVENT_SCHEMA = WF / "evidence-event.schema.json"
RENEWAL_SCHEMA = WF / "lease-renewal-request.schema.json"
REVOCATION_SCHEMA = WF / "lease-revocation-request.schema.json"
AUTH_REQ_SCHEMA = WF / "authority-transition-request.schema.json"
AUTH_DEC_SCHEMA = WF / "authority-transition-decision.schema.json"
POLICY_DEC_SCHEMA = WF / "policy-decision.schema.json"
QUORUM_DEC_SCHEMA = WF / "quorum-decision.schema.json"
TOMBSTONE_SCHEMA = WF / "tombstone-decision.schema.json"
RECONCILE_SCHEMA = WF / "reconcile-required.schema.json"
TRANSITION_SCHEMA = WF / "lifecycle-transition.schema.json"
STATE_MACHINE_SCHEMA = WF / "state-machine.schema.json"
ADAPTER_PROFILE_SCHEMA = WF / "adapter-profile.schema.json"

ADAPTER_FIXTURES = {
    "topolvm": ADP / "topolvm.example.json",
    "hypercore": ADP / "hypercore.example.json",
    "s3": ADP / "s3.example.json",
    "rsync": ADP / "rsync.example.json",
    "drive": ADP / "drive.example.json",
}

EXPECTED_STATES = {
    "DISCOVERED",
    "PROPOSED",
    "POLICY_EVALUATING",
    "QUORUM_EVALUATING",
    "LEASE_ISSUED",
    "ACTIVE",
    "DEGRADED",
    "RECONCILE_REQUIRED",
    "REVOKED",
    "TOMBSTONED",
}

REQUIRED_EDGES = {
    ("DISCOVERED", "PROPOSED"),
    ("PROPOSED", "POLICY_EVALUATING"),
    ("LEASE_ISSUED", "ACTIVE"),
    ("ACTIVE", "DEGRADED"),
    ("ACTIVE", "RECONCILE_REQUIRED"),
    ("ACTIVE", "TOMBSTONED"),
    ("ACTIVE", "REVOKED"),
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def require_keys(obj: dict, keys: list[str], label: str) -> None:
    missing = [k for k in keys if k not in obj]
    if missing:
        raise SystemExit(f"{label} missing keys: {missing}")


def main() -> int:
    required_paths = [
        REQUEST,
        LEASE,
        EVENT,
        RENEWAL,
        REVOCATION,
        AUTH_REQ,
        AUTH_DEC,
        POLICY_DEC,
        QUORUM_DEC,
        TOMBSTONE,
        RECONCILE,
        TRANSITION,
        STATE_MACHINE,
        REQ_SCHEMA,
        LEASE_SCHEMA,
        EVENT_SCHEMA,
        RENEWAL_SCHEMA,
        REVOCATION_SCHEMA,
        AUTH_REQ_SCHEMA,
        AUTH_DEC_SCHEMA,
        POLICY_DEC_SCHEMA,
        QUORUM_DEC_SCHEMA,
        TOMBSTONE_SCHEMA,
        RECONCILE_SCHEMA,
        TRANSITION_SCHEMA,
        STATE_MACHINE_SCHEMA,
        ADAPTER_PROFILE_SCHEMA,
        *ADAPTER_FIXTURES.values(),
    ]
    for path in required_paths:
        if not path.exists():
            raise SystemExit(f"missing required file: {path}")

    req = load(REQUEST)
    lease = load(LEASE)
    event = load(EVENT)
    renewal = load(RENEWAL)
    revocation = load(REVOCATION)
    auth_req = load(AUTH_REQ)
    auth_dec = load(AUTH_DEC)
    policy_dec = load(POLICY_DEC)
    quorum_dec = load(QUORUM_DEC)
    tombstone = load(TOMBSTONE)
    reconcile = load(RECONCILE)
    transition = load(TRANSITION)
    state_machine = load(STATE_MACHINE)

    req_schema = load(REQ_SCHEMA)
    lease_schema = load(LEASE_SCHEMA)
    event_schema = load(EVENT_SCHEMA)
    renewal_schema = load(RENEWAL_SCHEMA)
    revocation_schema = load(REVOCATION_SCHEMA)
    auth_req_schema = load(AUTH_REQ_SCHEMA)
    auth_dec_schema = load(AUTH_DEC_SCHEMA)
    policy_dec_schema = load(POLICY_DEC_SCHEMA)
    quorum_dec_schema = load(QUORUM_DEC_SCHEMA)
    tombstone_schema = load(TOMBSTONE_SCHEMA)
    reconcile_schema = load(RECONCILE_SCHEMA)
    transition_schema = load(TRANSITION_SCHEMA)
    state_machine_schema = load(STATE_MACHINE_SCHEMA)
    adapter_profile_schema = load(ADAPTER_PROFILE_SCHEMA)
    adapter_profiles = {name: load(path) for name, path in ADAPTER_FIXTURES.items()}

    require_keys(req, req_schema["required"], "request fixture")
    require_keys(lease, lease_schema["required"], "lease fixture")
    require_keys(event, event_schema["required"], "event fixture")
    require_keys(renewal, renewal_schema["required"], "renewal fixture")
    require_keys(revocation, revocation_schema["required"], "revocation fixture")
    require_keys(auth_req, auth_req_schema["required"], "authority request fixture")
    require_keys(auth_dec, auth_dec_schema["required"], "authority decision fixture")
    require_keys(policy_dec, policy_dec_schema["required"], "policy decision fixture")
    require_keys(quorum_dec, quorum_dec_schema["required"], "quorum decision fixture")
    require_keys(tombstone, tombstone_schema["required"], "tombstone decision fixture")
    require_keys(reconcile, reconcile_schema["required"], "reconcile-required fixture")
    require_keys(transition, transition_schema["required"], "transition fixture")
    require_keys(state_machine, state_machine_schema["required"], "state-machine fixture")

    for name, profile in adapter_profiles.items():
        require_keys(profile, adapter_profile_schema["required"], f"adapter profile {name}")

    require_keys(req["workspace"], ["cell", "id", "principal"], "request.workspace")
    require_keys(req["mount"], ["id", "backend", "authority_mode"], "request.mount")
    require_keys(lease["workspace"], ["cell", "id"], "lease.workspace")
    require_keys(lease["mount"], ["id", "backend", "authority_mode"], "lease.mount")
    require_keys(event, ["workspace_ref", "mount_ref", "dataset_ref", "correlation_id"], "event envelope")

    if req["workspace"]["id"] != lease["workspace"]["id"]:
        raise SystemExit("workspace id mismatch between request and lease")
    if req["mount"]["id"] != lease["mount"]["id"]:
        raise SystemExit("mount id mismatch between request and lease")
    if req["mount"]["authority_mode"] != lease["mount"]["authority_mode"]:
        raise SystemExit("authority mode mismatch between request and lease")
    if event["workspace_ref"] != req["workspace"]["id"]:
        raise SystemExit("event workspace_ref does not match request workspace id")
    if event["mount_ref"] != req["mount"]["id"]:
        raise SystemExit("event mount_ref does not match request mount id")

    dataset_ids = [d["id"] for d in req["datasets"]]
    if event["dataset_ref"] not in dataset_ids:
        raise SystemExit("event dataset_ref not found in request datasets")
    if lease["approved"]["datasets"][0] not in dataset_ids:
        raise SystemExit("lease approved dataset not found in request datasets")

    request_adapter_roles = {f"{a['kind']}:{a['role']}" for a in req["adapters"]}
    lease_adapter_roles = set(lease["approved"]["adapters"])
    if not lease_adapter_roles.issubset(request_adapter_roles):
        raise SystemExit("lease adapter approvals are not a subset of request adapters")

    for name, obj in [
        ("renewal", renewal),
        ("revocation", revocation),
        ("authority request", auth_req),
        ("authority decision", auth_dec),
        ("policy decision", policy_dec),
        ("quorum decision", quorum_dec),
        ("tombstone decision", tombstone),
        ("reconcile-required", reconcile),
        ("transition", transition),
    ]:
        if obj["workspace_ref"] != req["workspace"]["id"]:
            raise SystemExit(f"{name} workspace_ref does not match request workspace id")
        if obj["mount_ref"] != req["mount"]["id"]:
            raise SystemExit(f"{name} mount_ref does not match request mount id")

    if renewal["lease_id"] != lease["lease"]["id"]:
        raise SystemExit("renewal lease_id does not match lease fixture")
    if revocation["lease_id"] != lease["lease"]["id"]:
        raise SystemExit("revocation lease_id does not match lease fixture")

    if auth_req["current_authority"] != req["mount"]["authority_mode"]:
        raise SystemExit("authority request current_authority does not match request authority mode")
    if auth_req["requested_authority"] == auth_req["current_authority"]:
        raise SystemExit("authority request requested_authority must differ from current_authority in this fixture")
    if auth_dec["current_authority"] != auth_req["current_authority"]:
        raise SystemExit("authority decision current_authority does not match authority request")
    if auth_dec["correlation_id"] != auth_req["correlation_id"]:
        raise SystemExit("authority decision correlation_id does not match authority request")
    if auth_dec["decision_status"] == "approved":
        if not auth_dec["quorum_granted"]:
            raise SystemExit("approved authority decision must grant quorum")
        if auth_dec["resulting_authority"] != auth_req["requested_authority"]:
            raise SystemExit("approved authority decision resulting_authority does not match requested_authority")

    if policy_dec["policy_subject"] != "authority_transition":
        raise SystemExit("policy decision fixture should target authority_transition in this slice")
    if policy_dec["correlation_id"] != auth_req["correlation_id"]:
        raise SystemExit("policy decision correlation_id does not match authority request")
    if policy_dec["decision_status"] == "approved" and not policy_dec["reason_codes"]:
        raise SystemExit("approved policy decision must carry reason codes")

    if quorum_dec["subject"] != "authority_transition":
        raise SystemExit("quorum decision fixture should target authority_transition in this slice")
    if quorum_dec["correlation_id"] != auth_req["correlation_id"]:
        raise SystemExit("quorum decision correlation_id does not match authority request")
    if quorum_dec["decision_status"] == "granted" and quorum_dec["granted_approvers"] < quorum_dec["required_approvers"]:
        raise SystemExit("granted quorum decision must satisfy required approver count")

    # TOMBSTONED, not "tombstoned": `resulting_state` names a state in the mount state
    # machine, whose states are uppercase (see fixtures/state-machine.example.json), and
    # the sibling reconcile fixture already writes RECONCILE_REQUIRED into this same
    # field. This check used to demand the lowercase spelling, which made it enforce the
    # inconsistency rather than catch it — while line 283 below simultaneously required
    # an uppercase ("ACTIVE", "TOMBSTONED") edge to exist *because of this same fixture*.
    if tombstone["signed_tombstone"] and not tombstone["local_dirty"]:
        if tombstone["decision_status"] == "applied" and tombstone["resulting_state"] != "TOMBSTONED":
            raise SystemExit("applied tombstone must result in TOMBSTONED state in this fixture")

    if reconcile["resulting_state"] != "RECONCILE_REQUIRED":
        raise SystemExit("reconcile fixture must result in RECONCILE_REQUIRED")
    if transition["to_state"] == "RECONCILE_REQUIRED" and reconcile["correlation_id"] != transition["correlation_id"]:
        raise SystemExit("transition and reconcile fixture should share correlation_id in this fixture")

    profile_names = set(adapter_profiles.keys())
    if profile_names != {"topolvm", "hypercore", "s3", "rsync", "drive"}:
        raise SystemExit(f"unexpected adapter profile set: {sorted(profile_names)}")

    for name, profile in adapter_profiles.items():
        if profile["default_authority_mode"] not in profile["allowed_authority_modes"]:
            raise SystemExit(f"adapter profile {name} default_authority_mode not in allowed_authority_modes")

    if adapter_profiles["topolvm"]["default_authority_mode"] != "local_first":
        raise SystemExit("topolvm must default to local_first")
    if "topic_distribution" not in adapter_profiles["hypercore"]["default_roles"]:
        raise SystemExit("hypercore must advertise topic_distribution")
    if "object_snapshot_replica" not in adapter_profiles["s3"]["default_roles"]:
        raise SystemExit("s3 must advertise object_snapshot_replica")
    if "bulk_sync" not in adapter_profiles["rsync"]["default_roles"]:
        raise SystemExit("rsync must advertise bulk_sync")
    if "compatibility_mirror" not in adapter_profiles["drive"]["default_roles"]:
        raise SystemExit("drive must advertise compatibility_mirror")
    if adapter_profiles["drive"]["default_authority_mode"] == "provider_first":
        raise SystemExit("drive must not default to provider_first")

    states = set(state_machine["states"])
    if states != EXPECTED_STATES:
        raise SystemExit(f"unexpected state-machine state set: {sorted(states)}")
    transition_pairs = {(edge["from"], edge["to"]) for edge in state_machine["transitions"]}
    if not REQUIRED_EDGES.issubset(transition_pairs):
        missing = sorted(REQUIRED_EDGES - transition_pairs)
        raise SystemExit(f"state-machine missing required edges: {missing}")
    if (transition["from_state"], transition["to_state"]) not in transition_pairs:
        raise SystemExit("transition fixture edge is not present in the state-machine table")
    if not any(to_state == "RECONCILE_REQUIRED" for _, to_state in transition_pairs):
        raise SystemExit("state-machine must contain at least one path to RECONCILE_REQUIRED")
    if tombstone["decision_status"] == "applied" and ("ACTIVE", "TOMBSTONED") not in transition_pairs:
        raise SystemExit("state-machine must contain ACTIVE -> TOMBSTONED for the applied tombstone fixture")

    print("workspace-fabric fixtures: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
