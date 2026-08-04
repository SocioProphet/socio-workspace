"""Load + validate the declared, governed storage placement (registry/mesh-storage-placement.yaml).

Turns "size the parity to the threat" into a reviewed config change: each threat tier declares a
Placement, and this loader VALIDATES it fail-closed before anything relies on it. The estate rule
"declared-not-actuated is a trap" applies — so a declaration that is unsafe (a seizable tier left
unencrypted, k<1, m<0, replicas<1, or shard_replicas<1) is rejected HERE, at load, not discovered
in production after a raid.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from automation.storage_resilience import Placement

_ROOT = Path(__file__).resolve().parents[1]
_REGISTRY = _ROOT / "registry" / "mesh-storage-placement.yaml"
_THREAT_STATE = _ROOT / "status" / "mesh-threat-state.json"


def _validate(tier: str, p: Placement) -> None:
    if p.rs_k < 1:
        raise ValueError(f"tier '{tier}': rs_k must be >= 1")
    if p.rs_m < 0:
        raise ValueError(f"tier '{tier}': rs_m must be >= 0")
    if p.replicas < 1:
        raise ValueError(f"tier '{tier}': replicas must be >= 1")
    if p.shard_replicas < 1:
        raise ValueError(f"tier '{tier}': shard_replicas must be >= 1 (1 = no shard replication)")
    # The seizable tiers (flash, block) hold recoverable bytes; a captured node MUST yield
    # ciphertext. We refuse to load a placement that would leave plaintext on a seizable disk.
    if not p.encrypted_at_rest:
        raise ValueError(f"tier '{tier}': encrypted_at_rest MUST be true — seizable tiers cannot "
                         f"store plaintext (a captured node must yield ciphertext)")


def _tier_to_placement(spec: dict) -> Placement:
    return Placement(
        replicas=int(spec.get("replicas", 3)),
        rs_k=int(spec["rs_k"]),
        rs_m=int(spec["rs_m"]),
        encrypted_at_rest=bool(spec.get("encrypted_at_rest", True)),
        shard_replicas=int(spec.get("shard_replicas", 1)),
    )


def load_placement(threat_tier: Optional[str] = None, *, path: Optional[Path] = None) -> Placement:
    """Return the validated Placement for ``threat_tier`` (or the registry's ``default_tier``).

    Raises on an unknown tier or an unsafe declaration — the whole point is that an unsafe or
    typo'd placement never silently becomes the storage posture.
    """
    import yaml
    path = Path(path) if path is not None else _REGISTRY
    data = yaml.safe_load(path.read_text("utf-8")) or {}
    tiers = data.get("tiers") or {}
    tier = threat_tier or data.get("default_tier")
    if not tier:
        raise ValueError("no threat tier requested and no default_tier declared")
    if tier not in tiers:
        raise ValueError(f"unknown threat tier '{tier}'; declared: {sorted(tiers)}")
    placement = _tier_to_placement(tiers[tier])
    _validate(tier, placement)
    return placement


def load_all(path: Optional[Path] = None) -> dict:
    """Every declared tier -> its validated Placement (validates the whole file at once)."""
    import yaml
    path = Path(path) if path is not None else _REGISTRY
    data = yaml.safe_load(path.read_text("utf-8")) or {}
    out = {}
    for tier, spec in (data.get("tiers") or {}).items():
        p = _tier_to_placement(spec)
        _validate(tier, p)
        out[tier] = p
    return out


def load_runtime_placement(*, state_path: Optional[Path] = None,
                           path: Optional[Path] = None) -> Placement:
    """The placement NEW WRITES should use RIGHT NOW — honoring the live threat posture.

    This is the actuation->EFFECT link: the adaptive controller (detect_mesh_threat) escalates by
    writing the runtime posture to status/mesh-threat-state.json; this reads that posture's ``tier``
    and returns its Placement, so an escalation actually changes what parity new leaves are written
    with. Bounded and fail-safe:
      * no posture file / unreadable / unknown tier -> the registry ``default_tier`` (the floor).
      * a posture BELOW the floor is clamped UP to the floor — the runtime posture may only ADD
        resilience above the human-sanctioned baseline, never subtract it (compared by overhead).
    So the storage layer can never end up weaker than the reviewed default, whatever the state file
    says, and an escalation is realized without a redeploy.
    """
    floor = load_placement(path=path)  # the registry default_tier — the sanctioned minimum
    spath = Path(state_path) if state_path is not None else _THREAT_STATE
    try:
        tier = json.loads(spath.read_text("utf-8")).get("tier")
    except (FileNotFoundError, ValueError, AttributeError):
        return floor
    if not isinstance(tier, str) or not tier:
        return floor
    try:
        chosen = load_placement(tier, path=path)
    except ValueError:
        return floor  # posture names a tier the storage registry doesn't declare -> floor
    # never below the floor: the runtime posture may only raise resilience, never lower it.
    return chosen if chosen.durability_overhead >= floor.durability_overhead else floor
