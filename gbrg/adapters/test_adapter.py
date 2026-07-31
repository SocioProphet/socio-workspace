#!/usr/bin/env python3
"""Prove the GBRG evidence producer conforms to the estate EVIDENCE contract.

From a REAL ``gbrg-analyze`` ProofArtifact (the committed real fixture
``gbrg/governance/fixtures/proof-artifact.real.gbrg-core.as_label.json``) this
test asserts:

  (a) every produced observation VALIDATES against the estate-owned
      ``repo-governance-observation.v0.schema.json``;
  (b) both the mapped ``confidence`` (on the record) and the raw
      ``epistemicLevel`` (in the GBRG envelope) are present;
  (c) NO policyDecision / authorization field is emitted anywhere
      (evidence-only invariant);
  (d) the adapter's protocol methods (repositories/graph_fixture/source_inputs)
      behave, and graph_fixture carries the pinned corpus loop with an EMPTY
      policy_decision (GBRG does not decide policy).

Runs under pytest OR as a plain script (``python3 test_adapter.py``). It puts
the ``gbrg/`` parent on sys.path so ``gbrg.adapters`` imports as a package.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import jsonschema

_HERE = Path(__file__).resolve()
_GBRG_DIR = _HERE.parents[1]                 # .../gbrg
_REPO_ROOT = _HERE.parents[2]                # .../sociosphere worktree
if str(_GBRG_DIR.parent) not in sys.path:
    sys.path.insert(0, str(_GBRG_DIR.parent))

from gbrg.adapters import evidence as gbrg_evidence  # noqa: E402
from gbrg.adapters.gbrg_repo_graph_adapter import GbrgRepoGraphAdapter  # noqa: E402

REAL_FIXTURE = _GBRG_DIR / "governance" / "fixtures" / "proof-artifact.real.gbrg-core.as_label.json"
SCHEMA_PATH = (
    _REPO_ROOT / "registry" / "neurosymbolic-repo-graph-reasoner"
    / "repo-governance-observation.v0.schema.json"
)


def _load_real_artifact() -> dict:
    return json.loads(REAL_FIXTURE.read_text(encoding="utf-8"))


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_real_artifact_produces_schema_valid_evidence() -> None:
    artifact = _load_real_artifact()
    schema = _schema()
    validator = jsonschema.Draft202012Validator(schema)

    envelopes = gbrg_evidence.proof_to_observations(
        artifact, subject_repository="SocioProphet/sociosphere", repo_root=_REPO_ROOT
    )
    assert envelopes, "expected at least one evidence envelope from the real artifact"

    for env in envelopes:
        record = env["observation"]
        # (a) validates against the estate schema
        validator.validate(record)
        # (b) confidence present on record AND raw epistemicLevel present in envelope
        assert record["confidence"] in {"exact", "derived", "heuristic"}
        assert env["gbrg_extension"]["gbrgnrg:epistemicLevel"]
        # confidence is the documented coarsening of the raw epistemicLevel
        assert record["confidence"] == gbrg_evidence.epistemic_to_confidence(
            env["gbrg_extension"]["gbrgnrg:epistemicLevel"]
        )
        # (c) evidence-only: no authorization/policyDecision anywhere
        flat = json.dumps(env)
        for banned in ("policyDecision", "policy_decision", "authoriz", "verdict"):
            assert banned not in flat, f"forbidden authorization token {banned!r} leaked"
        gbrg_evidence.assert_evidence_only(env)


def test_confidence_and_epistemic_for_real_speculative_cell() -> None:
    artifact = _load_real_artifact()
    assert artifact["claim"]["epistemicLevel"] == "speculative"  # the real cell
    envelopes = gbrg_evidence.proof_to_observations(
        artifact, subject_repository="SocioProphet/sociosphere", repo_root=_REPO_ROOT
    )
    # speculative -> heuristic (documented mapping)
    assert all(e["observation"]["confidence"] == "heuristic" for e in envelopes)


def test_adapter_protocol_methods() -> None:
    adapter = GbrgRepoGraphAdapter.from_fixture_dir(
        _GBRG_DIR / "governance" / "fixtures", repo_root=_REPO_ROOT
    )
    repos = adapter.repositories()
    assert repos and repos[0].present_in_canonical_sources is True

    fixture = adapter.graph_fixture()
    assert fixture.corpus_loop == "watson-cyc-semantic-web-chronos-v1"
    # evidence-only: GBRG leaves the policy decision EMPTY
    assert fixture.policy_decision == ""

    inputs = adapter.source_inputs()
    assert any("gbrg-core/src/lib.rs" in gi.source_path for gi in inputs)

    # every evidence record the adapter emits is evidence-only
    for env in adapter.evidence_records():
        gbrg_evidence.assert_evidence_only(env)


def _main() -> int:
    tests = [
        test_real_artifact_produces_schema_valid_evidence,
        test_confidence_and_epistemic_for_real_speculative_cell,
        test_adapter_protocol_methods,
    ]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
