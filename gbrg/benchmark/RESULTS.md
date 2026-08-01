# GBRG Benchmark — token reduction & impact recall (Phase 5)

This is an **honest** measurement of what the Governed Blast-Radius Graph buys a
code-review workflow, run on real repositories with the real `gbrg-analyze`
pipeline. Every number below is captured output of `gbrg-benchmark`, not a target
we reverse-engineered. Where a number is modest, it is reported as measured.

> The reference tool `code-review-graph` advertises **71.4× fewer tokens** and
> **100% impact recall**. We treat that as a *claim to contextualize*, not a bar to
> fabricate parity with. See the **NON-CLAIM BOX** at the bottom.

---

## What is measured

### 1. Token reduction
For a review of one **changed cell**, compare two contexts an LLM reviewer could be
handed:

- **FULL context** — every reviewable cell body in the repo (the naive "dump the
  code" baseline).
- **MINIMAL context** — the changed cell **plus its blast radius** (its transitive
  graph dependents), which is what GBRG would select.

`token_reduction_ratio = full_tokens / minimal_tokens`, per changed cell.

### 2. Impact recall
The **true impacted set** of a changed cell = its actual graph dependents,
reverse-reachable via `CALLS` / `INHERITS` — computed by gbrg-core's public
`transitive_dependents` (a BFS over the frozen index's in-edge CSR).
`recall = |minimal_context ∩ true_impacted_set| / |true_impacted_set|`.

We report recall for **two** selection strategies so the metric visibly has teeth:
- **transitive (what GBRG sends)** — the full blast radius;
- **direct-only (depth-1)** — only immediate callers.

---

## Methodology (exact)

- **Token estimation:** `tokens = round(chars / 4)`. This is the well-known rough
  chars-per-token heuristic; **no offline tokenizer** is used (stated per the
  honesty requirement). The divisor is a CLI flag (`--divisor`); 4 is the default.
  Because both FULL and MINIMAL are divided by the same constant, the **ratio is
  divisor-independent** — the divisor only affects the absolute token figures.
- **Context text of a cell set** = characters in the **union** of the cells'
  1-based inclusive `[loc_start, loc_end]` line intervals, merged per file so a
  nested/overlapping cell (e.g. a method inside a class) is **never double-counted**.
- **Reviewable cell** = a non-test `function` or `class` cell (the units a reviewer
  actually reads). `module` cells span whole files and `import` cells are trivial,
  so both are excluded from context text **and** from the impacted set, keeping the
  measure cell-granular.
- **True impacted set (oracle)** = `transitive_dependents(cell)` intersected with the
  reviewable set. It is the graph's own reverse-reachable dependents — GBRG's real
  read, not a hand-authored answer key.
- **Leaf cells** (no dependents) are counted **separately** and excluded from the
  ratio aggregate: their minimal context is just themselves, which yields a huge but
  trivial ratio. Reporting them in the headline would inflate it.
- **Targets** = every reviewable cell with a blast radius ≥ 1.
- **Consume-only:** the harness calls `gbrg_analyze::analyze_path_report` for the
  exact resolved cells + edges, rebuilds the frozen index through gbrg-core's public
  `write_cell` / `write_edge` / `freeze` path, and uses gbrg-core's public
  `transitive_dependents` / `reverse_dependents`. It defines **no new graph logic**.

---

## Real results

### Target 1 — `gbrg/crates` (GBRG's own tree — the dogfood target)
~4,500 LOC of real multi-file Rust with tests. Analyzer parsed **20 files** (7 test
files), ingested **278 cells**, scored **216**; **159** reviewable fn/class cells.

| metric | value |
|---|---|
| FULL context | 82,627 chars ≈ **20,657 tokens** |
| targets (blast radius ≥ 1) | 88 |
| leaf cells (no dependents) | 71 |
| **token reduction — median** | **4.13×** |
| token reduction — min (hardest hub) | 2.27× |
| token reduction — max (trivial 1-dependent) | 2,295× |
| token reduction — mean | 135.9× *(outlier-inflated — see note)* |
| **impact recall — transitive (GBRG)** | **100.0%** |
| impact recall — direct-only (depth-1) | 37.7% |
| graph completeness | xfile calls resolved 136, ambiguous 80, external 670; TESTED_BY edges 128 |

Hardest case: `cell_iri_to_node_id` (21 transitive dependents) — minimal context is
still 9,110 tokens, so only **2.27×**. That is the honest floor for a hub function in
a small repo.

### Target 2 — `hg_analytics` (a larger real Rust crate; consume-only measurement)
~13,000 LOC, 38 files. **683 cells**, **575** scored, **372** reviewable.

| metric | value |
|---|---|
| FULL context | 342,108 chars ≈ **85,527 tokens** |
| targets (blast radius ≥ 1) | 234 |
| leaf cells (no dependents) | 138 |
| **token reduction — median** | **41.46×** |
| token reduction — min (hardest hub) | 1.40× |
| token reduction — max | 847× |
| token reduction — mean | 70.16× |
| **impact recall — transitive (GBRG)** | **100.0%** |
| impact recall — direct-only (depth-1) | 66.2% |
| graph completeness | xfile calls resolved 560, ambiguous 318, external 3,663; TESTED_BY edges 344 |

Hardest case: `len` (144 dependents) — a hub touched by most of the crate, so
minimal ≈ full and reduction is only **1.40×**. Honest: GBRG cannot shrink review
context for a change to a truly central symbol.

### Reading these numbers

- **Token reduction is repo-size-dependent.** Small repo → **median 4.1×**; a repo
  ~3× larger → **median 41.5×**. The ratio grows because FULL grows with the repo
  while a typical cell's blast radius does not. This is exactly why a small-repo
  number differs from a large-monorepo number — and why a headline "71×" only
  materialises on a large, loosely-coupled codebase.
- **The mean is outlier-inflated; the median is the honest headline.** Cells with a
  single small dependent produce four-digit ratios that drag the mean up. We lead
  with the **median** and the **min** (the hardest hub), not the mean or the max.
- **Recall is 100% by construction — and we say so.** GBRG's minimal selection *is*
  the graph's reverse-reachable set, so the transitive recall of 100% is a
  **completeness check on the CSR BFS** (nothing in the reverse-reachable set is
  dropped), not an independent discovery of impact. We compute it by explicit set
  membership so a regression that dropped a dependent would show < 100%.
- **The direct-only recall (37.7% / 66.2%) is where the metric has teeth.** It falls
  well below 100% whenever depth-≥2 dependents exist, proving the recall measurement
  is falsifiable and justifying why GBRG selects the *transitive* radius.
- **The real bound on recall is graph completeness, not the BFS.** The analyzer's own
  counters show many call sites are `ambiguous` (a common name like `len`/`new`
  defined in several files — never fabricated into an edge) or `external`. Those
  unresolved edges mean the graph may **undercount** true dependents, so recall
  against an *external* oracle (real execution / a complete call graph) would be
  ≤ 100%. GBRG is deliberately conservative here (it never invents an edge), and the
  counters are surfaced rather than hidden.

---

## NON-CLAIM BOX 🔴

- These numbers are **repo-size-dependent**. The 4.1×–41.5× median band above is a
  property of *these specific repos at their measured sizes*, not a universal figure.
- This benchmark **does NOT claim to beat, match, or reproduce** code-review-graph's
  published **71.4× / 100%** figures. Their methodology, repo, tokenizer, and
  favorable-case selection are **unverified by us**; comparing our honest medians to
  their headline would be apples-to-oranges. We deliberately did **not** tune the
  target, the sample, or the token method to manufacture parity.
- The **100% transitive recall is true by construction** (the selector and the oracle
  read the same graph). It certifies that GBRG's context selection is *complete with
  respect to its own dependency graph* — it is **not** a claim of perfect real-world
  impact discovery. Graph completeness (unresolved ambiguous/external edges) is the
  real limiter and is reported alongside every run.
- **GBRG's differentiator is governed provenance, not token-reduction supremacy.**
  Every selected cell carries an `epistemicLevel` (`empirical` / `bounded` /
  `speculative` / `rejected`) and a `ProofArtifact` explaining *why* it is in (or out
  of) the review context. The value is an **auditable, provenance-carrying** blast
  radius — a reviewer knows which included cells are test-covered vs merely
  speculated. Token reduction is a welcome side effect of a correct dependency graph,
  not the headline.

---

## Real vs stub

**Everything measured here is real.** The harness runs the real tree-sitter parse,
the real cross-file resolution, the real HellGraph ingest + `freeze()`, and the real
`transitive_dependents` / `reverse_dependents` reads. No number is stubbed,
hardcoded, or sampled to flatter. The only stubs in the wider GBRG tree
(`gbrg-napi` bodies, the `gbrg/mcp` tool bodies) are **not** on this measurement path.

## Reproduce

```sh
cd gbrg
cargo build -p gbrg-benchmark --release
# Dogfood target (this repo's own crates):
./target/release/gbrg-benchmark crates --json benchmark/results-gbrg-crates.json
# A larger target, to see the ratio scale with repo size:
./target/release/gbrg-benchmark <path-to-larger-rust-crate> --json out.json
```

Flags: `--divisor N` (chars-per-token, default 4; ratio is divisor-independent),
`--top N` (rows in the hardest-cases table), `--json <path>` (full machine report).

Captured machine reports live beside this file:
`results-gbrg-crates.json`, `results-hg-analytics.json`.
