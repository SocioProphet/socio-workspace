#!/usr/bin/env python3
"""LIVE supply-chain risk scoring over the real HellGraph blast-radius topology.

PR #547 shipped the contract + scorer + teeth (:mod:`supply_chain_risk`), but
the scorer takes CALLER-SUPPLIED factor/residual/component dicts. This module is
the missing half: it pulls node / path / cluster subjects off the REAL
``gbrg-analyze`` output — ``BlastRadiusProofArtifact``s plus the emitted
``CALLS``/``IMPORTS``/``TESTED_BY`` edges — and maps observed graph signals to
the six inherent factors and the four common-mode cluster components, so the
scorer runs over live topology instead of hand-supplied numbers.

Three moving parts, each consume-not-fork:

  (1) FACTORS FROM GRAPH SIGNALS.  :func:`factors_from_artifact` /
      :func:`cluster_components_from_artifacts` map artifact signals
      (``blast_radius``, ``dependents_count``, ``churn_frequency``,
      ``test_coverage_reach``, ``epistemicLevel``) to K,P,E,O,C,V and the four
      cluster components. The MAPPING is DECLARED DATA loaded from
      ``contracts/supply-chain-graph-signal-map.v0.json`` — never magic numbers
      here. A factor the code graph cannot observe (privilege / execution) uses
      a declared fail-closed prior raised only by real path signals on the cell
      locator, and is recorded as a PRIOR (not a measurement) in the derivation.

  (2) CONTROLS-EVIDENCE + KRI/KCI FROM REAL SOURCES, FAIL-CLOSED.  Controls come
      from an OPTIONAL ``evidence_index`` (real evidence where available); a
      subject with no evidence entry carries NO controls-evidence and a tier-0
      subject therefore fails CLOSED (REJECTED) in the scorer — missing evidence
      is not evidence of low risk. KRI/KCI metrics are auto-derived ONLY where
      the graph genuinely computes them (``KCI02`` graph visibility, ``KRI04``
      concentration); every other indicator is left unevaluated (never silently
      passed) unless supplied externally.

  (3) EMIT ONTO THE EVIDENCE PLANE, EVIDENCE-ONLY.  :func:`estate_evidence_envelopes`
      lifts each sealed ``SupplyChainRiskProofArtifact`` onto
      ``repo-governance-observation.v0`` via
      :func:`gbrg.adapters.evidence.scr_to_observations`, which enforces the SAME
      invariant as the rest of :mod:`gbrg.adapters.evidence`: GBRG emits EVIDENCE
      about risk, NEVER an authorization/verdict key. The scored verdict lives
      in the sealed, hash-chained ledger; the evidence plane carries only the
      measured risk signals that FEED policy-fabric.

CONSUME-ONLY: this module READS :mod:`supply_chain_risk` (the scorer),
:mod:`gbrg.adapters.evidence` (the evidence producer), and the two declared
contracts. It never modifies them. All new code lives under ``gbrg/``.

Cross-ref: SocioProphet/sociosphere#547, prophet-workspace#108 item 2.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

if __package__ in (None, ""):  # run as a plain script: bootstrap the package path
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from gbrg.governance import supply_chain_risk as scr
else:
    from . import supply_chain_risk as scr

# --------------------------------------------------------------------------- #
# Declared-data location (contracts/, consume-not-fork).
# --------------------------------------------------------------------------- #
_CONTRACTS = Path(__file__).resolve().parents[1] / "contracts"
DEFAULT_SIGNAL_MAP = _CONTRACTS / "supply-chain-graph-signal-map.v0.json"

# The six inherent factor keys, in the order the weights contract declares them.
_FACTOR_KEYS = (
    "criticality_K", "privilege_P", "execution_E",
    "opacity_O", "concentration_C", "velocity_V",
)


def load_signal_map(path: Path | str | None = None) -> dict[str, Any]:
    return json.loads(Path(path or DEFAULT_SIGNAL_MAP).read_text(encoding="utf-8"))


def load_bundle(path: Path | str) -> dict[str, Any]:
    """Load a ``gbrg-analyze --emit-edges`` bundle ``{artifacts, edges}``.

    Also accepts a bare ``[artifact, ...]`` array (no edges) for the
    default output shape — edges default to empty (no derivable paths).
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        return {"artifacts": data, "edges": []}
    return {"artifacts": data.get("artifacts", []), "edges": data.get("edges", [])}


