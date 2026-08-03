"""Portfolio / position -> hierarchy binding contract (OMNI-2).

The MISSING data-SOURCE layer directly beneath the omnirisk allocation walker
(``gbrg.governance.omnirisk_allocation``, OMNI-1). The walker aggregates and
allocates a ``RiskAllocationTree`` whose leaves already carry a risk
``component_contribution`` — but it ASSUMES those exposures exist. It has no
source: nothing proves a leaf's risk is backed by a real holding, that a node
asserted to carry risk actually owns any position, or that every exposure is
attributable to a resolvable counterparty. This contract supplies that source.

It binds, by CONTRACT (nothing is imported from the shared graph; no live read
or write of any kind):

    Position  ---- instrument_ref --->  Instrument
      (a holding: quantity, exposure)      (asset_class on the asset-class LADDER,
                                            F-builder that scores it, issuer_ref)
    Instrument ---- issuer_ref ------->  Issuer / Counterparty Entity
                                            (a regis-entity-graph EntityNode,
                                             identified by node_id + kind — a
                                             by-contract snapshot, NOT a live read)
    Position  ---- leaf_ref ---------->  omnirisk hierarchy LEAF (node_ref)
                                            which the RiskAllocationTree places
                                            under an org-cut node in EVERY cut

So a real book of positions rolls up into the EXACT hierarchy the OMNI-1 walker
expects, and the roll-up is checked against the walker itself.

Consume-not-fork. Three soft references, each by contract only:

  * ``gbrg.governance.omnirisk_allocation`` (OMNI-1, same repo) — the tree the
    book rolls into is handed to the REAL walker (``evaluate_tree``) to confirm
    the target hierarchy is itself conservation/coherence-valid. This is the one
    reference that is executed, because it lives here; it is still read-only
    (``persist=False``) and forks nothing.
  * The asset-class LADDER + credit/equity/crypto F builders —
    ``economic-prophet`` ``LossDistribution.simulate_credit`` /
    ``simulate_equity`` (branch ``feat/risk-adjusted-profit-raroc``) and the
    in-flight crypto builder (branch ``feat/crypto-asset-class``). Referenced as
    the set of asset classes each instrument must declare and the builder that
    scores it; NOT imported (CI stays independent of those PRs).
  * The estate entity-resolution plane — ``regis-entity-graph`` EntityNode
    ``{node_id, kind}`` (kind in ORG / PERSON / ENTITY_CLUSTER for an issuer or
    counterparty). The ``entities`` roster in a binding document is a BY-CONTRACT
    snapshot conforming to that schema. This module NEVER calls the ER service,
    the ER ``/resolve/entities`` endpoint, or the shared HellGraph, and NEVER
    writes anything anywhere. Runtime binding to the live ER is a follow-up.

Teeth (both directions) — see ``test_portfolio_position_binding.py``:
  VERIFIES
    * a book of positions rolls up to the SAME node exposures the omnirisk walker
      aggregates: Sum(position.exposure) rolling into a node == the node's declared
      exposure (leaf ``component_contribution`` / internal ``economic_capital``),
      within tolerance — the conservation law, sourced;
    * every position's instrument resolves an issuer to a roster EntityNode;
    * every instrument carries an asset_class on the ladder, with an F-builder;
    * the target tree is itself accepted by the OMNI-1 walker.
  REJECTS
    * a position whose issuer does NOT resolve to an entity (unattributed exposure);
    * a hierarchy node with NO backing positions (phantom node — risk asserted with
      no holdings);
    * a position/leaf double-counted across two org-cuts without reconciliation
      (a leaf that is not present exactly once in every cut);
    * an instrument with no asset_class (or one off the ladder);
    * a node whose backing-position exposures do not sum to its declared exposure
      (conservation violation, sourced);
    * a book whose target tree the OMNI-1 walker itself rejects.

Deterministic and stdlib-only; sha256 = FIPS-180-4 algorithm (not a FIPS-140
cryptographic module). Receipts are sealed on the existing hash-chained
``gbrg.governance.ledger`` — no new ledger machinery.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import ledger
from . import omnirisk_allocation as omni

# --------------------------------------------------------------------------- #
# Constants.
# --------------------------------------------------------------------------- #
AGENT_REF = "agent-registry://gbrg/portfolio-position-binding-validator"
CONTRACT_URN = "gbrg.portfolio-position-binding.v0"

# Soft references to the consumed contracts (not imported; see module docstring).
WALKER_REF = "gbrg.governance.omnirisk_allocation:evaluate_tree (OMNI-1)"
LADDER_CREDIT_REF = "economic-prophet@feat/risk-adjusted-profit-raroc:risk_measures.LossDistribution.simulate_credit"
LADDER_EQUITY_REF = "economic-prophet@feat/risk-adjusted-profit-raroc:risk_measures.LossDistribution.simulate_equity"
LADDER_CRYPTO_REF = "economic-prophet@feat/crypto-asset-class:risk_measures(in-flight)"
ER_ENTITY_REF = "regis-entity-graph:schemas/node.schema.json#EntityNode{node_id,kind}"

VERIFIES = "VERIFIES"
FLAGGED = "FLAGGED"
REJECTED = "REJECTED"

# The asset-class LADDER: each rung maps an asset_class to the F builder that
# scores it (soft reference). An instrument MUST declare a rung on this ladder.
ASSET_CLASS_LADDER: dict[str, str] = {
    "credit": LADDER_CREDIT_REF,
    "equity": LADDER_EQUITY_REF,
    "market": LADDER_EQUITY_REF,  # market risk reuses the equity return builder (+beta)
    "crypto": LADDER_CRYPTO_REF,  # in flight on feat/crypto-asset-class
}

# EntityNode kinds (regis-entity-graph) that may stand as an issuer/counterparty.
ISSUER_ENTITY_KINDS = frozenset({"ORG", "PERSON", "ENTITY_CLUSTER"})

TOL = 1e-6  # absolute tolerance for conservation reconciliation


class PortfolioBindingError(ValueError):
    """Raised for a structurally malformed binding document."""


# --------------------------------------------------------------------------- #
# Tree traversal helpers (read-only over the RiskAllocationTree shape).
# --------------------------------------------------------------------------- #
def _declared_exposure(node: dict[str, Any]) -> float | None:
    """A node's declared exposure: leaf component_contribution / node EC."""
    risk = node.get("risk", {})
    if "economic_capital" in risk:
        return float(risk["economic_capital"])
    if "component_contribution" in risk:
        return float(risk["component_contribution"])
    return None


