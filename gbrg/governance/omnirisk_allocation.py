"""Omnirisk cross-cut risk aggregation / allocation contract (OMNI-1).

The ARCHITECTURE + AGGREGATION layer of the estate's omnirisk plane. It does NOT
reimplement the per-node risk kernel: it **consumes it by soft reference**. Each
node's risk result (economic capital, standalone capital, Euler/marginal
contribution, sensitivities, higher moments) is produced upstream by the
Economic-Prophet risk kernel and is *given* to this layer as a labelled node
input. This module's job is to walk a ``RiskAllocationTree``, aggregate children
into parents, allocate parents down to children, and *reject* any tree that
violates the conservation/coherence laws that make economic capital allocable.

Consumed by soft reference (not imported; represented as given node inputs so CI
is independent of the kernel PR):
  * ``economic-prophet`` RM-1/RAP-1 RAROC kernel — branch
    ``feat/risk-adjusted-profit-raroc``: ``risk(F, kernel, reference, horizon)``
    with Sharpe/Sortino/LPM/Kappa/VaR/ES/spectral, ``LossDistribution.simulate_credit``
    / ``simulate_equity`` F builders, ``structural_transform`` (tranche waterfall),
    and ``euler_allocation`` marginal/component contributions
    (``src/open_ep_framework/risk_measures.py``, ``risk_adjusted_profit.py``).
  * ``economic-prophet`` memory-regime characterizer (separate PR, in flight):
    Hurst ``H`` / Lyapunov ``λ`` / fractal dimension → regime + fat-tailed /
    long-memory ``F`` (per Mandelbrot). Consumed here only as the ``regime`` label
    each node must carry.

The one-kernel principle (see ADR-004): the SAME ``risk(F, ·)`` scores credit and
equity; only the distribution ``F`` and the ``reference`` change. Because a
COHERENT measure (Expected Shortfall / a non-increasing spectral measure) is
subadditive and positively homogeneous, its Euler marginal contributions SUM to
the parent total exactly — so economic capital aggregates up and allocates down
an arbitrary hierarchy cut, and the bank total is invariant to the cut. VaR is
not subadditive and cannot underwrite allocation without an explicit incoherence
override.

Two operators, one calculus (both regime-aware):
  * INTEGRAL operators — coherent tail measures and distribution moments — aggregate
    WITH DIVERSIFICATION: parent ``EC <= Σ children EC_standalone``. Euler
    contributions conserve (sum to the parent).
  * DERIVATIVE operators — sensitivities: duration, convexity, marginal capital —
    aggregate VALUE-WEIGHTED: a ladder's duration is the value-weighted average of
    its legs' durations; WAL is principal-weighted. A weighted average is bounded
    by its inputs' min/max.

Teeth (both directions) — see ``test_omnirisk_allocation.py``:
  VERIFIES
    * Two cuts (product cut and client-segment cut) over the SAME transactions
      reconcile to the SAME bank total EC / duration / convexity / WAL
      (cut-invariance of the total).
    * For a coherent measure, component contributions SUM to the parent total
      (conservation — bound to the EP IC-1 conservation-settlement concept).
  REJECTS
    * child EC contributions that do NOT sum to the parent (conservation violation);
    * a non-coherent measure (VaR) used for cross-node allocation without an
      explicit ``incoherence_override`` flag;
    * a diversification claim that makes aggregate risk EXCEED the sum of standalone
      risks (super-additivity — impossible for a coherent measure ⇒ bad model);
    * a credit tranche node whose ``attach``/``detach`` is incoherent;
    * a node missing its ``regime`` label;
    * a ``provisional`` (n<30) node silently rolled into a non-provisional total;
    * mixing incompatible horizons / confidence levels / term regimes / tenors in
      one aggregation without an explicit ``rescale``;
    * a portfolio duration/convexity outside the min/max of its children's values
      (weighted-average bound), or one that is not the value-weighted (WAL:
      principal-weighted) average of its children.

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

# --------------------------------------------------------------------------- #
# Constants.
# --------------------------------------------------------------------------- #
AGENT_REF = "agent-registry://gbrg/omnirisk-allocation-walker"
CONTRACT_URN = "gbrg.omnirisk-allocation.v0"

# Soft references to the consumed kernel PRs (not imported; see module docstring).
KERNEL_RISK_REF = "economic-prophet@feat/risk-adjusted-profit-raroc:src/open_ep_framework/risk_measures.py"
KERNEL_RAROC_REF = "economic-prophet@feat/risk-adjusted-profit-raroc:src/open_ep_framework/risk_adjusted_profit.py"
KERNEL_REGIME_REF = "economic-prophet:memory-regime-characterizer(in-flight)"

VERIFIES = "VERIFIES"
FLAGGED = "FLAGGED"
REJECTED = "REJECTED"

# A coherent measure is subadditive + positively homogeneous ⇒ Euler-allocable.
COHERENT_MEASURES = frozenset({"expected_shortfall", "spectral"})
NONCOHERENT_MEASURES = frozenset({"var", "sharpe", "stddev"})

MIN_SAMPLES = 30
TOL = 1e-6  # absolute tolerance for conservation / weighted-average reconciliation
ASSET_CLASSES = frozenset({"credit", "equity", "market"})
REQUIRED_REGIME_KEYS = ("memory_regime", "market_regime")

# Term-structure regimes that cannot be aggregated together without a rescale.
_TERM_REGIME_INCOMPATIBLE = {
    frozenset({"upward", "inverted"}),
    frozenset({"persistent", "mean_reverting"}),
}


class OmniriskContractError(ValueError):
    """Raised for a structurally malformed tree the walker cannot even score."""


# --------------------------------------------------------------------------- #
# Aggregated roll-up of a subtree (the INTEGRAL + DERIVATIVE operators).
# --------------------------------------------------------------------------- #
@dataclass
class NodeAgg:
    """The computed roll-up under a node (what its children actually imply)."""

    node_ref: str
    ec: float  # economic capital (coherent tail contribution) — conserves
    standalone: float  # Σ standalone capital — the no-diversification ceiling
    value: float  # market value / notional — the weight for sensitivities
    principal: float  # principal — the weight for WAL
    duration: float  # value-weighted
    convexity: float  # value-weighted
    average_life: float  # principal-weighted (WAL)
    rar: float  # risk-adjusted return (additive, EP identity)
    provisional: bool
    measures: frozenset[str]
    alphas: frozenset[float]
    horizons: frozenset[float]
    term_regimes: frozenset[str]
    tenors: frozenset[str]
    leaf_durations: tuple[float, ...]  # for the weighted-average bound tooth


# --------------------------------------------------------------------------- #
# Structural / label validation (per node).
# --------------------------------------------------------------------------- #
def validate_regime(node: dict[str, Any], violations: list[str]) -> None:
    """A node MUST carry its regime label (from the memory-regime characterizer)."""
    ref = node.get("node_ref", "<unknown>")
    regime = node.get("label", {}).get("regime")
    if not isinstance(regime, dict) or not regime:
        violations.append(f"REJECTED: node {ref!r} is missing its regime label")
        return
    missing = [k for k in REQUIRED_REGIME_KEYS if k not in regime]
    if missing:
        violations.append(
            f"REJECTED: node {ref!r} regime label missing keys {missing}"
        )


def validate_structure(node: dict[str, Any], violations: list[str]) -> None:
    """A credit tranche node's [attach, detach] must be coherent."""
    ref = node.get("node_ref", "<unknown>")
    structure = node.get("label", {}).get("structure")
    if not structure:
        return
    if structure.get("kind") == "tranche":
        attach = structure.get("attach")
        detach = structure.get("detach")
        if attach is None or detach is None:
            violations.append(
                f"REJECTED: tranche node {ref!r} missing attach/detach"
            )
            return
        if not (0.0 <= attach < detach <= 1.0):
            violations.append(
                f"REJECTED: tranche node {ref!r} incoherent structure "
                f"attach={attach} detach={detach} (require 0<=attach<detach<=1)"
            )


