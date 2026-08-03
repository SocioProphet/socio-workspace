"""Teeth tests for the portfolio/position -> hierarchy binding (OMNI-2).

Both directions, over static fixtures. The fixtures embed the REAL OMNI-1
omnirisk two-cut valid tree, so the tree-walker binding is exercised for real
while staying independent of the in-flight economic-prophet kernel / ER PRs
(the asset-class ladder and entity roster are consumed by contract only).

VERIFIES
  * a real book of positions sources every leaf exposure and rolls up to the SAME
    node exposures the omnirisk walker aggregates (conservation, sourced);
  * every position's issuer resolves to a roster EntityNode;
  * every instrument carries an asset_class on the ladder;
  * the target tree is itself accepted by the OMNI-1 walker.
REJECTS (one fixture per tooth)
  * unattributed issuer, missing asset_class, phantom node (no backing positions),
    conservation violation, cross-cut double-count.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from gbrg.governance import ledger
from gbrg.governance import omnirisk_allocation as omni
from gbrg.governance import portfolio_position_binding as ppb

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "portfolio_position_binding"
CONTRACT_SCHEMA = (
    Path(__file__).resolve().parents[1] / "contracts" / "portfolio-position-binding.schema.json"
)


def _load(name: str) -> dict:
    return ppb.load_binding(FIXTURES / name)


# --------------------------------------------------------------------------- #
# VERIFIES side.
# --------------------------------------------------------------------------- #
def test_valid_book_verifies_and_sources_the_hierarchy() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        lp = Path(tmp) / "ppb.jsonl"
        result = ppb.evaluate_binding(_load("book_two_cut.valid.json"), ledger_path=lp)
    assert result.verdict == ppb.VERIFIES, result.reason
    assert result.violations == []
    # The book sources the whole bank total (t1..t4 = 40+30+20+10 = 100).
    assert result.book_total_exposure == pytest.approx(100.0)
    assert result.positions == 5
    assert result.leaves_backed == 4
    # And the target tree is itself accepted by the OMNI-1 walker.
    assert result.tree_walker_verdict == omni.VERIFIES


def test_valid_book_node_exposures_match_the_walker_rollup() -> None:
    """Conservation, sourced: Sum(position exposures) into each node == walker's node EC."""
    spec = _load("book_two_cut.valid.json")
    # Independently aggregate the book by leaf.
    leaf_exposure: dict[str, float] = {}
    for pos in spec["positions"]:
        leaf_exposure[pos["leaf_ref"]] = leaf_exposure.get(pos["leaf_ref"], 0.0) + pos["exposure"]
    # Walk the walker's own aggregation and compare declared node exposures.
    for cut_name, root in spec["tree"]["cuts"].items():
        for node, _is_leaf, subtree_leaves in ppb._iter_nodes(root):
            declared = ppb._declared_exposure(node)
            if declared is None:
                continue
            sourced = sum(leaf_exposure.get(lref, 0.0) for lref in subtree_leaves)
            assert sourced == pytest.approx(declared), (
                f"cut {cut_name} node {node['node_ref']}: sourced {sourced} != declared {declared}"
            )


def test_receipt_is_sealed_on_the_ledger() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        lp = Path(tmp) / "ppb.jsonl"
        result = ppb.evaluate_binding(_load("book_two_cut.valid.json"), ledger_path=lp)
        assert result.receipt
        v = ledger.verify_ledger(lp)
        assert v.ok, v.reason
        assert v.records == 1


# --------------------------------------------------------------------------- #
# REJECTS side — one fixture per tooth.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "fixture,needle",
    [
        ("unattributed_issuer.invalid.json", "does not resolve to an entity"),
        ("missing_asset_class.invalid.json", "carries no asset_class"),
        ("phantom_node.invalid.json", "phantom node"),
        ("conservation_violation.invalid.json", "conservation violation"),
        ("cross_cut_double_count.invalid.json", "double-counted within a single org-cut"),
    ],
)
def test_invalid_book_is_rejected_with_reason(fixture: str, needle: str) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        lp = Path(tmp) / "ppb.jsonl"
        result = ppb.evaluate_binding(_load(fixture), ledger_path=lp)
    assert result.verdict == ppb.REJECTED, fixture
    assert any(needle in v for v in result.violations), (
        f"{fixture}: expected a violation containing {needle!r}, got {result.violations}"
    )


def test_phantom_node_is_the_unbacked_leaf() -> None:
    """A hierarchy node with no backing positions is rejected in EVERY cut it appears."""
    result = ppb.evaluate_binding(_load("phantom_node.invalid.json"), persist=False)
    phantom = [v for v in result.violations if "phantom node" in v]
    # t4 appears in both cuts (client_segment under Geo_EU, product under BU_Credit).
    assert any("client_segment" in v for v in phantom)
    assert any("product" in v for v in phantom)


# --------------------------------------------------------------------------- #
# Structural / malformed guards.
# --------------------------------------------------------------------------- #
def test_missing_tree_raises() -> None:
    with pytest.raises(ppb.PortfolioBindingError):
        ppb.evaluate_binding({"binding_id": "x", "positions": [{}]}, persist=False)


def test_empty_positions_raises() -> None:
    spec = _load("book_two_cut.valid.json")
    spec["positions"] = []
    with pytest.raises(ppb.PortfolioBindingError):
        ppb.evaluate_binding(spec, persist=False)


# --------------------------------------------------------------------------- #
# Every fixture conforms to the published JSON Schema (contract-with-teeth).
# --------------------------------------------------------------------------- #
def test_all_fixtures_conform_to_contract_schema() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(CONTRACT_SCHEMA.read_text())
    validator = jsonschema.Draft7Validator(schema)
    # The 'missing_asset_class' fixture deliberately violates the schema's
    # instrument.asset_class requirement (that is its whole point), so it is the
    # one fixture exempt from structural conformance — the validator still rejects
    # it behaviourally. Every other fixture must be schema-valid.
    for fx in sorted(FIXTURES.glob("*.json")):
        if fx.name == "missing_asset_class.invalid.json":
            continue
        errors = sorted(validator.iter_errors(json.loads(fx.read_text())), key=str)
        assert not errors, f"{fx.name}: {[e.message for e in errors]}"
