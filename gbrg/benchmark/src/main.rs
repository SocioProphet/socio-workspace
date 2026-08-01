//! # gbrg-benchmark — honest token-reduction + impact-recall measurement (Phase 5)
//!
//! This harness does NOT re-implement GBRG. It drives the REAL pipeline
//! ([`gbrg_analyze::analyze_path_report`]) to get the exact resolved cells + edges,
//! rebuilds a frozen index through gbrg-core's public write path, and then measures
//! two things on a real repo using gbrg-core's public blast-radius reads:
//!
//! 1. **Token reduction** — for a review of one *changed cell*, compare the FULL
//!    review context (every reviewable cell body in the repo) against the MINIMAL
//!    context GBRG would send (the changed cell + its blast radius). Tokens are
//!    estimated as `chars / DIVISOR` (default DIVISOR = 4, a well-known rough
//!    chars-per-token heuristic; state your own with `--divisor`). Ratio =
//!    `full_tokens / minimal_tokens`.
//!
//! 2. **Impact recall** — the *true impacted set* of a changed cell is its actual
//!    graph dependents, reverse-reachable via CALLS/INHERITS (gbrg-core's
//!    [`gbrg_core::transitive_dependents`]). Recall = fraction of that set present in
//!    the minimal context. Reported for the transitive selection (what GBRG sends)
//!    AND for a direct-only (depth-1) selection, so the metric visibly has teeth
//!    (direct-only recall drops below 1.0 whenever depth-≥2 dependents exist).
//!
//! Usage:
//!   gbrg-benchmark <repo-dir> [--divisor N] [--json <out.json>] [--top N]
//!
//! Honesty: see gbrg/benchmark/RESULTS.md for the non-claim box. The numbers are
//! repo-size-dependent; a small repo yields a modest ratio and that is reported as
//! measured, never inflated.
//!
//! Cleanliness: every path in the emitted JSON (`repo`, `file`, and the `cell_id`
//! IRIs) is REPO-RELATIVE — an absolute repo root collapses to its dir name and cell
//! paths are stripped to `src/...` — so a public repo never leaks local filesystem
//! layout (`/Users/<name>/dev/...`). The FileCache still reads via the real absolute
//! path; only the OUTPUT is relativized.

use std::collections::{HashMap, HashSet};
use std::path::{Path, PathBuf};
use std::process::ExitCode;

use gbrg_analyze::{analyze_path_report, DEFAULT_CHURN_WINDOW_DAYS};
use gbrg_core::{
    reverse_dependents, transitive_dependents, write_cell, write_edge, CellKind, GraphEdge,
    ScoringConfig, SemanticCell,
};
use hg_analytics::{GraphIndex, NodeId, Store};
use serde::Serialize;

/// Make an absolute source path REPO-RELATIVE for the committed JSON, so a public
/// repo never leaks the local filesystem layout (e.g. `/Users/<name>/dev/...`).
/// `abs` is the cell's `file_path` as walked from `root`, so stripping `root` yields
/// a path relative to the analyzed repo (`src/interner.rs`). If `abs` is not under
/// `root` (shouldn't happen), it is returned unchanged rather than fabricated.
fn relativize(abs: &str, root: &Path) -> String {
    Path::new(abs)
        .strip_prefix(root)
        .map(|rel| rel.to_string_lossy().into_owned())
        .unwrap_or_else(|_| abs.to_string())
}

/// Rewrite a cell IRI so its embedded file path is repo-relative. The IRI is
/// `code://<lang>/<file_path>#<symbol>`; `file_path` appears verbatim, so a single
/// substring replacement is exact (the path is unique within its own IRI).
fn relativize_cell_id(cell_id: &str, abs_file: &str, rel_file: &str) -> String {
    cell_id.replacen(abs_file, rel_file, 1)
}

/// Rebuild the frozen index from the analyzer's EXACT cells + edges via gbrg-core's
/// public write path — the same discipline `WhatIfGraph::build_index` uses. No new
/// graph construction logic lives here; we only consume what the analyzer resolved.
fn build_index(cells: &[SemanticCell], edges: &[GraphEdge]) -> std::io::Result<GraphIndex> {
    let mut store = Store::memory(0);
    let mut written: HashSet<NodeId> = HashSet::new();
    for c in cells {
        let id = write_cell(&mut store, c)?;
        written.insert(id);
    }
    for e in edges {
        if written.contains(&e.from) && written.contains(&e.to) {
            write_edge(&mut store, e)?;
        }
    }
    Ok(store.freeze())
}

/// Lazily reads source files into line vectors so context sizing never re-reads a file.
struct FileCache {
    map: HashMap<String, Vec<String>>,
}
impl FileCache {
    fn new() -> Self {
        Self {
            map: HashMap::new(),
        }
    }
    fn lines(&mut self, path: &str) -> &Vec<String> {
        self.map.entry(path.to_string()).or_insert_with(|| {
            std::fs::read_to_string(path)
                .map(|s| s.lines().map(|l| l.to_string()).collect())
                .unwrap_or_default()
        })
    }
}

