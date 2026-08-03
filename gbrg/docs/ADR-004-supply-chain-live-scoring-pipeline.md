# ADR-004 — Live supply-chain risk scoring over real HellGraph topology

Status: Accepted
Date: 2026-08-03
Scope: `gbrg/contracts/supply-chain-graph-signal-map.v0.json` + `gbrg/governance/supply_chain_pipeline.py` + `gbrg/adapters/evidence.py` (`scr_to_observations`)
Cross-ref: SocioProphet/sociosphere#547 (the scorer this builds on), prophet-workspace#108 (item 2)

## Context

ADR-003 (#547) shipped the supply-chain operational-risk **contract + scorer +
teeth** (`supply_chain_risk.py`): `assess_node` / `assess_path` / `assess_cluster`
project a scored verdict over DECLARED weights. But the scorer takes
**caller-supplied** factor / residual / component dicts — it does not yet know how
to pull its subjects off the real graph. This ADR closes that gap: score the live
estate topology, not hand-supplied numbers.

The real graph is already produced: `gbrg-analyze --emit-edges` walks a crate and
emits `BlastRadiusProofArtifact`s (`blast_radius`, `dependents_count`,
`churn_frequency`, `test_coverage_reach`, `epistemicLevel`) plus the real
`CALLS` / `IMPORTS` / `TESTED_BY` edge topology.

## Decisions

### 1. The signal→factor mapping is DECLARED DATA, never magic numbers
`contracts/supply-chain-graph-signal-map.v0.json` declares how each of the six
inherent factors and four cluster components is DERIVED from an observed graph
signal — the live-scoring counterpart to the weights contract (which says how
factors *combine*). `supply_chain_pipeline.py` loads this file; changing a
derivation is a reviewable data change.

| factor | derived from | transform |
|---|---|---|
| criticality_K | `blast_radius` | identity |
| concentration_C | `dependents_count` | saturating(/15) |
| velocity_V | `churn_frequency` | saturating(/0.5) |
| opacity_O | `test_coverage_reach` + `epistemicLevel` | weighted (untested + epistemic opacity) |
| execution_E | fail-closed prior + source-locator path signals | prior, raised (not measured) |
| privilege_P | fail-closed prior + source-locator path signals | prior, raised (not measured) |

### 2. Honesty about what a code graph cannot see (observable:false)
Publishing/signing authority (P) and install/build execution capability (E) are
**not observable** from a function-call graph. Rather than fabricate a
measurement, the map marks these `observable:false` and derives them from a
declared **conservative prior** raised only by real path signals on the cell
locator (e.g. `build.rs` → execution, `publish|sign|token` → privilege). The
derivation string records them as PRIORS. `factor_provenance()` exposes the
observable/prior split so a consumer never mistakes a prior for a reading.

### 3. Controls-evidence + KRI/KCI from real sources, fail-closed
Controls come from an optional `evidence_index` (real evidence where available).
A subject with no entry carries NO controls-evidence, so a tier-0 subject fails
**closed** (REJECTED) in the unchanged scorer — assessing the estate with no
evidence leaves every subject REJECTED, the honest default. Only KRIs the graph
genuinely computes are auto-derived (`KCI02` graph visibility, `KRI04`
concentration); every other indicator is left unevaluated (never silently passed)
unless supplied externally.

### 4. Real paths and clusters from real topology
A path subject is a real `CALLS` chain enumerated off the edge topology
(`derive_call_paths`), scored as the scorer's noisy-OR over its members'
residuals. The cluster's common-mode components (HHI over `dependents_count`
shares, worst-case blast, untested fraction, mean opacity) are an aggregate over
real member artifacts.

### 5. Emit onto the evidence plane — EVIDENCE ONLY, never authorization
`scr_to_observations` lifts each sealed `SupplyChainRiskProofArtifact` onto
`repo-governance-observation.v0`, reusing the exact invariant of
`adapters/evidence.py`: the scored VERDICT (VERIFIES/FLAGGED/REJECTED) lives in
the sealed, hash-chained ledger; only the **measured** risk signals (residual
score, rating) cross to the plane, anchored to a real source blob. The verdict is
preserved as a namespaced risk CLASS (`gbrgnrg:riskClass`), and
`assert_evidence_only` guarantees no `verdict` / `decision` / `allow` / `deny` /
`policyDecision` key ever reaches the plane. GBRG feeds policy-fabric; it does not
decide.

## Consequences

- The scorer (`supply_chain_risk.py`) is **unchanged** — this ADR only supplies
  its inputs from the real graph and lifts its outputs onto the evidence plane
  (consume-not-fork end to end).
- Scoring the estate with no controls evidence is a wall of REJECTED verdicts by
  design. That is the fail-closed signal, not a bug: real controls evidence must
  be wired in (via `evidence_index`, later a real evidence source) to earn a
  VERIFIES.
- `P`/`E` priors are deliberately coarse. They should be replaced by real signals
  (publish-authority graph, install-script detection) as those become available;
  the `observable:false` flag marks exactly where that work lands.
