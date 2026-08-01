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

use std::collections::{HashMap, HashSet};
use std::io;
use std::path::{Path, PathBuf};

use gbrg_core::{
    cell_iri_to_node_id, churn_frequency, emit_proof_artifact, write_cell, write_edge,
    BlastRadiusProofArtifact, CellKind, EdgeKind, GraphEdge, ScoringConfig, SemanticCell,
    WhatIfGraph,
};
use gbrg_parser::{is_test_file, parse_file, Language, ParseError, ParseResult};
// `NodeId` (a `u64`) is hg_analytics' own type; gbrg-core does not re-export it.
use hg_analytics::{NodeId, Store};

/// Default git-history window (days) over which per-file `churn_frequency` is
/// measured by [`analyze_path`]. 90 days ≈ one quarter of activity.
pub const DEFAULT_CHURN_WINDOW_DAYS: u32 = 90;

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

// ===========================================================================
// REPO WALK — analyze_path: the multi-file spine that produces the FULL
// epistemicLevel spectrum. Single-file `analyze_file` cannot: a lone file has no
// cross-file callers and (crucially) no test file reaching into it, so every cell
// floors to `speculative`. `analyze_path` walks a whole tree, resolves the
// parser's per-file unresolved calls/inherits ACROSS files by symbol name, wires
// `TESTED_BY` edges from detected test files, and reads REAL per-file churn from
// git — so tested code derives `empirical`/`bounded` and untested code stays
// `speculative`.
// ===========================================================================

/// A repo-level analysis result: the scored artifacts plus honest counters about
/// what resolved, what stayed ambiguous, and how much test/churn signal was found.
/// The counters are the "prove it, don't assert it" surface — the CLI prints them.
#[derive(Clone, Debug, Default)]
pub struct AnalyzePathReport {
    /// One [`BlastRadiusProofArtifact`] per scored (non-test) cell.
    pub artifacts: Vec<BlastRadiusProofArtifact>,
    /// Source files successfully parsed.
    pub files_parsed: usize,
    /// Files classified as whole-file tests (Rust `tests/`, pytest, jest).
    pub test_files: usize,
    /// Distinct cells ingested into the graph (across all files).
    pub cells_total: usize,
    /// Cells actually scored (non-test cells; test cells are excluded).
    pub cells_scored: usize,
    /// Cells classified as test code and therefore excluded from scoring.
    pub test_cells: usize,
    /// Cross-file call sites resolved to a UNIQUE symbol (→ `CALLS`/`TESTED_BY`).
    pub xfile_calls_resolved: usize,
    /// Cross-file call sites left unresolved because the symbol was AMBIGUOUS
    /// (defined in >1 file) — never fabricated into an edge.
    pub xfile_calls_ambiguous: usize,
    /// Cross-file call sites whose symbol was defined nowhere in the tree
    /// (external / stdlib / third-party) — expected to be unresolved.
    pub xfile_calls_external: usize,
    /// Cross-file inheritance bases resolved to a unique symbol.
    pub xfile_inherits_resolved: usize,
    /// `TESTED_BY` edges written into the graph (intra- + cross-file).
    pub tested_by_edges: usize,
    /// Files with a non-zero git churn reading (proves churn wiring is real).
    pub churn_files_nonzero: usize,
    /// The distinct cells ingested (deduped by NodeId) — the exact node set of the
    /// scored graph. Exposed so `what-if` can rebuild an editable copy of the SAME
    /// graph the analyzer scored, rather than re-deriving it.
    pub cells: Vec<SemanticCell>,
    /// The edges actually written into the graph (both endpoints present; includes
    /// cross-file `CALLS`/`INHERITS`/`TESTED_BY`). Pairs with [`Self::cells`] to
    /// reconstruct the graph for `what-if`.
    pub edges: Vec<GraphEdge>,
    /// Per-file real git churn (commits/day), keyed by `file_path`. Lets `what-if`
    /// hold a target cell's REAL churn constant across before/after.
    pub churn_by_file: HashMap<String, f64>,
}