/// Characters covered by the UNION of `cells`' 1-based inclusive `[loc_start,loc_end]`
/// line intervals, MERGED per file so a nested/overlapping cell never double-counts.
/// Adds 1 char per line for the stripped newline. This is the "text a reviewer must
/// read" for a given set of cells.
fn context_chars(cells: &[&SemanticCell], fc: &mut FileCache) -> u64 {
    let mut by_file: HashMap<String, Vec<(u32, u32)>> = HashMap::new();
    for c in cells {
        by_file
            .entry(c.file_path.clone())
            .or_default()
            .push((c.loc_start, c.loc_end));
    }
    let mut total: u64 = 0;
    for (file, mut ivs) in by_file {
        ivs.sort_unstable();
        let mut merged: Vec<(u32, u32)> = Vec::new();
        for (s, e) in ivs {
            if let Some(last) = merged.last_mut() {
                // adjacent (last.1 + 1 == s) or overlapping intervals merge
                if s <= last.1.saturating_add(1) {
                    if e > last.1 {
                        last.1 = e;
                    }
                    continue;
                }
            }
            merged.push((s, e));
        }
        let lines = fc.lines(&file);
        if lines.is_empty() {
            continue;
        }
        for (s, e) in merged {
            let s0 = s.saturating_sub(1) as usize;
            let e0 = (e as usize).min(lines.len());
            for line in lines.iter().take(e0).skip(s0) {
                total += line.len() as u64 + 1;
            }
        }
    }
    total
}

#[derive(Serialize)]
struct TargetRow {
    cell_id: String,
    symbol: String,
    file: String,
    /// |true impacted set| = transitive reviewable dependents.
    blast_radius_size: usize,
    direct_dependents: usize,
    minimal_chars: u64,
    minimal_tokens: u64,
    token_reduction_ratio: f64,
    /// Recall of the true impacted set by the transitive (GBRG) selection — measured,
    /// not asserted. 1.0 by construction (selection ⊇ oracle); we compute it by set
    /// membership so a regression that dropped a dependent would show < 1.0.
    recall_transitive: f64,
    /// Recall by a direct-only (depth-1) selection — < 1.0 whenever depth-≥2
    /// dependents exist. Proves the recall metric is falsifiable.
    recall_direct: f64,
}

#[derive(Serialize)]
struct Aggregate {
    mean: f64,
    median: f64,
    min: f64,
    max: f64,
}

fn aggregate(mut xs: Vec<f64>) -> Option<Aggregate> {
    if xs.is_empty() {
        return None;
    }
    xs.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let n = xs.len();
    let mean = xs.iter().sum::<f64>() / n as f64;
    let median = if n % 2 == 1 {
        xs[n / 2]
    } else {
        (xs[n / 2 - 1] + xs[n / 2]) / 2.0
    };
    Some(Aggregate {
        mean,
        median,
        min: xs[0],
        max: xs[n - 1],
    })
}

#[derive(Serialize)]
struct Report {
    repo: String,
    token_method: String,
    token_divisor: f64,
    files_parsed: usize,
    cells_total: usize,
    cells_scored: usize,
    reviewable_cells: usize,
    // Graph-completeness caveat (the REAL bound on recall vs an external oracle).
    xfile_calls_resolved: usize,
    xfile_calls_ambiguous: usize,
    xfile_calls_external: usize,
    tested_by_edges: usize,
    full_context_chars: u64,
    full_context_tokens: u64,
    targets_with_blast_radius: usize,
    leaf_cells_no_dependents: usize,
    token_reduction_over_targets: Option<Aggregate>,
    recall_transitive_mean: Option<f64>,
    recall_direct_mean: Option<f64>,
    top_targets_by_blast_radius: Vec<TargetRow>,
}