# --------------------------------------------------------------------------- #
# Contract drift guard — the signal map and the weights contract must agree.
# --------------------------------------------------------------------------- #
def validate_signal_map(
    signal_map: dict[str, Any] | None = None,
    weights: dict[str, Any] | None = None,
) -> list[str]:
    """Verify the signal map cannot DRIFT from the weights contract. Returns violations.

    The signal map DERIVES the factors/components the weights contract COMBINES;
    if the two disagree on which factors, cluster components, or KRI/KCI ids
    exist, a derived value would be silently dropped (weighted by 0) or a KRI
    would be un-evaluatable. An empty list means the two declared files are
    mutually consistent. This is the same governance instinct as
    :func:`supply_chain_risk.validate_crosswalk` — a contract cannot smuggle a
    term its partner contract does not know.
    """
    signal_map = signal_map or load_signal_map()
    weights = weights or scr.load_weights()
    violations: list[str] = []

    def _cmp(kind: str, derived: set[str], declared: set[str]) -> None:
        for extra in sorted(derived - declared):
            violations.append(f"{kind}: signal-map derives {extra!r} absent from weights")
        for missing in sorted(declared - derived):
            violations.append(f"{kind}: weights declares {missing!r} with no signal-map derivation")

    _cmp(
        "inherent_factor",
        set(signal_map["inherent_factor_derivation"]["factors"]),
        set(weights["inherent_risk_factors"]["weights"]),
    )
    _cmp(
        "cluster_component",
        set(signal_map["cluster_common_mode_derivation"]["components"]),
        set(weights["cluster_common_mode_weights"]["weights"]),
    )

    # Every auto-derived KRI/KCI id must exist in the weights thresholds.
    declared_ids = {i["id"] for i in weights["kri_kci_thresholds"]["indicators"]}
    for kri_id in signal_map.get("derived_kri_kci", {}).get("indicators", {}):
        if kri_id not in declared_ids:
            violations.append(
                f"derived_kri_kci: {kri_id!r} has no threshold in weights kri_kci_thresholds"
            )

    # Every declared path-signal regex must compile — a malformed pattern in the
    # declared data must be caught HERE (fail-closed), not crash mid-scoring.
    for fac, spec in signal_map["inherent_factor_derivation"]["factors"].items():
        for sig in spec.get("path_signals", []):
            try:
                re.compile(sig["pattern"])
            except re.error as exc:
                violations.append(
                    f"inherent_factor {fac}: uncompilable path_signal {sig.get('pattern')!r} ({exc})"
                )
    return violations