impl AnalyzePathReport {
    /// Count of scored artifacts at each `epistemicLevel` (the spectrum).
    pub fn level_spread(&self) -> Vec<(&'static str, usize)> {
        use std::collections::BTreeMap;
        let mut m: BTreeMap<&'static str, usize> = BTreeMap::new();
        for a in &self.artifacts {
            *m.entry(a.claim.epistemic_level.as_str()).or_insert(0) += 1;
        }
        m.into_iter().collect()
    }
}

/// Walk every supported source file under `root`, ingest the whole codebase as one
/// graph, and emit a [`BlastRadiusProofArtifact`] per non-test cell. This is the
/// deliverable that shows CONTRAST across `epistemicLevel`.
///
/// Convenience wrapper returning just the artifacts (matches the work-order
/// signature). Use [`analyze_path_report`] for the full evidence bundle.
pub fn analyze_path(
    root: impl AsRef<Path>,
    config: &ScoringConfig,
) -> Result<Vec<BlastRadiusProofArtifact>, AnalyzeError> {
    Ok(analyze_path_report(root, config, DEFAULT_CHURN_WINDOW_DAYS)?.artifacts)
}

/// The full repo walk. See module notes above.
///
/// ## Cross-file resolution rule (documented, honest)
/// After every file is parsed, all cells are known. Each *unresolved* call site the
/// parser surfaced (a callee not defined in the caller's own file) is resolved by
/// **simple symbol name** against a global table of every function cell:
/// * exactly **one** definition of that name in the whole tree → resolve to it
///   (a `TESTED_BY` edge if the caller is test code, else a `CALLS` edge);
/// * **zero** definitions → external/stdlib, left unresolved (counted);
/// * **two or more** definitions (a name like `as_str`/`new` defined in several
///   places) → AMBIGUOUS: we do NOT guess and never fabricate an edge (counted).
///
/// This is deliberately conservative: it recovers the unambiguous cross-file spine
/// (the common case, e.g. a test calling `emit_proof_artifact`) without inventing
/// edges for overloaded/duplicated names. Inheritance bases resolve the same way
/// against a global class-cell table. Remaining ambiguity is reported, not hidden.
pub fn analyze_path_report(
    root: impl AsRef<Path>,
    config: &ScoringConfig,
    churn_window_days: u32,
) -> Result<AnalyzePathReport, AnalyzeError> {
    let root = root.as_ref();
    let mut report = AnalyzePathReport::default();

    // (1) DISCOVER — every supported source file under `root`.
    let mut files: Vec<PathBuf> = Vec::new();
    collect_source_files(root, &mut files)?;
    files.sort();

    // (2) PARSE — each file into cells + edges + unresolved sites + test cells.
    let mut all_cells: Vec<SemanticCell> = Vec::new();
    let mut all_edges: Vec<GraphEdge> = Vec::new();
    let mut global_test_cells: HashSet<String> = HashSet::new();
    let mut test_file_paths: HashSet<String> = HashSet::new();
    // symbol_name -> distinct defining NodeIds (for cross-file resolution).
    let mut func_defs: HashMap<String, HashSet<NodeId>> = HashMap::new();
    let mut class_defs: HashMap<String, HashSet<NodeId>> = HashMap::new();
    // Deferred until all cells known: (caller_iri, callee_symbol, caller_is_test).
    let mut pending_xfile_calls: Vec<(String, String, bool)> = Vec::new();
    let mut pending_xfile_inherits: Vec<(String, String)> = Vec::new();
    // Per-file churn (keyed by the cell's file_path string).
    let mut churn_by_file: HashMap<String, f64> = HashMap::new();

    for path in &files {
        let language = match Language::from_path(path) {
            Some(l) => l,
            None => continue,
        };
        let parsed: ParseResult = parse_file(path, language)?;
        report.files_parsed += 1;

        let file_path_str = path.to_string_lossy().into_owned();
        if is_test_file(path, language) {
            report.test_files += 1;
            test_file_paths.insert(file_path_str.clone());
        }

        // REAL churn: commits touching this file over the window (0.0 off-repo).
        let churn = file_churn(root, path, churn_window_days);
        if churn > 0.0 {
            report.churn_files_nonzero += 1;
        }
        churn_by_file.insert(file_path_str, churn);

        for iri in &parsed.test_cells {
            global_test_cells.insert(iri.clone());
        }
        for cell in &parsed.cells {
            match cell.kind {
                CellKind::Function => {
                    func_defs
                        .entry(cell.symbol_name.clone())
                        .or_default()
                        .insert(cell.node_id());
                }
                CellKind::Class => {
                    class_defs
                        .entry(cell.symbol_name.clone())
                        .or_default()
                        .insert(cell.node_id());
                }
                _ => {}
            }
        }
        // Intra-file edges already carry correct kinds (incl. TESTED_BY for a test
        // calling a same-file function).
        all_edges.extend(parsed.edges.iter().cloned());
        all_cells.extend(parsed.cells.iter().cloned());

        for uc in &parsed.unresolved_call_sites {
            pending_xfile_calls.push((
                uc.caller_iri.clone(),
                uc.callee_symbol.clone(),
                uc.caller_is_test,
            ));
        }
        for ui in &parsed.unresolved_inherit_sites {
            pending_xfile_inherits.push((ui.subclass_iri.clone(), ui.base_symbol.clone()));
        }
    }

    // (3) CROSS-FILE RESOLUTION — unique-symbol rule (see doc comment above).
    for (caller_iri, callee_symbol, caller_is_test) in pending_xfile_calls {
        let caller_node = cell_iri_to_node_id(&caller_iri);
        match func_defs.get(&callee_symbol) {
            None => report.xfile_calls_external += 1,
            Some(nodes) => {
                // Exclude the caller itself so a name that only matches self is not
                // a spurious edge.
                let candidates: Vec<NodeId> =
                    nodes.iter().copied().filter(|&n| n != caller_node).collect();
                match candidates.as_slice() {
                    [only] => {
                        let is_test =
                            caller_is_test || global_test_cells.contains(&caller_iri);
                        let kind = if is_test {
                            EdgeKind::TestedBy
                        } else {
                            EdgeKind::Calls
                        };
                        all_edges.push(GraphEdge {
                            from: caller_node,
                            to: *only,
                            kind,
                            weight: 1.0,
                        });
                        report.xfile_calls_resolved += 1;
                    }
                    [] => report.xfile_calls_external += 1,
                    _ => report.xfile_calls_ambiguous += 1,
                }
            }
        }
    }
    for (sub_iri, base_symbol) in pending_xfile_inherits {
        let sub_node = cell_iri_to_node_id(&sub_iri);
        if let Some(nodes) = class_defs.get(&base_symbol) {
            let candidates: Vec<NodeId> =
                nodes.iter().copied().filter(|&n| n != sub_node).collect();
            if let [only] = candidates.as_slice() {
                all_edges.push(GraphEdge {
                    from: sub_node,
                    to: *only,
                    kind: EdgeKind::Inherits,
                    weight: 1.0,
                });
                report.xfile_inherits_resolved += 1;
            }
        }
    }

    // (4) INGEST — dedupe cells by NodeId, write cells then edges. Skip (never
    // fabricate) any edge whose endpoint was not written.
    let mut store = Store::memory(0);
    let mut written: HashSet<NodeId> = HashSet::new();
    let mut unique_cells: Vec<SemanticCell> = Vec::with_capacity(all_cells.len());
    for cell in &all_cells {
        let id = write_cell(&mut store, cell)?;
        if written.insert(id) {
            unique_cells.push(cell.clone());
        }
    }
    report.cells_total = unique_cells.len();
    let mut written_edges: Vec<GraphEdge> = Vec::with_capacity(all_edges.len());
    for edge in &all_edges {
        if written.contains(&edge.from) && written.contains(&edge.to) {
            write_edge(&mut store, edge)?;
            written_edges.push(edge.clone());
            if edge.kind == EdgeKind::TestedBy {
                report.tested_by_edges += 1;
            }
        }
    }

    // (5) FREEZE once.
    let index = store.freeze();

    // (6) SCORE every NON-test cell, with its file's REAL churn.
    for cell in &unique_cells {
        let is_test_cell = global_test_cells.contains(&cell.cell_id)
            || test_file_paths.contains(&cell.file_path);
        if is_test_cell {
            report.test_cells += 1;
            continue;
        }
        let churn = churn_by_file.get(&cell.file_path).copied().unwrap_or(0.0);
        report
            .artifacts
            .push(emit_proof_artifact(cell, &index, churn, false, config));
    }
    report.cells_scored = report.artifacts.len();

    // Expose the exact graph (nodes + written edges) and real per-file churn so
    // `what-if` can rebuild an editable copy of the SAME graph and hold churn fixed.
    report.cells = unique_cells;
    report.edges = written_edges;
    report.churn_by_file = churn_by_file;

    Ok(report)
}

