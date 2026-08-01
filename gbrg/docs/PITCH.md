# GBRG — Governed Blast-Radius Graph

**One line:** Every AI code-review context decision becomes a declared, provenance-bearing claim — not a silent heuristic or a black-box score.

This document is deliberately anti-hype. Every number is measured and reproducible; every not-yet-real capability is labelled as such. That discipline is not a caveat on the product — it *is* the product.

---

## The problem

AI code review needs to decide *what code to look at* for a change. The state of the art (e.g. `code-review-graph`, 26.7k★) does this well on token efficiency, but the decision is a **black-box score**: "this function ranks high." You cannot see *why* a cell was included or excluded, whether the ranking is trustworthy, or who authorized it.

For governed / regulated / high-stakes engineering, an opaque prioritization is a liability: you can't audit it, can't contest it, can't prove the review saw what it should have.

## The differentiator

GBRG emits, for every changed cell, a **ProofArtifact** carrying a declared `epistemicLevel` and a written derivation — not a float:

```json
{ "epistemicLevel": "speculative", "dependents_count": 40, "test_coverage_reach": false,
  "blast_radius": 0.87, "declared_by": "agent-registry://gbrg/scorer",
  "derivation": "no test path reaches this cell; 40 dependents exceed the bounded
                 threshold of 15; absent test evidence the behaviour can only be
                 speculated → speculative" }
```

Same "40 callers, no tests" case the reference tool would silently rank first — but GBRG **declares it as speculative risk, and says why.** A reviewer (human or agent) sees the warrant, not just the verdict.

## What's real today (verified, tested, public)

All of this is merged or in [PR #509](https://github.com/SocioProphet/sociosphere/pull/509), each independently tested:

- **Code graph** — real tree-sitter parse (Rust/Python/TS) → cells + calls/imports/inherits edges → HellGraph, with fan-in blast-radius. Consumes HellGraph as a vendored Rust crate; never edits it.
- **Governed epistemicLevel** — derivation with overridable thresholds; the enum is inherited verbatim from SCOPE-D's `proof-artifact.schema.json`, not reinvented.
- **Governance gate** — every context inclusion/exclusion is a declared, sha256-sealed, ledgered decision through agent-registry's fail-closed authorizer. Proven to **block both ways** (allow *and* fail-closed deny), 27/27.
- **Zero-trust MCP server** — a2a-mcp-zero-trust conformant; agents get ProofArtifacts, never bare floats; ungranted calls are refused; every call is ledgered. Runs **live** (real SDK + Rust CLI).
- **Estate-native integration** — feeds the neurosymbolic-repo-graph corpus loop as an evidence producer (schema-valid, evidence-only — never authorization).
- **Reasoning — PLN risk-propagation** — real HellGraph `forwardChain`: risk flows along call edges with per-hop confidence decay.

## Benchmark — measured, not claimed

Reproducible harness on real code. **We do not claim to beat `code-review-graph`'s published 71.4× / 100%** — their methodology is unverified and favorable-case.

| Target | Token reduction (median) | Impact recall (transitive) | vs direct-only |
|---|---|---|---|
| `gbrg/crates` (~4.5k LOC) | **4.1×** | 100% | 37.7% |
| `hg_analytics` (~13k LOC) | **41.5×** | 100% | 66.2% |

**Non-claim box:** token-reduction is repo-size-dependent (4× small, 41× larger). The 100% recall is *completeness-by-construction* (selector and oracle read the same graph), bounded by graph completeness — not independent impact discovery. The direct-only column (37.7% / 66.2%, well under 100%) is shown precisely to prove the recall metric *can* fail. **GBRG's moat is governed provenance, not token-reduction supremacy.**

## What is NOT real yet (labelled, not hidden)

- **True causal inference** (do-calculus / counterfactuals) — a research track only. The design doc (`CAUSAL-INFERENCE-RESEARCH.md`) is explicit that real code graphs violate the load-bearing SCM assumptions (cycles; refactors as pervasive latent confounders), so most effects are not identifiable. Nothing here is implemented.
- **What-if recomputation** exists and is useful ("if this had tests: speculative→empirical") but is deterministic recompute-and-diff — *not* counterfactual causal inference. Enforced in code.
- **PLN edge autonomy** — call topology is currently supplied by the caller; wiring `gbrg-analyze` to emit its edges is a small follow-on.

## Why it earns trust

- **Open source** — the full development history is public; the work can be read, not just believed.
- **Every signal is a claim with a warrant** — provenance, threshold, and reason, per cell.
- **Controls that can fail** — the gate demonstrably denies; the recall metric demonstrably drops. Nothing is a green light that can only say yes.
- **Honest maturity everywhere** — real is tested, roadmap is labelled roadmap.

---

*Positioning note (internal): GBRG is a candidate live-demoable differentiator for governed-AI / Palantir-anchor conversations — precisely because its pitch survives scrutiny. Lead with the provenance and the falsifiable controls, not the token ratio.*
