"""Coverage for tools/discover_unregistered_repos.py.

The discovery logic is exercised against a FAKE org list (a recorded `gh repo list`
response replayed through an injected runner) and a FAKE registry (tiny surface files
written into a tmp root), so the test asserts exactly which repos are flagged
unregistered without ever touching the network or the committed estate.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, "tools")

import discover_unregistered_repos as disc  # noqa: E402


def make_runner(repos):
    """Return a runner that replays *repos* as a `gh repo list --json ...` response."""
    payload = json.dumps(repos)

    def runner(argv):
        assert argv[:3] == ["gh", "repo", "list"]
        assert "--json" in argv
        return disc.RunResult(0, stdout=payload)

    return runner


def write_registry(root: Path, *, boundaries=(), matrix=(), canonical=()):
    """Write a minimal registry: repos named here count as 'registered'."""
    (root / "catalog").mkdir(parents=True, exist_ok=True)
    (root / "registry").mkdir(parents=True, exist_ok=True)
    (root / "catalog" / "boundaries.yaml").write_text(
        yaml.safe_dump({"entries": [{"repo": r} for r in boundaries]}), "utf-8")
    (root / "registry" / "repo-governance-matrix-v0.yaml").write_text(
        yaml.safe_dump({"repositories": [{"name": r} for r in matrix]}), "utf-8")
    (root / "registry" / "canonical-repos.yaml").write_text(
        yaml.safe_dump({"repositories": [{"url": f"https://github.com/{r}"} for r in canonical]}), "utf-8")


ORG = "SocioProphet"


def _repo(name, *, archived=False, fork=False):
    return {"name": name, "url": f"https://github.com/{ORG}/{name}",
            "isArchived": archived, "isFork": fork}


def test_flags_exactly_the_unregistered(tmp_path):
    write_registry(tmp_path, boundaries=["SocioProphet/known-a"], matrix=["SocioProphet/known-b"])
    org_repos = [
        _repo("known-a"),          # registered via boundary atlas
        _repo("known-b"),          # registered via governance matrix
        _repo("socbase"),          # NOT registered -> must be flagged
        _repo("brand-new-repo"),   # NOT registered -> must be flagged
    ]
    report = disc.discover([ORG], root=tmp_path, runner=make_runner(org_repos))

    flagged = [u["repo"] for u in report["unregistered"]]
    assert flagged == ["SocioProphet/brand-new-repo", "SocioProphet/socbase"]  # sorted
    assert report["counts"]["org_total"] == 4
    assert report["counts"]["unregistered"] == 2


def test_archived_and_forks_excluded(tmp_path):
    write_registry(tmp_path)
    org_repos = [
        _repo("live-unregistered"),
        _repo("old-thing", archived=True),
        _repo("someones-fork", fork=True),
    ]
    report = disc.discover([ORG], root=tmp_path, runner=make_runner(org_repos))
    assert [u["repo"] for u in report["unregistered"]] == ["SocioProphet/live-unregistered"]


def test_allowlist_suppresses(tmp_path):
    write_registry(tmp_path)
    org_repos = [_repo(".github"), _repo("real-gap")]
    report = disc.discover([ORG], root=tmp_path, runner=make_runner(org_repos),
                           extra_allow=[".github"])
    assert [u["repo"] for u in report["unregistered"]] == ["SocioProphet/real-gap"]


def test_short_key_matches_across_url_and_orgname_forms():
    # a repo is registered whether the surface names it org/Name, a git URL, or bare
    assert disc.short("SocioProphet/socbase") == "socbase"
    assert disc.short("https://github.com/SocioProphet/socbase") == "socbase"
    assert disc.short("git@github-443:SocioProphet/socbase.git") == "socbase"
    assert disc.short("ssh://git@ssh.github.com:443/SocioProphet/socbase.git") == "socbase"
    assert disc.short("Socbase") == "socbase"


def test_registered_key_reads_all_surfaces(tmp_path):
    write_registry(tmp_path, boundaries=["SocioProphet/b-repo"],
                   matrix=["SocioProphet/m-repo"], canonical=["SocioProphet/c-repo"])
    keys = disc.load_registered_keys(tmp_path)
    assert {"b-repo", "m-repo", "c-repo"}.issubset(keys)


def test_main_exit_nonzero_when_unregistered(tmp_path, monkeypatch, capsys):
    write_registry(tmp_path)
    monkeypatch.setattr(disc, "ROOT", tmp_path)
    monkeypatch.setattr(disc, "list_org_repos",
                        lambda org, **kw: [_wire(_repo("gap"), org)])
    code = disc.main(["--org", ORG])
    assert code == 1
    assert "UNREGISTERED" in capsys.readouterr().out


def test_main_exit_zero_when_all_registered(tmp_path, monkeypatch, capsys):
    write_registry(tmp_path, boundaries=["SocioProphet/only-repo"])
    monkeypatch.setattr(disc, "ROOT", tmp_path)
    monkeypatch.setattr(disc, "list_org_repos",
                        lambda org, **kw: [_wire(_repo("only-repo"), org)])
    code = disc.main(["--org", ORG, "--json"])
    assert code == 0
    assert json.loads(capsys.readouterr().out)["counts"]["unregistered"] == 0


def _wire(raw, org):
    """Shape a fake `gh` record the way list_org_repos would."""
    return {"full_name": f"{org}/{raw['name']}", "org": org, "name": raw["name"],
            "url": raw["url"], "archived": raw["isArchived"], "fork": raw["isFork"]}


def test_build_register_has_one_entry_per_repo(tmp_path):
    write_registry(tmp_path)
    report = disc.discover([ORG], root=tmp_path,
                           runner=make_runner([_repo("a"), _repo("b")]))
    reg = disc.build_register(report)
    assert [r["repo"] for r in reg["repos"]] == ["SocioProphet/a", "SocioProphet/b"]
    assert all(r["status"] == "unregistered" for r in reg["repos"])


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