fn main() -> ExitCode {
    let mut args = std::env::args().skip(1);
    let mut repo: Option<PathBuf> = None;
    let mut divisor: f64 = 4.0;
    let mut json_out: Option<PathBuf> = None;
    let mut top: usize = 15;

    while let Some(a) = args.next() {
        match a.as_str() {
            "--divisor" => {
                divisor = args.next().and_then(|v| v.parse().ok()).unwrap_or(4.0);
            }
            "--json" => json_out = args.next().map(PathBuf::from),
            "--top" => top = args.next().and_then(|v| v.parse().ok()).unwrap_or(15),
            "-h" | "--help" => {
                println!(
                    "usage: gbrg-benchmark <repo-dir> [--divisor N] [--json out.json] [--top N]"
                );
                return ExitCode::SUCCESS;
            }
            other => {
                if repo.is_some() {
                    eprintln!("error: more than one repo path given");
                    return ExitCode::from(2);
                }
                repo = Some(PathBuf::from(other));
            }
        }
    }
    let repo = match repo {
        Some(r) => r,
        None => {
            eprintln!("usage: gbrg-benchmark <repo-dir> [--divisor N] [--json out.json] [--top N]");
            return ExitCode::from(2);
        }
    };
    if divisor <= 0.0 {
        eprintln!("error: --divisor must be > 0");
        return ExitCode::from(2);
    }

    let config = ScoringConfig::default();
    let report = match analyze_path_report(&repo, &config, DEFAULT_CHURN_WINDOW_DAYS) {
        Ok(r) => r,
        Err(e) => {
            eprintln!("error: analyzing {}: {e}", repo.display());
            return ExitCode::FAILURE;
        }
    };

    let index = match build_index(&report.cells, &report.edges) {
        Ok(i) => i,
        Err(e) => {
            eprintln!("error: building index: {e}");
            return ExitCode::FAILURE;
        }
    };

    // Non-test scored cells are exactly those the analyzer emitted an artifact for.
    let scored: HashSet<&str> = report
        .artifacts
        .iter()
        .map(|a| a.cell_id.as_str())
        .collect();

    // Reviewable = scored (non-test) Function|Class cells (the units a reviewer reads;
    // module cells span whole files and imports are trivial, so both are excluded from
    // the CONTEXT and from the impacted-set to keep the measure cell-granular).
    let reviewable: Vec<&SemanticCell> = report
        .cells
        .iter()
        .filter(|c| {
            scored.contains(c.cell_id.as_str())
                && matches!(c.kind, CellKind::Function | CellKind::Class)
        })
        .collect();
    let reviewable_nodes: HashSet<NodeId> = reviewable.iter().map(|c| c.node_id()).collect();
    let node_to_cell: HashMap<NodeId, &SemanticCell> =
        reviewable.iter().map(|c| (c.node_id(), *c)).collect();

    let mut fc = FileCache::new();
    let full_chars = context_chars(&reviewable, &mut fc);
    let full_tokens = (full_chars as f64 / divisor).round() as u64;

    let mut rows: Vec<TargetRow> = Vec::new();
    let mut ratios: Vec<f64> = Vec::new();
    let mut recalls_t: Vec<f64> = Vec::new();
    let mut recalls_d: Vec<f64> = Vec::new();
    let mut leaf = 0usize;

    for c in &reviewable {
        let node = c.node_id();

        // TRUE impacted set (oracle): transitive reverse-reachable dependents,
        // restricted to reviewable non-test cells.
        let oracle: HashSet<NodeId> = transitive_dependents(&index, node)
            .into_iter()
            .filter(|n| *n != node && reviewable_nodes.contains(n))
            .collect();

        if oracle.is_empty() {
            leaf += 1;
            continue; // leaf cell: no dependents, trivial review context — reported separately
        }

        // Direct (depth-1) dependents, restricted to reviewable.
        let direct: HashSet<NodeId> = reverse_dependents(&index, node, None)
            .into_iter()
            .filter(|n| *n != node && reviewable_nodes.contains(n))
            .collect();

        // MINIMAL (transitive) selection = {changed cell} ∪ blast radius.
        let mut sel_cells: Vec<&SemanticCell> = vec![*c];
        for n in &oracle {
            if let Some(cc) = node_to_cell.get(n) {
                sel_cells.push(*cc);
            }
        }
        let sel_nodes: HashSet<NodeId> = sel_cells.iter().map(|c| c.node_id()).collect();

        let min_chars = context_chars(&sel_cells, &mut fc);
        let min_tokens = (min_chars as f64 / divisor).round().max(1.0) as u64;
        let ratio = full_tokens as f64 / min_tokens as f64;

        // Recall MEASURED by set membership (not asserted).
        let hit_t = oracle.iter().filter(|n| sel_nodes.contains(n)).count();
        let recall_t = hit_t as f64 / oracle.len() as f64;
        let hit_d = oracle.iter().filter(|n| direct.contains(n)).count();
        let recall_d = hit_d as f64 / oracle.len() as f64;

        ratios.push(ratio);
        recalls_t.push(recall_t);
        recalls_d.push(recall_d);

        // REPO-RELATIVE paths in the committed output (no local-FS-layout leak).
        let rel_file = relativize(&c.file_path, &repo);
        let rel_cell_id = relativize_cell_id(&c.cell_id, &c.file_path, &rel_file);
        rows.push(TargetRow {
            cell_id: rel_cell_id,
            symbol: c.symbol_name.clone(),
            file: rel_file,
            blast_radius_size: oracle.len(),
            direct_dependents: direct.len(),
            minimal_chars: min_chars,
            minimal_tokens: min_tokens,
            token_reduction_ratio: ratio,
            recall_transitive: recall_t,
            recall_direct: recall_d,
        });
    }

    rows.sort_by(|a, b| b.blast_radius_size.cmp(&a.blast_radius_size));
    let top_rows: Vec<TargetRow> = rows.into_iter().take(top).collect();

    let recall_t_mean = if recalls_t.is_empty() {
        None
    } else {
        Some(recalls_t.iter().sum::<f64>() / recalls_t.len() as f64)
    };
    let recall_d_mean = if recalls_d.is_empty() {
        None
    } else {
        Some(recalls_d.iter().sum::<f64>() / recalls_d.len() as f64)
    };

    // Repo identity WITHOUT leaking local FS layout: an absolute root collapses to
    // its final component (the repo/dir name); a relative root (e.g. `gbrg/crates`)
    // is already layout-free and kept verbatim.
    let repo_field = if repo.is_absolute() {
        repo.file_name()
            .map(|n| n.to_string_lossy().into_owned())
            .unwrap_or_else(|| repo.display().to_string())
    } else {
        repo.display().to_string()
    };

    let out = Report {
        repo: repo_field,
        token_method: format!(
            "chars / {divisor} (rough chars-per-token heuristic; offline, no tokenizer)"
        ),
        token_divisor: divisor,
        files_parsed: report.files_parsed,
        cells_total: report.cells_total,
        cells_scored: report.cells_scored,
        reviewable_cells: reviewable.len(),
        xfile_calls_resolved: report.xfile_calls_resolved,
        xfile_calls_ambiguous: report.xfile_calls_ambiguous,
        xfile_calls_external: report.xfile_calls_external,
        tested_by_edges: report.tested_by_edges,
        full_context_chars: full_chars,
        full_context_tokens: full_tokens,
        targets_with_blast_radius: ratios.len(),
        leaf_cells_no_dependents: leaf,
        token_reduction_over_targets: aggregate(ratios.clone()),
        recall_transitive_mean: recall_t_mean,
        recall_direct_mean: recall_d_mean,
        top_targets_by_blast_radius: top_rows,
    };

    // Human summary to stdout.
    println!("=== GBRG benchmark: {} ===", out.repo);
    println!(
        "files_parsed={}  cells_total={}  cells_scored={}  reviewable(fn/class)={}",
        out.files_parsed, out.cells_total, out.cells_scored, out.reviewable_cells
    );
    println!(
        "graph completeness: xfile calls resolved={} ambiguous={} external={}  tested_by_edges={}",
        out.xfile_calls_resolved,
        out.xfile_calls_ambiguous,
        out.xfile_calls_external,
        out.tested_by_edges
    );
    println!(
        "token method: {}  |  FULL context = {} chars ≈ {} tokens",
        out.token_method, out.full_context_chars, out.full_context_tokens
    );
    println!(
        "targets with blast radius >=1: {}   leaf cells (no dependents): {}",
        out.targets_with_blast_radius, out.leaf_cells_no_dependents
    );
    if let Some(a) = &out.token_reduction_over_targets {
        println!(
            "TOKEN REDUCTION ratio over targets  mean={:.2}x  median={:.2}x  min={:.2}x  max={:.2}x",
            a.mean, a.median, a.min, a.max
        );
    }
    println!(
        "IMPACT RECALL  transitive(GBRG)={:.1}%   direct-only(depth1)={:.1}%",
        out.recall_transitive_mean.unwrap_or(0.0) * 100.0,
        out.recall_direct_mean.unwrap_or(0.0) * 100.0
    );
    println!("\ntop targets by blast radius (hardest cases — biggest minimal context):");
    println!(
        "{:<34} {:>6} {:>6} {:>9} {:>8} {:>8} {:>8}",
        "symbol", "blast", "direct", "min_tok", "ratio", "rec_t", "rec_d"
    );
    for r in &out.top_targets_by_blast_radius {
        let sym: String = r.symbol.chars().take(32).collect();
        println!(
            "{:<34} {:>6} {:>6} {:>9} {:>7.2}x {:>7.0}% {:>7.0}%",
            sym,
            r.blast_radius_size,
            r.direct_dependents,
            r.minimal_tokens,
            r.token_reduction_ratio,
            r.recall_transitive * 100.0,
            r.recall_direct * 100.0
        );
    }

    if let Some(path) = json_out {
        match serde_json::to_string_pretty(&out) {
            Ok(j) => {
                if let Err(e) = std::fs::write(&path, j) {
                    eprintln!("error: writing {}: {e}", path.display());
                    return ExitCode::FAILURE;
                }
                eprintln!("gbrg-benchmark: wrote JSON → {}", path.display());
            }
            Err(e) => {
                eprintln!("error: serialising report: {e}");
                return ExitCode::FAILURE;
            }
        }
    }

    ExitCode::SUCCESS
}
