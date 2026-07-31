//! # gbrg-core — Governed Blast-Radius Graph (core model)
//!
//! GBRG models a codebase as a semantic graph so that the *blast radius* of a
//! change (what depends on a cell, transitively, and whether tests reach it) can
//! be answered with a provenance-carrying [`ProofArtifact`]-shaped result.
//!
//! ## Substrate: `hg_analytics::graphdb` (consume-only)
//! We build ON TOP OF hellgraph's `hg_analytics` crate and never edit it. The
//! `graphdb` model was chosen over `hg_core` / `hg_kernel` because it gives us
//! exactly the primitives GBRG needs at this layer:
//!   * a mutable [`Store`] with an append-only WAL (`add_node`, `add_edge`,
//!     `set_prop`),
//!   * a `freeze()` step to a read-optimised [`GraphIndex`] (dense CSR), and
//!   * the [`GraphCore`] traversal surface (`in_degree`, `in_neighbors`, plus
//!     raw `in_off`/`in_nbr` slices we can feed to [`bfs_on_csr`]).
//! See `docs/ADR-001-gbrg-architecture.md`.
//!
//! ## Data-model mapping notes
//! * A node in `graphdb` is a bare `NodeId (u64)` — there is NO native label or
//!   type field on a node. So a [`SemanticCell`]'s `kind` and every other
//!   attribute is stored as a node **property** via `Store::set_prop`.
//! * `NodeId` is derived **deterministically** from a stable code IRI (see
//!   [`cell_iri_to_node_id`]) so the same symbol always maps to the same node.
//! * `graphdb` **properties are node-scoped** — an edge cannot carry a property.
//!   Therefore an edge's `weight` is held in an explicit side map
//!   ([`EdgeWeights`]) keyed by `(from, to, label)`, NOT as a graph property.
//!   (Decision recorded in ADR-001.)

use std::collections::HashMap;
use std::io;

// Everything below comes from the consumed hellgraph crate. We never redefine it.
use hg_analytics::{bfs_on_csr, sha256_hex, GraphCore, GraphIndex, NodeId, Prop, Store};

// ---------------------------------------------------------------------------
// Scoring differentiator: blast-radius normalisation, epistemicLevel derivation,
// and ProofArtifact emission. This is the governance-native output layer that
// replaces the former `blast_radius_score` `todo!()`.
// ---------------------------------------------------------------------------
pub mod scoring;
pub use scoring::{
    blast_radius_score, build_proof_artifact, churn_frequency, code_dependents_count,
    derive_epistemic_level, emit_proof_artifact, BlastRadiusInputs, BlastRadiusProofArtifact,
    EpistemicLevel, ProofClaim, ScoringConfig, DECLARED_BY,
};

// ---------------------------------------------------------------------------
// Containment: governed sever / residual-reachability. Topology-agnostic — the
// same reads serve code-impact blast radius AND network-endpoint isolation.
// ---------------------------------------------------------------------------
pub mod containment;
pub use containment::{
    build_containment_artifact, emit_containment_artifact, reachable_set, sever_residual,
    ContainmentProofArtifact, ContainmentReading, Direction, SeverScope, CONTAINMENT_DECLARED_BY,
};

// ---------------------------------------------------------------------------
// Node property keys (namespaced to avoid clashes with other graphdb users).
// ---------------------------------------------------------------------------
/// Property key under which a cell's [`CellKind`] is stored (as `Prop::Text`).
pub const PROP_KIND: &str = "gbrg.kind";
pub const PROP_LANGUAGE: &str = "gbrg.language";
pub const PROP_FILE_PATH: &str = "gbrg.file_path";
pub const PROP_SYMBOL: &str = "gbrg.symbol_name";
pub const PROP_AST_HASH: &str = "gbrg.ast_hash";
pub const PROP_CELL_ID: &str = "gbrg.cell_id";
pub const PROP_LOC_START: &str = "gbrg.loc_start";
pub const PROP_LOC_END: &str = "gbrg.loc_end";
pub const PROP_GENERATED: &str = "gbrg.generated";

// ---------------------------------------------------------------------------
// Cell kind
// ---------------------------------------------------------------------------

/// The syntactic role of a [`SemanticCell`].
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum CellKind {
    Function,
    Class,
    Import,
    Module,
}

impl CellKind {
    /// Stable string form persisted as the `gbrg.kind` node property and used in
    /// the JSON contracts (`contracts/semantic-cell.schema.json`).
    pub fn as_str(&self) -> &'static str {
        match self {
            CellKind::Function => "function",
            CellKind::Class => "class",
            CellKind::Import => "import",
            CellKind::Module => "module",
        }
    }
}

