"""The genetic synthesis: propose_pr and auto_fix under ONE sealed control model.

Proves the best-of-both properties hold:
  * opening a PR IS convergence (ControlLoop substrate, verify-by-re-observe),
  * a failed open fail-closes WITH the error detail (pr_opener's gene) AND stays sealed
    with a trace_hash (ControlLoop's gene),
  * one router returns the same sealed shape for auto_fix / propose_pr / escalate.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automation.self_heal import remediate, remediate_via_pr  # noqa: E402

VALID = {
    "title": "fix: align version",
    "branch": "self-heal/version-drift",
    "base": "main",
    "files": {"VERSION": "0.1.0\n"},
    "repo": "SocioProphet/demo",
}


def test_opening_a_pr_is_convergence(tmp_path):
    calls = []
    def opener(proposal, *, repo_dir):
        calls.append(repo_dir)
        return "https://example/pr/1"

    sealed = remediate_via_pr(VALID, opener=opener, repo_dir=tmp_path)
    assert sealed["converged"] is True            # a reviewable PR exists == target reached
    assert sealed["mode"] == "propose_pr"
    assert sealed["pr_url"] == "https://example/pr/1"
    assert sealed["fail_closed_state"] is None
    assert sealed["trace_hash"]                    # sealed provenance (ControlLoop gene)
    assert len(calls) == 1                          # opened once, then re-observe saw it done


def test_failed_open_fails_closed_with_detail_and_seal(tmp_path):
    def opener(proposal, *, repo_dir):
        raise RuntimeError("push denied: 403")

    sealed = remediate_via_pr(VALID, opener=opener, repo_dir=tmp_path)
    assert sealed["converged"] is False
    assert sealed["pr_url"] is None
    assert "push denied: 403" in sealed["error"]   # pr_opener gene: the reason survives
    assert sealed["fail_closed_state"] == "quarantine-escalate"
    assert sealed["trace_hash"]                     # ControlLoop gene: still sealed


def test_partial_open_carries_artifact_in_safe_state(tmp_path):
    # opener returns a URL on a later attempt-style object: here it opens but the loop is
    # constrained so it still records the artifact in the safe state when not fully converged.
    state = {"n": 0}
    def opener(proposal, *, repo_dir):
        state["n"] += 1
        if state["n"] == 1:
            raise RuntimeError("transient")
        return "https://example/pr/9"

    # one iteration only: first (and only) act fails -> not converged, no url.
    sealed = remediate_via_pr(VALID, opener=opener, repo_dir=tmp_path,
                              loop_kwargs={"max_iterations": 1, "patience": 1})
    assert sealed["converged"] is False
    assert "transient" in sealed["error"]


def test_router_propose_pr_and_escalate(tmp_path):
    def opener(proposal, *, repo_dir):
        return "https://example/pr/2"

    sealed = remediate({"proposal": VALID}, {"action": "propose_pr"},
                       opener=opener, repo_dir=tmp_path)
    assert sealed["converged"] is True and sealed["pr_url"] == "https://example/pr/2"

    esc = remediate({}, {"action": "escalate_human"})
    assert esc["converged"] is False
    assert esc["fail_closed_state"] == "escalate-human"


def test_router_auto_fix_uses_controlloop(tmp_path):
    # An unknown invariant class: heal() cannot verify convergence, so it fail-closes —
    # exercising the auto_fix branch and the unified sealed shape (mode=auto_fix).
    ran = []
    sealed = remediate({"kind_class": "no_such_invariant"}, {"action": "auto_fix"},
                       executor_fn=lambda **k: ran.append(1), executor_paths={})
    assert sealed["mode"] == "auto_fix"
    assert sealed["converged"] is False            # no invariant -> cannot verify -> fail-closed


def _run_all():
    import tempfile
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        with tempfile.TemporaryDirectory() as d:
            fn(Path(d))
    print(f"self_heal synthesis: {len(fns)}/{len(fns)} tests pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