def _asset_class_ok(node: dict[str, Any], violations: list[str]) -> None:
    ref = node.get("node_ref", "<unknown>")
    ac = node.get("label", {}).get("asset_class")
    if ac not in ASSET_CLASSES:
        violations.append(
            f"REJECTED: node {ref!r} asset_class {ac!r} not in {sorted(ASSET_CLASSES)}"
        )


# --------------------------------------------------------------------------- #
# The walker: aggregate children -> parent, allocate parent -> children.
# --------------------------------------------------------------------------- #
def _leaf_agg(node: dict[str, Any], violations: list[str]) -> NodeAgg:
    r = node.get("risk", {})
    t = node.get("term", {})
    ref = node["node_ref"]
    n = int(r.get("n_samples", 0))
    measure = r.get("measure", "expected_shortfall")

    # A leaf's own EC contribution to the global tail == its Euler component.
    ec = float(r.get("component_contribution", r.get("economic_capital", 0.0)))
    standalone = float(r.get("standalone_capital", ec))
    if ec > standalone + TOL:
        violations.append(
            f"REJECTED: leaf {ref!r} component contribution {ec} exceeds its own "
            f"standalone capital {standalone} — super-additive; a coherent measure's "
            "marginal contribution can never exceed standalone (bad diversification model)"
        )
    duration = float(t.get("duration", 0.0))
    return NodeAgg(
        node_ref=ref,
        ec=ec,
        standalone=standalone,
        value=float(t.get("value", 0.0)),
        principal=float(t.get("principal", 0.0)),
        duration=duration,
        convexity=float(t.get("convexity", 0.0)),
        average_life=float(t.get("average_life", 0.0)),
        rar=float(r.get("risk_adjusted_return", 0.0)),
        provisional=bool(r.get("provisional", n < MIN_SAMPLES)),
        measures=frozenset({measure}),
        alphas=frozenset({float(r.get("alpha", 0.0))}),
        horizons=frozenset({float(r.get("horizon", 1.0))}),
        term_regimes=frozenset({t.get("term_regime")}) if t.get("term_regime") else frozenset(),
        tenors=frozenset({t.get("tenor_bucket")}) if t.get("tenor_bucket") else frozenset(),
        leaf_durations=(duration,),
    )