// ---------------------------------------------------------------------------
// SemanticCell
// ---------------------------------------------------------------------------

/// A unit of code (function / class / import / module) — one node in the GBRG.
///
/// `cell_id` is expected to be a **stable code IRI** (e.g.
/// `code://rust/src/foo.rs#bar`). The graph `NodeId` is derived from it
/// deterministically by [`SemanticCell::node_id`].
#[derive(Clone, Debug, PartialEq)]
pub struct SemanticCell {
    /// Stable code IRI. Hashed to the graph `NodeId`.
    pub cell_id: String,
    pub kind: CellKind,
    pub language: String,
    pub file_path: String,
    pub symbol_name: String,
    /// sha256 hex of the cell's AST/source slice (see [`ast_hash_of`]).
    pub ast_hash: String,
    pub loc_start: u32,
    pub loc_end: u32,
    /// True if this cell is machine-generated (codegen). This is the estate's
    /// `generated` concept and is INDEPENDENT of the `synthetic` epistemic level
    /// (which means synthetic *data*, never "auto-generated code"). See ADR-001.
    pub generated: bool,
}

impl SemanticCell {
    /// Deterministic `cell_id (IRI)` -> `NodeId (u64)` mapping.
    pub fn node_id(&self) -> NodeId {
        cell_iri_to_node_id(&self.cell_id)
    }
}

/// Deterministic mapping from a stable code IRI to a `graphdb` `NodeId`.
///
/// Definition: the first 8 bytes (16 hex chars) of `sha256(iri)` interpreted as
/// a big-endian `u64`. Stable across runs and machines; collision probability is
/// negligible for realistic cell counts.
pub fn cell_iri_to_node_id(iri: &str) -> NodeId {
    let hex = sha256_hex(iri.as_bytes());
    // sha256_hex always returns 64 lowercase hex chars, so [..16] is safe.
    u64::from_str_radix(&hex[..16], 16).expect("sha256_hex returns valid hex")
}

/// Convenience: sha256-hex an AST/source byte slice for [`SemanticCell::ast_hash`].
pub fn ast_hash_of(bytes: &[u8]) -> String {
    sha256_hex(bytes)
}

// ---------------------------------------------------------------------------
// GraphEdge
// ---------------------------------------------------------------------------

/// The typed relationship between two cells.
///
/// Convention (blast-radius orientation): `from` DEPENDS ON `to`. So for a call
/// `B -> A` (B calls A), `from = B`, `to = A`. Then A's **dependents** are its
/// in-neighbors, and `in_degree(A)` counts how many cells would be impacted if A
/// changed.
#[derive(Clone, Debug, PartialEq)]
pub enum EdgeKind {
    Calls,
    Inherits,
    Imports,
    TestedBy,
    ChurnsWith,
}

impl EdgeKind {
    /// The `graphdb` edge label string used for this kind.
    pub fn as_label(&self) -> &'static str {
        match self {
            EdgeKind::Calls => "CALLS",
            EdgeKind::Inherits => "INHERITS",
            EdgeKind::Imports => "IMPORTS",
            EdgeKind::TestedBy => "TESTED_BY",
            EdgeKind::ChurnsWith => "CHURNS_WITH",
        }
    }
}

/// A typed, weighted edge. `weight` is NOT stored on the graph (graphdb props are
/// node-scoped); persist it via [`EdgeWeights`].
#[derive(Clone, Debug, PartialEq)]
pub struct GraphEdge {
    pub from: NodeId,
    pub to: NodeId,
    pub kind: EdgeKind,
    pub weight: f64,
}

/// Explicit side map for edge weights, keyed by `(from, to, label)`.
///
/// This is GBRG's answer to "graphdb has no edge properties": rather than reify
/// every edge as a node, we keep weights in this compact companion structure
/// alongside the frozen index. (Alternative considered — edge reification — is
/// documented and rejected for the common case in ADR-001.)
#[derive(Clone, Debug, Default)]
pub struct EdgeWeights {
    map: HashMap<(NodeId, NodeId, String), f64>,
}

impl EdgeWeights {
    pub fn new() -> Self {
        Self::default()
    }

    /// Record (or overwrite) the weight for `edge`'s `(from, to, label)` key.
    pub fn set(&mut self, edge: &GraphEdge) {
        self.map
            .insert((edge.from, edge.to, edge.kind.as_label().to_string()), edge.weight);
    }

    /// Look up the weight for a `(from, to, label)` triple.
    pub fn get(&self, from: NodeId, to: NodeId, label: &str) -> Option<f64> {
        self.map.get(&(from, to, label.to_string())).copied()
    }