def _iter_nodes(node: dict[str, Any]):
    """Yield (node, is_leaf, leaf_refs_in_subtree) for every node in a subtree."""
    children = node.get("children")
    if not children:
        yield node, True, (node.get("node_ref"),)
        return
    subtree_leaves: list[str] = []
    for child in children:
        for sub, is_leaf, leaves in _iter_nodes(child):
            if is_leaf:
                subtree_leaves.extend(leaves)
            yield sub, is_leaf, leaves
    yield node, False, tuple(subtree_leaves)


def _cut_leaves(root: dict[str, Any]) -> list[str]:
    """Every leaf node_ref reachable in a cut (with multiplicity)."""
    return [n.get("node_ref") for n, is_leaf, _ in _iter_nodes(root) if is_leaf]


# --------------------------------------------------------------------------- #
# The binding validator.
# --------------------------------------------------------------------------- #
@dataclass
class BindingVerdict:
    binding_id: str
    verdict: str
    status: str
    epistemic_level: str
    reason: str
    book_total_exposure: float | None
    positions: int
    leaves_backed: int
    tree_walker_verdict: str
    violations: list[str] = field(default_factory=list)
    proof_id: str = ""
    receipt: str = ""

    def proof_artifact(self) -> dict[str, Any]:
        return {
            "schemaVersion": "gbrg.portfolio-position-binding-proof-artifact.v0",
            "version": "1.0.0",
            "proofId": self.proof_id,
            "bindingId": self.binding_id,
            "claim": {
                "claimId": f"claim.portfolio-position-binding.{self.binding_id}",
                "claimType": "portfolio_position_hierarchy_binding",
                "statement": (
                    f"binding {self.binding_id!r}: {self.positions} positions "
                    f"backing {self.leaves_backed} leaves, book exposure "
                    f"{self.book_total_exposure} -> {self.verdict}"
                ),
                "epistemicLevel": self.epistemic_level,
            },
            "status": self.status,
            "verdict": self.verdict,
            "reason": self.reason,
            "bookTotalExposure": self.book_total_exposure,
            "positions": self.positions,
            "leavesBacked": self.leaves_backed,
            "treeWalkerVerdict": self.tree_walker_verdict,
            "violations": self.violations,
            "consumes": {
                "omnirisk_walker": WALKER_REF,
                "asset_class_ladder": {k: v for k, v in ASSET_CLASS_LADDER.items()},
                "entity_resolution": ER_ENTITY_REF,
            },
            "contractUrn": CONTRACT_URN,
            "declared_by": AGENT_REF,
        }


