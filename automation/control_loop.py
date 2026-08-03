"""Closed-loop control for the reasoned responder — bounded, convergent, fail-closed.

`responder.decide()` chooses an action and `executors` act ONCE. But a single corrective
step is not control: a real loop RE-OBSERVES the error after acting and keeps acting until
the error is driven to the target (converged) or it gives up safely (fail-closed). This is
the estate's long-standing `detect != control-loop` gap (Loops-vs-DAGs).

A loop is valid here only if it is:
  - BOUNDED     — `max_iterations` AND a wall-clock `deadline_s`; it can never spin forever.
  - CONVERGENT  — a measurable numeric `error` (lower is better) that must reach `target`,
                  and must strictly decrease; `patience` consecutive non-decreasing steps
                  means it is stuck, so it stops.
  - FAIL-CLOSED — on non-convergence it returns a `safe_state` (the caller escalates /
                  quarantines); it never reports success it did not verify, and never
                  leaves the system open.

Honors the ControlLoop contract (sovereign-compute-fabric control-loop.v0):
VJ (value-judgment) == the responder's meet() verdict, WM (world-model) == the observed
system error, KD (knowledge) == the beacon/evidence. Observation and action are injected,
so the same loop drives any invariant+executor pair (mirror-drift today, more later).
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass
from typing import Callable, Dict, List, Optional

_EPS = 1e-12


@dataclass
class LoopResult:
    converged: bool
    iterations: int
    initial_error: float
    final_error: float
    trace: List[dict]
    fail_closed_state: Optional[str]
    reason: str

    def to_json(self) -> dict:
        d = asdict(self)
        d["trace_hash"] = hashlib.sha256(
            json.dumps(self.trace, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return d


class ControlLoop:
    """Drive a system to `target` error via `act`, bounded + convergent + fail-closed."""

    def __init__(self, *, max_iterations: int = 5, deadline_s: float = 30.0,
                 target: float = 0.0, patience: int = 2,
                 safe_state: str = "quarantine-escalate",
                 clock: Callable[[], float] = time.monotonic) -> None:
        # a loop that is not bounded is not a valid control loop — refuse to build one.
        if max_iterations < 1:
            raise ValueError("control loop must be bounded: max_iterations >= 1")
        if deadline_s <= 0:
            raise ValueError("control loop must be bounded: deadline_s > 0")
        if patience < 1:
            raise ValueError("patience >= 1")
        self.max_iterations = max_iterations
        self.deadline_s = deadline_s
        self.target = target
        self.patience = patience
        self.safe_state = safe_state
        self._clock = clock

    @staticmethod
    def _observe(observe: Callable[[], float]) -> float:
        # A loop that can be crashed by a misbehaving `observe` is not fail-closed — it would
        # raise instead of returning a LoopResult, losing the fail_closed_state entirely and
        # potentially leaving the caller's try/except (if any) to decide, unverified. Treat an
        # unreadable/un-assessable observation as maximal error: it can never look converged,
        # and the bounded iteration/deadline/patience guards below still apply on top of it.
        try:
            return float(observe())
        except Exception:
            return float("inf")

    @staticmethod
    def _act(act: Callable[[], None]) -> None:
        # Same reasoning as `_observe`: `act` raising must not crash the loop. The next
        # `observe()` re-checks reality regardless of whether the action "succeeded" — verify
        # the artifact, not the exit code — so a raising action just looks like a no-op step
        # and is bounded by the same iteration/deadline/patience guards.
        try:
            act()
        except Exception:
            pass

    def run(self, observe: Callable[[], float], act: Callable[[], None]) -> LoopResult:
        t0 = self._clock()
        trace: List[dict] = []
        err = self._observe(observe)
        initial = err
        best = float("inf")
        stall = 0
        converged = False
        reason = ""
        i = 0
        while True:
            step = {"iter": i, "error": err, "elapsed_s": round(self._clock() - t0, 6)}
            trace.append(step)
            if err <= self.target + _EPS:
                converged = True
                reason = f"error {err} <= target {self.target}"
                break
            if i >= self.max_iterations:
                reason = f"exhausted max_iterations={self.max_iterations} without reaching target"
                break
            if self._clock() - t0 > self.deadline_s:
                reason = f"deadline {self.deadline_s}s exceeded"
                break
            # convergence guard: require strict decrease within `patience`
            if err < best - _EPS:
                best = err
                stall = 0
            else:
                stall += 1
                if stall >= self.patience:
                    reason = f"error not decreasing for {self.patience} steps (stuck) — refusing to loop"
                    break
            step["action"] = "act"
            self._act(act)
            err = self._observe(observe)
            i += 1
        # re-check terminal condition after the last act
        if err <= self.target + _EPS:
            converged = True
            if not reason:
                reason = f"error {err} <= target {self.target}"
        return LoopResult(
            converged=converged,
            iterations=len(trace),
            initial_error=initial,
            final_error=err,
            trace=trace,
            fail_closed_state=None if converged else self.safe_state,
            reason=reason,
        )


# ---- invariants: kind_class -> observe() error function (0.0 == healthy) ----
# Parallel to responder.EXECUTORS; the loop drives the executor until the invariant holds.
def _mirror_drift_error(*, registry_path, status_path, **_) -> float:
    from automation.executors import is_in_sync
    try:
        return 0.0 if is_in_sync(registry_path, status_path) else 1.0
    except Exception:
        # un-assessable (e.g. corrupted source) -> maximal error -> fail-closed, never auto-heal
        return float("inf")


INVARIANTS: Dict[str, Callable[..., float]] = {
    "mirror_drift": _mirror_drift_error,
}


def heal(kind_class: str, executor_fn: Callable, executor_paths: dict,
         **loop_kwargs) -> LoopResult:
    """Drive `executor_fn` under a ControlLoop until `kind_class`'s invariant holds.

    observe() = the invariant's error; act() = run the executor (swallowing its exception so
    the loop RE-OBSERVES rather than trusting a return code — verify the artifact, not the
    command). If the invariant is unknown, we cannot measure convergence, so we fail closed.
    """
    invariant = INVARIANTS.get(kind_class)
    if invariant is None:
        return LoopResult(False, 0, float("inf"), float("inf"), [],
                          "quarantine-escalate",
                          f"no invariant registered for '{kind_class}' — cannot verify convergence")

    def observe() -> float:
        return invariant(**executor_paths)

    def act() -> None:
        try:
            executor_fn(**executor_paths)
        except Exception:
            pass  # loop re-observes; persistent failure -> fail-closed

    return ControlLoop(**loop_kwargs).run(observe, act)