def _check_homogeneity(
    node_ref: str, children: list[NodeAgg], rescale: bool, violations: list[str]
) -> None:
    """Extend the horizon/confidence-mixing tooth to the term structure."""
    if rescale:
        return
    alphas = set().union(*(c.alphas for c in children))
    horizons = set().union(*(c.horizons for c in children))
    if len({a for a in alphas if a}) > 1 or len({h for h in horizons}) > 1:
        violations.append(
            f"REJECTED: node {node_ref!r} aggregates incompatible confidence/horizon "
            f"(alphas={sorted(a for a in alphas if a)}, horizons={sorted(horizons)}) "
            "without an explicit rescale"
        )
    term_regimes = set().union(*(c.term_regimes for c in children))
    for incompatible in _TERM_REGIME_INCOMPATIBLE:
        if incompatible <= term_regimes:
            violations.append(
                f"REJECTED: node {node_ref!r} aggregates incompatible term regimes "
                f"{sorted(incompatible)} without an explicit rescale"
            )
    tenors = set().union(*(c.tenors for c in children))
    if len(tenors) > 1:
        violations.append(
            f"REJECTED: node {node_ref!r} aggregates mixed tenors {sorted(tenors)} "
            "without an explicit rescale"
        )


def walk(
    node: dict[str, Any],
    *,
    incoherence_override: bool = False,
    allow_provisional: bool = False,
    rescale: bool = False,
    violations: list[str],
) -> NodeAgg:
    """Recursively aggregate a subtree, appending any conservation-law violations."""
    ref = node.get("node_ref")
    if not ref:
        raise OmniriskContractError("every node requires a node_ref")

    validate_regime(node, violations)
    _asset_class_ok(node, violations)
    validate_structure(node, violations)

    children = node.get("children")
    if not children:
        return _leaf_agg(node, violations)

    # Coherence gate: a non-coherent measure cannot underwrite allocation.
    for child in children:
        measure = child.get("risk", {}).get("measure")
        if measure in NONCOHERENT_MEASURES and not incoherence_override:
            violations.append(
                f"REJECTED: node {ref!r} allocates over non-coherent measure "
                f"{measure!r} without incoherence_override"
            )

    child_aggs = [
        walk(
            c,
            incoherence_override=incoherence_override,
            allow_provisional=allow_provisional,
            rescale=rescale,
            violations=violations,
        )
        for c in children
    ]

    _check_homogeneity(ref, child_aggs, rescale, violations)

    # ---- INTEGRAL operators: EC conserves, diversifies. --------------------- #
    computed_ec = sum(c.ec for c in child_aggs)
    computed_standalone = sum(c.standalone for c in child_aggs)
    computed_rar = sum(c.rar for c in child_aggs)
    if computed_ec > computed_standalone + TOL:
        violations.append(
            f"REJECTED: node {ref!r} aggregate EC {computed_ec:.6f} EXCEEDS the sum of "
            f"standalone risks {computed_standalone:.6f} — super-additive; a coherent "
            "measure cannot do this (bad diversification model)"
        )

    # ---- DERIVATIVE operators: value-weighted / principal-weighted. --------- #
    computed_value = sum(c.value for c in child_aggs)
    computed_principal = sum(c.principal for c in child_aggs)
    if computed_value > 0:
        computed_duration = sum(c.value * c.duration for c in child_aggs) / computed_value
        computed_convexity = sum(c.value * c.convexity for c in child_aggs) / computed_value
    else:
        computed_duration = computed_convexity = 0.0
    if computed_principal > 0:
        computed_wal = sum(c.principal * c.average_life for c in child_aggs) / computed_principal
    else:
        computed_wal = 0.0

    leaf_durations = tuple(d for c in child_aggs for d in c.leaf_durations)

    # ---- Reconcile computed roll-up against any DECLARED parent values. ----- #
    declared = node.get("risk", {})
    if "economic_capital" in declared:
        if abs(float(declared["economic_capital"]) - computed_ec) > TOL:
            violations.append(
                f"REJECTED: node {ref!r} declared EC {declared['economic_capital']} != "
                f"sum of child contributions {computed_ec:.6f} (conservation violation)"
            )
    term = node.get("term", {})
    if "duration" in term:
        _check_weighted(ref, "duration", float(term["duration"]),
                        computed_duration, leaf_durations, violations)
    if "convexity" in term:
        _check_weighted(ref, "convexity", float(term["convexity"]),
                        computed_convexity, None, violations)
    if "average_life" in term:
        _check_weighted(ref, "average_life", float(term["average_life"]),
                        computed_wal, None, violations)

    # ---- provisional roll-up tooth ----------------------------------------- #
    child_provisional = any(c.provisional for c in child_aggs)
    node_provisional = bool(declared.get("provisional", False))
    if child_provisional and not node_provisional and not allow_provisional:
        violations.append(
            f"REJECTED: node {ref!r} silently rolls a provisional (n<{MIN_SAMPLES}) "
            "child into a non-provisional total (mark it provisional or set allow_provisional)"
        )

    return NodeAgg(
        node_ref=ref,
        ec=computed_ec,
        standalone=computed_standalone,
        value=computed_value,
        principal=computed_principal,
        duration=computed_duration,
        convexity=computed_convexity,
        average_life=computed_wal,
        rar=computed_rar,
        provisional=child_provisional or node_provisional,
        measures=frozenset().union(*(c.measures for c in child_aggs)),
        alphas=frozenset().union(*(c.alphas for c in child_aggs)),
        horizons=frozenset().union(*(c.horizons for c in child_aggs)),
        term_regimes=frozenset().union(*(c.term_regimes for c in child_aggs)),
        tenors=frozenset().union(*(c.tenors for c in child_aggs)),
        leaf_durations=leaf_durations,
    )


