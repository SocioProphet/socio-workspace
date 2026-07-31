//! # what-if — deterministic *recompute-and-diff* over a hypothetically-edited graph
//!
//! 🔴 HONESTY (read this first). This module is **NOT** counterfactual causal
//! inference. It does **not** implement Pearl's do-operator, adjust for
//! confounders, estimate treatment effects, or reason about unobserved causes. It
//! does exactly one, fully deterministic, fully auditable thing:
//!
//! 1. take the CURRENT (baseline) GBRG graph and score a target cell into a
//!    [`BlastRadiusProofArtifact`] (`before`);
//! 2. make an **in-memory COPY** of the graph, apply a concrete, syntactic
//!    hypothetical edit to the COPY (never the baseline), re-freeze it, and re-run
//!    the SAME scoring path over the edited copy (`after`);
//! 3. **diff** `after` against `before` and report the change.
//!
//! So "what-if I added a test?" is answered by *literally adding a synthetic
//! `TESTED_BY` edge to a throwaway copy of the graph and recomputing the blast
//! radius*, then subtracting. There is no model of causation here — only the same
//! scoring function [`crate::emit_proof_artifact`] applied to two graphs (the real
//! one and an edited clone) and the arithmetic difference of the two results. The
//! delta is a **recomputation delta**, not an estimated causal effect. Anyone
//! reading `after` should read it as "this is what the deterministic score WOULD
//! print if the graph actually looked like this", nothing stronger.
//!
//! The baseline graph is guaranteed untouched: every mutation is applied to a
//! `clone()` of the cells/edges, and [`WhatIfGraph`] exposes [`WhatIfGraph::score_cell`]
//! so a caller can re-score the baseline after a what-if and confirm it is
//! byte-for-byte identical (the `tests/whatif.rs` real test does exactly this).

use std::io;

use serde::Serialize;

use crate::{
    emit_proof_artifact, write_cell, write_edge, BlastRadiusProofArtifact, CellKind, EdgeKind,
    EpistemicLevel, GraphEdge, ScoringConfig, SemanticCell,
};
use hg_analytics::{GraphIndex, NodeId, Store};

// ---------------------------------------------------------------------------
// Mutation — the hypothetical, syntactic edits we can apply to a graph copy.
// ---------------------------------------------------------------------------

/// A concrete, syntactic edit applied to an **in-memory copy** of the graph.
///
/// These are graph edits, not causal interventions: each names an exact
/// structural change (add an edge / drop an edge) whose effect on the score is
/// then recomputed deterministically. See the module-level honesty note.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Mutation {
    /// Hypothesise that a test now reaches the target cell: add a synthetic
    /// `TESTED_BY` in-edge (from a synthetic test node) into the copy. On recompute
    /// this flips `test_coverage_reach` to `true`, which is exactly what a real test
    /// would do.
    AddTests,
    /// Hypothesise that one caller is removed: drop a single incoming `CALLS` edge
    /// to the target cell in the copy. On recompute this lowers `dependents_count`
    /// by one.
    RemoveDependent,
}

impl Mutation {
    /// Stable string form (matches the serde `snake_case` and the CLI flag values).
    pub fn as_str(&self) -> &'static str {
        match self {
            Mutation::AddTests => "add_tests",
            Mutation::RemoveDependent => "remove_dependent",
        }
    }

    /// Parse the CLI flag value (`add_tests` | `remove_dependent`).
    pub fn parse(s: &str) -> Option<Self> {
        match s.trim().to_ascii_lowercase().as_str() {
            "add_tests" | "add-tests" | "addtests" => Some(Mutation::AddTests),
            "remove_dependent" | "remove-dependent" | "removedependent" => {
                Some(Mutation::RemoveDependent)
            }
            _ => None,
        }
    }
}

// ---------------------------------------------------------------------------
// Errors.
// ---------------------------------------------------------------------------

/// Everything a what-if run can refuse to do.
#[derive(Debug)]
pub enum WhatIfError {
    /// No cell in the graph has the requested `cell_id`.
    CellNotFound(String),
    /// A `hg_analytics` write (`add_node`/`add_edge`/`set_prop`) failed while
    /// (re)building an index.
    Io(io::Error),
}

