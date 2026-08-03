#!/usr/bin/env python3
"""Map a GBRG ProofArtifact to repo-governance-observation.v0 EVIDENCE records.

GBRG's ``gbrg-analyze`` produces a ``BlastRadiusProofArtifact`` per code cell
(function/method): ``dependents_count`` (in-degree), ``test_coverage_reach``,
``churn_frequency``, a ``blast_radius`` float, and a ``claim`` whose
``epistemicLevel`` sits on GBRG's 6-value spectrum. This module lifts each such
artifact onto the estate's EVIDENCE plane by emitting records that validate
against the estate-owned schema

    registry/neurosymbolic-repo-graph-reasoner/repo-governance-observation.v0.schema.json

so GBRG becomes a first-class, provenance-carrying evidence source for the
governance corpus loop — the "future Prophet Platform adapter" the bootstrap
adapter docstring invites, implemented at CODE granularity.

────────────────────────────────────────────────────────────────────────────
EVIDENCE ONLY, NEVER AUTHORIZATION  (load-bearing invariant)
────────────────────────────────────────────────────────────────────────────
A ProofArtifact is EVIDENCE about code. It is NOT a policy decision. This module
therefore NEVER emits ``policyDecision`` / ``policy_decision`` or any
authorization/verdict field. GBRG evidence FEEDS policy-fabric; it does not
decide. The estate schema is ``additionalProperties: false`` and has no
``policyDecision`` property, so a conformant record is *structurally* incapable
of carrying one — and :func:`assert_evidence_only` enforces the same invariant
on the surrounding envelope as a second, explicit gate. See the NRG code-cell
TTL extension (``gbrg/contracts/nrg-codecell-extension.ttl``): it too declares
no policy term.

────────────────────────────────────────────────────────────────────────────
epistemicLevel → confidence  (a documented, lossy coarsening)
────────────────────────────────────────────────────────────────────────────
The estate ``confidence`` enum has 3 values; GBRG's ``epistemicLevel`` has 6.
The mapping below is a SUPERSET coarsening: mapping DOWN to confidence loses
information, so the raw 6-value ``epistemicLevel`` is preserved verbatim in the
GBRG-namespaced envelope (``gbrgnrg:epistemicLevel``) alongside the record.

    epistemicLevel   confidence   rationale
    --------------   ----------   ---------------------------------------------
    proved           exact        machine-checked / direct evidence
    empirical        exact        grounded in real test/measurement reads
    bounded          derived      holds within proven bounds/thresholds
    synthetic        derived      derived over synthetic (not-real) data
    speculative      heuristic    no test evidence; behaviour speculated
    rejected         heuristic    claim could not be established

Provenance fields on every record:
  parser_id         = "gbrg-tree-sitter"  (GBRG parses via tree-sitter)
  extraction_method = the frozen-index blast-radius read that produced the value
  source_blob_sha   = the 40-hex git blob SHA-1 of the cell's source file
  evidence_digest   = 64-hex sha256 over the record's canonical semantic content

NOTE on ``ast_hash``: GBRG's ``SemanticCell.ast_hash`` is a *sha256* (64 hex) of
the AST/source slice, which does NOT satisfy the schema's ``source_blob_sha``
40-hex git-SHA-1 pattern. So ``source_blob_sha`` is the true git blob SHA-1 of
the source file (content-addressed identity the estate can resolve), and when an
artifact carries an ``ast_hash`` it is preserved in the envelope as
``gbrgnrg:astHash``.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "0.1"
PARSER_ID = "gbrg-tree-sitter"

# The evidence-plane confidence enum is a 3-value COARSENING of GBRG's 6-value
# epistemicLevel spectrum. Mapping is documented in the module docstring.
EPISTEMIC_TO_CONFIDENCE: dict[str, str] = {
    "proved": "exact",
    "empirical": "exact",
    "bounded": "derived",
    "synthetic": "derived",
    "speculative": "heuristic",
    "rejected": "heuristic",
}

# Keys that would turn EVIDENCE into AUTHORIZATION. None may ever appear on a
# GBRG-produced observation record or its envelope. (Belt-and-suspenders: the
# estate schema already forbids unknown keys and has no such property.)
FORBIDDEN_AUTHORIZATION_KEYS = frozenset({
    "policyDecision", "policy_decision", "policydecision",
    "authorization", "authorize", "authorized",
    "decision", "verdict", "allow", "deny", "ledgerRequired",
})


def epistemic_to_confidence(epistemic_level: str) -> str:
    """Coarsen a GBRG epistemicLevel to the evidence-plane confidence enum."""
    try:
        return EPISTEMIC_TO_CONFIDENCE[epistemic_level]
    except KeyError as exc:  # unknown level -> weakest confidence, never crash silently
        raise ValueError(
            f"unknown GBRG epistemicLevel {epistemic_level!r}; "
            f"expected one of {sorted(EPISTEMIC_TO_CONFIDENCE)}"
        ) from exc


def _sanitize_id(text: str) -> str:
    """Reduce arbitrary text to the observation_id charset [A-Za-z0-9._/-]."""
    return re.sub(r"[^A-Za-z0-9._/-]+", "-", text).strip("-")


def cell_source_path(cell_id: str) -> str:
    """Repo-relative source path for a GBRG cell id.

    ``code://rust/crates/gbrg-core/src/lib.rs#as_label`` ->
    ``gbrg/crates/gbrg-core/src/lib.rs`` (drop the ``code://`` scheme, drop the
    leading language segment, and re-root under ``gbrg/`` where the crates live).
    """
    locator = cell_id.split("://", 1)[-1].split("#", 1)[0]
    parts = locator.split("/")
    if parts and parts[0] in {"rust", "python", "py", "ts", "typescript", "js"}:
        parts = parts[1:]
    rel = "/".join(parts)
    if not rel.startswith("gbrg/"):
        rel = f"gbrg/{rel}"
    return rel


def git_blob_sha(abs_path: str | Path) -> str:
    """40-hex git blob SHA-1 of a file's bytes (matches ``git hash-object``)."""
    data = Path(abs_path).read_bytes()
    h = hashlib.sha1()
    h.update(b"blob " + str(len(data)).encode() + b"\x00")
    h.update(data)
    return h.hexdigest()