def _validate_instruments_and_issuers(
    spec: dict[str, Any], violations: list[str]
) -> None:
    """Instrument tooth (asset_class on ladder) + issuer resolution tooth."""
    entities = spec.get("entities", {})
    instruments = spec.get("instruments", {})
    for iref, inst in instruments.items():
        ac = inst.get("asset_class")
        if not ac:
            violations.append(
                f"REJECTED: instrument {iref!r} carries no asset_class "
                "(unclassifiable exposure — cannot pick an F builder)"
            )
        elif ac not in ASSET_CLASS_LADDER:
            violations.append(
                f"REJECTED: instrument {iref!r} asset_class {ac!r} is not on the "
                f"asset-class ladder {sorted(ASSET_CLASS_LADDER)}"
            )
        issuer = inst.get("issuer_ref")
        if not issuer:
            violations.append(
                f"REJECTED: instrument {iref!r} has no issuer_ref "
                "(unattributed exposure — no counterparty)"
            )
            continue
        ent = entities.get(issuer)
        if ent is None:
            violations.append(
                f"REJECTED: instrument {iref!r} issuer {issuer!r} does not resolve "
                "to an entity in the roster (unattributed exposure)"
            )
        elif ent.get("kind") not in ISSUER_ENTITY_KINDS:
            violations.append(
                f"REJECTED: instrument {iref!r} issuer {issuer!r} resolves to a "
                f"{ent.get('kind')!r} node, not an issuer kind {sorted(ISSUER_ENTITY_KINDS)}"
            )


def _validate_positions(
    spec: dict[str, Any], violations: list[str]
) -> dict[str, float]:
    """Every position must reference a known instrument; return leaf->exposure sum."""
    instruments = spec.get("instruments", {})
    leaf_exposure: dict[str, float] = {}
    for pos in spec.get("positions", []):
        pid = pos.get("position_id", "<unknown>")
        iref = pos.get("instrument_ref")
        if iref not in instruments:
            violations.append(
                f"REJECTED: position {pid!r} references unknown instrument {iref!r}"
            )
            continue
        leaf = pos.get("leaf_ref")
        if not leaf:
            violations.append(f"REJECTED: position {pid!r} has no leaf_ref")
            continue
        leaf_exposure[leaf] = leaf_exposure.get(leaf, 0.0) + float(pos.get("exposure", 0.0))
    return leaf_exposure


