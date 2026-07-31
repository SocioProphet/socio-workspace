# ADR-001 — GBRG (Governed Blast-Radius Graph) architecture

Status: Accepted (skeleton)
Date: 2026-07-30
Scope: `gbrg/` spine — a compiling skeleton with pinned contracts, not a full implementation.

## Context

GBRG answers "if this code cell changes, what is the blast radius?" as a
governed, provenance-carrying result — a ProofArtifact, not a bare number. It is
built as a self-contained Cargo workspace + pnpm package so it can later be
extracted to a standalone repo.

## Decisions

### 1. Language map (one job per layer)
- **Rust core (`gbrg-core`)** — the data model and graph reads. All load-bearing
  logic lives here.
- **`gbrg-napi` bridge** — a `cdylib` N-API crate exposing `gbrg-core` to Node.
  Thin; returns ProofArtifact JSON strings.
- **TS MCP (`gbrg/mcp`)** — the agent-facing MCP server. Tools return
  ProofArtifact objects.
- **Python governance** — (future) policy/gate layer that consumes ProofArtifacts.

### 2. Consume hellgraph, never edit it
`gbrg-core` depends on `hg_analytics` by **path** and treats it as read-only. We
do not edit, and do not add files to, hellgraph (or hellgraph-rust, SCOPE-D,
agent-registry, synapseiq).

Why `graphdb` (inside `hg_analytics`) over `hg_core` / `hg_kernel`:
- `graphdb` gives exactly the primitives GBRG needs at this layer — a mutable
  `Store` (append-only WAL: `add_node`/`add_edge`/`set_prop`), a `freeze()` to a
  read-optimised dense-CSR `GraphIndex`, and the `GraphCore` traversal trait
  (`in_degree`, `in_neighbors`, and raw `in_off`/`in_nbr` slices).
- `hg_core` is the lower storage/fieldpack substrate; `hg_kernel` is the
  proof/runtime kernel. Neither exposes the labelled-property-graph read surface
  GBRG wants, and pulling them in would couple GBRG to internals it should not
  see. `graphdb` is the right altitude.

### 3. SemanticCell → NodeId mapping (deterministic)
A `graphdb` node is a bare `NodeId (u64)` — there is **no native label/type
field**. So a cell's `kind`, language, file_path, symbol_name, ast_hash,
loc_start/loc_end, and `generated` flag are all stored as node **properties**
(`Store::set_prop`, `Prop::Text`/`Int`/`Bool`).

`cell_id` is a **stable code IRI** (e.g. `code://rust/src/lib.rs#foo`). The
NodeId is derived deterministically as `u64::from_be(first 8 bytes of
sha256(cell_id))` (implemented via the exported `hg_analytics::sha256_hex`, first
16 hex chars). Same symbol ⇒ same node, across runs and machines.

### 4. Edge-weight modeling (side map, NOT a graph property)
`graphdb` properties are **node-scoped**; an edge cannot carry a property. So an
edge's `weight` is held in an explicit companion structure,
`gbrg_core::EdgeWeights`, a `HashMap<(from, to, label), f64>`.

Alternative considered and rejected for the common case: **reifying** each edge
as its own node (so weight becomes a node property). Rejected because it doubles
node count, distorts `in_degree`/`in_neighbors` blast-radius reads (the metric we
most care about), and complicates traversal. The side map keeps the graph reads
honest; reification remains available for the rare edge that needs rich,
queryable attributes.

### 5. `synthetic` → `generated` correction (semantic guard)
In the estate, the ProofArtifact `epistemicLevel: "synthetic"` means
**synthetic / not-real DATA**. It must NOT be overloaded to mean
"auto-generated code". Auto-generated/codegen cells are flagged by a **separate
`generated: bool`** — on `SemanticCell` and on the blast-radius ProofArtifact.
The `epistemicLevel` enum is inherited **verbatim** from SCOPE-D and is not
extended. This rule is pinned in `$comment`s in
`contracts/blast-radius-proof-artifact.schema.json` and
`contracts/semantic-cell.schema.json`.

### 6. `blast_radius` numeric scale = 0.0–1.0 float
The ProofArtifact's `blast_radius` is a normalised float in `[0.0, 1.0]` so it
can feed SCOPE-D's `computeRiskScore` directly. The raw inputs
(`dependents_count`, `churn_frequency`, `test_coverage_reach`) are carried
un-normalised alongside it. The exact normalisation curve is not yet settled —
`gbrg_core::blast_radius_score` is currently a `todo!()` stub; every other read
is real.

### 7. ProofArtifact inheritance from SCOPE-D
`contracts/blast-radius-proof-artifact.schema.json` extends SCOPE-D's
ProofArtifact and cites the source path
(`/Users/michaelheller/dev/SCOPE-D/config/schemas/proof-artifact.schema.json`) in
a `$comment`. The `epistemicLevel` enum is copied verbatim:
`["proved","bounded","empirical","synthetic","speculative","rejected"]`. Added
GBRG fields: `dependents_count`, `test_coverage_reach`, `churn_frequency`,
`blast_radius`, `derivation`, `declared_by` (pattern `^agent-registry://`),
`generated`.

### 8. Path-dep → git-dep follow-up
For THIS skeleton, `gbrg-core` depends on `hg_analytics` by a relative **path**
(resolving to `/Users/michaelheller/dev/hellgraph-rust/crates/hg_analytics`) so
it compiles locally. The merge-ready form should become a **pinned GIT
dependency** (`{ git = "...", rev = "<sha>" }`) for portability once GBRG is
extracted. Recorded in `gbrg-core/Cargo.toml`.

### 9. Parser will be REAL tree-sitter
Cell extraction will use **real tree-sitter** grammars per language — not a
regex/heuristic parser. `synapseiq` is a TypeScript/JavaScript **LSP assist**
only; it is NOT tree-sitter and is not the cell parser. (synapseiq is
consume-only if referenced at all.)

## Consequences
- `gbrg-core` compiles and its smoke test passes against the external
  `hg_analytics` path dep (the linchpin proof).
- `gbrg-napi` and `gbrg/mcp` are well-formed skeletons; their build is deferred
  (napi toolchain / npm network may be unavailable in-sandbox).
- The `synthetic` vs `generated` distinction is enforced by schema `$comment`s
  and mirrored in the TS types.
