# gbrg/reasoning — PLN risk propagation (GBRG causal TRACK 1)

Transitive **risk propagation** over the GBRG blast-radius graph, using
[`@socioprophet/hellgraph`]'s in-process **PLN** (Probabilistic Logic Networks)
forward chainer.

## What this is (honest label)

This is **probabilistic-logic risk propagation**: the risk of a downstream cell
flows *up* the call graph to its (transitive) callers, and a `(strength,
confidence)` truth value is attenuated at every hop. Concretely it runs PLN
**deduction** — `A→B (s1,c1) ⊗ B→C (s2,c2) ⇒ A→C (s1·s2, c1·c2·0.9)` — so a
derived transitive-risk edge always carries **lower confidence** than the direct
edges it was chained from (per-hop decay).

## What this is **NOT**

This is **NOT Pearl / structural causal inference**. There is:

- **no** do-calculus or interventions,
- **no** counterfactuals,
- **no** SCM identification / back-door / front-door adjustment.

"Causal TRACK 1" is the program/track name, not a claim of Pearl causality. If
you need interventional or counterfactual semantics, this module does not
provide them and must not be described as if it does.

## What is real vs. supplied

- **Risk seeds are REAL.** Cells and their risk come from real `gbrg-analyze`
  `ProofArtifact`s, obtained through the same subprocess pattern as
  `gbrg/mcp/src/analyze.ts` (`makeAnalyze(binPath)`). We do **not** re-score
  anything in TypeScript — that is the GBRG lane rule.
- **Inference is REAL.** Transitive edges are produced by the real
  `forwardChain()` in `@socioprophet/hellgraph`. We project onto the store and
  read back what it derived; we never reimplement the chainer.
- **Call topology is supplied by the caller.** The `gbrg-analyze` CLI emits one
  `ProofArtifact` per cell on stdout but does **not** surface its internal
  `CALLS` edges there, so the directed `CallEdge[]` (`from` calls `to`) is passed
  in explicitly. In the real pipeline these come from the same source tree's
  call graph; in the test, from the `A→B→C` chain.

## `pln.ts` is the shallow in-process fallback

`@socioprophet/hellgraph`'s `pln.ts` is the fast, **in-process** deduction /
revision / abduction path — a shallow fallback for zero-latency inference. The
full URE-backed OpenCog PLN chaining lives in the sidecar. This module consumes
the in-process path; swapping in the sidecar chainer would deepen (not change
the meaning of) the propagation.

## Risk → truth-value seeding rule

An edge is seeded from its **callee** (`to`) — the cell whose risk flows upward:

| epistemic level | base strength | rationale |
| --- | --- | --- |
| `speculative` | 0.90 | untested + unproven → highest transitive risk |
| `synthetic`   | 0.80 | built on synthetic/not-real data |
| `empirical`   | 0.60 | observed, not proven |
| `bounded`     | 0.45 | bounded guarantee |
| `proved`      | 0.30 | proven → leaks little risk |
| `rejected`    | 0.20 | claim rejected |

- **strength** `= base (+0.05 if untested, capped 0.95)`. "How strongly risk
  propagates along this edge." Speculative/untested → high.
- **confidence** `= test_coverage_reach ? 0.90 : 0.80`. "How much evidence backs
  the truth value." Kept high enough that hellgraph's `×0.9` per-hop decay is the
  dominant, visible attenuation in the derived edge.

## API

```ts
import { analyzeAndPropagate, propagateFromArtifacts, projectAndPropagate }
  from '@socioprophet/gbrg-reasoning'

// End-to-end: REAL gbrg-analyze subprocess → risk graph → forwardChain
const { artifacts, propagation } = await analyzeAndPropagate(
  binPath, srcDir, [{ from: aCellId, to: bCellId }, { from: bCellId, to: cCellId }],
)
propagation.derived // DerivedRiskEdge[] — transitive-risk edges with per-hop decay
```

## Test (runs LIVE)

```
npm install        # @socioprophet/hellgraph via a local file: dep
npm test           # tsx + node:test; spawns the REAL gbrg-analyze binary
```

The test writes a real `A→B→C` TypeScript fixture, runs the real `gbrg-analyze`
CLI on it, projects the real speculative/untested artifacts onto the store, runs
the real `forwardChain()`, and asserts (a) a derived `A→C` edge exists, (b) its
confidence `< ` the direct edges (decay, exactly `c1·c2·0.9`), and (c) its
strength is sane (`s1·s2`, in `(0,1]`). Point it at a prebuilt binary with
`GBRG_ANALYZE_BIN`, or build one first:
`(cd gbrg && cargo build -p gbrg-analyze --release)`.

[`@socioprophet/hellgraph`]: ../../.. "consumed via a local file: dependency; never edited"
