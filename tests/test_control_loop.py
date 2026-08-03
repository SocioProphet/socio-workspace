"""ControlLoop — bounded, convergent, fail-closed: prove the guarantee, not just the shape.

This primitive is a safety boundary (Loops-vs-DAGs `detect != control-loop` gap), so its
edge cases matter more than usual: adversarial `observe`/`act` callables, exact iteration
counts, and the `patience` stall-detection boundary are exercised directly rather than
trusted because the code "looks right".
"""

import pytest

from automation.control_loop import ControlLoop, LoopResult, heal


# --- construction: refuse to build an unbounded loop -------------------------

def test_rejects_max_iterations_below_one():
    with pytest.raises(ValueError):
        ControlLoop(max_iterations=0)


def test_rejects_non_positive_deadline():
    with pytest.raises(ValueError):
        ControlLoop(deadline_s=0)
    with pytest.raises(ValueError):
        ControlLoop(deadline_s=-1)


def test_rejects_patience_below_one():
    with pytest.raises(ValueError):
        ControlLoop(patience=0)


# --- convergence ---------------------------------------------------------------

def test_converges_when_act_fixes_state_in_one_step():
    state = {"error": 5.0}

    def observe():
        return state["error"]

    def act():
        state["error"] = 0.0

    result = ControlLoop(max_iterations=5).run(observe, act)
    assert result.converged is True
    assert result.fail_closed_state is None
    assert result.final_error == 0.0
    assert result.initial_error == 5.0


def test_already_converged_never_calls_act():
    calls = {"act": 0}

    def observe():
        return 0.0

    def act():
        calls["act"] += 1

    result = ControlLoop().run(observe, act)
    assert result.converged is True
    assert result.iterations == 1  # single observation, no action needed
    assert calls["act"] == 0


def test_converges_over_multiple_strictly_decreasing_steps():
    state = {"error": 3.0}

    def observe():
        return state["error"]

    def act():
        state["error"] -= 1.0

    result = ControlLoop(max_iterations=5, patience=5).run(observe, act)
    assert result.converged is True
    assert result.final_error == 0.0


# --- fail-closed on stuck (patience) ------------------------------------------

def test_fails_closed_when_error_never_decreases():
    def observe():
        return 1.0

    def act():
        pass  # never fixes anything

    result = ControlLoop(max_iterations=10, patience=2).run(observe, act)
    assert result.converged is False
    assert result.fail_closed_state == "quarantine-escalate"
    assert "stuck" in result.reason


def test_patience_boundary_stops_after_exactly_patience_non_decreasing_observations():
    """patience=N stalls after N consecutive non-decreasing steps, not N-1 or N+1."""
    calls = {"observe": 0}

    def observe():
        calls["observe"] += 1
        return 1.0  # constant: never decreases after the first reading

    def act():
        pass

    result = ControlLoop(max_iterations=50, patience=3, deadline_s=30).run(observe, act)
    assert result.converged is False
    # first observation establishes the baseline (not itself a "non-decreasing step");
    # then it takes exactly `patience` more non-decreasing observations to stop.
    assert calls["observe"] == 1 + 3
    assert result.iterations == 1 + 3


def test_custom_safe_state_is_returned_on_failure():
    result = ControlLoop(max_iterations=1, patience=1, safe_state="rollback").run(
        lambda: 1.0, lambda: None
    )
    assert result.fail_closed_state == "rollback"


# --- bounded on max_iterations -------------------------------------------------

def test_bounded_by_max_iterations_calls_act_at_most_max_iterations_times():
    calls = {"act": 0}

    def observe():
        return 1.0  # never converges

    def act():
        calls["act"] += 1

    result = ControlLoop(max_iterations=3, patience=100, deadline_s=30).run(observe, act)
    assert result.converged is False
    assert calls["act"] == 3
    assert "max_iterations" in result.reason


# --- bounded on deadline_s (independent axis) ----------------------------------

def test_bounded_by_deadline_independent_of_max_iterations():
    """A fake clock that blows the deadline on the very first check must stop the loop
    even though max_iterations and patience would otherwise allow it to continue."""
    clock = {"t": 0.0}

    def fake_clock():
        return clock["t"]

    def observe():
        return 1.0  # never converges

    def act():
        clock["t"] += 100.0  # simulate a slow action blowing the deadline

    loop = ControlLoop(max_iterations=1000, patience=1000, deadline_s=5.0, clock=fake_clock)
    result = loop.run(observe, act)
    assert result.converged is False
    assert "deadline" in result.reason
    # exactly one action was attempted before the deadline check caught the overrun
    assert result.iterations == 2


# --- fail-closed under adversarial observe()/act() -----------------------------

def test_observe_raising_never_crashes_the_loop_and_fails_closed():
    def observe():
        raise RuntimeError("sensor is on fire")

    def act():
        pass

    result = ControlLoop(max_iterations=2, patience=2).run(observe, act)
    assert isinstance(result, LoopResult)
    assert result.converged is False
    assert result.fail_closed_state == "quarantine-escalate"
    assert result.initial_error == float("inf")
    assert result.final_error == float("inf")


def test_act_raising_never_crashes_the_loop_and_still_converges_if_state_fixes_itself():
    """act() raising must not stop the loop from re-observing — a transient action failure
    should not be indistinguishable from a permanent one if reality recovers regardless."""
    state = {"error": 1.0, "n": 0}

    def observe():
        return state["error"]

    def act():
        state["n"] += 1
        if state["n"] == 1:
            raise RuntimeError("executor blew up")
        state["error"] = 0.0  # second act (never reached if the first crash propagated) fixes it

    result = ControlLoop(max_iterations=5, patience=5).run(observe, act)
    assert result.converged is True
    assert state["n"] == 2  # first raised, loop recovered and tried again


def test_act_raising_every_time_still_fails_closed_and_returns():
    def observe():
        return 1.0

    def act():
        raise RuntimeError("always fails")

    result = ControlLoop(max_iterations=3, patience=2).run(observe, act)
    assert result.converged is False
    assert result.fail_closed_state == "quarantine-escalate"


# --- LoopResult / to_json --------------------------------------------------------

def test_to_json_includes_trace_hash():
    result = ControlLoop().run(lambda: 0.0, lambda: None)
    d = result.to_json()
    assert "trace_hash" in d
    assert isinstance(d["trace_hash"], str) and len(d["trace_hash"]) == 64


# --- heal(): the integration seam ----------------------------------------------

def test_heal_unknown_invariant_fails_closed_without_calling_executor():
    calls = {"n": 0}

    def executor(**_):
        calls["n"] += 1

    result = heal("no_such_invariant", executor, {})
    assert result.converged is False
    assert result.fail_closed_state == "quarantine-escalate"
    assert calls["n"] == 0


def test_heal_mirror_drift_converges_when_executor_fixes_it(monkeypatch, tmp_path):
    state = {"synced": False}

    def fake_is_in_sync(registry_path, status_path):
        return state["synced"]

    def fake_executor(**_):
        state["synced"] = True

    monkeypatch.setattr("automation.executors.is_in_sync", fake_is_in_sync)

    result = heal(
        "mirror_drift", fake_executor,
        {"registry_path": tmp_path / "registry.yaml", "status_path": tmp_path / "status.yaml"},
    )
    assert result.converged is True
    assert result.fail_closed_state is None
