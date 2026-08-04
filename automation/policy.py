"""Policy-bound governance for the reasoned responder, with an opinionated default.

The responder's decisions used to be governed by constants scattered through responder.py.
This makes that governance an explicit, declared `ResponsePolicy`:

  - law_by_kind   : the strongest verdict each failure CLASS may reach for auto-action
  - verdict_action: verdict -> action on the lattice
  - default_law   : the Law for an unknown class (fail-closed)
  - iri_block     : the identity-risk block threshold
  - boundary_axes : the Ring-1 octonion safety axes

It ships an OPINIONATED DEFAULT (`DEFAULT_POLICY`) so the loop is governed and useful out of
the box, and it is overridable from a DECLARED YAML (`registry/self-heal-policy.yaml`, or a
path in `$SOCIOSPHERE_SELF_HEAL_POLICY`) with no code change. An override is validated (Law /
verdict / action values must be known) and MERGED over the default, so a partial policy can
tighten or relax specific classes without redeclaring the whole thing. The committed
`registry/self-heal-policy.yaml` is asserted (in tests) to equal `DEFAULT_POLICY`, so the
declared governance and the opinionated default cannot silently drift apart.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Dict, Optional, Tuple

# The canonical verdict lattice (weakest -> strongest) and the actions a policy may name.
VERDICTS: Tuple[str, ...] = ("refuse", "quarantine", "weak", "probable", "sealed")
ACTIONS: Tuple[str, ...] = (
    "auto_fix", "canary_fix", "propose_pr", "quarantine", "block", "escalate_human",
)

_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY_FILE = _ROOT / "registry" / "self-heal-policy.yaml"


@dataclass(frozen=True)
class ResponsePolicy:
    law_by_kind: Dict[str, str]
    verdict_action: Dict[str, str]
    default_law: str = "refuse"
    iri_block: float = 0.55
    boundary_axes: Tuple[str, ...] = (
        "legality", "containment", "provenance", "privacy",
        "performance", "reproducibility", "licensing", "governance",
    )
    # A condition already decided within this window is suppressed, so a persistent
    # (e.g. cross-repo) failure is escalated once per window, not every scheduler cycle.
    suppression_cooldown_seconds: float = 3600.0

    def law_for(self, kind: str) -> str:
        """The Law ceiling for a class; unknown classes fall to default_law (fail-closed)."""
        return self.law_by_kind.get(kind, self.default_law)

    def action_for(self, verdict: str) -> str:
        """The action for a verdict; anything unmapped escalates to a human (fail-closed)."""
        return self.verdict_action.get(verdict, "escalate_human")

    def as_dict(self) -> dict:
        return {
            "law_by_kind": dict(self.law_by_kind),
            "verdict_action": dict(self.verdict_action),
            "default_law": self.default_law,
            "iri_block": self.iri_block,
            "boundary_axes": list(self.boundary_axes),
            "suppression_cooldown_seconds": self.suppression_cooldown_seconds,
        }


# ── the opinionated default ────────────────────────────────────────────────
# Reversible regenerate-from-source classes may auto-heal (sealed); a cross-repo change is
# proposal-only (weak); a policy breach is quarantined and never auto-fixed.
DEFAULT_POLICY = ResponsePolicy(
    law_by_kind={
        "mirror_drift": "sealed",
        "vendored_graph_drift": "sealed",
        "build_failure": "probable",
        "stale_vendor": "weak",
        "workspace_lock_drift": "weak",  # bumps pins -> propose for review, never auto-apply
        "policy_violation": "quarantine",
        "unknown": "refuse",
    },
    verdict_action={
        "sealed": "auto_fix",
        "probable": "canary_fix",
        "weak": "propose_pr",
        "quarantine": "quarantine",
        "refuse": "block",
    },
    default_law="refuse",
    iri_block=0.55,
)


def validate_policy(p: ResponsePolicy) -> None:
    """Reject a policy that names an unknown verdict or action, or an out-of-range threshold."""
    for kind, law in p.law_by_kind.items():
        if law not in VERDICTS:
            raise ValueError(f"law_by_kind[{kind!r}]={law!r} is not a verdict {VERDICTS}")
    if p.default_law not in VERDICTS:
        raise ValueError(f"default_law={p.default_law!r} is not a verdict {VERDICTS}")
    for verdict, action in p.verdict_action.items():
        if verdict not in VERDICTS:
            raise ValueError(f"verdict_action key {verdict!r} is not a verdict {VERDICTS}")
        if action not in ACTIONS:
            raise ValueError(f"verdict_action[{verdict!r}]={action!r} is not an action {ACTIONS}")
    if not (0.0 <= p.iri_block <= 1.0):
        raise ValueError(f"iri_block={p.iri_block} must be in [0, 1]")
    if not p.boundary_axes:
        raise ValueError("boundary_axes must be non-empty (fail-closed needs a fence)")
    if p.suppression_cooldown_seconds < 0:
        raise ValueError(f"suppression_cooldown_seconds={p.suppression_cooldown_seconds} must be >= 0")


validate_policy(DEFAULT_POLICY)


def policy_from_mapping(data: Optional[dict]) -> ResponsePolicy:
    """Merge a (partial) declared mapping over DEFAULT_POLICY and validate the result."""
    data = data or {}
    merged = replace(
        DEFAULT_POLICY,
        law_by_kind={**DEFAULT_POLICY.law_by_kind, **(data.get("law_by_kind") or {})},
        verdict_action={**DEFAULT_POLICY.verdict_action, **(data.get("verdict_action") or {})},
        default_law=data.get("default_law", DEFAULT_POLICY.default_law),
        iri_block=float(data.get("iri_block", DEFAULT_POLICY.iri_block)),
        boundary_axes=tuple(data.get("boundary_axes") or DEFAULT_POLICY.boundary_axes),
        suppression_cooldown_seconds=float(
            data.get("suppression_cooldown_seconds", DEFAULT_POLICY.suppression_cooldown_seconds)
        ),
    )
    validate_policy(merged)
    return merged


def load_policy(path: Optional[Path] = None, *, use_default_file: bool = True) -> ResponsePolicy:
    """Load the governing policy: explicit path, else env, else the committed default file.

    Falls back to `DEFAULT_POLICY` when no source exists, so the loop is always governed.
    """
    src: Optional[Path] = None
    if path is not None:
        src = Path(path)
    elif os.environ.get("SOCIOSPHERE_SELF_HEAL_POLICY"):
        src = Path(os.environ["SOCIOSPHERE_SELF_HEAL_POLICY"])
    elif use_default_file and DEFAULT_POLICY_FILE.exists():
        src = DEFAULT_POLICY_FILE

    if src is None or not src.exists():
        return DEFAULT_POLICY

    import yaml

    data = yaml.safe_load(src.read_text("utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"policy file {src} must parse to a mapping, got {type(data).__name__}")
    return policy_from_mapping(data)
