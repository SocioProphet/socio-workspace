# ADR-005 — Portfolio/position binding: the data source under the omnirisk hierarchy

Status: Accepted
Date: 2026-08-03
Scope: `gbrg/governance/portfolio_position_binding.py` +
`gbrg/governance/fixtures/portfolio_position_binding/*` +
`gbrg/contracts/portfolio-position-binding.schema.json`
Consumes (soft ref, not forked):
- `gbrg.governance.omnirisk_allocation` (OMNI-1, ADR-004, same repo) — the walker
  that aggregates/allocates a `RiskAllocationTree`. Executed read-only
  (`evaluate_tree(..., persist=False)`) to confirm the target hierarchy is itself
  valid; forks nothing.
- The asset-class **ladder** + credit/equity/crypto **F builders** —
  `economic-prophet@feat/risk-adjusted-profit-raroc`
  (`LossDistribution.simulate_credit` / `simulate_equity`) and the in-flight
  crypto builder (`economic-prophet@feat/crypto-asset-class`). Referenced as the
  set of asset classes each instrument must declare; NOT imported.
- The estate entity-resolution plane — `regis-entity-graph` EntityNode
  `{node_id, kind}` (`schemas/node.schema.json`). The `entities` roster is a
  **by-contract snapshot** of that schema. This module NEVER calls the ER
  service, the ER `/resolve/entities` endpoint, or the shared HellGraph, and
  NEVER writes anywhere.

## Context

OMNI-1 (ADR-004) walks a `RiskAllocationTree`: it aggregates children into
parents and allocates parents down to children along any org-cut, and rejects any
tree that breaks the conservation/coherence laws. But the walker **assumes** its
leaves' exposures exist. The tree is handed to it with `component_contribution`
already on each leaf and `economic_capital` already on each org node. Nothing
proves:

1. that a leaf's asserted risk is **backed by a real holding**;
2. that an org node claiming risk actually **owns any position** (or is a phantom
   node — risk asserted with no book behind it);
3. that every exposure is **attributable** to a resolvable counterparty rather
   than floating unowned;
4. that a position isn't **double-counted** across two org-cuts.

The hierarchy was, in effect, assuming an org tree with no source. This ADR adds
the missing data-source layer directly beneath the walker: a typed
`PortfolioPositionBinding` that makes a real book of positions roll up into the
exact hierarchy OMNI-1 expects — and that has teeth in both directions.

## Decision

A binding document links four things by contract:

```
Position ── instrument_ref ─▶ Instrument ── issuer_ref ─▶ Issuer/Counterparty Entity
  (holding: quantity,          (asset_class on the         (regis-entity-graph
   exposure, leaf_ref)          ladder + F builder)         EntityNode {node_id, kind})
     │
     └── leaf_ref ─▶ omnirisk hierarchy LEAF (node_ref), which the
                     RiskAllocationTree places under an org-cut node in EVERY cut
```

- **Position** — a holding: `instrument_ref`, `quantity`, `exposure` (the
  economic-capital contribution it sources), and `leaf_ref` (the hierarchy leaf it
  backs). Positions are the atoms below the walker's leaves; many positions may
  source one leaf.
- **Instrument** — carries an `asset_class` on the ladder
  (`credit`/`equity`/`market`/`crypto`), each rung mapped to the economic-prophet
  F builder that scores it, and an `issuer_ref`.
- **Issuer/Counterparty Entity** — `issuer_ref` is the `node_id` of an EntityNode
  in the `entities` roster, a by-contract snapshot conforming to
  `regis-entity-graph`'s `node.schema.json` (kind ∈ {ORG, PERSON, ENTITY_CLUSTER}
  for an issuer). Read-only, never a live ER read.
- **Hierarchy node** — the org-cut node the OMNI-1 walker aggregates. The tree is
  embedded verbatim and re-validated by the real walker.

Home rationale: this lives in `sociosphere/gbrg` next to the walker (OMNI-1),
because the conservation and phantom-node teeth are defined **against the walker's
`RiskAllocationTree`** and can only be checked there. Co-locating lets the same
`pytest -q` + `make validate` CI exercise source and hierarchy together. The EP F
builders and the ER plane are consumed by soft contract — the same
consume-not-fork pattern the walker already uses for the EP kernel — which keeps
this a typed binding contract over fixtures, not a live probe, and keeps CI
independent of the in-flight kernel/ER PRs.

## Teeth

VERIFIES
- **Conservation, sourced.** For every node in every cut,
  `Σ(position.exposure rolling into the node) == node's declared exposure`
  (leaf `component_contribution` / internal `economic_capital`), within
  tolerance. A real book rolls up to the SAME node exposures the walker
  aggregates.
- **Attribution.** Every instrument's issuer resolves to a roster EntityNode of an
  issuer kind.
- **Classification.** Every instrument carries an asset_class on the ladder, with
  an F builder.
- **Hierarchy validity.** The embedded tree is itself accepted by the OMNI-1
  walker.

REJECTS (one fixture per tooth, under `fixtures/portfolio_position_binding/`)
- `unattributed_issuer.invalid.json` — an issuer that does not resolve to an
  entity (unattributed exposure).
- `phantom_node.invalid.json` — a hierarchy node with NO backing positions
  (risk asserted with no holdings); flagged in every cut the node appears in.
- `cross_cut_double_count.invalid.json` — a leaf present more than once in one
  org-cut (or not present in every cut), i.e. exposure double-counted across cuts
  without reconciliation.
- `conservation_violation.invalid.json` — a node whose backing-position exposures
  do not sum to its declared exposure.
- `missing_asset_class.invalid.json` — an instrument with no asset_class.

## Consequences

- Deterministic and stdlib-only (sha256 = FIPS-180-4 algorithm, not a FIPS-140
  module). Every verdict is sealed as a hash-chained receipt on the existing
  `gbrg.governance.ledger` — no new ledger machinery.
- Strictly read-only / audit-only. No writes to the shared HellGraph or any
  live/shared state. The entity roster is a contract snapshot; runtime binding to
  the live ER `/resolve/entities` is deliberately out of scope.

## Follow-ups

- Live position feed: replace static `positions` fixtures with a feed from the
  book-of-record (ledger / custody), keyed to instrument identifiers.
- Entity-resolution runtime binding: resolve `issuer_ref` against the live
  `regis-entity-graph` `/resolve/entities` under entitlement, replacing the
  by-contract roster — still read-only, still no HellGraph writes.
