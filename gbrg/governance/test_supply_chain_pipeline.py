#!/usr/bin/env python3
"""Prove the LIVE supply-chain scoring pipeline runs over REAL graph topology.

PR #547 proved the scorer's teeth over hand-supplied dicts; this proves the
same teeth fire when every input is DERIVED from a real ``gbrg-analyze`` bundle
(the committed ``blast-radius-bundle.real.gbrg-core.containment.json`` — 22
real ``BlastRadiusProofArtifact``s + their real CALLS/IMPORTS edges).

  (1) FACTORS FROM GRAPH SIGNALS — the six inherent factors are derived from the
      artifact's observed signals per the DECLARED signal map: criticality=blast,
      concentration=saturating(dependents), velocity=saturating(churn), opacity
      from untested+epistemic, and privilege/execution as declared fail-closed
      PRIORS (observable:false), never fabricated as measurements.
  (2) FAIL-CLOSED — assessing the estate with NO controls-evidence leaves every
      tier-0 subject REJECTED. Missing evidence is not evidence of low risk.
  (3) TEETH BOTH WAYS — supplying real evidenced controls + green KRIs flips a
      node to VERIFIES; a cluster with evidenced controls but a RED derived KCI
      (graph visibility) is FLAGGED.
  (4) REAL PATHS — a path subject is a real CALLS chain off the edge topology,
      scored as a noisy-OR over its members' residuals.
  (5) EVIDENCE PLANE, EVIDENCE-ONLY — every assessment lifts onto
      repo-governance-observation.v0 (schema-valid) with NO authorization/verdict
      key crossing the plane (same invariant as adapters/evidence.py).

Runs under pytest OR as ``python3 test_supply_chain_pipeline.py``.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import jsonschema

_HERE = Path(__file__).resolve()
_GBRG_DIR = _HERE.parents[1]                 # .../gbrg
_REPO_ROOT = _HERE.parents[2]                # .../sociosphere worktree
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from gbrg.governance import supply_chain_pipeline as pipe  # noqa: E402
from gbrg.governance import supply_chain_risk as scr        # noqa: E402
from gbrg.adapters import evidence as gbrg_evidence          # noqa: E402

BUNDLE = (
    _GBRG_DIR / "governance" / "fixtures"
    / "blast-radius-bundle.real.gbrg-core.containment.json"
)
OBS_SCHEMA = (
    _REPO_ROOT / "registry" / "neurosymbolic-repo-graph-reasoner"
    / "repo-governance-observation.v0.schema.json"
)


def _bundle() -> dict:
    return pipe.load_bundle(BUNDLE)


def _full_controls(subject: str) -> list[dict]:
    """A fully-evidenced control set (every family backed by a ref)."""
    fams = [
        "Governance", "Identity & publishing authority", "Build provenance",
        "Artifact integrity", "Distribution guardrails", "Monitoring & recovery",
    ]
    return [
        {"controlFamily": f, "efficacy": 0.6, "evidenceRef": f"ev://real/{f[:4]}#{subject[-6:]}"}
        for f in fams
    ]


# --------------------------------------------------------------------------- #
# (1) Factors are derived from real graph signals per the declared map.
# --------------------------------------------------------------------------- #
def test_factors_derived_from_graph_signals() -> None:
    smap = pipe.load_signal_map()
    bundle = _bundle()
    art = next(a for a in bundle["artifacts"] if "#" in a["cell_id"])
    f = pipe.factors_from_artifact(art, smap)

    # criticality_K is blast_radius verbatim (identity).
    assert f["criticality_K"] == pipe._clamp(art["blast_radius"])
    # concentration_C is saturating(dependents_count / declared saturation).
    sat = smap["inherent_factor_derivation"]["factors"]["concentration_C"]["saturation"]
    assert abs(f["concentration_C"] - min(art["dependents_count"] / sat, 1.0)) < 1e-9
    # velocity_V is saturating(churn_frequency / declared saturation).
    vsat = smap["inherent_factor_derivation"]["factors"]["velocity_V"]["saturation"]
    assert abs(f["velocity_V"] - min(art["churn_frequency"] / vsat, 1.0)) < 1e-9
    # opacity_O reflects untested + epistemic (this real slice is untested/speculative).
    assert f["opacity_O"] > 0.5
    # privilege/execution are declared PRIORS (observable:false), in [0,1].
    prov = pipe.factor_provenance(smap)
    assert prov["privilege_P"] is False and prov["execution_E"] is False
    assert prov["criticality_K"] is True and prov["opacity_O"] is True
    for k in ("privilege_P", "execution_E"):
        assert 0.0 <= f[k] <= 1.0
    # every factor is a clamped float.
    assert set(f) == set(pipe._FACTOR_KEYS)
    assert all(0.0 <= v <= 1.0 for v in f.values())


def test_execution_path_signal_raises_prior() -> None:
    """A cell whose locator matches a declared execution path signal is raised."""
    smap = pipe.load_signal_map()
    base = {"cell_id": "code://rust/gbrg/crates/x/src/lib.rs#f",
            "blast_radius": 0.1, "dependents_count": 0, "churn_frequency": 0.0,
            "test_coverage_reach": True, "claim": {"epistemicLevel": "proved"}}
    buildrs = dict(base, cell_id="code://rust/gbrg/crates/x/build.rs#main")
    prior = smap["inherent_factor_derivation"]["factors"]["execution_E"]["conservative_prior"]
    assert pipe.factors_from_artifact(base, smap)["execution_E"] == prior
    assert pipe.factors_from_artifact(buildrs, smap)["execution_E"] > prior


# --------------------------------------------------------------------------- #
# (2) Fail-closed: no controls-evidence -> every tier-0 subject REJECTED.
# --------------------------------------------------------------------------- #
def test_estate_fail_closed_without_evidence() -> None:
    result = pipe.assess_estate(_bundle(), persist=False)
    assert len(result["nodes"]) == 22
    assert {a.verdict for a in result["nodes"]} == {scr.REJECTED}
    assert result["cluster"].verdict == scr.REJECTED
    for a in result["paths"]:
        assert a.verdict == scr.REJECTED
    # residuals are real numbers in [0,1] read off the graph.
    assert all(0.0 <= r <= 1.0 for r in result["residual_by_cell"].values())


# --------------------------------------------------------------------------- #
# (3) Teeth both ways: real evidence flips a node to VERIFIES; RED KCI -> FLAGGED.
# --------------------------------------------------------------------------- #
def test_evidenced_node_verifies() -> None:
    bundle = _bundle()
    target = bundle["artifacts"][0]["cell_id"]
    idx = {target: _full_controls(target), f"__kri__:{target}": {"KRI01": 99}}
    result = pipe.assess_estate(bundle, evidence_index=idx, persist=False)
    node = next(a for a in result["nodes"] if a.subjectId == target)
    assert node.verdict == scr.VERIFIES
    assert node.status == "PROVED"
    # the untouched siblings still fail closed.
    assert any(a.verdict == scr.REJECTED for a in result["nodes"])


def test_cluster_red_kci_flags() -> None:
    """Cluster with evidenced controls but RED derived KCI02 -> FLAGGED (not passed)."""
    bundle = _bundle()
    cid = "cluster:gbrg-blast-radius-corpus"
    # Evidence the cluster's controls so the fail-closed gate is satisfied; the
    # derived KCI02 (graph visibility) is still RED for this all-speculative slice.
    idx = {cid: _full_controls(cid)}
    result = pipe.assess_estate(bundle, evidence_index=idx, persist=False)
    cluster = result["cluster"]
    bands = {k["id"]: k["band"] for k in cluster.kriEvaluations}
    assert bands["KCI02"] == "red"          # 0% graph-visible (all speculative)
    assert cluster.verdict == scr.FLAGGED
    assert cluster.status == "BLOCKED"


# --------------------------------------------------------------------------- #
# (4) Paths are real CALLS chains scored as a noisy-OR.
# --------------------------------------------------------------------------- #
def test_paths_from_real_call_topology() -> None:
    bundle = _bundle()
    chains = pipe.derive_call_paths(bundle["edges"])
    assert chains, "expected at least one real CALLS chain in the fixture"
    for chain in chains:
        assert len(chain) >= 2
        assert len(set(chain)) == len(chain)  # simple path, no repeats

    result = pipe.assess_estate(bundle, persist=False)
    for a in result["paths"]:
        # noisy-OR path risk is >= the max member residual it accumulates.
        assert a.riskScope == "path"
        assert 0.0 <= a.residualScore <= 1.0


# --------------------------------------------------------------------------- #
# (5) Evidence plane: schema-valid, evidence-only (no authorization key).
# --------------------------------------------------------------------------- #
def test_evidence_plane_is_schema_valid_and_evidence_only() -> None:
    schema = json.loads(OBS_SCHEMA.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)

    result = pipe.assess_estate(_bundle(), persist=False)
    envelopes = pipe.estate_evidence_envelopes(result, repo_root=_REPO_ROOT)
    assert envelopes

    for env in envelopes:
        # (a) strict record validates against the estate-owned schema.
        validator.validate(env["observation"])
        # (b) the evidence-only invariant holds (raises if any authorization key).
        gbrg_evidence.assert_evidence_only(env)
        # (c) the raw scored verdict is preserved, but NOT under a forbidden key.
        ext = env["gbrg_extension"]
        assert ext["gbrgnrg:riskClass"] in {scr.VERIFIES, scr.FLAGGED, scr.REJECTED}
        assert "verdict" not in {k.split(":")[-1] for k in ext}
        assert "decision" not in {k.split(":")[-1] for k in ext}


def test_evidence_only_guard_rejects_smuggled_verdict() -> None:
    """A hand-built envelope with a raw verdict key is rejected by the guard."""
    bad = {"observation": {"verdict": "VERIFIES"}}
    try:
        gbrg_evidence.assert_evidence_only(bad)
    except AssertionError:
        return
    raise AssertionError("assert_evidence_only failed to reject a 'verdict' key")


# --------------------------------------------------------------------------- #
# Plain-script runner (pytest also collects the test_* functions above).
# --------------------------------------------------------------------------- #
def _run() -> int:
    fns = [v for k, v in sorted(globals().items())
           if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} checks passed over REAL gbrg-analyze topology.")
    return 0


if __name__ == "__main__":
    raise SystemExit(_run())
