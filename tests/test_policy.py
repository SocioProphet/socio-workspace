"""Policy-bound governance: the declared policy governs decisions, with an opinionated default.

Keystone: the committed registry/self-heal-policy.yaml must equal the code DEFAULT_POLICY, so
the declared governance and the opinionated default cannot silently drift. The rest proves the
policy actually governs `decide` and that overrides are validated and merged.
"""

import textwrap

import pytest

from automation import responder
from automation.policy import (
    DEFAULT_POLICY,
    DEFAULT_POLICY_FILE,
    ResponsePolicy,
    load_policy,
    policy_from_mapping,
    validate_policy,
)


def _beacon(kind="stale_vendor", **ev):
    e = {"detector": "d", "reproducible": True, "stale": False}
    e.update(ev)
    return {"kind_class": kind, "system": "x", "evidence": e}


# --- keystone: declared policy == opinionated default -----------------------

def test_committed_policy_file_equals_default():
    assert DEFAULT_POLICY_FILE.exists(), "the declared default policy file must be committed"
    assert load_policy(DEFAULT_POLICY_FILE).as_dict() == DEFAULT_POLICY.as_dict()


def test_default_policy_is_valid():
    validate_policy(DEFAULT_POLICY)  # must not raise


# --- the policy actually governs decide -------------------------------------

def test_default_decision_matches_default_policy():
    # stale_vendor Law is weak by default -> propose_pr
    assert responder.decide(_beacon("stale_vendor"))["action"] == "propose_pr"


def test_custom_law_changes_the_decision():
    custom = policy_from_mapping({"law_by_kind": {"stale_vendor": "sealed"}})
    r = responder.decide(_beacon("stale_vendor"), policy=custom)
    assert r["action"] == "auto_fix"          # governed up to auto_fix by the override


def test_tighter_iri_threshold_escalates():
    b = _beacon("mirror_drift")
    b["entropy_uniqueness"] = 0.3             # IRI = 0.45*0.3 = 0.135
    assert responder.decide(b)["action"] == "auto_fix"      # under default 0.55
    strict = policy_from_mapping({"iri_block": 0.1})
    assert responder.decide(b, policy=strict)["action"] == "escalate_human"


def test_run_once_is_governed_by_policy(tmp_path, monkeypatch):
    from automation.durable_queue import DurableQueue, state_dir
    monkeypatch.setenv("SOCIOSPHERE_STATE_DIR", str(tmp_path / "state"))
    inbox = DurableQueue(state_dir() / "beacons")
    decisions = DurableQueue(state_dir() / "decisions")
    inbox.put(_beacon("build_failure"))       # default Law probable -> canary_fix
    strict = policy_from_mapping({"law_by_kind": {"build_failure": "refuse"}})
    out = responder.run_once(inbox=inbox, decisions=decisions, policy=strict)
    assert out[0]["action"] == "block"        # governed down to refuse -> block


# --- overrides are partial, merged, and validated ---------------------------

def test_partial_override_merges_over_default():
    p = policy_from_mapping({"law_by_kind": {"build_failure": "sealed"}})
    assert p.law_for("build_failure") == "sealed"     # overridden
    assert p.law_for("stale_vendor") == "weak"        # untouched default
    assert p.action_for("weak") == "propose_pr"       # default verdict_action preserved


def test_unknown_class_falls_to_default_law():
    assert DEFAULT_POLICY.law_for("some_new_class") == "refuse"  # fail-closed


@pytest.mark.parametrize("bad", [
    {"law_by_kind": {"mirror_drift": "bogus"}},
    {"default_law": "nope"},
    {"verdict_action": {"sealed": "explode"}},
    {"verdict_action": {"not_a_verdict": "auto_fix"}},
    {"iri_block": 1.5},
])
def test_invalid_policy_is_rejected(bad):
    with pytest.raises(ValueError):
        policy_from_mapping(bad)


def test_empty_boundary_axes_falls_back_to_default_fence():
    # An empty/omitted axes list cannot silently disable the safety fence — it keeps default.
    p = policy_from_mapping({"boundary_axes": []})
    assert p.boundary_axes == DEFAULT_POLICY.boundary_axes


def test_directly_constructed_empty_fence_is_rejected():
    from dataclasses import replace
    with pytest.raises(ValueError):
        validate_policy(replace(DEFAULT_POLICY, boundary_axes=()))


# --- loading from declared sources ------------------------------------------

def test_load_missing_file_returns_default(tmp_path):
    got = load_policy(tmp_path / "nope.yaml")
    assert got.as_dict() == DEFAULT_POLICY.as_dict()


def test_load_from_yaml_override(tmp_path):
    f = tmp_path / "policy.yaml"
    f.write_text(textwrap.dedent("""\
        law_by_kind:
          stale_vendor: sealed
        iri_block: 0.9
    """), encoding="utf-8")
    p = load_policy(f)
    assert p.law_for("stale_vendor") == "sealed"
    assert p.iri_block == 0.9
    assert p.law_for("mirror_drift") == "sealed"    # default preserved


def test_env_var_selects_policy_source(tmp_path, monkeypatch):
    f = tmp_path / "env-policy.yaml"
    f.write_text("iri_block: 0.2\n", encoding="utf-8")
    monkeypatch.setenv("SOCIOSPHERE_SELF_HEAL_POLICY", str(f))
    assert load_policy().iri_block == 0.2