def _check_weighted(
    ref: str,
    name: str,
    declared: float,
    computed: float,
    bound_inputs: tuple[float, ...] | None,
    violations: list[str],
) -> None:
    """Sensitivity teeth: value/principal-weighted AND within the min/max bound."""
    if bound_inputs:
        lo, hi = min(bound_inputs), max(bound_inputs)
        if declared < lo - TOL or declared > hi + TOL:
            violations.append(
                f"REJECTED: node {ref!r} {name} {declared} is outside its children's "
                f"[{lo}, {hi}] (a weighted average is bounded by its inputs)"
            )
            return
    if abs(declared - computed) > 1e-4:
        violations.append(
            f"REJECTED: node {ref!r} declared {name} {declared} != value-weighted "
            f"aggregate {computed:.6f}"
        )


# --------------------------------------------------------------------------- #
# Cut-invariance: the same transactions, two hierarchies, one bank total.
# --------------------------------------------------------------------------- #
def reconcile_cuts(cut_aggs: dict[str, NodeAgg], violations: list[str]) -> None:
    """Every cut over the SAME transactions must yield the SAME bank total."""
    names = list(cut_aggs)
    if len(names) < 2:
        return
    base = cut_aggs[names[0]]
    for other_name in names[1:]:
        other = cut_aggs[other_name]
        for attr in ("ec", "value", "principal", "duration", "convexity", "average_life"):
            a, b = getattr(base, attr), getattr(other, attr)
            if abs(a - b) > 1e-4:
                violations.append(
                    f"REJECTED: cut '{names[0]}' and cut '{other_name}' disagree on "
                    f"bank total {attr} ({a:.6f} != {b:.6f}) — allocation is not cut-invariant"
                )


