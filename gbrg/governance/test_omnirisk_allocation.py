"""Teeth tests for the omnirisk cross-cut allocation contract (OMNI-1).

Both directions, over static fixtures whose per-node risk results are GIVEN
inputs (consumed from the economic-prophet kernel by reference), so this suite is
independent of the in-flight kernel PR.

VERIFIES
  * the valid two-cut tree reconciles to the SAME bank total under the product cut
    and the client-segment cut (cut-invariance);
  * component contributions SUM to the parent total for a coherent measure
    (conservation — the IC-1 settlement law);
  * sensitivities aggregate value-weighted (duration/convexity) / principal-weighted
    (WAL), within the children's min/max bound.
REJECTS (one fixture per tooth)
  * conservation violation, non-coherent measure without override, super-additive
    diversification, incoherent tranche, missing regime, provisional silent
    roll-up, mixed horizon/confidence, mixed term regime, duration out of bounds.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from gbrg.governance import ledger
from gbrg.governance import omnirisk_allocation as omni

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "omnirisk"


def _load(name: str) -> dict:
    return omni.load_tree(FIXTURES / name)


# --------------------------------------------------------------------------- #
# VERIFIES side.
# --------------------------------------------------------------------------- #
def test_valid_tree_verifies_and_is_cut_invariant() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        lp = Path(tmp) / "omni.jsonl"
        result = omni.evaluate_tree(_load("omnirisk_two_cut.valid.json"), ledger_path=lp)
        assert result.verdict == omni.VERIFIES, result.reason
        assert result.cut_invariant is True
        # Bank total is 100 economic capital regardless of cut.
        assert abs(result.bank_total_ec - 100.0) < 1e-9
        # RAROC = rar/EC = 20.5/100 >= hurdle 0.12; EP = 20.5 - 0.12*100 = 8.5.
        assert abs(result.bank_raroc - 0.205) < 1e-9
        assert abs(result.bank_economic_profit - 8.5) < 1e-9
        # The verdict receipt is sealed and the chain verifies (FIPS-180-4 sha256).
        v = ledger.verify_ledger(lp)
        assert v.ok, v.reason
        assert result.receipt


def test_cut_invariance_holds_across_all_aggregated_quantities() -> None:
    spec = _load("omnirisk_two_cut.valid.json")
    viols: list[str] = []
    product = omni.walk(spec["cuts"]["product"], violations=viols)
    client = omni.walk(spec["cuts"]["client_segment"], violations=viols)
    assert viols == [], viols
    # Same transactions, two hierarchies -> identical bank totals.
    for attr in ("ec", "value", "principal", "duration", "convexity", "average_life"):
        assert abs(getattr(product, attr) - getattr(client, attr)) < 1e-9, attr
    assert abs(product.ec - 100.0) < 1e-9


def test_conservation_sum_to_total_for_coherent_measure() -> None:
    spec = _load("omnirisk_two_cut.valid.json")
    bank = spec["cuts"]["product"]
    viols: list[str] = []
    child_ecs = [omni.walk(c, violations=viols).ec for c in bank["children"]]
    assert viols == []
    # Euler contributions of the children SUM to the declared parent total.
    assert abs(sum(child_ecs) - bank["risk"]["economic_capital"]) < 1e-9


def test_sensitivities_aggregate_value_and_principal_weighted() -> None:
    spec = _load("omnirisk_two_cut.valid.json")
    viols: list[str] = []
    bank = omni.walk(spec["cuts"]["product"], violations=viols)
    assert viols == []
    # Value-weighted duration/convexity; principal-weighted WAL.
    assert abs(bank.duration - 5.0) < 1e-9
    assert abs(bank.convexity - 42.75) < 1e-9
    assert abs(bank.average_life - 6.5) < 1e-9


def test_ep_identity_and_raroc_helpers() -> None:
    assert abs(omni.economic_profit(20.5, 0.12, 100.0) - 8.5) < 1e-9
    assert abs(omni.raroc(20.5, 100.0) - 0.205) < 1e-9


# --------------------------------------------------------------------------- #
# REJECTS side — one fixture per tooth, each rejected for the RIGHT reason.
# --------------------------------------------------------------------------- #
_REJECT_CASES = [
    ("conservation_violation.invalid.json", "conservation violation"),
    ("noncoherent_no_override.invalid.json", "non-coherent measure"),
    ("superadditive_diversification.invalid.json", "super-additive"),
    ("incoherent_tranche.invalid.json", "incoherent structure"),
    ("missing_regime.invalid.json", "missing its regime label"),
    ("provisional_silent_rollup.invalid.json", "provisional"),
    ("mixed_horizon.invalid.json", "incompatible confidence/horizon"),
    ("mixed_term_regime.invalid.json", "incompatible term regimes"),
    ("duration_out_of_bounds.invalid.json", "outside its children's"),
]


def test_each_tooth_rejects_for_the_right_reason() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        lp = Path(tmp) / "omni.jsonl"
        for fixture, needle in _REJECT_CASES:
            result = omni.evaluate_tree(_load(fixture), ledger_path=lp)
            assert result.verdict == omni.REJECTED, f"{fixture} should REJECT"
            assert any(needle in v for v in result.violations), (
                f"{fixture}: expected a violation containing {needle!r}, got {result.violations}"
            )
        # Even rejected verdicts are sealed; the ledger stays tamper-evident.
        v = ledger.verify_ledger(lp)
        assert v.ok, v.reason


def test_all_fixtures_behave_as_named() -> None:
    """*.valid.json must not REJECT; *.invalid.json must REJECT."""
    with tempfile.TemporaryDirectory() as tmp:
        lp = Path(tmp) / "omni.jsonl"
        fixtures = sorted(FIXTURES.glob("*.json"))
        assert fixtures, "no fixtures found"
        for fx in fixtures:
            result = omni.evaluate_tree(omni.load_tree(fx), ledger_path=lp)
            if fx.name.endswith(".invalid.json"):
                assert result.verdict == omni.REJECTED, fx.name
            else:
                assert result.verdict != omni.REJECTED, fx.name


def test_incoherence_override_permits_var_allocation() -> None:
    """A VaR allocation is allowed only with the explicit incoherence override."""
    spec = _load("noncoherent_no_override.invalid.json")
    spec["incoherence_override"] = True
    with tempfile.TemporaryDirectory() as tmp:
        result = omni.evaluate_tree(spec, ledger_path=Path(tmp) / "l.jsonl")
        # VaR is now permitted; no coherence violation remains.
        assert not any("non-coherent measure" in v for v in result.violations)


if __name__ == "__main__":
    raise SystemExit(omni.main())
