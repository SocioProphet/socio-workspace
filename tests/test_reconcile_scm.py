"""Tests for the SCM reconcile heal — the safety-critical part is the decision to fast-forward vs
STOP. Never force the golden repo; only add missing commits; skip clean when unconfigured."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import importlib.util  # noqa: E402
spec = importlib.util.spec_from_file_location("reconcile_scm", ROOT / "tools" / "reconcile_scm.py")
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


# ── classify: the pure decision (fully testable) ──────────────────────────────────────────────

def test_in_sync():
    assert r.classify("abc", "abc", "ok", ff_safe=False) == r.IN_SYNC


def test_behind_is_fast_forward():
    assert r.classify("newsha", "oldsha", "ok", ff_safe=True) == r.BEHIND_FF


def test_diverged_is_conflict_never_forced():
    assert r.classify("shaA", "shaB", "ok", ff_safe=False) == r.DIVERGED


def test_gitea_missing_repo():
    assert r.classify("abc", None, "missing", ff_safe=False) == r.GITEA_MISSING


def test_unreadable_is_unknown_not_failure():
    assert r.classify("abc", None, "unauth", ff_safe=False) == r.UNKNOWN
    assert r.classify("abc", None, "error", ff_safe=False) == r.UNKNOWN


def test_no_github_head_is_unknown():
    assert r.classify(None, "abc", "ok", ff_safe=False) == r.UNKNOWN


# ── reconcile_repo: the actuation, with an injected git runner ────────────────────────────────

class FakeGit:
    """Answers git subcommands with configured return codes; records the push."""
    def __init__(self, is_ancestor_rc=0, push_rc=0):
        self.is_ancestor_rc = is_ancestor_rc
        self.push_rc = push_rc
        self.calls = []

    def __call__(self, args):
        self.calls.append(args)
        if "--is-ancestor" in args:
            return self.is_ancestor_rc, ""
        if "push" in args:
            return self.push_rc, ""
        return 0, ""

    def pushed(self):
        return any("push" in c for c in self.calls)


def test_reconcile_in_sync_does_not_push():
    g = FakeGit()
    st = r.reconcile_repo("repo", gh="same", gt="same", gt_status="ok", run=g)
    assert st == r.IN_SYNC and not g.pushed()


def test_reconcile_behind_fast_forwards():
    g = FakeGit(is_ancestor_rc=0, push_rc=0)   # gitea head IS an ancestor -> ff safe
    st = r.reconcile_repo("repo", gh="new", gt="old", gt_status="ok", run=g)
    assert st == r.HEALED and g.pushed()


def test_reconcile_diverged_never_pushes():
    g = FakeGit(is_ancestor_rc=1)              # not an ancestor -> conflict
    st = r.reconcile_repo("repo", gh="A", gt="B", gt_status="ok", run=g)
    assert st == r.DIVERGED and not g.pushed()


def test_reconcile_push_failure_reported():
    g = FakeGit(is_ancestor_rc=0, push_rc=1)   # ff safe but push fails
    st = r.reconcile_repo("repo", gh="new", gt="old", gt_status="ok", run=g)
    assert st == r.PUSH_FAILED


def test_reconcile_gitea_missing_does_not_push():
    g = FakeGit()
    st = r.reconcile_repo("repo", gh="x", gt=None, gt_status="missing", run=g)
    assert st == r.GITEA_MISSING and not g.pushed()


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
    print(f"reconcile_scm: {len(fns)}/{len(fns)} tests pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
