//! Linchpin smoke test.
//!
//! Proves that the full load-bearing `hg_analytics` path works from an EXTERNAL
//! crate: write cells + edges into a `Store`, `freeze()` to a `GraphIndex`, and
//! read blast-radius facts back through `GraphCore`.
//!
//! Topology:  A <-CALLS- B  and  A <-CALLS- C   (B and C call A)
//! Expectation: A has 2 dependents; its in-neighbors under "CALLS" are {B, C}.

use gbrg_core::{
    ast_hash_of, dependents_count, reverse_dependents, write_cell, write_edge, CellKind, EdgeKind,
    GraphEdge, SemanticCell,
};
use hg_analytics::{GraphCore, Store};

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

#[test]
fn smoke_blast_radius_in_degree() {
    let mut store = Store::memory(0);

    // Three cells.
    let a = write_cell(&mut store, &cell("a", b"fn a() {}")).unwrap();
    let b = write_cell(&mut store, &cell("b", b"fn b() { a(); }")).unwrap();
    let c = write_cell(&mut store, &cell("c", b"fn c() { a(); }")).unwrap();

    // Deterministic mapping must give three distinct nodes.
    assert_ne!(a, b);
    assert_ne!(a, c);
    assert_ne!(b, c);

    // B calls A, C calls A  =>  A <-CALLS- B , A <-CALLS- C.
    write_edge(
        &mut store,
        &GraphEdge { from: b, to: a, kind: EdgeKind::Calls, weight: 1.0 },
    )
    .unwrap();
    write_edge(
        &mut store,
        &GraphEdge { from: c, to: a, kind: EdgeKind::Calls, weight: 1.0 },
    )
    .unwrap();

    // Freeze to the read-optimised dense-CSR index.
    let index = store.freeze();

    // (1) A has exactly 2 dependents (in_degree == 2).
    assert_eq!(
        dependents_count(&index, a),
        Some(2),
        "A must have 2 dependents (in_degree)"
    );

    // (2) in_neighbors(A, CALLS) == {B, C}.
    let mut deps = reverse_dependents(&index, a, Some(EdgeKind::Calls.as_label()));
    deps.sort_unstable();
    let mut expected = vec![b, c];
    expected.sort_unstable();
    assert_eq!(deps, expected, "reverse_dependents(A, CALLS) must be {{B, C}}");

    // (3) Prove the raw GraphCore path directly, not only via our wrappers.
    let ad = index.dense(a).expect("A present in index");
    assert_eq!(index.in_degree(ad), 2, "raw GraphCore::in_degree(A) == 2");
}