def _evidence_digest(record_wo_digest: dict[str, Any]) -> str:
    """64-hex sha256 over the record's canonical (sorted, compact) content."""
    canonical = json.dumps(record_wo_digest, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# Each metric emitted from one ProofArtifact: (metric key, value builder).
# predicate/surface are drawn from the CLOSED estate enums. The base schema was
# authored for repo-granularity governance surfaces and has no numeric-metric
# predicate, so code metrics use the closest honest enum members:
#   surface   = "canonical_sources"  (the value is read off parsed source code)
#   predicate = "mentions_repo"      (the cell participates in the repo's graph)
# The specific metric identity is preserved in observation_id and the envelope,
# and the value string is self-describing.
_METRICS = ("dependents_count", "test_coverage_reach", "churn")


def _metric_value(metric: str, artifact: dict[str, Any]) -> Any:
    if metric == "dependents_count":
        return str(int(artifact["dependents_count"]))
    if metric == "test_coverage_reach":
        return bool(artifact["test_coverage_reach"])  # boolean value
    if metric == "churn":
        churn = artifact.get("churn_frequency", artifact.get("churn"))
        return f"{float(churn):.10g}"
    raise ValueError(f"unknown metric {metric!r}")


def proof_to_observations(
    artifact: dict[str, Any],
    *,
    subject_repository: str,
    repo_root: str | Path,
    valid_at: datetime | None = None,
) -> list[dict[str, Any]]:
    """Map ONE ProofArtifact to a list of evidence ENVELOPES (one per metric).

    Each envelope is::

        {"observation": <strict repo-governance-observation.v0 record>,
         "gbrg_extension": {"gbrgnrg:...": ...}}   # the superset, kept separate

    The ``observation`` validates against repo-governance-observation.v0; the
    ``gbrg_extension`` carries the raw 6-value epistemicLevel and other
    GBRG-namespaced context the (additionalProperties:false) record cannot hold.
    """
    when = (valid_at or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")

    cell_id = artifact["cell_id"]
    claim = artifact.get("claim", {})
    epistemic_level = claim.get("epistemicLevel", "")
    confidence = epistemic_to_confidence(epistemic_level)

    source_path = cell_source_path(cell_id)
    abs_source = Path(repo_root) / source_path
    source_blob = git_blob_sha(abs_source)

    cell_slug = _sanitize_id(cell_id)
    envelopes: list[dict[str, Any]] = []

    for metric in _METRICS:
        value = _metric_value(metric, artifact)
        extraction_method = (
            f"gbrg-analyze/frozen-index blast-radius read: {metric} "
            f"(tree-sitter AST cells -> hg_analytics in-degree/tested-by/churn)"
        )
        record: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "observation_id": f"obs:gbrg/{cell_slug}/{metric}",
            "subject_repository": subject_repository,
            "surface": "canonical_sources",
            "predicate": "mentions_repo",
            "value": value,
            "source_path": source_path,
            "source_blob_sha": source_blob,
            "parser_id": PARSER_ID,
            "extraction_method": extraction_method,
            "confidence": confidence,
            "temporal_validity": {"valid_at": when, "valid_until": None},
        }
        record["evidence_digest"] = _evidence_digest(record)

        extension: dict[str, Any] = {
            "gbrgnrg:cellId": cell_id,
            "gbrgnrg:metric": metric,
            "gbrgnrg:epistemicLevel": epistemic_level,  # raw 6-value superset
            "gbrgnrg:confidenceMappedFrom": epistemic_level,
            "gbrgnrg:blastRadius": artifact.get("blast_radius"),
            "gbrgnrg:status": artifact.get("status"),
            "gbrgnrg:proofId": artifact.get("proofId"),
            "gbrgnrg:claimId": claim.get("claimId"),
            "gbrgnrg:generated": artifact.get("generated"),
            "gbrgnrg:declaredBy": artifact.get("declared_by"),
        }
        if "ast_hash" in artifact:  # sha256, does not fit source_blob_sha slot
            extension["gbrgnrg:astHash"] = artifact["ast_hash"]

        envelope = {"observation": record, "gbrg_extension": extension}
        assert_evidence_only(envelope)
        envelopes.append(envelope)

    return envelopes


# Measured signals lifted from a SupplyChainRiskProofArtifact onto the plane.
# The scored VERDICT (VERIFIES/FLAGGED/REJECTED) is NOT one of these: it lives in
# the sealed ledger, and only namespaced (gbrgnrg:) risk context crosses here —
# never as an authorization key (see assert_evidence_only + module docstring).
_SCR_METRICS = ("residualScore", "rating")


def _scr_metric_value(metric: str, artifact: dict[str, Any]) -> str:
    if metric == "residualScore":
        return f"{float(artifact['residualScore']):.6g}"
    if metric == "rating":
        return str(artifact["rating"])
    raise ValueError(f"unknown SCR metric {metric!r}")


def scr_to_observations(
    scr_artifact: dict[str, Any],
    *,
    subject_repository: str,
    repo_root: str | Path,
    anchor_cell_id: str,
    valid_at: datetime | None = None,
) -> list[dict[str, Any]]:
    """Lift ONE SupplyChainRiskProofArtifact onto the EVIDENCE plane.

    Emits ``repo-governance-observation.v0`` envelopes for the artifact's MEASURED
    risk signals (residual score, rating), each anchored to a real source blob via
    ``anchor_cell_id`` (a node subject anchors to its own cell; a path/cluster to a
    representative member cell). The scored VERDICT and status are risk classes,
    not authorization: they are preserved in the GBRG-namespaced envelope under
    non-authorization keys, and :func:`assert_evidence_only` guarantees no
    verdict/decision/allow/deny/policyDecision key ever reaches the plane. GBRG
    feeds policy-fabric; it never decides.
    """
    when = (valid_at or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")

    claim = scr_artifact.get("claim", {})
    epistemic_level = claim.get("epistemicLevel", "")
    confidence = epistemic_to_confidence(epistemic_level)

    source_path = cell_source_path(anchor_cell_id)
    source_blob = git_blob_sha(Path(repo_root) / source_path)

    subject_slug = _sanitize_id(scr_artifact.get("subjectId", ""))
    risk_scope = scr_artifact.get("riskScope", "node")
    kri_bands = [
        {"id": k.get("id"), "band": k.get("band")}
        for k in scr_artifact.get("kriEvaluations", [])
    ]
    envelopes: list[dict[str, Any]] = []

    for metric in _SCR_METRICS:
        value = _scr_metric_value(metric, scr_artifact)
        extraction_method = (
            f"gbrg supply-chain-risk scorer: {risk_scope} {metric} over declared "
            f"weights (graph-signal-derived factors -> residual, Assay projection)"
        )
        record: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "observation_id": f"obs:gbrg-scr/{risk_scope}/{subject_slug}/{metric}",
            "subject_repository": subject_repository,
            "surface": "topology",
            "predicate": "mentions_repo",
            "value": value,
            "source_path": source_path,
            "source_blob_sha": source_blob,
            "parser_id": PARSER_ID,
            "extraction_method": extraction_method,
            "confidence": confidence,
            "temporal_validity": {"valid_at": when, "valid_until": None},
        }
        record["evidence_digest"] = _evidence_digest(record)

        extension: dict[str, Any] = {
            "gbrgnrg:proofId": scr_artifact.get("proofId"),
            "gbrgnrg:riskScope": risk_scope,
            "gbrgnrg:subjectId": scr_artifact.get("subjectId"),
            "gbrgnrg:metric": metric,
            "gbrgnrg:residualScore": scr_artifact.get("residualScore"),
            "gbrgnrg:rating": scr_artifact.get("rating"),
            # The scored verdict is a RISK CLASS, not an authorization decision —
            # keyed to avoid any forbidden-authorization word, and gated below.
            "gbrgnrg:riskClass": scr_artifact.get("verdict"),
            "gbrgnrg:status": scr_artifact.get("status"),
            "gbrgnrg:epistemicLevel": epistemic_level,
            "gbrgnrg:weightsRef": scr_artifact.get("weightsRef"),
            "gbrgnrg:kriBands": kri_bands,
            "gbrgnrg:anchorCellId": anchor_cell_id,
            "gbrgnrg:declaredBy": scr_artifact.get("declared_by"),
        }
        envelope = {"observation": record, "gbrg_extension": extension}
        assert_evidence_only(envelope)  # EVIDENCE only — never an authorization key
        envelopes.append(envelope)

    return envelopes


def observation_records(envelopes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Strict schema-valid records only (drop the GBRG envelope)."""
    return [env["observation"] for env in envelopes]


def assert_evidence_only(envelope: dict[str, Any]) -> None:
    """Enforce the evidence-only invariant: no authorization/policyDecision key.

    Raises AssertionError if any forbidden key appears anywhere in the envelope
    (record or extension). GBRG produces evidence; it never authorizes.
    """
    def _walk(obj: Any, path: str) -> None:
        if isinstance(obj, dict):
            for key, val in obj.items():
                bare = key.split(":", 1)[-1]  # ignore gbrgnrg: namespace prefix
                if bare in FORBIDDEN_AUTHORIZATION_KEYS or key in FORBIDDEN_AUTHORIZATION_KEYS:
                    raise AssertionError(
                        f"evidence-only invariant violated: authorization key "
                        f"{key!r} at {path}. GBRG emits evidence, never a decision."
                    )
                _walk(val, f"{path}.{key}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                _walk(item, f"{path}[{i}]")

    _walk(envelope, "$")
