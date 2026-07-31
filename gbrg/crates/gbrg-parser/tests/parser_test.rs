//! Integration proof: the parser produces real cells + call/inherit/import edges.
//!
//! The load-bearing assertion (task requirement) is the Rust A→B→C call chain.

use std::path::PathBuf;

use gbrg_core::{CellKind, EdgeKind};
use gbrg_parser::{parse_file, Language};

fn fixture(name: &str) -> PathBuf {
    let mut p = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    p.push("tests");
    p.push("fixtures");
    p.push(name);
    p
}

/// Find the function cell's node id by symbol name.
macro_rules! fn_id {
    ($res:expr, $sym:expr) => {
        $res.cells
            .iter()
            .find(|c| c.symbol_name == $sym && c.kind == CellKind::Function)
            .unwrap_or_else(|| panic!("no function cell named {}", $sym))
            .node_id()
    };
}

fn has_edge(res: &gbrg_parser::ParseResult, from: u64, to: u64, kind: EdgeKind) -> bool {
    res.edges
        .iter()
        .any(|e| e.from == from && e.to == to && e.kind == kind)
}

#[test]
fn rust_call_chain_a_b_c() {
    let res = parse_file(fixture("rust_calls.rs"), Language::Rust).expect("parse rust fixture");

    // Cells for A, B, C exist as functions.
    let a = fn_id!(res, "a");
    let b = fn_id!(res, "b");
    let c = fn_id!(res, "c");

    // The load-bearing proof: A→B and B→C call edges.
    assert!(
        has_edge(&res, a, b, EdgeKind::Calls),
        "expected calls edge a->b; edges={:?}",
        res.edges
    );
    assert!(
        has_edge(&res, b, c, EdgeKind::Calls),
        "expected calls edge b->c; edges={:?}",
        res.edges
    );

    // Structural extras: a trait + struct cell, an import cell, and an
    // `impl Greeter for Robot` inherits edge, plus a `use` imports edge.
    assert!(res.cells.iter().any(|c| c.symbol_name == "Greeter"));
    assert!(res.cells.iter().any(|c| c.symbol_name == "Robot"));
    assert!(
        res.edges.iter().any(|e| e.kind == EdgeKind::Imports),
        "expected at least one imports edge"
    );
    let robot = res
        .cells
        .iter()
        .find(|c| c.symbol_name == "Robot")
        .unwrap()
        .node_id();
    let greeter = res
        .cells
        .iter()
        .find(|c| c.symbol_name == "Greeter")
        .unwrap()
        .node_id();
    assert!(
        has_edge(&res, robot, greeter, EdgeKind::Inherits),
        "expected Robot inherits Greeter; edges={:?}",
        res.edges
    );
}

#[test]
fn python_call_chain_and_inherits() {
    let res = parse_file(fixture("py_calls.py"), Language::Python).expect("parse py fixture");
    let a = fn_id!(res, "a");
    let b = fn_id!(res, "b");
    let c = fn_id!(res, "c");
    assert!(has_edge(&res, a, b, EdgeKind::Calls), "py a->b");
    assert!(has_edge(&res, b, c, EdgeKind::Calls), "py b->c");

    let dog = res
        .cells
        .iter()
        .find(|c| c.symbol_name == "Dog")
        .unwrap()
        .node_id();
    let animal = res
        .cells
        .iter()
        .find(|c| c.symbol_name == "Animal")
        .unwrap()
        .node_id();
    assert!(
        has_edge(&res, dog, animal, EdgeKind::Inherits),
        "py Dog inherits Animal"
    );
}

#[test]
fn typescript_call_chain_and_extends() {
    let res = parse_file(fixture("ts_calls.ts"), Language::TypeScript).expect("parse ts fixture");
    let a = fn_id!(res, "a");
    let b = fn_id!(res, "b");
    let c = fn_id!(res, "c");
    assert!(has_edge(&res, a, b, EdgeKind::Calls), "ts a->b");
    assert!(has_edge(&res, b, c, EdgeKind::Calls), "ts b->c");

    let dog = res
        .cells
        .iter()
        .find(|c| c.symbol_name == "Dog")
        .unwrap()
        .node_id();
    let animal = res
        .cells
        .iter()
        .find(|c| c.symbol_name == "Animal")
        .unwrap()
        .node_id();
    assert!(
        has_edge(&res, dog, animal, EdgeKind::Inherits),
        "ts Dog extends Animal"
    );
}