impl std::fmt::Display for WhatIfError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            WhatIfError::CellNotFound(id) => {
                write!(f, "cell not found in graph: {id}")
            }
            WhatIfError::Io(e) => write!(f, "graph (re)build error: {e}"),
        }
    }
}

impl std::error::Error for WhatIfError {}

impl From<io::Error> for WhatIfError {
    fn from(e: io::Error) -> Self {
        WhatIfError::Io(e)
    }
}

// ---------------------------------------------------------------------------
// WhatIfGraph — an owned, editable snapshot of the GBRG (cells + edges).
// ---------------------------------------------------------------------------

/// An owned, **editable** in-memory representation of a GBRG graph: the full cell
/// list and the full edge list. This is deliberately a plain data copy (not the
/// frozen [`GraphIndex`], which is read-only CSR) so a hypothetical edit can be
/// applied and the graph re-frozen from scratch.
///
/// Building the graph from real source is the caller's job (e.g. `gbrg-analyze`
/// parses a path and hands the resolved cells + edges here); this crate only needs
/// the cells and edges to reconstruct an index and score.
#[derive(Clone, Debug)]
pub struct WhatIfGraph {
    cells: Vec<SemanticCell>,
    edges: Vec<GraphEdge>,
}

impl WhatIfGraph {
    /// Construct from a cell list and an edge list (as produced by the analyzer).
    pub fn new(cells: Vec<SemanticCell>, edges: Vec<GraphEdge>) -> Self {
        Self { cells, edges }
    }

    /// The cells in this graph.
    pub fn cells(&self) -> &[SemanticCell] {
        &self.cells
    }

    /// The edges in this graph.
    pub fn edges(&self) -> &[GraphEdge] {
        &self.edges
    }

    /// Look up a cell by its stable `cell_id` IRI.
    fn find_cell(&self, cell_id: &str) -> Option<&SemanticCell> {
        self.cells.iter().find(|c| c.cell_id == cell_id)
    }

    /// Build a frozen [`GraphIndex`] from a cell/edge slice pair. The returned index
    /// owns its data (the temporary [`Store`] is dropped), so it is safe to build
    /// two independent indices (baseline + edited) and diff their scores.
    ///
    /// Cells are deduped by `NodeId`; any edge whose endpoint was not written is
    /// skipped (never fabricated) so the graph stays sound — the same discipline the
    /// analyzer's ingest uses.
    fn build_index(cells: &[SemanticCell], edges: &[GraphEdge]) -> io::Result<GraphIndex> {
        let mut store = Store::memory(0);
        let mut written = std::collections::HashSet::new();
        for cell in cells {
            let id = write_cell(&mut store, cell)?;
            written.insert(id);
        }
        for edge in edges {
            if written.contains(&edge.from) && written.contains(&edge.to) {
                write_edge(&mut store, edge)?;
            }
        }
        Ok(store.freeze())
    }

    /// Score a single cell against the CURRENT (unmodified) graph. Used for the
    /// baseline `before` and by tests to prove the baseline is untouched after a
    /// what-if (re-scoring must return an identical artifact).
    pub fn score_cell(
        &self,
        cell_id: &str,
        churn: f64,
        dead: bool,
        config: &ScoringConfig,
    ) -> Result<BlastRadiusProofArtifact, WhatIfError> {
        let cell = self
            .find_cell(cell_id)
            .ok_or_else(|| WhatIfError::CellNotFound(cell_id.to_string()))?
            .clone();
        let index = Self::build_index(&self.cells, &self.edges)?;
        Ok(emit_proof_artifact(&cell, &index, churn, dead, config))
    }
}

// ---------------------------------------------------------------------------
// Result types.
// ---------------------------------------------------------------------------

/// A compact scoring snapshot (`before` / `after`), lifted from a full
/// [`BlastRadiusProofArtifact`].
#[derive(Clone, Debug, Serialize)]
pub struct WhatIfSnapshot {
    #[serde(rename = "epistemicLevel")]
    pub epistemic_level: EpistemicLevel,
    /// Coarse SCOPE-D status (`PROVED`/`BOUNDED`/`INCONCLUSIVE`/…).
    pub status: String,
    pub blast_radius: f64,
    pub dependents_count: u32,
    pub test_coverage_reach: bool,
    pub derivation: String,
}