# --------------------------------------------------------------------------- #
# EP grounding (consumed identity, checked not recomputed).
# --------------------------------------------------------------------------- #
def economic_profit(rar: float, hurdle: float, ec: float) -> float:
    """EP = risk-adjusted return − Hurdle × EconomicCapital (RAP-1 identity)."""
    return rar - hurdle * ec


def raroc(rar: float, ec: float) -> float:
    """RAROC = risk-adjusted return / EconomicCapital (per node)."""
    return rar / ec if ec else float("inf")


# --------------------------------------------------------------------------- #
# The gate: walk -> reconcile cuts -> project verdict -> seal -> persist.
# --------------------------------------------------------------------------- #
@dataclass
class AllocationVerdict:
    tree_id: str
    verdict: str
    status: str
    epistemic_level: str
    reason: str
    bank_total_ec: float | None
    bank_raroc: float | None
    bank_economic_profit: float | None
    cut_invariant: bool
    violations: list[str] = field(default_factory=list)
    proof_id: str = ""
    receipt: str = ""

    def proof_artifact(self) -> dict[str, Any]:
        return {
            "schemaVersion": "gbrg.omnirisk-allocation-proof-artifact.v0",
            "version": "1.0.0",
            "proofId": self.proof_id,
            "treeId": self.tree_id,
            "claim": {
                "claimId": f"claim.omnirisk-allocation.{self.tree_id}",
                "claimType": "omnirisk_capital_allocation",
                "statement": (
                    f"tree {self.tree_id!r} bank EC {self.bank_total_ec} "
                    f"({'cut-invariant' if self.cut_invariant else 'NOT cut-invariant'}) "
                    f"-> {self.verdict}"
                ),
                "epistemicLevel": self.epistemic_level,
            },
            "status": self.status,
            "verdict": self.verdict,
            "reason": self.reason,
            "bankTotalEconomicCapital": self.bank_total_ec,
            "bankRaroc": self.bank_raroc,
            "bankEconomicProfit": self.bank_economic_profit,
            "cutInvariant": self.cut_invariant,
            "violations": self.violations,
            "consumes": {
                "risk_kernel": KERNEL_RISK_REF,
                "raroc_kernel": KERNEL_RAROC_REF,
                "memory_regime": KERNEL_REGIME_REF,
            },
            "contractUrn": CONTRACT_URN,
            "declared_by": AGENT_REF,
        }


