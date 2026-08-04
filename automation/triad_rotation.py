"""Triad master rotation — a geometric, triangular-even leader schedule for the k3s masters.

The three k3s HA masters are the vertices of a triangle. Leaving one master as the permanent
leader/writer is a standing single point of compromise, and over time it collapses the Lazerus
writer≠replica separation onto one identity. This rotates the roles around the triangle by a
**120° turn each epoch** — the cyclic symmetry group C₃ of the triangle. Over every full turn of
three epochs each vertex holds each role *exactly once*: perfect triangular evenness.

Two properties make it usable as an integrity primitive, not just a rota:

  1. **Deterministic** — the assignment is a pure function of the ordered triad + the epoch, so
     every master (and the verifier that checks receipts) computes the SAME schedule with no
     coordination or leader election. A receipt whose ``writer_principal`` is not the scheduled
     leader for its epoch is off-schedule and can be flagged.
  2. **writer≠replica always** — leader and attestor are distinct vertices in every epoch, so the
     rotation never violates the Lazerus rule it exists to strengthen.

"Geometric" here is literal: each epoch applies a rotation by ``step`` × 120° around the triangle.
Only a ``step`` coprime with 3 (i.e. 1 or 2) visits every vertex within one turn — that is what
"triangular even" requires — so any other step is rejected. Epochs are uniform in time (an even
rota); the declared period lives in registry/triad-rotation.yaml.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

_ROOT = Path(__file__).resolve().parents[1]
_REGISTRY = _ROOT / "registry" / "triad-rotation.yaml"

# leader = writer_principal, attestor = replica_principal (Lazerus role separation), witness =
# the third vertex (cross-vantage audit — the vault_pair/asn_hint disagreement check rides here).
ROLES = ("leader", "attestor", "witness")


@dataclass(frozen=True)
class Assignment:
    """Who holds each role at one epoch. leader/attestor/witness are the three distinct masters."""
    epoch: int
    leader: str
    attestor: str
    witness: str

    @property
    def writer_replica(self) -> Tuple[str, str]:
        """The (writer_principal, replica_principal) a master stamps into its receipt this epoch."""
        return (self.leader, self.attestor)


def rotate(masters: Sequence[str], epoch: int, *, step: int = 1) -> Assignment:
    """The role assignment at ``epoch``: a step×120° rotation of the triad around the triangle.

    ``masters`` is the fixed, ordered triad (3 distinct identities). ``step`` must be coprime with
    3 (1 or 2) so a full turn visits every vertex — the triangular-evenness guarantee. ``epoch``
    may be negative; rotation is modular either way.
    """
    if len(masters) != 3 or len(set(masters)) != 3:
        raise ValueError("a triad is exactly 3 distinct masters")
    if step % 3 == 0:
        raise ValueError(f"step {step} is a multiple of 3 — it never leaves a vertex (not triangular-even)")
    shift = (epoch * step) % 3
    order = [masters[(i + shift) % 3] for i in range(3)]
    return Assignment(epoch=epoch, leader=order[0], attestor=order[1], witness=order[2])


def epoch_for_time(t_epoch_s: float, *, period_s: float, phase_s: float = 0.0) -> int:
    """Map a wall-clock time (unix seconds) to an epoch index, given the period and phase.

    ``phase_s`` shifts the epoch boundaries (the schedule's t0). Uses floor division so the epoch
    is monotone in time and stable across masters reading the same clock.
    """
    if period_s <= 0:
        raise ValueError("period_s must be positive")
    import math
    return int(math.floor((t_epoch_s - phase_s) / period_s))


def leader_counts(masters: Sequence[str], epochs: range, *, step: int = 1) -> Dict[str, int]:
    """How many times each master leads over ``epochs`` — the evenness witness (used by tests)."""
    counts: Dict[str, int] = {m: 0 for m in masters}
    for e in epochs:
        counts[rotate(masters, e, step=step).leader] += 1
    return counts


# ── declared, governed schedule ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RotationSchedule:
    masters: List[str]
    period_s: float
    step: int = 1
    phase_s: float = 0.0

    def at_epoch(self, epoch: int) -> Assignment:
        return rotate(self.masters, epoch, step=self.step)

    def at_time(self, t_epoch_s: float) -> Assignment:
        return self.at_epoch(epoch_for_time(t_epoch_s, period_s=self.period_s, phase_s=self.phase_s))


def load_schedule(path: Optional[Path] = None) -> RotationSchedule:
    """Load the declared rotation from registry/triad-rotation.yaml. Validates it (a bad schedule
    raises here, not at rotate-time), so the governance file cannot declare an uneven rotation."""
    import yaml
    path = Path(path) if path is not None else _REGISTRY
    data = yaml.safe_load(path.read_text("utf-8")) or {}
    masters = data.get("masters") or []
    if len(masters) != 3 or len(set(masters)) != 3:
        raise ValueError("triad-rotation.yaml: masters must be exactly 3 distinct identities")
    step = int(data.get("step", 1))
    period_s = float(data.get("period_s", 0))
    # Validate the step is triangular-even before anyone relies on the schedule.
    rotate(masters, 0, step=step)
    return RotationSchedule(masters=list(masters), period_s=period_s,
                            step=step, phase_s=float(data.get("phase_s", 0.0)))