impl WhatIfSnapshot {
    fn from_artifact(a: &BlastRadiusProofArtifact) -> Self {
        Self {
            epistemic_level: a.claim.epistemic_level,
            status: a.status.clone(),
            blast_radius: a.blast_radius,
            dependents_count: a.dependents_count,
            test_coverage_reach: a.test_coverage_reach,
            derivation: a.derivation.clone(),
        }
    }
}

/// The recomputation delta (`after` − `before`). These are arithmetic differences
/// of two deterministic scores, **not** estimated causal effects.
#[derive(Clone, Debug, Serialize)]
pub struct WhatIfDelta {
    /// `after.blast_radius - before.blast_radius` (negative = the edit shrinks blast
    /// radius).
    pub blast_radius_change: f64,
    /// Human-readable epistemic transition, e.g. `"speculative→empirical"` or
    /// `"empirical (unchanged)"`.
    #[serde(rename = "epistemicLevel_change")]
    pub epistemic_level_change: String,
}

/// The full what-if verdict for one (cell, mutation) pair.
#[derive(Clone, Debug, Serialize)]
pub struct WhatIfResult {
    /// The scored cell's stable IRI.
    pub cell_id: String,
    /// The hypothetical edit that was applied to the graph copy.
    pub mutation: Mutation,
    /// Baseline score (real graph).
    pub before: WhatIfSnapshot,
    /// Score after the hypothetical edit (edited copy).
    pub after: WhatIfSnapshot,
    /// `after` − `before`.
    pub delta: WhatIfDelta,
    /// One-line human summary, e.g.
    /// `"IF add_tests: speculative→empirical, blast 0.25→0.05"`.
    pub summary: String,
    /// Whether the edit actually changed the graph. `false` is honest, not an error:
    /// e.g. `remove_dependent` on a cell that has no incoming `CALLS` edge, or
    /// `add_tests` on an already-tested cell — the recompute then equals the
    /// baseline and `delta` is zero.
    pub applied: bool,
    /// What the mutation did (or why it was a no-op) — auditable provenance.
    pub note: String,
    /// 🔴 Honesty banner carried in the machine output itself.
    pub method: String,
}

impl WhatIfResult {
    /// Serialise to a JSON string.
    pub fn to_json(&self) -> serde_json::Result<String> {
        serde_json::to_string(self)
    }
    /// Serialise to a pretty JSON string.
    pub fn to_json_pretty(&self) -> serde_json::Result<String> {
        serde_json::to_string_pretty(self)
    }
}

/// The honesty banner embedded in every [`WhatIfResult::method`].
pub const WHATIF_METHOD: &str =
    "deterministic recompute-and-diff over an in-memory-edited graph copy; \
     NOT counterfactual causal inference (no do-operator / confounders / Pearl)";

// ---------------------------------------------------------------------------
// The what-if computation.
// ---------------------------------------------------------------------------

