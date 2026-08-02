# ADR-002 — `kind: pattern` SemanticCells (native regex-corpus ingest)

Status: Accepted
Date: 2026-08-02
Scope: `gbrg/contracts/semantic-cell.schema.json`, `gbrg-core::CellKind`.

## Context

The estate's REGEX corpus is published as a governed, catalog-ready dataset:
prophet-core-catalog `ds.regex-operational-dataset`
(`datasets/regex-operational-dataset/`, PR #5). Its blast-radius projection
(`gbrg-blast-radius.jsonl`) is already a bipartite graph shaped to drop directly
onto GBRG: one node per distinct regex, one node per first-party usage site, and
a "uses" edge from each code file to each pattern it depends on. See that
dataset's `SCHEMA.md` ("Blast-radius model").

Before this ADR, GBRG's `SemanticCell.kind` enum admitted only the four **code**
kinds (`function`, `class`, `import`, `module`), so a pattern node had no native
`kind` and the corpus could not be ingested without a lossy re-label. This ADR
seeds the convention so the dataset ingests natively.

## Decision

Add **`pattern`** as an additive fifth `SemanticCell` kind. A pattern cell is a
non-code node standing for one distinct regex from the corpus.

### 1. Pattern cell id form
```
cell_id : rx://rx-<sha1[0:10] of the raw pattern>     e.g. rx://rx-25ef703b14
```
The `rx-<sha1[0:10]>` fragment is the corpus record `id` (a stable content hash,
so the same regex across N repos collapses to ONE pattern node); the `rx://`
scheme distinguishes a pattern IRI from a `code://` cell IRI. Like every GBRG
cell, `cell_id` is hashed deterministically to a graphdb `NodeId` (first 8 bytes
of `sha256(cell_id)`) — see ADR-001 §3, no special-casing needed.

### 2. Pattern-usage edge = `imports`
```
code://<repo>/<file>  --imports-->  rx://<id>
```
A code-file cell **depends on** the pattern it uses, matching GBRG edge
orientation (`from` DEPENDS-ON `to`; ADR-001, graph-edge.schema.json). No new
edge kind is introduced — `imports` was already in the edge enum and is the
correct semantics for "this file pulls in / uses this pattern". A pattern node's
in-degree over `imports` edges is its blast radius (the corpus `use_count`).

### 3. `sources[]` is the native edge set
In the corpus, each pattern record's `sources[]` array **is** the edge set for
that pattern node: every `{repo, file, line}` element is one
`code://<repo>/<file> --imports--> rx://<id>` edge. Ingest is therefore
mechanical — no derivation, no join. The dataset's own `gbrg-blast-radius.jsonl`
pre-expands `sources[]` into explicit `GraphEdge` records (one per site).

### 4. Field-shape note (why this is convention, not a schema rewrite)
The corpus's `SemanticCell` projection is deliberately **lighter** than a code
cell — it carries governance/curation fields (`intent`, `category`,
`risk_class`, `redos_suspect`, `use_count`, `provider_reference`) instead of the
code-cell fields (`language`, `file_path`, `ast_hash`, `loc_start/loc_end`). This
ADR keeps the change **surgical**: it adds only the enum value (schema +
`CellKind`), leaving the four code kinds and their required fields untouched.
Reconciling the pattern projection's distinct required/optional field set into
`semantic-cell.schema.json` (e.g. a `kind`-conditional branch) is a documented
follow-up; it is not required for the corpus to be recognised as pattern cells.

## Consequences

- `kind: pattern` is a first-class, recognised SemanticCell kind in both the JSON
  contract and the Rust model (`CellKind::Pattern` ⇄ `"pattern"`).
- prophet-core-catalog `ds.regex-operational-dataset` /
  `gbrg-blast-radius.jsonl` maps onto GBRG with no re-labelling.
- Example: `contracts/examples/pattern-cell.example.jsonl` (one real
  cell + edge pair, verbatim from the dataset shape).