def evaluate_tree(
    spec: dict[str, Any],
    *,
    ledger_path: Path | str | None = None,
    persist: bool = True,
) -> AllocationVerdict:
    """Score a RiskAllocationTree: aggregate, reconcile cuts, project a verdict."""
    tree_id = spec.get("tree_id", "<unnamed>")
    cuts = spec.get("cuts")
    if not isinstance(cuts, dict) or not cuts:
        raise OmniriskContractError("tree requires a non-empty 'cuts' map")
    hurdle = float(spec.get("hurdle_rate", 0.0))
    incoherence_override = bool(spec.get("incoherence_override", False))
    allow_provisional = bool(spec.get("allow_provisional", False))
    rescale = bool(spec.get("rescale", False))

    violations: list[str] = []
    cut_aggs: dict[str, NodeAgg] = {}
    for cut_name, root in cuts.items():
        cut_aggs[cut_name] = walk(
            root,
            incoherence_override=incoherence_override,
            allow_provisional=allow_provisional,
            rescale=rescale,
            violations=violations,
        )

    reconcile_cuts(cut_aggs, violations)

    cut_invariant = not any("not cut-invariant" in v for v in violations)
    bank = next(iter(cut_aggs.values())) if cut_aggs else None
    bank_ec = bank.ec if bank else None
    bank_rar = bank.rar if bank else None
    bank_raroc = raroc(bank_rar, bank_ec) if bank and bank_ec else None
    bank_ep = economic_profit(bank_rar, hurdle, bank_ec) if bank else None

    verdict, status, level, reason = _project_verdict(violations, bank_raroc, hurdle)

    result = AllocationVerdict(
        tree_id=tree_id,
        verdict=verdict,
        status=status,
        epistemic_level=level,
        reason=reason,
        bank_total_ec=bank_ec,
        bank_raroc=bank_raroc,
        bank_economic_profit=bank_ep,
        cut_invariant=cut_invariant,
        violations=violations,
    )
    _seal_and_persist(result, ledger_path=ledger_path, persist=persist)
    return result


def _project_verdict(
    violations: list[str], bank_raroc: float | None, hurdle: float
) -> tuple[str, str, str, str]:
    """Assay-style projection -> (verdict, status, epistemicLevel, reason)."""
    if violations:
        return (
            REJECTED, "FAILED", "rejected",
            "REJECTED: " + "; ".join(violations),
        )
    if bank_raroc is not None and bank_raroc < hurdle:
        return (
            FLAGGED, "BLOCKED", "speculative",
            f"FLAGGED value-destroying: bank RAROC {bank_raroc:.6f} < hurdle {hurdle:.6f}",
        )
    return (
        VERIFIES, "PROVED", "empirical",
        "VERIFIES: conservation + coherence + cut-invariance hold; RAROC >= hurdle",
    )


def _seal_and_persist(
    result: AllocationVerdict, *, ledger_path: Path | str | None, persist: bool
) -> AllocationVerdict:
    """Hash-chained receipt on the existing gbrg ledger. sha256 = FIPS-180-4."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    result.proof_id = "proof-omni-" + uuid.uuid4().hex[:16]
    records = ledger.read_all(ledger_path) if _ledger_exists(ledger_path) else []
    prev = (records[-1].get("hash") or records[-1].get("receipt")) if records else ledger.GENESIS
    core = {
        "type": "OmniriskAllocationVerdict",
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
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "omnirisk"


def load_tree(path: Path | str) -> dict[str, Any]:
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
        ledger_path = Path(tmp) / "omni.jsonl"
        for fx in fixtures:
            spec = load_tree(fx)
            result = evaluate_tree(spec, ledger_path=ledger_path)
            expect_reject = fx.name.endswith(".invalid.json")
            got_reject = result.verdict == REJECTED
            ok = got_reject == expect_reject
            tag = "OK " if ok else "FAIL"
            print(f"[{tag}] {fx.name}: verdict={result.verdict} "
                  f"(expected {'REJECTED' if expect_reject else 'VERIFIES/FLAGGED'})")
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
    print(f"\nALL {len(fixtures)} fixtures behaved as declared — omnirisk allocation has teeth both ways.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