/// Recompute a target cell's [`BlastRadiusProofArtifact`] under a hypothetical
/// graph edit and diff it against the baseline.
///
/// `churn` and `dead` are held **constant** across `before` and `after` (the
/// mutations are purely topological — tests / dependents), so the reported delta is
/// attributable to the edit alone, not to a moving churn/dead input.
///
/// The baseline graph (`graph`) is never mutated: the edit is applied to a clone.
///
/// See the module honesty note — this is recompute-and-diff, not causal inference.
pub fn what_if(
    graph: &WhatIfGraph,
    cell_id: &str,
    mutation: Mutation,
    churn: f64,
    dead: bool,
    config: &ScoringConfig,
) -> Result<WhatIfResult, WhatIfError> {
    // --- Baseline (real graph). ---
    let target = graph
        .find_cell(cell_id)
        .ok_or_else(|| WhatIfError::CellNotFound(cell_id.to_string()))?
        .clone();
    let target_node = target.node_id();

    let baseline_index = WhatIfGraph::build_index(&graph.cells, &graph.edges)?;
    let before_art = emit_proof_artifact(&target, &baseline_index, churn, dead, config);

    // --- Apply the hypothetical edit to an IN-MEMORY COPY (baseline untouched). ---
    let mut cells = graph.cells.clone();
    let mut edges = graph.edges.clone();
    let (applied, note) = apply_mutation(&mut cells, &mut edges, &target, target_node, mutation);

    // --- Recompute over the edited copy. ---
    let edited_index = WhatIfGraph::build_index(&cells, &edges)?;
    let after_art = emit_proof_artifact(&target, &edited_index, churn, dead, config);

    // --- Diff. ---
    let before = WhatIfSnapshot::from_artifact(&before_art);
    let after = WhatIfSnapshot::from_artifact(&after_art);

    let level_change = if before.epistemic_level == after.epistemic_level {
        format!("{} (unchanged)", before.epistemic_level.as_str())
    } else {
        format!(
            "{}→{}",
            before.epistemic_level.as_str(),
            after.epistemic_level.as_str()
        )
    };
    let summary = format!(
        "IF {}: {}, blast {:.2}→{:.2}",
        mutation.as_str(),
        level_change,
        before.blast_radius,
        after.blast_radius
    );

    let delta = WhatIfDelta {
        blast_radius_change: after.blast_radius - before.blast_radius,
        epistemic_level_change: level_change,
    };

    Ok(WhatIfResult {
        cell_id: target.cell_id.clone(),
        mutation,
        before,
        after,
        delta,
        summary,
        applied,
        note,
        method: WHATIF_METHOD.to_string(),
    })
}

/// Apply `mutation` to the (already-cloned) `cells`/`edges`. Returns
/// `(applied, note)` where `applied` is `false` for a legitimate no-op (e.g. no
/// `CALLS` edge to drop, or the cell is already tested).
fn apply_mutation(
    cells: &mut Vec<SemanticCell>,
    edges: &mut Vec<GraphEdge>,
    target: &SemanticCell,
    target_node: NodeId,
    mutation: Mutation,
) -> (bool, String) {
    match mutation {
        Mutation::AddTests => {
            // Already tested? Adding another TESTED_BY edge changes nothing.
            let already_tested = edges
                .iter()
                .any(|e| e.to == target_node && e.kind == EdgeKind::TestedBy);
            if already_tested {
                return (
                    false,
                    "cell already has a TESTED_BY edge; adding another is a no-op \
                     (test_coverage_reach was already true)"
                        .to_string(),
                );
            }
            // Synthetic test node with a stable, obviously-synthetic IRI so it can
            // never collide with a real cell.
            let synth_iri = format!("code://whatif-synthetic/test#{}", target.cell_id);
            let synth = SemanticCell {
                cell_id: synth_iri,
                kind: CellKind::Function,
                language: target.language.clone(),
                file_path: "<whatif-synthetic-test>".to_string(),
                symbol_name: format!("whatif_test_for_{}", target.symbol_name),
                ast_hash: crate::ast_hash_of(b"whatif synthetic test"),
                loc_start: 0,
                loc_end: 0,
                generated: true,
            };
            let synth_node = synth.node_id();
            cells.push(synth);
            edges.push(GraphEdge {
                from: synth_node,
                to: target_node,
                kind: EdgeKind::TestedBy,
                weight: 1.0,
            });
            (
                true,
                "added one synthetic TESTED_BY edge into the target on the graph copy \
                 → test_coverage_reach recomputes to true"
                    .to_string(),
            )
        }
        Mutation::RemoveDependent => {
            // Drop the FIRST incoming CALLS edge to the target, if any.
            let pos = edges
                .iter()
                .position(|e| e.to == target_node && e.kind == EdgeKind::Calls);
            match pos {
                Some(i) => {
                    let removed = edges.remove(i);
                    (
                        true,
                        format!(
                            "dropped one incoming CALLS edge (from node {:#018x}) on the \
                             graph copy → dependents_count recomputes one lower",
                            removed.from
                        ),
                    )
                }
                None => (
                    false,
                    "target has no incoming CALLS edge to drop; recompute equals \
                     baseline (no-op)"
                        .to_string(),
                ),
            }
        }
    }
}
