#!/usr/bin/env python3
"""GBRG supply-chain operational-risk scoring — a scored verdict, never a number.

Integrates the software supply-chain operational-risk framework (BIAN/FICO,
workbook v0.2) into the GBRG governed blast-radius graph / risk plane. It scores
a graph subject at three granularities — a single **node**, a critical-service
**path** (chain of nodes), or a common-mode concentration **cluster** — and emits
a governance-native ``SupplyChainRiskProofArtifact`` (extends the estate-canonical
ProofArtifact v1), sealed and persisted to the durable, hash-chained
:mod:`gbrg.governance.ledger` (the receipt spine reused verbatim).

CONSUME, NOT FORK
-----------------
  * Weights, rating thresholds, controls-evidence requirements and KRI/KCI
    thresholds are DECLARED DATA loaded from
    ``contracts/supply-chain-risk-weights.v0.json`` — never magic numbers here.
  * The BIAN/FICO control-taxonomy binding is loaded from
    ``contracts/supply-chain-bian-fico-crosswalk.v0.json``; the ``governed_ontology``
    in that file is the SINGLE allow-list a crosswalk term may bind to.
  * The seal + verify machinery is :mod:`gbrg.governance.ledger` (sha256 =
    FIPS-180-4), reused unchanged: each assessment is a hash-chained ledger event
    that ``ledger.verify_ledger`` verifies with no modification.
  * The ok/sad/bad projection follows the estate's **Assay** verdict model:
    ``method=computed`` over declared weights, projected to a VERIFIES / FLAGGED /
    REJECTED verdict at assessment time.

TEETH (fires BOTH ways, fail-closed on missing evidence)
--------------------------------------------------------
  * A node/path/cluster assessed with EVIDENCED controls and all KRIs within
    threshold **VERIFIES** (status PROVED, epistemicLevel empirical).
  * A subject that claims control efficacy (> 0) with NO evidence reference, or
    with no controls-evidence at all, is **REJECTED** — fail-closed: an
    unverifiable control claim is not evidence of low risk (status FAILED,
    epistemicLevel rejected).
  * A subject whose KRI/KCI lands in the RED band (threshold breach) is
    **FLAGGED** (status BLOCKED, epistemicLevel speculative).
  * A crosswalk term that is NOT a member of the governed ontology is REJECTED
    (:func:`validate_crosswalk_term`) — a crosswalk cannot smuggle an ungoverned
    control term into the estate vocabulary.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import ledger
from .ledger import GENESIS

# --------------------------------------------------------------------------- #
# Declared-data locations (contracts/, consume-not-fork).
# --------------------------------------------------------------------------- #
_CONTRACTS = Path(__file__).resolve().parents[1] / "contracts"
DEFAULT_WEIGHTS = _CONTRACTS / "supply-chain-risk-weights.v0.json"
DEFAULT_CROSSWALK = _CONTRACTS / "supply-chain-bian-fico-crosswalk.v0.json"

AGENT_REF = "agent-registry://gbrg/supply-chain-risk-scorer"
WEIGHTS_URN = "gbrg.supply-chain-risk.weights.v0"

# Verdicts (Assay-style projection).
VERIFIES = "VERIFIES"
FLAGGED = "FLAGGED"
REJECTED = "REJECTED"


class CrosswalkTermError(ValueError):
    """Raised when a crosswalk binds a term absent from the governed ontology."""


# --------------------------------------------------------------------------- #
# Load declared data.
# --------------------------------------------------------------------------- #
def load_weights(path: Path | str | None = None) -> dict[str, Any]:
    return json.loads(Path(path or DEFAULT_WEIGHTS).read_text(encoding="utf-8"))


def load_crosswalk(path: Path | str | None = None) -> dict[str, Any]:
    return json.loads(Path(path or DEFAULT_CROSSWALK).read_text(encoding="utf-8"))


def governed_terms(crosswalk: dict[str, Any]) -> set[str]:
    """Flatten every governed-ontology category into one allow-list set."""
    onto = crosswalk.get("governed_ontology", {})
    terms: set[str] = set()
    for category in onto.values():
        if isinstance(category, list):
            terms.update(category)
    return terms


# --------------------------------------------------------------------------- #
# Crosswalk validation — a term not in the governed ontology is rejected.
# --------------------------------------------------------------------------- #
def validate_crosswalk_term(term: str, crosswalk: dict[str, Any]) -> str | None:
    """Return None if ``term`` is a governed-ontology member, else a reason string."""
    if term in governed_terms(crosswalk):
        return None
    return f"crosswalk term {term!r} is not in the governed ontology (rejected)"


def validate_crosswalk(crosswalk: dict[str, Any]) -> list[str]:
    """Verify EVERY crosswalk entry binds only governed terms. Returns violations.

    An empty list means the crosswalk is internally governed. A non-empty list
    names each (alignment_id, term) that would smuggle an ungoverned control
    term into the estate vocabulary.
    """
    allow = governed_terms(crosswalk)
    violations: list[str] = []
    for side in ("bian_crosswalk", "fico_crosswalk"):
        for entry in crosswalk.get(side, {}).get("entries", []):
            aid = entry.get("alignment_id", "?")
            for term in entry.get("binds_ontology", []):
                if term not in allow:
                    violations.append(f"{aid}: ungoverned term {term!r}")
    return violations


def resolve_crosswalk_refs(
    refs: list[str], crosswalk: dict[str, Any]
) -> tuple[list[str], list[str]]:
    """Resolve alignment ids (e.g. 'B001','F003') -> (bound_terms, violations).

    A referenced alignment id whose bound terms are all governed contributes its
    terms; any ungoverned bound term (or an unknown alignment id) is a violation.
    """
    by_id: dict[str, dict[str, Any]] = {}
    for side in ("bian_crosswalk", "fico_crosswalk"):
        for entry in crosswalk.get(side, {}).get("entries", []):
            by_id[entry["alignment_id"]] = entry
    allow = governed_terms(crosswalk)
    bound: list[str] = []
    violations: list[str] = []
    for ref in refs:
        entry = by_id.get(ref)
        if entry is None:
            violations.append(f"unknown crosswalk alignment id {ref!r}")
            continue
        for term in entry.get("binds_ontology", []):
            if term in allow:
                bound.append(term)
            else:
                violations.append(f"{ref}: ungoverned term {term!r}")
    return bound, violations


# --------------------------------------------------------------------------- #
# Scoring — over the DECLARED weights.
# --------------------------------------------------------------------------- #
def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def rating_for(score: float, weights: dict[str, Any]) -> str:
    """Rating band for a residual score, per declared ordered thresholds."""
    for band in weights["rating_thresholds"]["ordered_bands"]:
        if score >= band["min_score"]:
            return band["rating"]
    return "Low"


def score_node_inherent(factors: dict[str, float], weights: dict[str, Any]) -> float:
    """Weighted inherent risk from the six declared factors (K,P,E,O,C,V)."""
    fw = weights["inherent_risk_factors"]["weights"]
    total = 0.0
    for key, spec in fw.items():
        total += spec["weight"] * float(factors.get(key, 0.0))
    return _clamp(total)


def score_control_efficacy(
    controls_evidence: list[dict[str, Any]], weights: dict[str, Any]
) -> float:
    """Weighted control efficacy from the six declared control families.

    Only families present in controls_evidence contribute; a family absent from
    the assessment contributes 0 efficacy (no unearned credit).
    """
    cw = weights["control_efficacy_families"]["weights"]
    by_evidence_key = {spec["evidence_key"]: (fam, spec) for fam, spec in cw.items()}
    total = 0.0
    for ce in controls_evidence:
        fam_spec = by_evidence_key.get(ce.get("controlFamily", ""))
        if fam_spec is None:
            continue
        _, spec = fam_spec
        total += spec["weight"] * float(ce.get("efficacy", 0.0))
    return _clamp(total)


def unverifiable_controls(controls_evidence: list[dict[str, Any]]) -> list[str]:
    """Return control families that claim efficacy > 0 but carry NO evidence ref.

    This is the fail-closed core: an unverifiable control claim must not be
    counted as risk reduction. An empty controls_evidence list on a subject that
    would otherwise need controls is handled by the caller (no evidence at all).
    """
    bad: list[str] = []
    for ce in controls_evidence:
        efficacy = float(ce.get("efficacy", 0.0))
        ref = ce.get("evidenceRef")
        if efficacy > 0.0 and (ref is None or str(ref).strip() == ""):
            bad.append(ce.get("controlFamily", "?"))
    return bad


def score_path_risk(node_residuals: list[float]) -> float:
    """Path risk = 1 - product(1 - residual_i) (noisy-OR over the chain)."""
    surv = 1.0
    for r in node_residuals:
        surv *= 1.0 - _clamp(float(r))
    return _clamp(1.0 - surv)


def score_cluster_inherent(
    components: dict[str, float], weights: dict[str, Any]
) -> float:
    """Common-mode inherent from the four declared cluster components."""
    cw = weights["cluster_common_mode_weights"]["weights"]
    total = 0.0
    for key, spec in cw.items():
        total += spec["weight"] * float(components.get(key, 0.0))
    return _clamp(total)


def hhi_normalized(shares: list[float]) -> float:
    """Normalized Herfindahl-Hirschman Index for provider concentration.

    HHI = sum(share^2); normalized = (HHI - 1/n)/(1 - 1/n), clamped to [0,1].
    A single provider (share 1.0) -> 1.0; n equal providers -> 0.0.
    """
    active = [float(s) for s in shares if float(s) > 0.0]
    n = len(active)
    if n <= 1:
        return 1.0 if n == 1 else 0.0
    hhi = sum(s * s for s in active)
    return _clamp((hhi - 1.0 / n) / (1.0 - 1.0 / n))


# --------------------------------------------------------------------------- #
# KRI / KCI evaluation against declared thresholds.
# --------------------------------------------------------------------------- #
def _indicator(kri_id: str, weights: dict[str, Any]) -> dict[str, Any] | None:
    for ind in weights["kri_kci_thresholds"]["indicators"]:
        if ind["id"] == kri_id:
            return ind
    return None


def evaluate_kri(kri_id: str, value: float, weights: dict[str, Any]) -> str:
    """Return 'green' | 'amber' | 'red' for a metric value against its thresholds.

    Unknown indicator -> 'red' (fail-closed: we do not silently pass an
    indicator we cannot evaluate).
    """
    ind = _indicator(kri_id, weights)
    if ind is None:
        return "red"
    v = float(value)
    if ind.get("direction") == "higher_is_better":
        if v >= ind["green"]:
            return "green"
        if v >= ind["amber_low"]:
            return "amber"
        return "red"
    # lower_is_better
    green_max = ind.get("green_max", 0)
    amber_max = ind.get("amber_max", green_max)
    if v <= green_max:
        return "green"
    if v <= amber_max:
        return "amber"
    return "red"


def evaluate_kri_set(
    metrics: dict[str, float], weights: dict[str, Any]
) -> list[dict[str, Any]]:
    """Evaluate {kri_id: value} -> a list of {id,value,band} records."""
    return [
        {"id": kri_id, "value": float(value), "band": evaluate_kri(kri_id, value, weights)}
        for kri_id, value in metrics.items()
    ]


# --------------------------------------------------------------------------- #
# The assessment record — sealed to the hash-chained ledger (receipt spine).
# --------------------------------------------------------------------------- #
@dataclass
class Assessment:
    """A scored, verdict-bearing supply-chain risk assessment (one subject)."""

    riskScope: str  # node | path | cluster
    subjectId: str
    inherentScore: float | None
    controlEfficacy: float | None
    residualScore: float
    rating: str
    verdict: str  # VERIFIES | FLAGGED | REJECTED
    status: str
    epistemicLevel: str
    controlsEvidence: list[dict[str, Any]]
    kriEvaluations: list[dict[str, Any]]
    crosswalkRefs: list[str]
    derivation: str
    proofId: str = ""
    receipt: str = ""  # the chained ledger hash, filled at persist time
    _boundTerms: list[str] = field(default_factory=list)

    def proof_artifact(self) -> dict[str, Any]:
        """Render the estate-canonical SupplyChainRiskProofArtifact (never a bare number)."""
        art: dict[str, Any] = {
            "schemaVersion": "gbrg.supply-chain-risk-proof-artifact.v0",
            "version": "1.0.0",
            "proofId": self.proofId,
            "riskScope": self.riskScope,
            "subjectId": self.subjectId,
            "claim": {
                "claimId": f"claim.supply-chain-risk.{self.riskScope}.{self.subjectId}",
                "claimType": "supply_chain_operational_risk",
                "statement": (
                    f"{self.riskScope} {self.subjectId!r} residual risk "
                    f"{self.residualScore:.3f} -> {self.rating} ({self.verdict})"
                ),
                "epistemicLevel": self.epistemicLevel,
            },
            "status": self.status,
            "residualScore": round(self.residualScore, 6),
            "rating": self.rating,
            "verdict": self.verdict,
            "weightsRef": WEIGHTS_URN,
            "crosswalkRefs": self.crosswalkRefs,
            "controlsEvidence": self.controlsEvidence,
            "kriEvaluations": self.kriEvaluations,
            "derivation": self.derivation,
            "declared_by": AGENT_REF,
        }
        if self.inherentScore is not None:
            art["inherentScore"] = round(self.inherentScore, 6)
        if self.controlEfficacy is not None:
            art["controlEfficacy"] = round(self.controlEfficacy, 6)
        return art


def _next_prev_hash(ledger_path: Path | str | None) -> str:
    """Chain head of the ledger (GENESIS if empty). Reads the VERIFIED path."""
    records = ledger.read_all(ledger_path)
    if not records:
        return GENESIS
    last = records[-1]
    return last.get("hash") or last["receipt"]


def _seal_and_persist(
    assessment: Assessment, *, ledger_path: Path | str | None, persist: bool
) -> Assessment:
    """Build a hash-chained ledger event over the artifact and append it.

    Reuses gbrg.governance.ledger unchanged: the event carries ``prev_hash`` +
    ``hash`` = ledger._sha(core), exactly the chained-event shape
    ``ledger.verify_ledger`` recomputes and walks. sha256 = FIPS-180-4.
    """
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    assessment.proofId = "proof-scr-" + uuid.uuid4().hex[:16]
    prev = _next_prev_hash(ledger_path)
    core = {
        "type": "SupplyChainRiskAssessment",
        "ts": ts,
        "prev_hash": prev,
        "artifact": assessment.proof_artifact(),
    }
    event_hash = ledger._sha(core)  # sha256 over canonical core (FIPS-180-4)
    event = dict(core)
    event["hash"] = event_hash
    assessment.receipt = event_hash
    if persist:
        ledger.append(event, ledger_path=ledger_path)
    return assessment


# --------------------------------------------------------------------------- #
# The gate: score -> project verdict -> seal -> persist.
# --------------------------------------------------------------------------- #
def _project_verdict(
    *,
    controls_evidence: list[dict[str, Any]],
    kri_evals: list[dict[str, Any]],
    require_controls: bool,
    crosswalk_violations: list[str],
) -> tuple[str, str, str, str]:
    """Assay-style projection -> (verdict, status, epistemicLevel, reason).

    Order of teeth (strictest first, fail-closed):
      1. ungoverned crosswalk term          -> REJECTED
      2. unverifiable / missing controls    -> REJECTED  (fail-closed on evidence)
      3. any KRI in the RED band            -> FLAGGED
      4. otherwise                          -> VERIFIES
    """
    if crosswalk_violations:
        return (
            REJECTED, "FAILED", "rejected",
            "REJECTED: ungoverned crosswalk term(s): " + "; ".join(crosswalk_violations),
        )

    bad_controls = unverifiable_controls(controls_evidence)
    if bad_controls:
        return (
            REJECTED, "FAILED", "rejected",
            "REJECTED (fail-closed): control efficacy claimed with NO evidence for "
            + ", ".join(bad_controls),
        )
    if require_controls and not controls_evidence:
        return (
            REJECTED, "FAILED", "rejected",
            "REJECTED (fail-closed): tier-0 subject scored with NO controls-evidence",
        )

    red = [k["id"] for k in kri_evals if k["band"] == "red"]
    if red:
        return (
            FLAGGED, "BLOCKED", "speculative",
            "FLAGGED: KRI/KCI threshold breach (RED) for " + ", ".join(red),
        )

    return (
        VERIFIES, "PROVED", "empirical",
        "VERIFIES: controls evidenced and all KRIs within threshold",
    )


def assess_node(
    *,
    subject_id: str,
    factors: dict[str, float],
    controls_evidence: list[dict[str, Any]],
    kri_metrics: dict[str, float] | None = None,
    crosswalk_refs: list[str] | None = None,
    weights: dict[str, Any] | None = None,
    crosswalk: dict[str, Any] | None = None,
    tier0: bool = True,
    ledger_path: Path | str | None = None,
    persist: bool = True,
) -> Assessment:
    """Score a single node, project a verdict, seal + persist the artifact."""
    weights = weights or load_weights()
    crosswalk = crosswalk or load_crosswalk()
    crosswalk_refs = crosswalk_refs or []
    kri_metrics = kri_metrics or {}

    bound, violations = resolve_crosswalk_refs(crosswalk_refs, crosswalk)
    inherent = score_node_inherent(factors, weights)
    # Control efficacy counts ONLY evidenced families (fail-closed at projection).
    verifiable_ce = [c for c in controls_evidence if c.get("evidenceRef")]
    efficacy = score_control_efficacy(verifiable_ce, weights)
    residual = _clamp(inherent * (1.0 - efficacy))
    rating = rating_for(residual, weights)
    kri_evals = evaluate_kri_set(kri_metrics, weights)

    verdict, status, level, reason = _project_verdict(
        controls_evidence=controls_evidence,
        kri_evals=kri_evals,
        require_controls=tier0,
        crosswalk_violations=violations,
    )
    derivation = (
        f"node {subject_id!r}: inherent={inherent:.3f} (K,P,E,O,C,V weighted), "
        f"control_efficacy={efficacy:.3f} (evidenced families only), "
        f"residual={residual:.3f} -> {rating}. {reason}. "
        f"crosswalk={crosswalk_refs} bound_terms={sorted(set(bound))}."
    )
    a = Assessment(
        riskScope="node", subjectId=subject_id, inherentScore=inherent,
        controlEfficacy=efficacy, residualScore=residual, rating=rating,
        verdict=verdict, status=status, epistemicLevel=level,
        controlsEvidence=controls_evidence, kriEvaluations=kri_evals,
        crosswalkRefs=crosswalk_refs, derivation=derivation, _boundTerms=bound,
    )
    return _seal_and_persist(a, ledger_path=ledger_path, persist=persist)


def assess_path(
    *,
    subject_id: str,
    node_residuals: list[float],
    kri_metrics: dict[str, float] | None = None,
    controls_evidence: list[dict[str, Any]] | None = None,
    crosswalk_refs: list[str] | None = None,
    weights: dict[str, Any] | None = None,
    crosswalk: dict[str, Any] | None = None,
    ledger_path: Path | str | None = None,
    persist: bool = True,
) -> Assessment:
    """Accumulate node residuals into a path risk, project a verdict, seal + persist.

    A path inherits its nodes' evidenced controls; ``controls_evidence`` here is
    the union used for the fail-closed check. A path is a tier-0 service chain, so
    it requires controls-evidence.
    """
    weights = weights or load_weights()
    crosswalk = crosswalk or load_crosswalk()
    crosswalk_refs = crosswalk_refs or []
    controls_evidence = controls_evidence or []
    kri_metrics = kri_metrics or {}

    bound, violations = resolve_crosswalk_refs(crosswalk_refs, crosswalk)
    path_risk = score_path_risk(node_residuals)
    rating = rating_for(path_risk, weights)
    kri_evals = evaluate_kri_set(kri_metrics, weights)

    verdict, status, level, reason = _project_verdict(
        controls_evidence=controls_evidence,
        kri_evals=kri_evals,
        require_controls=True,
        crosswalk_violations=violations,
    )
    derivation = (
        f"path {subject_id!r}: {len(node_residuals)} nodes, "
        f"noisy-OR path_risk={path_risk:.3f} -> {rating}. {reason}. "
        f"crosswalk={crosswalk_refs} bound_terms={sorted(set(bound))}."
    )
    a = Assessment(
        riskScope="path", subjectId=subject_id, inherentScore=None,
        controlEfficacy=None, residualScore=path_risk, rating=rating,
        verdict=verdict, status=status, epistemicLevel=level,
        controlsEvidence=controls_evidence, kriEvaluations=kri_evals,
        crosswalkRefs=crosswalk_refs, derivation=derivation, _boundTerms=bound,
    )
    return _seal_and_persist(a, ledger_path=ledger_path, persist=persist)


def assess_cluster(
    *,
    subject_id: str,
    components: dict[str, float] | None = None,
    shares: list[float] | None = None,
    resilience_control: float = 0.0,
    controls_evidence: list[dict[str, Any]] | None = None,
    kri_metrics: dict[str, float] | None = None,
    crosswalk_refs: list[str] | None = None,
    weights: dict[str, Any] | None = None,
    crosswalk: dict[str, Any] | None = None,
    ledger_path: Path | str | None = None,
    persist: bool = True,
) -> Assessment:
    """Score a common-mode concentration cluster, project a verdict, seal + persist.

    If ``shares`` is given and no explicit hhi_normalized_concentration component,
    the normalized HHI is computed from the shares (consume the workbook model).
    """
    weights = weights or load_weights()
    crosswalk = crosswalk or load_crosswalk()
    crosswalk_refs = crosswalk_refs or []
    controls_evidence = controls_evidence or []
    kri_metrics = kri_metrics or {}
    components = dict(components or {})

    if shares and "hhi_normalized_concentration" not in components:
        components["hhi_normalized_concentration"] = hhi_normalized(shares)

    bound, violations = resolve_crosswalk_refs(crosswalk_refs, crosswalk)
    inherent = score_cluster_inherent(components, weights)
    residual = _clamp(inherent * (1.0 - _clamp(resilience_control)))
    rating = rating_for(residual, weights)
    kri_evals = evaluate_kri_set(kri_metrics, weights)

    verdict, status, level, reason = _project_verdict(
        controls_evidence=controls_evidence,
        kri_evals=kri_evals,
        require_controls=True,
        crosswalk_violations=violations,
    )
    derivation = (
        f"cluster {subject_id!r}: common_mode_inherent={inherent:.3f} "
        f"(HHI,blast,ttr,exit weighted), resilience={resilience_control:.3f}, "
        f"residual={residual:.3f} -> {rating}. {reason}. "
        f"crosswalk={crosswalk_refs} bound_terms={sorted(set(bound))}."
    )
    a = Assessment(
        riskScope="cluster", subjectId=subject_id, inherentScore=inherent,
        controlEfficacy=_clamp(resilience_control), residualScore=residual,
        rating=rating, verdict=verdict, status=status, epistemicLevel=level,
        controlsEvidence=controls_evidence, kriEvaluations=kri_evals,
        crosswalkRefs=crosswalk_refs, derivation=derivation, _boundTerms=bound,
    )
    return _seal_and_persist(a, ledger_path=ledger_path, persist=persist)