/// Build an editable [`WhatIfGraph`] from a real source path by reusing the full
/// analyzer pipeline ([`analyze_path_report`]): parse, cross-file resolution, and
/// ingest. Returns the graph plus the per-file real churn map (so a caller can hold
/// a target cell's churn constant across a what-if before/after).
///
/// This deliberately does NOT re-implement any graph construction — it consumes the
/// analyzer's own resolved cells + edges, so a what-if is diffed against exactly the
/// graph the analyzer would score.
pub fn build_whatif_graph(
    root: impl AsRef<Path>,
    config: &ScoringConfig,
    churn_window_days: u32,
) -> Result<(WhatIfGraph, HashMap<String, f64>), AnalyzeError> {
    let report = analyze_path_report(root, config, churn_window_days)?;
    let churn = report.churn_by_file.clone();
    Ok((WhatIfGraph::new(report.cells, report.edges), churn))
}

/// Per-file churn from real git history, rooted at `root`. `churn_frequency`
/// returns `0.0` gracefully when `root` is not a git repo, so this is safe on any
/// directory. The pathspec is made relative to `root` so `git -C root log -- <p>`
/// addresses the file correctly.
fn file_churn(root: &Path, path: &Path, window_days: u32) -> f64 {
    let rel = path.strip_prefix(root).unwrap_or(path);
    let rel_str = rel.to_string_lossy();
    churn_frequency(root, &rel_str, window_days).unwrap_or(0.0)
}

/// Recursively collect files with a supported extension under `dir`, skipping
/// build/VCS noise (`target/`, `.git/`, `node_modules/`, and dot-directories).
fn collect_source_files(dir: &Path, out: &mut Vec<PathBuf>) -> io::Result<()> {
    if dir.is_file() {
        if Language::from_path(dir).is_some() {
            out.push(dir.to_path_buf());
        }
        return Ok(());
    }
    let entries = match std::fs::read_dir(dir) {
        Ok(e) => e,
        Err(_) => return Ok(()), // unreadable dir → skip, not fatal
    };
    for entry in entries {
        let entry = entry?;
        let path = entry.path();
        let name = entry.file_name();
        let name = name.to_string_lossy();
        if path.is_dir() {
            if name == "target"
                || name == "node_modules"
                || name.starts_with('.')
            {
                continue;
            }
            collect_source_files(&path, out)?;
        } else if Language::from_path(&path).is_some() {
            out.push(path);
        }
    }
    Ok(())
}
