# GBRG What-If (Causal Track 2) — deterministic recompute-and-diff

> 🔴 **Honesty first.** GBRG what-if is **NOT counterfactual causal inference.**
> It does not implement Pearl's do-operator, adjust for confounders, estimate
> average/individual treatment effects, or reason about unobserved causes. It is a
> **deterministic recompute-and-diff** over a hypothetically-edited copy of the
> graph. Read every `after` as *"this is exactly what the deterministic score WOULD
> print if the graph literally looked like this"* — nothing stronger.

## What it actually does

Given a real GBRG graph, a target cell, and one hypothetical **graph edit**:

1. **Baseline.** Score the target cell into a `BlastRadiusProofArtifact` on the
   current graph (`before`), using the same `emit_proof_artifact` path the analyzer
   uses.
2. **Edit a copy.** Clone the cells + edges, apply a concrete syntactic edit to the
   **copy** (never the baseline), and re-`freeze()` a fresh index.
3. **Recompute.** Score the same cell on the edited copy (`after`) with the same
   scoring function.
4. **Diff.** Report `after − before` as a `WhatIfResult`.

The reported delta is an **arithmetic difference of two deterministic scores**, not
an estimated causal effect. `churn` and `dead` are held **constant** across
`before`/`after`, so the change is attributable to the edit alone (the mutations are
purely topological).

## The mutations (concrete graph edits, not interventions)

| Mutation           | Graph edit on the COPY                                        | Recompute effect                          |
|--------------------|--------------------------------------------------------------|-------------------------------------------|
| `add_tests`        | Add one synthetic `TESTED_BY` in-edge into the target        | `test_coverage_reach` → `true`; level can climb `speculative → empirical`/`bounded`; blast radius shrinks |
| `remove_dependent` | Drop one incoming `CALLS` edge to the target                 | `dependents_count` → one lower; blast radius shrinks |

A mutation that cannot change anything (e.g. `remove_dependent` on a cell with no
incoming `CALLS` edge, or `add_tests` on an already-tested cell) is an **honest
no-op**: `applied = false`, `delta = 0`, and `note` explains why. It is not an error.

## Why this is NOT Pearl / do-calculus

- **No causal model.** There is no DAG of causes, no structural equations, no
  intervention semantics. We edit the *dependency graph's data*, not a model of how
  variables cause one another.
- **No confounding, no adjustment.** We do not identify or block back-door paths, do
  not compute `P(Y | do(X))`, and do not correct for anything. We recompute a
  deterministic function on edited inputs.
- **No inference / no estimation.** The result is exact and reproducible from the
  inputs — no sampling, no estimand, no uncertainty over unobserved variables.

The honesty banner is carried in the machine output itself
(`WhatIfResult.method`) and in the module docs (`gbrg-core/src/whatif.rs`), so a
downstream consumer cannot mistake a recompute-delta for a causal effect.

## CLI

```text
gbrg-analyze whatif <file|dir> --cell <cell_id> --mutation add_tests|remove_dependent
```

- Builds the graph from `<path>` using the **same** analyzer pipeline
  (`build_whatif_graph` → `analyze_path_report`): parse → cross-file resolution →
  ingest. The what-if is therefore diffed against exactly the graph the analyzer
  would score.
- The target cell's **real** per-file git churn is held constant across
  before/after.
- Prints a `WhatIfResult` as pretty JSON on stdout; a one-line summary and the
  honesty banner go to stderr.

Example summary:

```text
IF add_tests: speculative→empirical, blast 0.35→0.10
```

## Guarantees

- **Baseline never mutated.** Every edit is applied to a `clone()` of the graph.
  `WhatIfGraph::score_cell` lets a caller re-score the baseline after a what-if and
  confirm it is byte-for-byte identical — the real test (`tests/whatif.rs`) asserts
  exactly this, plus that the synthetic edge never leaks into the baseline edge set.
- **Same scoring path.** `before` and `after` both go through
  `gbrg_core::emit_proof_artifact`; what-if adds no parallel scoring logic.
