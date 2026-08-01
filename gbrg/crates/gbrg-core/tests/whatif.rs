//! What-if recompute-and-diff — the REAL proof.
//!
//! Builds an editable [`WhatIfGraph`] (an untested target cell with several CALLS
//! dependents → `speculative`), applies the `add_tests` hypothetical edit, and
//! asserts the recomputed-and-diffed result:
//!   (a) `after.epistemicLevel` climbs to `empirical`/`bounded` (a test now reaches it),
//!   (b) `after.blast_radius < before.blast_radius` (coverage shrinks blast radius),
//!   (c) the BASELINE graph is untouched — re-scoring it returns the identical
//!       artifact and the edge count is unchanged (the edit hit a clone, not the graph).
//!
//! Also proves `remove_dependent` really drops one caller on the copy and lowers the
//! blast radius, with the baseline again untouched.

use gbrg_core::{
    ast_hash_of, what_if, CellKind, EdgeKind, GraphEdge, Mutation, ScoringConfig, SemanticCell,
    WhatIfGraph,
};

fn cell(symbol: &str, src: &[u8]) -> SemanticCell {
    SemanticCell {
        cell_id: format!("code://rust/src/lib.rs#{symbol}"),
        kind: CellKind::Function,
        language: "rust".to_string(),
        file_path: "src/lib.rs".to_string(),
        symbol_name: symbol.to_string(),
        ast_hash: ast_hash_of(src),
        loc_start: 1,
        loc_end: 3,
        generated: false,
    }
}

/// Build a graph: `target` with `n_callers` CALLS dependents and NO test.
fn graph_with_untested_target(n_callers: u32) -> (WhatIfGraph, SemanticCell) {
    let target = cell("target", b"fn target() {}");
    let target_node = target.node_id();

    let mut cells = vec![target.clone()];
    let mut edges = Vec::new();
    for i in 0..n_callers {
        let c = cell(&format!("caller{i}"), b"fn caller() { target(); }");
        edges.push(GraphEdge {
            from: c.node_id(),
            to: target_node,
            kind: EdgeKind::Calls,
            weight: 1.0,
        });
        cells.push(c);
    }
    (WhatIfGraph::new(cells, edges), target)
}

#[test]
fn add_tests_lifts_level_and_shrinks_blast_radius_without_mutating_baseline() {
    let config = ScoringConfig::default();
    // Several dependents (3, below the bounded threshold of 15) and no test → the
    // untested-with-few-dependents shape, which derives `speculative`.
    let (graph, target) = graph_with_untested_target(3);
    let baseline_edge_count = graph.edges().len();

    // Independent baseline read of the SAME cell (the "before" the diff should match).
    let baseline_before = graph
        .score_cell(&target.cell_id, 0.0, false, &config)
        .expect("baseline scores");
    assert_eq!(
        baseline_before.claim.epistemic_level.as_str(),
        "speculative",
        "untested target must start speculative; derivation: {}",
        baseline_before.derivation
    );
    assert_eq!(baseline_before.dependents_count, 3);

    // --- The what-if: hypothesise a test reaches the target. ---
    let result = what_if(&graph, &target.cell_id, Mutation::AddTests, 0.0, false, &config)
        .expect("what_if runs");

    // The diff's `before` must equal the independent baseline read (same graph).
    assert_eq!(
        result.before.epistemic_level.as_str(),
        "speculative",
        "before must be the untouched baseline"
    );
    assert_eq!(result.before.blast_radius, baseline_before.blast_radius);

    // (a) after.epistemicLevel climbs to empirical (or bounded).
    let after_level = result.after.epistemic_level.as_str();
    assert!(
        after_level == "empirical" || after_level == "bounded",
        "add_tests must lift the level to empirical/bounded, got `{after_level}`; \
         derivation: {}",
        result.after.derivation
    );
    assert!(
        result.after.test_coverage_reach,
        "after add_tests the target must be test-reached"
    );

    // (b) after.blast_radius strictly less than before.
    assert!(
        result.after.blast_radius < result.before.blast_radius,
        "add_tests must SHRINK blast radius: before={} after={}",
        result.before.blast_radius,
        result.after.blast_radius
    );
    assert!(
        result.delta.blast_radius_change < 0.0,
        "delta.blast_radius_change must be negative, got {}",
        result.delta.blast_radius_change
    );
    assert!(
        result.applied,
        "add_tests on an untested cell must actually apply"
    );

    // (c) BASELINE UNCHANGED — the edit hit a clone, never the graph.
    assert_eq!(
        graph.edges().len(),
        baseline_edge_count,
        "the synthetic TESTED_BY edge must NOT leak into the baseline graph"
    );
    let baseline_after = graph
        .score_cell(&target.cell_id, 0.0, false, &config)
        .expect("baseline re-scores");
    assert_eq!(
        baseline_after.claim.epistemic_level.as_str(),
        "speculative",
        "re-scoring the baseline after a what-if must still be speculative (unmutated)"
    );
    assert_eq!(
        baseline_after.blast_radius, baseline_before.blast_radius,
        "baseline blast_radius must be byte-identical before and after the what-if"
    );
    assert_eq!(
        baseline_after.dependents_count, baseline_before.dependents_count,
        "baseline dependents_count must be unchanged"
    );

    // Honesty banner is carried in the machine output.
    assert!(
        result.method.to_lowercase().contains("not counterfactual"),
        "WhatIfResult.method must carry the honesty banner: {}",
        result.method
    );

    // Human summary shape, e.g. "IF add_tests: speculative→empirical, blast 0.35→0.10".
    assert!(
        result.summary.starts_with("IF add_tests:") && result.summary.contains("blast"),
        "unexpected summary: {}",
        result.summary
    );
    eprintln!("what-if summary: {}", result.summary);
}

