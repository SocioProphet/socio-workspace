# ADR-004 — Omnirisk architecture: one risk kernel, allocable along every axis

Status: Accepted
Date: 2026-08-03
Scope: `gbrg/governance/omnirisk_allocation.py` + `gbrg/governance/fixtures/omnirisk/*`
Consumes (soft ref, not forked):
- `economic-prophet@feat/risk-adjusted-profit-raroc` — RM-1 risk-measure family
  (`src/open_ep_framework/risk_measures.py`) + RAP-1 RAROC contract
  (`src/open_ep_framework/risk_adjusted_profit.py`).
- `economic-prophet` memory-regime characterizer (separate PR, in flight) — Hurst
  `H` / Lyapunov `λ` / fractal dimension → regime + fat-tailed / long-memory `F`.

## Context

The estate needs a single governed place where **economic capital, RAROC and
Economic Profit are computable AND allocable along every axis at once** — the
"omnirisk" plane. Grounding image (McKinsey Working Papers on Risk #24): economic
capital is allocated down a **product cut** (Bank → Business-unit → Subportfolio →
Transaction) *and* a **client-segment cut** (Geography / Segment → Obligor), with
market risk (FX, commodity, rates) cross-cutting both. We generalize that to the
axes:

```
asset_class {credit, equity, market}
  × issuer/obligor × issuance/instrument
  × structure (tranche / seniority / capital-structure)
  × regime (memory-regime H/λ/D  ×  market-regime)
  × term regime (upward/inverted; persistent/mean-reverting via tenor-dim Hurst)
  × time/sensitivity (WAL, duration, convexity, higher moments)
  × org_cut (ANY hierarchy: product-cut or client-segment-cut)
```

The per-node risk kernel already exists on `economic-prophet` (the RAROC PR in
flight). This ADR is about the **architecture + aggregation layer** that sits on
top of it, in the GBRG risk plane. It **consumes, does not fork** the kernel.

### Home: why GBRG (`sociosphere/gbrg`)

GBRG already owns cross-entity risk scoring on the estate: the supply-chain
operational-risk contract (ADR-003, sociosphere#547) established exactly the
pattern we extend here — a declared contract, a validator *with teeth*, static
fixtures (valid + one invalid per tooth), verdicts projected Assay-style
(VERIFIES/FLAGGED/REJECTED), and hash-chained receipts on
`gbrg.governance.ledger`, all gated by `pytest -q` in `validate.yml`. A cross-node
risk **graph/hierarchy** is the natural next node on that plane. `economic-prophet`
is the canonical *engine* and must not host the estate's blast-radius/risk-graph
aggregation; and its RAROC kernel PR is in flight there, so authoring here also
avoids collision.

## Decisions

### 1. One kernel — same `risk(F, ·)` for credit AND equity; only `F` and `reference` change
The kernel exposes a single interface `risk(F, kernel, reference, horizon, alpha,
order, phi)` over one loss/return distribution `F`. Sharpe, Sortino, Kappa/LPM,
VaR, Expected Shortfall and spectral measures are all *lenses on the same `F`*.
Credit `F` comes from `LossDistribution.simulate_credit` (one-factor common
shock); equity/market `F` from `simulate_equity` (fat-tailed Student-t return).
This layer never re-derives a measure — it carries the kernel's result per node as
a given input and *aggregates* it.

### 2. Regime-aware `F` (fat-tailed / long-memory, per Mandelbrot)
`F` is not assumed Gaussian. The memory-regime characterizer (consumed PR) labels
each node with its memory regime from Hurst `H` (long memory when `H≠0.5`),
Lyapunov `λ` (sensitivity/chaos) and fractal dimension `D`, and hands the kernel a
fat-tailed / long-memory `F` accordingly. **Every node in a `RiskAllocationTree`
MUST carry its `regime` label** — a node without one is REJECTED, because an
un-regimed capital number is not auditable.

### 3. Coherence is the precondition for allocation
Only a **coherent** measure (subadditive + positively homogeneous — Expected
Shortfall, or a non-increasing spectral measure) admits **Euler / marginal**
allocation whose component contributions **sum to the parent total** exactly
(`E[loss_i | portfolio ∈ tail]` is conditionally linear). **VaR is not
subadditive** and cannot underwrite cross-node allocation; using it for allocation
requires an explicit `incoherence_override` flag, else REJECTED. Consequences:

- **Conservation** — children EC contributions sum to the parent EC. This is the
  same sum-to-total law as the EP **IC-1 conservation-settlement** contract; a tree
  that violates it is REJECTED.
- **Cut-invariance** — because Euler contributions are per-transaction, the bank
  total is invariant to the hierarchy: the product cut and the client-segment cut
  over the SAME transactions reconcile to the SAME bank total EC (and the same
  aggregated duration/convexity/WAL). A tree whose two cuts disagree is REJECTED.
- **Subadditivity** — a coherent aggregate can never EXCEED the sum of standalone
  risks (diversification benefit ≥ 0). A node whose aggregate exceeds the sum of
  standalone risks is **super-additive**, which is impossible for a coherent
  measure and therefore signals a bad model — REJECTED.

### 4. Two operators, one calculus — both regime-aware
The omnirisk calculus has exactly two aggregation operators:

- **INTEGRAL operators** — the coherent tail measures and the distribution moments
  (skew, kurtosis) — are integrals of `F`. They aggregate **with diversification**:
  Euler contributions conserve (sum to the parent) and the diversified total is
  bounded above by the standalone sum.
- **DERIVATIVE operators** — the sensitivities: **duration, convexity, marginal
  capital** — are derivatives of the value/risk functionals. They aggregate
  **value-weighted**: a bond ladder's duration is the value-weighted average of its
  legs' durations; **WAL** (average life) is principal-weighted. A weighted average
  is bounded by its inputs' min/max, so a node claiming a portfolio
  duration/convexity outside its children's range is REJECTED.

Both operators are regime-aware. **Term regime** (the regime of the *term
structure* — upward/inverted; persistent/mean-reverting via the tenor-dimension
Hurst) is a first-class node axis: an aggregation that mixes incompatible term
regimes or tenors without an explicit `rescale` is REJECTED — the same spirit as
the horizon/confidence-mixing rejection, extended to the term structure.

### 5. EP grounding (consumed identity, checked not recomputed)
- `EconomicCapital = coherent-tail(F) @ confidence over horizon` (given per node
  by the kernel).
- `EconomicProfit = RiskAdjustedReturn − Hurdle × EconomicCapital` (RAP-1 / the
  canonical EP additive identity).
- `RAROC = RiskAdjustedReturn / EconomicCapital` at **every** node; a bank total
  with `RAROC < Hurdle` is FLAGGED value-destroying (returned, not raised).

### 6. Receipts and FIPS scoping
Each verdict is sealed as a hash-chained event on the existing
`gbrg.governance.ledger` and verified, unchanged, by `ledger.verify_ledger` — no
new ledger machinery. **SHA-256 is the FIPS-180-4 *algorithm*** used for
tamper-evident chaining; this is **not** a FIPS-140 validated cryptographic
module, and no such claim is made.

## The contract: `RiskAllocationTree`

A tree carries `cuts: { <org_cut>: <root node>, ... }` over the SAME underlying
transactions. Every node carries a `label` `{asset_class, issuer?, issuance?,
structure?, regime, org_cut}`, a per-node `risk` result consumed from the kernel
(`measure, coherent, alpha, horizon, component_contribution, standalone_capital,
economic_capital, risk_adjusted_return, n_samples, provisional, distribution_id,
risk_ref`), and a `term` block `{value, principal, duration, convexity,
average_life, skew, kurtosis, term_regime, tenor_bucket}`. Leaves carry the
kernel's Euler `component_contribution`; internal nodes declare an
`economic_capital` that the walker reconciles against the sum of its children.

## Teeth, both directions (`test_omnirisk_allocation.py`, 8 tests; fixtures 1 valid + 9 invalid)

VERIFIES — the valid two-cut tree reconciles to the SAME bank total under both
cuts (cut-invariance); coherent-measure component contributions SUM to the parent
(conservation / IC-1); duration & convexity aggregate value-weighted and WAL
principal-weighted.

REJECTS — one fixture per tooth: conservation violation; non-coherent (VaR)
allocation without `incoherence_override`; super-additive diversification; an
incoherent credit tranche (`attach ≥ detach`); a node missing its regime label; a
provisional (n<30) node silently rolled into a non-provisional total; mixed
horizon/confidence without rescale; mixed term regime without rescale; a portfolio
duration outside its children's min/max bound.

## Consequences

- The omnirisk plane can now aggregate/allocate economic capital along every axis
  at once, and *prove* the allocation is coherent, conserving and cut-invariant.
- Self-contained: node risk results are given inputs (consumed by reference), so
  `omnirisk-allocation-validate` (wired into `make validate`) and `pytest -q` are
  independent of the in-flight kernel PR. When that PR merges, the fixtures'
  `risk_ref` soft-references resolve to live kernel output with no contract change.
- Follow-up: once the RAROC kernel and the memory-regime characterizer land, add a
  thin adapter that emits `RiskAllocationTree` nodes directly from
  `euler_allocation` + the characterizer, replacing hand-authored fixtures with
  live kernel receipts.