    pub fn len(&self) -> usize {
        self.map.len()
    }

    pub fn is_empty(&self) -> bool {
        self.map.is_empty()
    }
}

// ---------------------------------------------------------------------------
// Write path (REAL — exercised by tests/smoke.rs)
// ---------------------------------------------------------------------------

/// Write a [`SemanticCell`] into the store: add its node, then persist every
/// attribute as a node property. Returns the derived `NodeId`.
pub fn write_cell(store: &mut Store, cell: &SemanticCell) -> io::Result<NodeId> {
    let id = cell.node_id();
    store.add_node(id)?;
    store.set_prop(id, PROP_KIND, Prop::Text(cell.kind.as_str().to_string()))?;
    store.set_prop(id, PROP_LANGUAGE, Prop::Text(cell.language.clone()))?;
    store.set_prop(id, PROP_FILE_PATH, Prop::Text(cell.file_path.clone()))?;
    store.set_prop(id, PROP_SYMBOL, Prop::Text(cell.symbol_name.clone()))?;
    store.set_prop(id, PROP_AST_HASH, Prop::Text(cell.ast_hash.clone()))?;
    store.set_prop(id, PROP_CELL_ID, Prop::Text(cell.cell_id.clone()))?;
    store.set_prop(id, PROP_LOC_START, Prop::Int(cell.loc_start as i64))?;
    store.set_prop(id, PROP_LOC_END, Prop::Int(cell.loc_end as i64))?;
    store.set_prop(id, PROP_GENERATED, Prop::Bool(cell.generated))?;
    Ok(id)
}

/// Write a [`GraphEdge`] into the store as a labelled graphdb edge.
///
/// PRECONDITION: both endpoints must already exist (write their cells first).
/// `weight` is intentionally not written here — record it in [`EdgeWeights`].
pub fn write_edge(store: &mut Store, edge: &GraphEdge) -> io::Result<()> {
    store.add_edge(edge.from, edge.to, edge.kind.as_label())?;
    Ok(())
}

// ---------------------------------------------------------------------------
// Blast-radius reads (REAL — over a frozen GraphIndex)
// ---------------------------------------------------------------------------

/// Number of **direct** dependents of `cell` = its in-degree in the frozen index.
/// `None` if the cell is not present in the index.
pub fn dependents_count(index: &GraphIndex, cell: NodeId) -> Option<u32> {
    index.dense(cell).map(|d| index.in_degree(d))
}

/// Direct dependents (in-neighbors) of `cell`, optionally filtered by edge
/// `label`. Dense indices returned by `GraphCore::in_neighbors` are mapped back
/// to `NodeId`s. Empty if the cell (or label) is absent.
pub fn reverse_dependents(index: &GraphIndex, cell: NodeId, label: Option<&str>) -> Vec<NodeId> {
    match index.dense(cell) {
        None => Vec::new(),
        Some(d) => index
            .in_neighbors(d, label)
            .iter()
            .map(|&nd| index.original(nd))
            .collect(),
    }
}

/// **Transitive** blast radius: every cell reachable from `cell` by walking
/// in-edges (dependents, dependents-of-dependents, ...). Implemented for real by
/// feeding the index's IN-CSR (`in_off`/`in_nbr`) into [`bfs_on_csr`]. Excludes
/// `cell` itself. Note: this ignores edge labels (BFS is over all in-edges); a
/// label-scoped transitive walk is a future refinement.
pub fn transitive_dependents(index: &GraphIndex, cell: NodeId) -> Vec<NodeId> {
    let n = index.node_count();
    let src = match index.dense(cell) {
        Some(d) => d as usize,
        None => return Vec::new(),
    };
    let dist = bfs_on_csr(n, index.in_off(), index.in_nbr(), src);
    (0..n)
        .filter(|&i| i != src && dist[i] != u32::MAX)
        .map(|i| index.original(i as u32))
        .collect()
}

/// Whether `cell` is reached by at least one test (an incoming `TESTED_BY` edge).
pub fn test_coverage_reach(index: &GraphIndex, cell: NodeId) -> bool {
    !reverse_dependents(index, cell, Some(EdgeKind::TestedBy.as_label())).is_empty()
}

// NOTE: `blast_radius_score` (the normalised 0.0..=1.0 curve) previously lived
// here as a `todo!()`. It is now REAL and lives in [`mod scoring`]
// (`scoring::blast_radius_score`), re-exported at the crate root above. See that
// module for the documented normalisation curve and the SCOPE-D precedents it
// inherits.