#[test]
fn remove_dependent_drops_one_caller_and_lowers_blast_radius_without_mutating_baseline() {
    let config = ScoringConfig::default();
    // 20 callers (> threshold) so the effect is visible and the level stays speculative.
    let (graph, target) = graph_with_untested_target(20);
    let baseline_edge_count = graph.edges().len();

    let before = graph
        .score_cell(&target.cell_id, 0.0, false, &config)
        .expect("baseline scores");
    assert_eq!(before.dependents_count, 20);

    let result = what_if(
        &graph,
        &target.cell_id,
        Mutation::RemoveDependent,
        0.0,
        false,
        &config,
    )
    .expect("what_if runs");

    assert!(result.applied, "remove_dependent must apply when a CALLS edge exists");
    assert_eq!(
        result.after.dependents_count, 19,
        "removing one caller must drop dependents_count by exactly one"
    );
    assert!(
        result.after.blast_radius < result.before.blast_radius,
        "fewer dependents must lower blast radius: before={} after={}",
        result.before.blast_radius,
        result.after.blast_radius
    );

    // Baseline untouched.
    assert_eq!(graph.edges().len(), baseline_edge_count);
    let after_baseline = graph
        .score_cell(&target.cell_id, 0.0, false, &config)
        .expect("re-score");
    assert_eq!(
        after_baseline.dependents_count, 20,
        "baseline still has all 20 callers (edit hit the copy)"
    );
}

/// An honest no-op: `remove_dependent` on a cell with no incoming CALLS edge does
/// not fail — it reports `applied=false` and a zero delta.
#[test]
fn remove_dependent_no_caller_is_honest_noop() {
    let config = ScoringConfig::default();
    let target = cell("lonely", b"fn lonely() {}");
    let graph = WhatIfGraph::new(vec![target.clone()], Vec::new());

    let result = what_if(
        &graph,
        &target.cell_id,
        Mutation::RemoveDependent,
        0.0,
        false,
        &config,
    )
    .expect("runs");
    assert!(!result.applied, "no CALLS edge → not applied");
    assert_eq!(result.delta.blast_radius_change, 0.0);
    assert!(
        result.note.to_lowercase().contains("no-op"),
        "note must explain the no-op: {}",
        result.note
    );
}
