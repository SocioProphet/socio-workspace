# GBRG — Governed Blast-Radius Graph

GBRG models a codebase as a semantic graph so the **blast radius** of a change
(what depends on a cell, transitively, and whether tests reach it) can be
answered as a governed, provenance-carrying **ProofArtifact** — never a bare
number.

It is built ON TOP OF hellgraph's `hg_analytics::graphdb` (consume-only; GBRG
never edits hellgraph) and is a self-contained Cargo workspace + pnpm package so
it can later be lifted into its own repo.

## Module layout

```
gbrg/
├── Cargo.toml                       # workspace (members: gbrg-core, gbrg-parser, gbrg-analyze; excludes gbrg-napi)
├── crates/
│   ├── gbrg-core/                   # Rust core model + blast-radius + containment reads (LOAD-BEARING)
│   │   ├── src/lib.rs               # SemanticCell, GraphEdge, write_/read_ API
│   │   ├── src/scoring.rs           # epistemicLevel derivation + blast_radius + ProofArtifact
│   │   ├── src/containment.rs       # reachable_set / sever_residual (governed isolation)
│   │   └── tests/                   # smoke, scoring, containment
│   ├── gbrg-parser/                 # tree-sitter cell + calls/imports/inherits edge extraction (Rust/Py/TS)
│   ├── gbrg-analyze/                # END-TO-END pipeline: parse → ingest → freeze → score → ProofArtifacts
│   └── gbrg-napi/                   # N-API bridge (cdylib) — skeleton, build deferred
├── mcp/                             # @socioprophet/gbrg-mcp TS MCP server — skeleton
│   └── src/server.ts               # impact_query / minimal_context_query / graph_status
├── contracts/                       # JSON Schema (draft 2020-12)
│   ├── semantic-cell.schema.json
│   ├── graph-edge.schema.json
│   ├── blast-radius-proof-artifact.schema.json   # extends SCOPE-D ProofArtifact
│   └── containment-proof-artifact.schema.json    # sever/residual reachability
└── docs/
    └── ADR-001-gbrg-architecture.md
```

## Run the tests (the load-bearing proof)

```sh
cd gbrg
cargo test
```

Expected: `smoke_blast_radius_in_degree ... ok` (the linchpin — proves the full
`hg_analytics` path works from an external crate, A having exactly 2 dependents),
plus the scoring, containment, parser, and end-to-end analyze/spectrum suites.

## What is real vs. stub

- **Real (core):** the write path (`write_cell`/`write_edge`), `dependents_count`
  (in-degree), `reverse_dependents` (in-neighbors), `transitive_dependents`
  (`bfs_on_csr` over the in-CSR), `test_coverage_reach`, and the deterministic
  `cell_id → NodeId` mapping.
- **Real (scoring):** `blast_radius_score` (normalised 0.0–1.0 curve),
  `derive_epistemic_level` (SCOPE-D enum), real git churn, and
  `emit_proof_artifact`.
- **Real (containment):** `reachable_set` / `sever_residual` /
  `emit_containment_artifact` (module `containment`). Topology-agnostic
  sever/residual reachability — the same reads serve code-boundary severing
  (Upstream/dependents) and network host isolation (Downstream/reaches). Proven
  on both a code graph and a network-endpoint graph in `tests/containment.rs`,
  including that a real sever shrinks reachability and a no-op sever is
  downgraded to `speculative` rather than presented as clean containment.
- **Real (parser):** `gbrg-parser` extracts cells + `CALLS`/`IMPORTS`/`INHERITS`
  edges from Rust/Python/TypeScript via tree-sitter (cross-file resolution is a
  documented follow-up; `unresolved_*` counts are surfaced).
- **Real (analyze):** `gbrg-analyze` is the end-to-end pipeline — parse a repo →
  ingest cells/edges → `freeze()` → score → emit ProofArtifacts across the full
  epistemicLevel spectrum (repo walk + `TESTED_BY` + real churn).
- **Stub:** `gbrg-napi` bodies and the `gbrg/mcp` tool bodies (both governed,
  provenance-shaped JSON) until the napi/MCP toolchains are wired.

See `docs/ADR-001-gbrg-architecture.md` for the design decisions (why `graphdb`,
edge-weight side map, `synthetic` vs `generated`, 0.0–1.0 blast_radius scale, and
the path-dep → git-dep follow-up).