# --------------------------------------------------------------------------- #
# Transforms (over the DECLARED signal map — never magic numbers here).
# --------------------------------------------------------------------------- #
def _clamp(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _saturating(value: float, saturation: float) -> float:
    """Linear saturating map: value/saturation, clamped to [0,1]."""
    if saturation <= 0:
        return 1.0 if value > 0 else 0.0
    return _clamp(float(value) / float(saturation))


def _source_locator(artifact: dict[str, Any]) -> str:
    """The cell's source locator (path portion of the cell_id, no fragment)."""
    cell_id = artifact.get("cell_id", "")
    return cell_id.split("://", 1)[-1].split("#", 1)[0]


def _path_signal_value(locator: str, signals: list[dict[str, Any]]) -> float | None:
    """Max declared path-signal value whose pattern matches the locator, else None."""
    best: float | None = None
    for sig in signals:
        if re.search(sig["pattern"], locator):
            val = float(sig["value"])
            best = val if best is None else max(best, val)
    return best


# --------------------------------------------------------------------------- #
# (1) Factors from real graph signals.
# --------------------------------------------------------------------------- #
def factors_from_artifact(
    artifact: dict[str, Any], signal_map: dict[str, Any]
) -> dict[str, float]:
    """Map ONE BlastRadiusProofArtifact's graph signals to the six factors.

    Returns ``{criticality_K, privilege_P, execution_E, opacity_O,
    concentration_C, velocity_V}``, each clamped to [0,1], derived per the
    DECLARED ``inherent_factor_derivation`` in the signal map.
    """
    spec = signal_map["inherent_factor_derivation"]["factors"]
    epistemic = artifact.get("claim", {}).get("epistemicLevel", "")
    locator = _source_locator(artifact)
    out: dict[str, float] = {}

    # criticality_K <- blast_radius (identity)
    out["criticality_K"] = _clamp(artifact.get("blast_radius", 0.0))

    # concentration_C <- saturating(dependents_count)
    c = spec["concentration_C"]
    out["concentration_C"] = _saturating(
        artifact.get("dependents_count", 0), c["saturation"]
    )

    # velocity_V <- saturating(churn_frequency)
    v = spec["velocity_V"]
    out["velocity_V"] = _saturating(
        artifact.get("churn_frequency", 0.0), v["saturation"]
    )

    # opacity_O <- untested_component + epistemic_component
    o = spec["opacity_O"]
    unt = o["untested_component"]
    tested = bool(artifact.get("test_coverage_reach", False))
    untested_val = unt["value_when_tested"] if tested else unt["value_when_untested"]
    epi = o["epistemic_component"]
    epi_val = epi["opacity_by_level"].get(epistemic, 1.0)  # unknown level -> opaque
    out["opacity_O"] = _clamp(
        unt["weight"] * untested_val + epi["weight"] * epi_val
    )

    # execution_E <- fail-closed prior, raised by codegen / path signals
    e = spec["execution_E"]
    e_val = float(e["conservative_prior"])
    if artifact.get("generated", False):
        e_val = max(e_val, float(e["generated_raises_to"]))
    e_sig = _path_signal_value(locator, e.get("path_signals", []))
    if e_sig is not None:
        e_val = max(e_val, e_sig)
    out["execution_E"] = _clamp(e_val)

    # privilege_P <- fail-closed prior, raised by path signals
    p = spec["privilege_P"]
    p_val = float(p["conservative_prior"])
    p_sig = _path_signal_value(locator, p.get("path_signals", []))
    if p_sig is not None:
        p_val = max(p_val, p_sig)
    out["privilege_P"] = _clamp(p_val)

    return out


def factor_provenance(signal_map: dict[str, Any]) -> dict[str, bool]:
    """{factor: observable?} — whether each factor is read off the graph or a prior."""
    spec = signal_map["inherent_factor_derivation"]["factors"]
    return {k: bool(spec[k].get("observable", False)) for k in _FACTOR_KEYS}


# --------------------------------------------------------------------------- #
# Cluster components from an aggregate over member artifacts.
# --------------------------------------------------------------------------- #
def cluster_components_from_artifacts(
    artifacts: list[dict[str, Any]], signal_map: dict[str, Any]
) -> tuple[dict[str, float], list[float]]:
    """Derive the four common-mode components + the provider shares for a cluster.

    Returns ``(components, shares)`` where ``components`` feeds
    :func:`supply_chain_risk.assess_cluster` and ``shares`` (members'
    dependents_count normalized to sum 1) is its HHI input.
    """
    if not artifacts:
        return {}, []
    deps = [max(0.0, float(a.get("dependents_count", 0))) for a in artifacts]
    total = sum(deps)
    shares = [d / total for d in deps] if total > 0 else [1.0 / len(deps)] * len(deps)

    blasts = [_clamp(a.get("blast_radius", 0.0)) for a in artifacts]
    untested = [not bool(a.get("test_coverage_reach", False)) for a in artifacts]
    opacities = [factors_from_artifact(a, signal_map)["opacity_O"] for a in artifacts]

    components = {
        # hhi_normalized_concentration is computed by assess_cluster from `shares`;
        # we still expose it here for derivation transparency.
        "hhi_normalized_concentration": scr.hhi_normalized(shares),
        "blast_radius": max(blasts) if blasts else 0.0,
        "time_to_recover": sum(untested) / len(untested),
        "exit_difficulty": sum(opacities) / len(opacities),
    }
    return components, shares


# --------------------------------------------------------------------------- #
# (2) Controls-evidence + KRI/KCI from real sources, fail-closed.
# --------------------------------------------------------------------------- #
def controls_from_index(
    subject_id: str, evidence_index: dict[str, list[dict[str, Any]]] | None
) -> list[dict[str, Any]]:
    """Controls-evidence for a subject from a real evidence index, else [].

    ``evidence_index`` maps ``subject_id -> [{controlFamily, efficacy,
    evidenceRef}, ...]``. A subject with no entry gets NO controls-evidence, so a
    tier-0 subject fails CLOSED in the scorer (REJECTED). This is the deliberate
    fail-closed default when real controls evidence is absent.
    """
    if not evidence_index:
        return []
    return list(evidence_index.get(subject_id, []))


def graph_visibility_percent(
    artifacts: list[dict[str, Any]], signal_map: dict[str, Any]
) -> float:
    """KCI02: percent of members whose epistemicLevel is graph-visible."""
    ind = signal_map["derived_kri_kci"]["indicators"]["KCI02"]
    visible = set(ind["graph_visible_levels"])
    if not artifacts:
        return 0.0
    n_vis = sum(
        1 for a in artifacts
        if a.get("claim", {}).get("epistemicLevel", "") in visible
    )
    return 100.0 * n_vis / len(artifacts)


def cluster_kri_metrics(
    artifacts: list[dict[str, Any]],
    hhi: float,
    signal_map: dict[str, Any],
) -> dict[str, float]:
    """Auto-derived cluster-scope KRI/KCI metrics (only the genuinely computable)."""
    ind = signal_map["derived_kri_kci"]["indicators"]
    thr = float(ind["KRI04"]["concentration_threshold"])
    return {
        "KCI02": graph_visibility_percent(artifacts, signal_map),
        "KRI04": 1.0 if hhi > thr else 0.0,
    }


# --------------------------------------------------------------------------- #
# Path derivation from real CALLS topology.
# --------------------------------------------------------------------------- #
def derive_call_paths(
    edges: list[dict[str, Any]],
    *,
    kinds: tuple[str, ...] = ("CALLS",),
    max_paths: int = 8,
    max_len: int = 12,
) -> list[list[str]]:
    """Derive representative call chains from the real edge topology.

    A "path" (critical-service chain) is a deterministic greedy walk in the
    directed subgraph of ``kinds`` edges, starting from a root (no in-edge of
    that kind) and following the smallest-id unvisited successor to a sink. A
    greedy walk (not exact-longest, which is NP-hard) keeps this O(V+E) so it is
    safe over large crates; the simple-path guard breaks recursion cycles.
    Bounded by ``max_paths`` / ``max_len``.
    """
    adj: dict[str, list[str]] = {}
    indeg: dict[str, int] = {}
    nodes: set[str] = set()
    for e in edges:
        if e.get("kind") not in kinds:
            continue
        frm, to = e["from"], e["to"]
        adj.setdefault(frm, []).append(to)
        indeg[to] = indeg.get(to, 0) + 1
        nodes.add(frm)
        nodes.add(to)
    for succs in adj.values():
        succs.sort()

    roots = sorted(n for n in nodes if indeg.get(n, 0) == 0)
    paths: list[list[str]] = []

    def walk_from(start: str) -> list[str]:
        path = [start]
        seen = {start}
        while len(path) < max_len:
            nxt = next((s for s in adj.get(path[-1], []) if s not in seen), None)
            if nxt is None:  # sink (or all successors already on this simple path)
                break
            path.append(nxt)
            seen.add(nxt)
        return path

    for root in roots:
        chain = walk_from(root)
        if len(chain) >= 2:  # a path needs at least one edge
            paths.append(chain)
        if len(paths) >= max_paths:
            break
    # Longest chains first, deterministic.
    paths.sort(key=lambda p: (-len(p), p))
    return paths[:max_paths]


# --------------------------------------------------------------------------- #
# Cluster derivation from real module boundaries.
# --------------------------------------------------------------------------- #
def derive_module_clusters(
    artifacts: list[dict[str, Any]], *, min_members: int = 2
) -> list[tuple[str, list[dict[str, Any]]]]:
    """Group artifacts into per-module common-mode clusters (by source locator).

    A source file is a natural common-mode boundary — its cells share ownership,
    build, and publish authority, so a failure there is a *common-mode* failure
    across all of them. Returns ``[(module_locator, members), ...]`` sorted by
    locator, keeping only modules with at least ``min_members`` cells (a
    single-cell module has degenerate concentration and is not a cluster story).
    """
    by_module: dict[str, list[dict[str, Any]]] = {}
    for art in artifacts:
        locator = _source_locator(art)
        by_module.setdefault(locator, []).append(art)
    return [
        (loc, members)
        for loc, members in sorted(by_module.items())
        if len(members) >= min_members
    ]


# --------------------------------------------------------------------------- #
# (3) Orchestration: assess the estate over real topology.
# --------------------------------------------------------------------------- #
def assess_estate(
    bundle: dict[str, Any],
    *,
    evidence_index: dict[str, list[dict[str, Any]]] | None = None,
    node_crosswalk_refs: list[str] | None = None,
    cluster_subject_id: str = "cluster:gbrg-blast-radius-corpus",
    tier0: bool = True,
    weights: dict[str, Any] | None = None,
    crosswalk: dict[str, Any] | None = None,
    signal_map: dict[str, Any] | None = None,
    ledger_path: Path | str | None = None,
    persist: bool = False,
) -> dict[str, Any]:
    """Score node / path / cluster subjects off a real gbrg-analyze bundle.

    Returns ``{"nodes": [Assessment...], "paths": [Assessment...],
    "cluster": Assessment, "residual_by_cell": {cell_id: residual}}``.

    Every subject is scored through the UNMODIFIED :mod:`supply_chain_risk`
    scorer; only the INPUTS (factors, node residuals, cluster components,
    controls-evidence, KRI metrics) are now derived from the real graph. With no
    ``evidence_index`` and ``tier0=True``, every subject fails CLOSED (REJECTED)
    — the honest default when real controls evidence is absent.
    """
    weights = weights or scr.load_weights()
    crosswalk = crosswalk or scr.load_crosswalk()
    signal_map = signal_map or load_signal_map()
    node_crosswalk_refs = node_crosswalk_refs or []

    artifacts = bundle.get("artifacts", [])
    edges = bundle.get("edges", [])

    # ── Nodes ────────────────────────────────────────────────────────────────
    node_assessments: list[scr.Assessment] = []
    residual_by_cell: dict[str, float] = {}
    for art in artifacts:
        cell_id = art["cell_id"]
        factors = factors_from_artifact(art, signal_map)
        controls = controls_from_index(cell_id, evidence_index)
        node_kri = _external_kri(cell_id, evidence_index)
        a = scr.assess_node(
            subject_id=cell_id,
            factors=factors,
            controls_evidence=controls,
            kri_metrics=node_kri,
            crosswalk_refs=node_crosswalk_refs,
            weights=weights, crosswalk=crosswalk,
            tier0=tier0, ledger_path=ledger_path, persist=persist,
        )
        node_assessments.append(a)
        residual_by_cell[cell_id] = a.residualScore

    # ── Paths (real CALLS chains) ─────────────────────────────────────────────
    path_assessments: list[scr.Assessment] = []
    for chain in derive_call_paths(edges):
        # Node residuals along the chain (0.0 for a member not in this bundle).
        residuals = [residual_by_cell.get(cell, 0.0) for cell in chain]
        head, tail = chain[0].split("#")[-1], chain[-1].split("#")[-1]
        subject_id = f"path:{head}->{tail}:{len(chain)}nodes"
        controls = controls_from_index(subject_id, evidence_index)
        path_kri = _external_kri(subject_id, evidence_index)
        a = scr.assess_path(
            subject_id=subject_id,
            node_residuals=residuals,
            kri_metrics=path_kri,
            controls_evidence=controls,
            crosswalk_refs=node_crosswalk_refs,
            weights=weights, crosswalk=crosswalk,
            ledger_path=ledger_path, persist=persist,
        )
        a._anchorCellId = chain[0]  # head node anchors the evidence-plane lift
        path_assessments.append(a)

    def _score_cluster(subject_id: str, members: list[dict[str, Any]]) -> scr.Assessment:
        components, shares = cluster_components_from_artifacts(members, signal_map)
        hhi = scr.hhi_normalized(shares)
        cluster_kri = cluster_kri_metrics(members, hhi, signal_map)
        cluster_kri.update(_external_kri(subject_id, evidence_index))
        a = scr.assess_cluster(
            subject_id=subject_id,
            components=components,
            shares=shares,
            resilience_control=_cluster_resilience(subject_id, evidence_index),
            controls_evidence=controls_from_index(subject_id, evidence_index),
            kri_metrics=cluster_kri,
            crosswalk_refs=node_crosswalk_refs,
            weights=weights, crosswalk=crosswalk,
            ledger_path=ledger_path, persist=persist,
        )
        if members:  # highest-blast member anchors the evidence-plane lift
            a._anchorCellId = max(members, key=lambda m: m.get("blast_radius", 0.0))["cell_id"]
        return a

    # ── Cluster: whole corpus (estate-level common-mode roll-up) ──────────────
    cluster_assessment = _score_cluster(cluster_subject_id, artifacts)

    # ── Clusters: per real module boundary (common-mode concentration groups) ─
    module_clusters = [
        _score_cluster(f"cluster:module:{locator}", members)
        for locator, members in derive_module_clusters(artifacts)
    ]

    return {
        "nodes": node_assessments,
        "paths": path_assessments,
        "cluster": cluster_assessment,     # estate-level roll-up
        "clusters": module_clusters,       # per-module concentration clusters
        "residual_by_cell": residual_by_cell,
    }


def _external_kri(
    subject_id: str, evidence_index: dict[str, Any] | None
) -> dict[str, float]:
    """Externally-supplied KRI metrics for a subject (``__kri__`` sidecar), else {}."""
    if not evidence_index:
        return {}
    return dict(evidence_index.get(f"__kri__:{subject_id}", {}))


def _cluster_resilience(
    subject_id: str, evidence_index: dict[str, Any] | None
) -> float:
    """Externally-supplied resilience control [0,1] for a cluster, else 0.0 (fail-closed)."""
    if not evidence_index:
        return 0.0
    return float(evidence_index.get(f"__resilience__:{subject_id}", 0.0))


# --------------------------------------------------------------------------- #
# (3) Emit onto the evidence plane (evidence-only, never authorization).
# --------------------------------------------------------------------------- #
def estate_evidence_envelopes(
    result: dict[str, Any],
    *,
    subject_repository: str = "SocioProphet/sociosphere",
    repo_root: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Lift every scored assessment onto ``repo-governance-observation.v0``.

    Reuses :func:`gbrg.adapters.evidence.scr_to_observations`, which enforces the
    evidence-only invariant (no authorization/verdict key reaches the plane). The
    scored verdict stays in the sealed ledger; only measured risk signals cross.
    """
    from gbrg.adapters import evidence as gbrg_evidence

    root = repo_root or Path(__file__).resolve().parents[2]
    envelopes: list[dict[str, Any]] = []
    for a in result.get("nodes", []):
        envelopes.extend(
            gbrg_evidence.scr_to_observations(
                a.proof_artifact(), subject_repository=subject_repository,
                repo_root=root, anchor_cell_id=a.subjectId,
            )
        )
    aggregates = list(result.get("paths", []))
    aggregates += list(result.get("clusters", []))
    cluster = result.get("cluster")
    if cluster is not None:
        aggregates.append(cluster)
    for a in aggregates:
        envelopes.extend(
            gbrg_evidence.scr_to_observations(
                a.proof_artifact(), subject_repository=subject_repository,
                repo_root=root, anchor_cell_id=getattr(a, "_anchorCellId", a.subjectId),
            )
        )
    return envelopes


# --------------------------------------------------------------------------- #
# Estate summary — a governance-legible roll-up of a scored assessment.
# --------------------------------------------------------------------------- #
def summarize_estate(result: dict[str, Any]) -> dict[str, Any]:
    """Roll a scored estate up to verdict/rating tallies + the worst subjects.

    Pure reporting over :func:`assess_estate` output — carries NO decision, only
    counts and the highest-residual subjects a reviewer should look at first.
    """
    subjects: list[scr.Assessment] = list(result.get("nodes", []))
    subjects += list(result.get("paths", []))
    subjects += list(result.get("clusters", []))
    cluster = result.get("cluster")
    if cluster is not None:
        subjects.append(cluster)

    def _tally(key: str) -> dict[str, int]:
        out: dict[str, int] = {}
        for s in subjects:
            out[getattr(s, key)] = out.get(getattr(s, key), 0) + 1
        return dict(sorted(out.items()))

    worst = sorted(subjects, key=lambda s: -s.residualScore)[:5]
    return {
        "subjects": len(subjects),
        "by_verdict": _tally("verdict"),
        "by_rating": _tally("rating"),
        "worst_residuals": [
            {"scope": s.riskScope, "subject": s.subjectId,
             "residual": round(s.residualScore, 4), "rating": s.rating,
             "verdict": s.verdict}
            for s in worst
        ],
    }


# --------------------------------------------------------------------------- #
# CLI (mirrors gbrg-analyze): score a real bundle, emit a summary / evidence.
# --------------------------------------------------------------------------- #
_DEFAULT_BUNDLE = (
    Path(__file__).resolve().parent / "fixtures"
    / "blast-radius-bundle.real.gbrg-core.containment.json"
)


def main(argv: list[str] | None = None) -> int:
    """``supply_chain_pipeline <bundle> [--evidence f.json] [--emit-evidence] [--ledger p]``.

    Scores node/path/cluster off a real gbrg-analyze bundle (defaults to the
    committed fixture) and prints a governance summary to stdout. ``--evidence``
    supplies a real controls/KRI ``evidence_index`` (JSON); with none, tier-0
    subjects fail CLOSED. ``--emit-evidence`` prints the evidence-plane envelopes
    (evidence-only) as JSON. ``--ledger`` seals each assessment to a hash-chained
    ledger and verifies the whole chain.
    """
    import argparse

    parser = argparse.ArgumentParser(prog="supply_chain_pipeline")
    parser.add_argument("bundle", nargs="?", default=str(_DEFAULT_BUNDLE),
                        help="gbrg-analyze --emit-edges bundle (or bare artifact array)")
    parser.add_argument("--evidence", help="JSON evidence_index (controls/KRI by subject)")
    parser.add_argument("--emit-evidence", action="store_true",
                        help="print evidence-plane observation envelopes as JSON")
    parser.add_argument("--ledger", help="seal + verify assessments to this ledger path")
    args = parser.parse_args(argv)

    drift = validate_signal_map()
    if drift:  # a drifted contract is fail-closed: refuse to score
        print("REFUSED: signal-map <-> weights drift:", *drift, sep="\n  ")
        return 2

    bundle = load_bundle(args.bundle)
    evidence_index = (
        json.loads(Path(args.evidence).read_text(encoding="utf-8"))
        if args.evidence else None
    )
    result = assess_estate(
        bundle, evidence_index=evidence_index,
        ledger_path=args.ledger, persist=bool(args.ledger),
    )

    # With --emit-evidence, stdout is PURE envelope JSON (pipeable) and the
    # human summary goes to stderr; otherwise the summary is the stdout payload.
    import sys as _sys
    summary = summarize_estate(result)
    print(json.dumps(summary, indent=2), file=_sys.stderr if args.emit_evidence else _sys.stdout)

    if args.ledger:
        from gbrg.governance import ledger
        vr = ledger.verify_ledger(args.ledger)
        print(f"ledger: ok={vr.ok} head={vr.head}", file=_sys.stderr)
        if not vr.ok:
            return 1

    if args.emit_evidence:
        print(json.dumps(estate_evidence_envelopes(result), indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
