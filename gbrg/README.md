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
├── Cargo.toml                       # workspace (members: gbrg-core; excludes gbrg-napi)
├── crates/
│   ├── gbrg-core/                   # Rust core model + blast-radius reads (LOAD-BEARING)
│   │   ├── src/lib.rs               # SemanticCell, GraphEdge, write_/read_ API
│   │   └── tests/smoke.rs           # linchpin proof (in_degree == 2)
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

## Run the smoke test (the load-bearing proof)

```sh
cd gbrg/crates/gbrg-core
cargo test
```

Expected: `smoke_blast_radius_in_degree ... ok` — proves the full
`hg_analytics` path (write cells + edges → `freeze()` → `GraphCore::in_degree` /
`in_neighbors`) works from an external crate, with A having exactly 2 dependents.

## What is real vs. stub

- **Real:** the write path (`write_cell`/`write_edge`), `dependents_count`
  (in-degree), `reverse_dependents` (in-neighbors), `transitive_dependents`
  (`bfs_on_csr` over the in-CSR), `test_coverage_reach`, and the deterministic
  `cell_id → NodeId` mapping.
- **Real (containment):** `reachable_set` / `sever_residual` /
  `emit_containment_artifact` (module `containment`). Topology-agnostic
  sever/residual reachability — the same reads serve code-boundary severing
  (Upstream/dependents) and network host isolation (Downstream/reaches). Proven
  on both a code graph and a network-endpoint graph in `tests/containment.rs`,
  including that a real sever shrinks reachability and a no-op sever is
  downgraded to `speculative` rather than presented as clean containment.
- **Stub:** `blast_radius_score` (`todo!()` — normalisation curve pending),
  `gbrg-napi` bodies, and the `gbrg/mcp` tool bodies.

See `docs/ADR-001-gbrg-architecture.md` for the design decisions (why `graphdb`,
edge-weight side map, `synthetic` vs `generated`, 0.0–1.0 blast_radius scale, and
the path-dep → git-dep follow-up).