def _check_cross_cut_reconciliation(
    cuts: dict[str, Any], backed_leaves: set[str], violations: list[str]
) -> None:
    """A leaf must appear exactly once in EVERY cut (else double-count/unreconciled)."""
    cut_leaf_sets: dict[str, set[str]] = {}
    for cut_name, root in cuts.items():
        leaves = _cut_leaves(root)
        seen: set[str] = set()
        for lref in leaves:
            if lref in seen:
                violations.append(
                    f"REJECTED: leaf {lref!r} appears more than once in cut "
                    f"{cut_name!r} — exposure double-counted within a single org-cut"
                )
            seen.add(lref)
        cut_leaf_sets[cut_name] = seen
    names = list(cut_leaf_sets)
    if len(names) >= 2:
        base_name, base = names[0], cut_leaf_sets[names[0]]
        for other_name in names[1:]:
            other = cut_leaf_sets[other_name]
            only_base = base - other
            only_other = other - base
            if only_base or only_other:
                violations.append(
                    f"REJECTED: cuts {base_name!r} and {other_name!r} do not cover the "
                    f"same leaves (only in {base_name}: {sorted(only_base)}; only in "
                    f"{other_name}: {sorted(only_other)}) — the book is not reconciled "
                    "across org-cuts (a position present in one cut and absent in another "
                    "double-counts or leaks exposure)"
                )
    # A backed leaf that no cut places into the hierarchy is orphaned exposure.
    all_cut_leaves: set[str] = set().union(*cut_leaf_sets.values()) if cut_leaf_sets else set()
    for lref in backed_leaves - all_cut_leaves:
        violations.append(
            f"REJECTED: leaf {lref!r} is backed by positions but appears in no cut "
            "of the hierarchy (orphaned exposure — not allocated anywhere)"
        )


def _check_conservation_and_phantoms(
    cuts: dict[str, Any], leaf_exposure: dict[str, float], violations: list[str]
) -> None:
    """Sum(position exposures) into a node == node's declared exposure; no phantoms."""
    for cut_name, root in cuts.items():
        for node, is_leaf, subtree_leaves in _iter_nodes(root):
            ref = node.get("node_ref", "<unknown>")
            backing = sum(leaf_exposure.get(lref, 0.0) for lref in subtree_leaves)
            has_any = any(lref in leaf_exposure for lref in subtree_leaves)
            # Phantom-node tooth: a node with NO backing positions in its subtree.
            if not has_any:
                kind = "leaf" if is_leaf else "hierarchy node"
                violations.append(
                    f"REJECTED: {kind} {ref!r} in cut {cut_name!r} has NO backing "
                    "positions (phantom node — risk asserted with no holdings)"
                )
                continue
            # Conservation tooth: sourced exposure must equal declared exposure.
            declared = _declared_exposure(node)
            if declared is not None and abs(backing - declared) > TOL:
                violations.append(
                    f"REJECTED: node {ref!r} in cut {cut_name!r} declared exposure "
                    f"{declared} != Sum(backing position exposures) {backing:.6f} "
                    "(conservation violation — book does not source the asserted risk)"
                )


def evaluate_binding(
    spec: dict[str, Any],
    *,
    ledger_path: Path | str | None = None,
    persist: bool = True,
) -> BindingVerdict:
    """Score a PortfolioPositionBinding: attribute, source, reconcile, seal."""
    binding_id = spec.get("binding_id", "<unnamed>")
    tree = spec.get("tree")
    if not isinstance(tree, dict) or not isinstance(tree.get("cuts"), dict) or not tree["cuts"]:
        raise PortfolioBindingError("binding requires a 'tree' with a non-empty 'cuts' map")
    if not isinstance(spec.get("positions"), list) or not spec["positions"]:
        raise PortfolioBindingError("binding requires a non-empty 'positions' list")

    violations: list[str] = []
    cuts = tree["cuts"]

    # 1. Instrument (asset_class) + issuer resolution teeth.
    _validate_instruments_and_issuers(spec, violations)

    # 2. Positions -> leaf exposure aggregation.
    leaf_exposure = _validate_positions(spec, violations)
    backed_leaves = set(leaf_exposure)

    # 3. Cross-cut reconciliation (double-count / leak) tooth.
    _check_cross_cut_reconciliation(cuts, backed_leaves, violations)

    # 4. Conservation + phantom-node teeth.
    _check_conservation_and_phantoms(cuts, leaf_exposure, violations)

    # 5. Bind to the OMNI-1 walker: the target hierarchy must itself be valid.
    #    Read-only (persist=False); forks nothing. A tree the walker rejects means
    #    the book is rolling into an incoherent hierarchy.
    tree_walker_verdict = "SKIPPED"
    try:
        wv = omni.evaluate_tree(tree, persist=False)
        tree_walker_verdict = wv.verdict
        if wv.verdict == omni.REJECTED:
            violations.append(
                "REJECTED: the target RiskAllocationTree is itself rejected by the "
                f"OMNI-1 walker ({wv.reason})"
            )
    except omni.OmniriskContractError as exc:
        tree_walker_verdict = "MALFORMED"
        violations.append(f"REJECTED: target tree is malformed for the OMNI-1 walker: {exc}")

    book_total = sum(leaf_exposure.values()) if leaf_exposure else 0.0
    verdict, status, level, reason = _project_verdict(violations)

    result = BindingVerdict(
        binding_id=binding_id,
        verdict=verdict,
        status=status,
        epistemic_level=level,
        reason=reason,
        book_total_exposure=book_total,
        positions=len(spec["positions"]),
        leaves_backed=len(backed_leaves),
        tree_walker_verdict=tree_walker_verdict,
        violations=violations,
    )
    _seal_and_persist(result, ledger_path=ledger_path, persist=persist)
    return result


