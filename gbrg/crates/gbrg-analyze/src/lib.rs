//! # gbrg-analyze — the END-TO-END GBRG pipeline
//!
//! This crate is where the three GBRG feeders finally COMPOSE into one flow that
//! turns a real source file into governance-native [`BlastRadiusProofArtifact`]s:
//!
//! ```text
//!   source file
//!     │  gbrg_parser::parse_file            (tree-sitter → cells + edges)
//!     ▼
//!   ParseResult { cells, edges, … }
//!     │  gbrg_core::write_cell / write_edge (ingest into a HellGraph Store)
//!     ▼
//!   Store  ── freeze() ──▶  GraphIndex      (dense-CSR read model)
//!     │  gbrg_core::emit_proof_artifact     (dependents + test-reach off the index)
//!     ▼
//!   Vec<BlastRadiusProofArtifact>           (the money artifact)
//! ```
//!
//! Nothing here re-implements the model: [`gbrg_core`] owns the [`SemanticCell`] /
//! [`GraphEdge`] types, the write path and the scoring; [`gbrg_parser`] owns the
//! extraction. `gbrg-analyze` is pure glue plus a thin CLI ([`crate`]'s `main`).
//!
//! ## Honest edges (what is real vs. deferred)
//! * **Real:** the parse, the graph ingest, the `freeze()`, and the dependents /
//!   test-coverage reads that drive `epistemicLevel`.
//! * **Deferred (documented):** `churn_frequency` is passed as `0.0` by
//!   [`analyze_file`] — a from-parse-only analysis carries no git history, and the
//!   parser emits no `TESTED_BY` edges, so a purely-parsed function is `speculative`
//!   until coverage edges are supplied. `churn` and `dead` are first-class inputs to
//!   [`gbrg_core::emit_proof_artifact`]; a richer caller can supply real values via
//!   [`analyze_file_with`]. This crate keeps the from-parse defaults explicit rather
//!   than hiding them.

use std::collections::HashSet;
use std::io;
use std::path::Path;

use gbrg_core::{
    emit_proof_artifact, write_cell, write_edge, BlastRadiusProofArtifact, ScoringConfig,
};
use gbrg_parser::{parse_file, Language, ParseError, ParseResult};
// `NodeId` (a `u64`) is hg_analytics' own type; gbrg-core does not re-export it.
use hg_analytics::{NodeId, Store};

/// Everything that can go wrong end-to-end: parsing or the graph write path.
#[derive(Debug)]
pub enum AnalyzeError {
    /// The parser (tree-sitter) failed.
    Parse(ParseError),
    /// A `hg_analytics` write (`add_node` / `add_edge` / `set_prop`) failed.
    Io(io::Error),
}

impl std::fmt::Display for AnalyzeError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            AnalyzeError::Parse(e) => write!(f, "parse error: {e}"),
            AnalyzeError::Io(e) => write!(f, "graph write error: {e}"),
        }
    }
}

impl std::error::Error for AnalyzeError {}

impl From<ParseError> for AnalyzeError {
    fn from(e: ParseError) -> Self {
        AnalyzeError::Parse(e)
    }
}
impl From<io::Error> for AnalyzeError {
    fn from(e: io::Error) -> Self {
        AnalyzeError::Io(e)
    }
}

/// Per-run knobs beyond the scoring config: the churn and dead signals that the
/// parser cannot know from a single file. [`analyze_file`] uses the defaults
/// (`churn = 0.0`, `dead = false`); richer callers use [`analyze_file_with`].
#[derive(Clone, Copy, Debug)]
pub struct AnalyzeOptions {
    /// Historical change frequency (commits/day). From-parse default `0.0`.
    pub churn: f64,
    /// Whether the analysed cells are flagged dead. From-parse default `false`.
    pub dead: bool,
}

impl Default for AnalyzeOptions {
    fn default() -> Self {
        Self { churn: 0.0, dead: false }
    }
}

/// Parse `path`, ingest into a HellGraph [`Store`], `freeze()`, and emit one
/// [`BlastRadiusProofArtifact`] per (distinct) cell. This is the demoable spine.
///
/// `churn` is `0.0` and `dead` is `false` (see [`AnalyzeOptions`]); the dependents
/// and test-coverage evidence that drive `epistemicLevel` are REAL reads off the
/// frozen index.
pub fn analyze_file(
    path: impl AsRef<Path>,
    language: Language,
    config: &ScoringConfig,
) -> Result<Vec<BlastRadiusProofArtifact>, AnalyzeError> {
    analyze_file_with(path, language, config, AnalyzeOptions::default())
}

/// Like [`analyze_file`] but with explicit [`AnalyzeOptions`] (real churn / dead).
pub fn analyze_file_with(
    path: impl AsRef<Path>,
    language: Language,
    config: &ScoringConfig,
    opts: AnalyzeOptions,
) -> Result<Vec<BlastRadiusProofArtifact>, AnalyzeError> {
    // (1) PARSE — tree-sitter → cells + edges.
    let parsed: ParseResult = parse_file(path, language)?;

    // (2) INGEST — write cells then edges into an in-memory HellGraph Store via the
    // spine's existing write path. Dedupe cells by NodeId so a repeated IRI does
    // not produce a duplicate artifact; the CRDT Store tolerates re-adds, but the
    // OUTPUT should carry each cell once.
    let mut store = Store::memory(0);
    let mut written: HashSet<NodeId> = HashSet::new();
    let mut unique_cells = Vec::with_capacity(parsed.cells.len());
    for cell in &parsed.cells {
        let id = write_cell(&mut store, cell)?;
        if written.insert(id) {
            unique_cells.push(cell.clone());
        }
    }

    // write_edge's precondition is that both endpoints already exist. The parser
    // only resolves intra-file edges, so both endpoints are always among the cells
    // we just wrote — but we assert it defensively and skip (never fabricate) any
    // edge that would dangle, so the graph stays sound.
    let mut skipped_edges = 0usize;
    for edge in &parsed.edges {
        if written.contains(&edge.from) && written.contains(&edge.to) {
            write_edge(&mut store, edge)?;
        } else {
            skipped_edges += 1;
        }
    }
    debug_assert_eq!(
        skipped_edges, 0,
        "parser emitted an edge with an endpoint that was never written as a cell"
    );

    // (3) FREEZE — build the dense-CSR read index.
    let index = store.freeze();

    // (4) SCORE — emit a ProofArtifact per distinct cell, reading dependents and
    // test-reach off the frozen index (REAL), with the supplied churn/dead.
    let artifacts = unique_cells
        .iter()
        .map(|cell| emit_proof_artifact(cell, &index, opts.churn, opts.dead, config))
        .collect();

    Ok(artifacts)
}
