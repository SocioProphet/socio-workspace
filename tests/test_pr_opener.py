"""Tests for the self-heal PR opener + drainer — the piece that makes a recorded
proposal become an actual, human-reviewable fix PR. Everything runs against a fake
git/gh runner so no network, credentials, or real repo are touched."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automation.pr_opener import RunResult, open_pr  # noqa: E402
from automation import executors  # noqa: E402
from automation.durable_queue import DurableQueue  # noqa: E402
from automation.open_recorded_proposals import drain_and_open  # noqa: E402


class FakeGit:
    """Records argv calls; returns canned results keyed by a command signature."""
    def __init__(self, pr_exists=False):
        self.calls = []
        self.pr_exists = pr_exists

    def __call__(self, argv, *, cwd=None):
        self.calls.append(argv)
        # gh pr list --head ... --json url : return an existing URL only if pr_exists
        if argv[:3] == ["gh", "pr", "list"]:
            return RunResult(0, stdout=("https://example/pr/7\n" if self.pr_exists else "\n"))
        if argv[:3] == ["gh", "pr", "create"]:
            return RunResult(0, stdout="https://example/pr/42\n")
        if argv[:2] == ["git", "status"]:
            return RunResult(0, stdout=" M packaging/x\n")  # pretend there is a delta
        return RunResult(0)

    def ran(self, *prefix):
        return any(c[:len(prefix)] == list(prefix) for c in self.calls)


VALID = {
    "title": "fix(pkg): align version",
    "branch": "self-heal/version-drift",
    "base": "main",
    "files": {"packaging/VERSION": "0.1.0\n"},
    "repo": "SocioProphet/demo",
}


def test_opens_new_pr_and_writes_files(tmp_path):
    (tmp_path / "packaging").mkdir()
    git = FakeGit(pr_exists=False)
    url = open_pr(VALID, repo_dir=tmp_path, runner=git)
    assert url == "https://example/pr/42"
    # file was materialized
    assert (tmp_path / "packaging/VERSION").read_text() == "0.1.0\n"
    # branch started from origin/main, committed, pushed with lease, PR created
    assert git.ran("git", "checkout", "-B", "self-heal/version-drift", "origin/main")
    assert git.ran("git", "commit")
    assert git.ran("git", "push", "--force-with-lease")
    assert git.ran("gh", "pr", "create")


REVERT = {
    "title": "revert(self-heal): abc123 — search-api regressed",
    "branch": "self-heal/deploy_regression/revert-abc123",
    "base": "main",
    "revert": "abc123def456",
    "repo": "SocioProphet/demo",
}


def test_revert_proposal_git_reverts_the_bad_commit(tmp_path):
    git = FakeGit(pr_exists=False)
    url = open_pr(REVERT, repo_dir=tmp_path, runner=git)
    assert url == "https://example/pr/42"
    # it git-reverts the offending commit (not a hand-patch), then pushes + opens the PR
    assert git.ran("git", "revert", "--no-edit", "abc123def456")
    assert not git.ran("git", "add")            # no file materialization on a revert
    assert git.ran("git", "push", "--force-with-lease")
    assert git.ran("gh", "pr", "create")


def test_proposal_needs_files_or_revert(tmp_path):
    import pytest
    with pytest.raises(ValueError):
        open_pr({"title": "t", "branch": "b", "repo": "o/r"}, repo_dir=tmp_path, runner=FakeGit())


def test_reuses_existing_pr(tmp_path):
    (tmp_path / "packaging").mkdir()
    git = FakeGit(pr_exists=True)
    url = open_pr(VALID, repo_dir=tmp_path, runner=git)
    assert url == "https://example/pr/7"          # reused, not created
    assert not git.ran("gh", "pr", "create")


def test_fail_closed_on_push_error(tmp_path):
    (tmp_path / "packaging").mkdir()

    def boom(argv, *, cwd=None):
        if argv[:2] == ["git", "push"]:
            return RunResult(1, stderr="permission denied")
        if argv[:2] == ["git", "status"]:
            return RunResult(0, stdout=" M x\n")
        return RunResult(0)

    try:
        open_pr(VALID, repo_dir=tmp_path, runner=boom)
    except RuntimeError as exc:
        assert "permission denied" in str(exc)
    else:
        raise AssertionError("expected RuntimeError on push failure")


def test_rejects_path_escape(tmp_path):
    bad = {**VALID, "files": {"../etc/passwd": "x"}}
    try:
        open_pr(bad, repo_dir=tmp_path, runner=FakeGit())
    except ValueError as exc:
        assert "escapes" in str(exc)
    else:
        raise AssertionError("expected ValueError on path escape")


def test_invalid_proposal_rejected(tmp_path):
    for bad in [{}, {"title": "x"}, {"title": "x", "branch": "b", "files": {}}]:
        try:
            open_pr(bad, repo_dir=tmp_path, runner=FakeGit())
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected ValueError for {bad!r}")


def test_record_then_drain_and_open(tmp_path):
    """End-to-end: propose_pr records (no opener) -> drainer opens via a fake opener."""
    proposals = tmp_path / "proposals"
    beacon = {"kind_class": "version_drift", "system": "turtleterm", "proposal": VALID}
    rec = executors.propose_pr(beacon=beacon, proposals_dir=proposals)
    assert rec["proposed"] is True and rec["opened"] is False
    assert DurableQueue(proposals).qsize() == 1

    seen = {}
    def fake_opener(proposal, *, repo_dir):
        seen["p"] = proposal
        seen["dir"] = repo_dir
        return "https://example/pr/99"
    def fake_checkout(repo, workdir):
        seen["repo"] = repo
        return workdir / "checkout"

    results = drain_and_open(proposals_dir=proposals, opener=fake_opener, checkout=fake_checkout)
    assert len(results) == 1 and results[0]["opened"] is True
    assert results[0]["pr_url"] == "https://example/pr/99"
    assert seen["p"]["branch"] == "self-heal/version-drift"
    assert seen["repo"] == "SocioProphet/demo"          # target repo was checked out
    assert seen["dir"].name == "checkout"               # opener ran in that checkout
    assert DurableQueue(proposals).empty()  # consumed on success


def test_drain_requeues_then_dead_letters(tmp_path):
    proposals = tmp_path / "proposals"
    dead = tmp_path / "dead"
    DurableQueue(proposals).put({"id": "x1", "beacon_kind": "k", "proposal": VALID})

    def always_fail(proposal, *, repo_dir):
        raise RuntimeError("nope")
    passthrough_checkout = lambda repo, workdir: tmp_path

    # attempts 1 and 2 re-queue; attempt 3 dead-letters and drains.
    for expected_attempt in (1, 2):
        res = drain_and_open(proposals_dir=proposals, dead_letter_dir=dead,
                             opener=always_fail, checkout=passthrough_checkout)
        assert res[0]["opened"] is False and res[0]["attempts"] == expected_attempt
        assert not res[0].get("dead_lettered")
        assert DurableQueue(proposals).qsize() == 1  # re-queued

    res = drain_and_open(proposals_dir=proposals, dead_letter_dir=dead,
                         opener=always_fail, checkout=passthrough_checkout)
    assert res[0]["dead_lettered"] is True and res[0]["attempts"] == 3
    assert DurableQueue(proposals).empty()          # no longer retried
    assert DurableQueue(dead).qsize() == 1          # parked for a human


def _run_all():
    import tempfile
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        with tempfile.TemporaryDirectory() as d:
            fn(Path(d))
        passed += 1
    print(f"pr_opener: {passed}/{len(fns)} tests pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