def _project_verdict(violations: list[str]) -> tuple[str, str, str, str]:
    """Assay-style projection -> (verdict, status, epistemicLevel, reason)."""
    if violations:
        return (
            REJECTED, "FAILED", "rejected",
            "REJECTED: " + "; ".join(violations),
        )
    return (
        VERIFIES, "PROVED", "empirical",
        "VERIFIES: every exposure is sourced to a position, attributed to an entity, "
        "and classified on the ladder; the book conserves into the walker's hierarchy",
    )


def _seal_and_persist(
    result: BindingVerdict, *, ledger_path: Path | str | None, persist: bool
) -> BindingVerdict:
    """Hash-chained receipt on the existing gbrg ledger. sha256 = FIPS-180-4."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    result.proof_id = "proof-ppb-" + uuid.uuid4().hex[:16]
    records = ledger.read_all(ledger_path) if _ledger_exists(ledger_path) else []
    prev = (records[-1].get("hash") or records[-1].get("receipt")) if records else ledger.GENESIS
    core = {
        "type": "PortfolioPositionBindingVerdict",
        "ts": ts,
        "prev_hash": prev,
        "artifact": result.proof_artifact(),
    }
    event_hash = ledger._sha(core)
    event = dict(core)
    event["hash"] = event_hash
    result.receipt = event_hash
    if persist:
        ledger.append(event, ledger_path=ledger_path)
    return result


def _ledger_exists(ledger_path: Path | str | None) -> bool:
    if ledger_path is None:
        return False
    return Path(ledger_path).exists()


# --------------------------------------------------------------------------- #
# Load + CLI (drives the Makefile validate target over the fixtures).
# --------------------------------------------------------------------------- #
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "portfolio_position_binding"


def load_binding(path: Path | str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def main(argv: list[str] | None = None) -> int:
    """Validate every fixture: *.valid.json must VERIFY, *.invalid.json must REJECT."""
    import tempfile

    failures: list[str] = []
    fixtures = sorted(FIXTURE_DIR.glob("*.json"))
    if not fixtures:
        print(f"ERR: no fixtures found under {FIXTURE_DIR}")
        return 1
    with tempfile.TemporaryDirectory() as tmp:
        ledger_path = Path(tmp) / "ppb.jsonl"
        for fx in fixtures:
            spec = load_binding(fx)
            result = evaluate_binding(spec, ledger_path=ledger_path)
            expect_reject = fx.name.endswith(".invalid.json")
            got_reject = result.verdict == REJECTED
            ok = got_reject == expect_reject
            tag = "OK " if ok else "FAIL"
            print(f"[{tag}] {fx.name}: verdict={result.verdict} "
                  f"(expected {'REJECTED' if expect_reject else 'VERIFIES'})")
            if ok and expect_reject:
                print(f"        -> {result.violations[0]}")
            if not ok:
                failures.append(fx.name)
        v = ledger.verify_ledger(ledger_path)
        if not v.ok:
            failures.append(f"ledger tamper-check failed: {v.reason}")
        else:
            print(f"[OK ] ledger: {v.records} sealed receipts, chain verified (FIPS-180-4 sha256)")

    if failures:
        print(f"\nFAILED: {failures}")
        return 1
    print(f"\nALL {len(fixtures)} fixtures behaved as declared — "
          "portfolio/position binding has teeth both ways.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
