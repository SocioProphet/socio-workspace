#!/usr/bin/env python3
"""Prove the GBRG supply-chain risk scorer has TEETH — and they fire BOTH ways.

A risk scorer that only ever produces a number is not governance. This test
asserts the four teeth from the work order:

  (A) VERIFIES — a node with EVIDENCED controls and all KRIs within threshold
      -> verdict VERIFIES (status PROVED, epistemicLevel empirical), sealed to
      the hash-chained ledger, and the WHOLE ledger verifies.
  (B) REJECTED — a node claiming control efficacy > 0 with NO evidence ref, and
      a tier-0 node with NO controls-evidence at all, both fail CLOSED (verdict
      REJECTED, status FAILED). Missing evidence is not evidence of low risk.
  (C) FLAGGED — a critical-service PATH whose KRI lands in the RED band (a
      threshold breach) -> verdict FLAGGED (status BLOCKED).
  (D) REJECTED — a crosswalk term that is NOT in the governed ontology is
      rejected (validate_crosswalk_term + an assess referencing an ungoverned
      binding), and the SHIPPED crosswalk is internally governed (0 violations).

Plus receipt-spine reuse: every assessment is a hash-chained ledger event that
gbrg.governance.ledger.verify_ledger walks; a single tampered field breaks it.

Runs under pytest OR as `python3 test_supply_chain_risk.py`.
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from gbrg.governance import ledger, supply_chain_risk as scr  # noqa: E402


def _evidenced_controls() -> list[dict]:
    """A realistic, fully-evidenced control set (each efficacy backed by a ref)."""
    return [
        {"controlFamily": "Governance", "efficacy": 0.7, "evidenceRef": "ev://owner-register#N003"},
        {"controlFamily": "Identity & publishing authority", "efficacy": 0.6, "evidenceRef": "ev://oidc-trusted-publish#N003"},
        {"controlFamily": "Build provenance", "efficacy": 0.6, "evidenceRef": "ev://slsa-attestation#N003"},
        {"controlFamily": "Artifact integrity", "efficacy": 0.5, "evidenceRef": "ev://sigstore-rekor#N003"},
        {"controlFamily": "Distribution guardrails", "efficacy": 0.4, "evidenceRef": "ev://lockfile-policy#N003"},
        {"controlFamily": "Monitoring & recovery", "efficacy": 0.5, "evidenceRef": "ev://rollback-drill-q3#N003"},
    ]


def run_scenario(ledger_path: Path) -> dict:
    w = scr.load_weights()
    x = scr.load_crosswalk()

    # (A) VERIFIES — evidenced controls, KRIs green.
    a_verify = scr.assess_node(
        subject_id="N003:CI/CD runner / build system",
        factors={"criticality_K": 0.9, "privilege_P": 0.9, "execution_E": 0.9,
                 "opacity_O": 0.5, "concentration_C": 0.7, "velocity_V": 0.7},
        controls_evidence=_evidenced_controls(),
        kri_metrics={"KRI01": 98, "KCI01": 96},  # both green (>=95)
        crosswalk_refs=["B001", "F003"],
        weights=w, crosswalk=x, ledger_path=ledger_path,
    )

    # (B) REJECTED — efficacy claimed with NO evidence ref (fail-closed).
    no_ev = _evidenced_controls()
    no_ev[2]["evidenceRef"] = None  # Build provenance claims 0.6 but cannot show it
    b_no_evref = scr.assess_node(
        subject_id="N003:unevidenced-provenance",
        factors={"criticality_K": 0.9, "privilege_P": 0.9, "execution_E": 0.9,
                 "opacity_O": 0.5, "concentration_C": 0.7, "velocity_V": 0.7},
        controls_evidence=no_ev,
        kri_metrics={"KRI01": 98},
        crosswalk_refs=["B001"], weights=w, crosswalk=x, ledger_path=ledger_path,
    )

    # (B2) REJECTED — tier-0 node with NO controls-evidence at all.
    b_empty = scr.assess_node(
        subject_id="N002:maintainer-identity-no-controls",
        factors={"criticality_K": 0.95, "privilege_P": 1.0, "execution_E": 0.1,
                 "opacity_O": 0.6, "concentration_C": 0.7, "velocity_V": 0.5},
        controls_evidence=[], kri_metrics={}, crosswalk_refs=["B001"],
        weights=w, crosswalk=x, tier0=True, ledger_path=ledger_path,
    )

    # (C) FLAGGED — a path whose KRI breaches the RED band.
    c_path = scr.assess_path(
        subject_id="P004:Publish release",
        node_residuals=[0.3, 0.25, 0.2, 0.15],
        controls_evidence=_evidenced_controls(),
        kri_metrics={"KRI05": 6.0},  # median rollback 6h > 4h -> RED
        crosswalk_refs=["B002", "B008"], weights=w, crosswalk=x,
        ledger_path=ledger_path,
    )

    # (D) REJECTED — crosswalk that binds an UNGOVERNED term.
    tampered = copy.deepcopy(x)
    tampered["bian_crosswalk"]["entries"].append({
        "alignment_id": "B999",
        "software_ormf_object": "smuggled control",
        "binds_ontology": ["quantum_flux_capacitor"],  # not in governed ontology
        "bian_service_domain": "Nonexistent",
    })
    d_crosswalk = scr.assess_node(
        subject_id="N001:ungoverned-crosswalk",
        factors={"criticality_K": 0.8, "privilege_P": 0.4, "execution_E": 0.2,
                 "opacity_O": 0.5, "concentration_C": 0.6, "velocity_V": 0.8},
        controls_evidence=_evidenced_controls(), kri_metrics={},
        crosswalk_refs=["B999"], weights=w, crosswalk=tampered,
        ledger_path=ledger_path,
    )

    return {
        "verify": a_verify, "no_evref": b_no_evref, "empty": b_empty,
        "flagged_path": c_path, "crosswalk": d_crosswalk,
        "weights": w, "crosswalk_doc": x, "tampered": tampered,
    }


def _assert_all(r: dict, ledger_path: Path) -> list[str]:
    checks: list[str] = []

    def ok(name: str, cond: bool, detail: str = "") -> None:
        assert cond, f"FAILED: {name} {detail}"
        checks.append(f"PASS: {name}")

    w = r["weights"]

    # Declared weights are internally consistent (sum to 1.0).
    for grp in ("inherent_risk_factors", "control_efficacy_families", "cluster_common_mode_weights"):
        s = sum(spec["weight"] for spec in w[grp]["weights"].values())
        ok(f"weights sum to 1.0 ({grp})", abs(s - 1.0) < 1e-9, f"got {s}")

    # (A) VERIFIES.
    a = r["verify"]
    ok("(A) verdict VERIFIES", a.verdict == scr.VERIFIES, f"got {a.verdict}")
    ok("(A) status PROVED", a.status == "PROVED", f"got {a.status}")
    ok("(A) epistemicLevel empirical", a.epistemicLevel == "empirical")
    ok("(A) residual < inherent (controls reduced risk)", a.residualScore < a.inherentScore)
    ok("(A) rating from thresholds", a.rating in {"Low", "Moderate", "High", "Critical"})
    ok("(A) proof artifact carries residualScore not a bare float",
       "residualScore" in a.proof_artifact() and "claim" in a.proof_artifact())

    # (B) REJECTED — fail-closed on missing evidence.
    b = r["no_evref"]
    ok("(B) no-evidence-ref -> REJECTED", b.verdict == scr.REJECTED, f"got {b.verdict}")
    ok("(B) status FAILED", b.status == "FAILED", f"got {b.status}")
    ok("(B) epistemicLevel rejected", b.epistemicLevel == "rejected")
    ok("(B) derivation names fail-closed", "fail-closed" in b.derivation.lower())

    b2 = r["empty"]
    ok("(B2) tier-0 no-controls -> REJECTED", b2.verdict == scr.REJECTED, f"got {b2.verdict}")
    ok("(B2) status FAILED", b2.status == "FAILED")

    # Same-shape contrast: (A) and (B) have identical factors; only evidence differs.
    ok("(A vs B) evidence, not score, drives the split",
       a.verdict == scr.VERIFIES and b.verdict == scr.REJECTED
       and abs(a.inherentScore - b.inherentScore) < 1e-9)

    # (C) FLAGGED — KRI red band.
    c = r["flagged_path"]
    ok("(C) path KRI-red -> FLAGGED", c.verdict == scr.FLAGGED, f"got {c.verdict}")
    ok("(C) status BLOCKED", c.status == "BLOCKED", f"got {c.status}")
    ok("(C) a KRI evaluated RED", any(k["band"] == "red" for k in c.kriEvaluations))
    ok("(C) path_risk is noisy-OR accumulation (> max node residual)",
       c.residualScore > 0.3, f"got {c.residualScore}")

    # (D) REJECTED — ungoverned crosswalk term.
    d = r["crosswalk"]
    ok("(D) ungoverned crosswalk term -> REJECTED", d.verdict == scr.REJECTED, f"got {d.verdict}")
    ok("(D) derivation... rejection recorded on the artifact",
       "ungoverned" in d.derivation.lower() or d.status == "FAILED")

    # (D) unit-level term validation + the shipped crosswalk is internally governed.
    x = r["crosswalk_doc"]
    ok("(D) validate_crosswalk_term passes a governed term",
       scr.validate_crosswalk_term("node_risk", x) is None)
    ok("(D) validate_crosswalk_term rejects an ungoverned term",
       scr.validate_crosswalk_term("quantum_flux_capacitor", x) is not None)
    ok("(D) SHIPPED crosswalk has 0 ungoverned bindings",
       scr.validate_crosswalk(x) == [], f"violations={scr.validate_crosswalk(x)}")
    ok("(D) TAMPERED crosswalk is caught by validate_crosswalk",
       any("quantum_flux_capacitor" in v for v in scr.validate_crosswalk(r["tampered"])))

    # KRI evaluator directly, both directions.
    ok("KRI05 (lower-is-better) 6h -> red", scr.evaluate_kri("KRI05", 6.0, w) == "red")
    ok("KRI05 1h -> green", scr.evaluate_kri("KRI05", 1.0, w) == "green")
    ok("KRI01 (higher-is-better) 98% -> green", scr.evaluate_kri("KRI01", 98, w) == "green")
    ok("KRI01 85% -> amber", scr.evaluate_kri("KRI01", 85, w) == "amber")
    ok("unknown KRI -> red (fail-closed)", scr.evaluate_kri("KRI_NOPE", 100, w) == "red")

    # Cluster HHI: single provider -> 1.0; two equal -> 0.0.
    ok("HHI single provider -> 1.0", abs(scr.hhi_normalized([1.0]) - 1.0) < 1e-9)
    ok("HHI two equal providers -> 0.0", abs(scr.hhi_normalized([0.5, 0.5]) - 0.0) < 1e-9)

    # RECEIPT SPINE — the whole ledger verifies, and a tamper is caught.
    vr = ledger.verify_ledger(ledger_path)
    ok("ledger verifies (hash chain intact)", vr.ok, f"reason={vr.reason}")
    persisted = ledger.read_all(ledger_path)
    ok("all 5 assessments persisted", len(persisted) == 5, f"got {len(persisted)}")
    for rec in persisted:
        seal = rec["hash"]
        ok(f"receipt is sha256 ({rec['artifact']['riskScope']}/{rec['artifact']['verdict']})",
           isinstance(seal, str) and seal.startswith("sha256:") and len(seal) == len("sha256:") + 64)

    # Tamper a persisted artifact field -> verification must FAIL.
    raw = ledger_path.read_text(encoding="utf-8").splitlines()
    first = json.loads(raw[0])
    first["artifact"]["residualScore"] = 0.0  # forge a lower risk
    raw[0] = json.dumps(first, sort_keys=True, separators=(",", ":"))
    tamper_path = ledger_path.parent / "tampered.jsonl"
    tamper_path.write_text("\n".join(raw) + "\n", encoding="utf-8")
    vr2 = ledger.verify_ledger(tamper_path)
    ok("tampered ledger FAILS verification (tamper-evident)", not vr2.ok,
       f"unexpectedly ok; head={vr2.head}")

    return checks


def test_supply_chain_risk_has_teeth() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ledger_path = Path(tmp) / "scr.jsonl"
        results = run_scenario(ledger_path)
        checks = _assert_all(results, ledger_path)
    assert checks, "no checks ran"


def _main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        ledger_path = Path(tmp) / "scr.jsonl"
        results = run_scenario(ledger_path)
        checks = _assert_all(results, ledger_path)
        for c in checks:
            print(c)
        print("\n--- REJECTED (fail-closed, no controls-evidence) ---")
        print(json.dumps(results["empty"].proof_artifact(), indent=2, sort_keys=True))
        print("\n--- FLAGGED (path KRI threshold breach) ---")
        print(json.dumps(results["flagged_path"].proof_artifact(), indent=2, sort_keys=True))
    print(f"\nALL {len(checks)} CHECKS PASSED — scorer has teeth, fires all four ways.")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
