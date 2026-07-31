//! Containment engine tests — proving the sever/residual reads are correct AND
//! topology-agnostic.
//!
//! Two graphs go through the *same* functions:
//!   1. a CODE dependency graph (Upstream / dependents) — code-impact containment;
//!   2. a NETWORK endpoint graph (Downstream / reaches) — host isolation.
//!
//! Teeth are proven in both directions:
//!   * a real sever SHRINKS reachability (contained set is non-empty and correct);
//!   * a no-op sever does NOT falsely claim containment (residual == baseline, and
//!     the emitted artifact is downgraded to `speculative`, never a clean result).

use gbrg_core::{
    ast_hash_of, build_containment_artifact, cell_iri_to_node_id, emit_containment_artifact,
    reachable_set, sever_residual, transitive_dependents, write_cell, write_edge, CellKind,
    Direction, EdgeKind, EpistemicLevel, GraphEdge, SemanticCell, SeverScope,
};
use hg_analytics::{NodeId, Store};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

fn code_cell(symbol: &str, src: &[u8]) -> SemanticCell {
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

/// Add a bare network-endpoint node (no code semantics needed — the engine only
/// cares about graph structure). Returns the deterministic node id.
fn endpoint(store: &mut Store, host: &str) -> NodeId {
    let id = cell_iri_to_node_id(&format!("endpoint://{host}"));
    store.add_node(id).unwrap();
    id
}

fn sorted(mut v: Vec<NodeId>) -> Vec<NodeId> {
    v.sort_unstable();
    v
}

// ---------------------------------------------------------------------------
// 1. CODE graph — Upstream (dependents) containment
// ---------------------------------------------------------------------------
//
// Edges use the GBRG orientation `from DEPENDS ON to`:
//   B -> A   (B calls A)
//   C -> A   (C calls A)
//   D -> C   (D calls C)
// So A's transitive dependents (in-edges) are {B, C, D}. Severing the boundary
// cell C should contain D (which only reaches A THROUGH C) while leaving B.
#[test]
fn code_graph_sever_boundary_contains_transitive_dependent() {
    let mut store = Store::memory(0);
    let a = write_cell(&mut store, &code_cell("a", b"fn a() {}")).unwrap();
    let b = write_cell(&mut store, &code_cell("b", b"fn b(){a();}")).unwrap();
    let c = write_cell(&mut store, &code_cell("c", b"fn c(){a();}")).unwrap();
    let d = write_cell(&mut store, &code_cell("d", b"fn d(){c();}")).unwrap();

    for (from, to) in [(b, a), (c, a), (d, c)] {
        write_edge(&mut store, &GraphEdge { from, to, kind: EdgeKind::Calls, weight: 1.0 }).unwrap();
    }
    let index = store.freeze();

    // reachable_set(Upstream) must equal the existing transitive_dependents primitive.
    assert_eq!(
        sorted(reachable_set(&index, a, Direction::Upstream)),
        sorted(transitive_dependents(&index, a)),
        "reachable_set(Upstream) must agree with transitive_dependents"
    );
    assert_eq!(sorted(reachable_set(&index, a, Direction::Upstream)), sorted(vec![b, c, d]));

    // Sever the boundary cell C (Full). D reaches A only through C → D is contained.
    let reading = sever_residual(&index, a, &[c], &SeverScope::Full, &[], Direction::Upstream);
    assert_eq!(reading.baseline_reachable, sorted(vec![b, c, d]));
    assert_eq!(reading.residual_reachable, sorted(vec![b, c]), "B and C stay reachable; C is cut but still one hop from A");
    assert_eq!(reading.contained, vec![d], "severing C contains D");

    // Teeth: a real sever strictly shrinks reachability.
    assert!(reading.residual_count() < reading.baseline_count());
}

// ---------------------------------------------------------------------------
// 2. NETWORK graph — Downstream (reaches) isolation
// ---------------------------------------------------------------------------
//
// Edges are "can connect to" (out-orientation). Labels are network protocols —
// arbitrary strings, proving the engine is not tied to code EdgeKind labels.
//   F --SMB--> wks1 --SMB--> dc --SMB--> fileserver
//   F --RDP--> wks2
//   F --EDR--> edr        (allow-listed control channel)
#[test]
fn network_graph_full_vs_selective_isolation() {
    let mut store = Store::memory(0);
    let f = endpoint(&mut store, "vvv-648e9d56f1a"); // compromised foothold
    let wks1 = endpoint(&mut store, "wks-2970");
    let wks2 = endpoint(&mut store, "wks-0d06");
    let dc = endpoint(&mut store, "dc-01");
    let fileserver = endpoint(&mut store, "file-srv");
    let edr = endpoint(&mut store, "edr-epp");

    // Arbitrary string labels (NOT gbrg EdgeKind) — topology-agnostic proof.
    for (from, to, label) in [
        (f, wks1, "SMB"),
        (wks1, dc, "SMB"),
        (dc, fileserver, "SMB"),
        (f, wks2, "RDP"),
        (f, edr, "EDR"),
    ] {
        store.add_edge(from, to, label).unwrap();
    }
    let index = store.freeze();

    // Baseline: the foothold can reach everything (5 nodes).
    let baseline = sorted(reachable_set(&index, f, Direction::Downstream));
    assert_eq!(baseline, sorted(vec![wks1, wks2, dc, fileserver, edr]));

    // FULL isolation of the foothold, EDR allow-listed: residual is EDR only.
    let full = sever_residual(&index, f, &[f], &SeverScope::Full, &[edr], Direction::Downstream);
    assert_eq!(full.residual_reachable, vec![edr], "full isolation leaves only the EDR control channel");
    assert_eq!(full.contained, sorted(vec![wks1, wks2, dc, fileserver]), "everything else is contained");

    // SELECTIVE isolation keeping RDP (+EDR): wks2 stays reachable; the SMB chain is cut.
    let selective = sever_residual(
        &index,
        f,
        &[f],
        &SeverScope::Selective { keep_labels: vec!["RDP".into(), "EDR".into()] },
        &[edr],
        Direction::Downstream,
    );
    assert_eq!(selective.residual_reachable, sorted(vec![wks2, edr]));
    assert_eq!(selective.contained, sorted(vec![wks1, dc, fileserver]));

    // Teeth: Full isolation contains strictly more than Selective.
    assert!(
        full.contained_count() > selective.contained_count(),
        "Full ({}) must contain more than Selective ({})",
        full.contained_count(),
        selective.contained_count()
    );

    // The emitted artifact for a real containment is empirical (observed traversal).
    let artifact = emit_containment_artifact(
        &index, f, &[f], &SeverScope::Full, &[edr], Direction::Downstream,
    );
    assert_eq!(artifact.epistemic_level, EpistemicLevel::Empirical);
    assert_eq!(artifact.severed_scope, "full");
    assert_eq!(artifact.residual_reachable_count, 1);
    assert_eq!(artifact.contained_count, 4);
}

// ---------------------------------------------------------------------------
// 2b. The serialized artifact conforms to contracts/containment-proof-artifact.schema.json
// ---------------------------------------------------------------------------
#[test]
fn artifact_serialization_conforms_to_contract() {
    let mut store = Store::memory(0);
    let f = endpoint(&mut store, "host-x");
    let g = endpoint(&mut store, "host-y");
    let edr = endpoint(&mut store, "edr");
    store.add_edge(f, g, "SMB").unwrap();
    store.add_edge(f, edr, "EDR").unwrap();
    let index = store.freeze();

    let artifact =
        emit_containment_artifact(&index, f, &[f], &SeverScope::Full, &[edr], Direction::Downstream);
    let v: serde_json::Value = serde_json::to_value(&artifact).unwrap();

    // Every required key from the contract schema must be present with the right type.
    for key in [
        "schemaVersion", "proofId", "claimType", "statement", "epistemicLevel", "status",
        "source", "severedScope", "baselineReachableCount", "residualReachableCount",
        "containedCount", "residualReachable", "derivation", "declaredBy",
    ] {
        assert!(v.get(key).is_some(), "artifact missing required contract key: {key}");
    }
    // Enum + pattern constraints the schema declares.
    assert!(["proved", "bounded", "empirical", "synthetic", "speculative", "rejected"]
        .contains(&v["epistemicLevel"].as_str().unwrap()));
    assert!(["PROVED", "BOUNDED", "FAILED", "BLOCKED", "INCONCLUSIVE", "SYNTHETIC_ONLY"]
        .contains(&v["status"].as_str().unwrap()));
    assert!(v["proofId"].as_str().unwrap().starts_with("proof-"));
    assert!(v["declaredBy"].as_str().unwrap().starts_with("agent-registry://"));
    assert!(["full", "selective"].contains(&v["severedScope"].as_str().unwrap()));
    assert!(v["residualReachable"].is_array());
}

// ---------------------------------------------------------------------------
// 2c. An allow-listed endpoint is terminal even when a kept label reaches it —
//     Selective isolation must not pivot THROUGH the EDR channel.
// ---------------------------------------------------------------------------
#[test]
fn selective_does_not_pivot_through_allow_listed_endpoint() {
    let mut store = Store::memory(0);
    let f = endpoint(&mut store, "foothold");
    let edr = endpoint(&mut store, "edr");
    let secret = endpoint(&mut store, "secret-behind-edr");
    // Foothold reaches EDR via a KEPT label; EDR in turn reaches a secret node.
    store.add_edge(f, edr, "EDR").unwrap();
    store.add_edge(edr, secret, "SMB").unwrap();
    let index = store.freeze();

    let reading = sever_residual(
        &index, f, &[f],
        &SeverScope::Selective { keep_labels: vec!["EDR".into()] },
        &[edr], Direction::Downstream,
    );
    // EDR is reachable (terminal) but the secret behind it must NOT be — no pivot.
    assert!(reading.residual_reachable.contains(&edr), "EDR stays reachable");
    assert!(!reading.residual_reachable.contains(&secret), "must not pivot through the allow-listed EDR");
    assert_eq!(reading.contained, vec![secret], "the secret behind EDR is contained");
}

// ---------------------------------------------------------------------------
// 3. Reverse teeth — a no-op sever must NOT be read as a clean containment
// ---------------------------------------------------------------------------
#[test]
fn noop_sever_is_downgraded_not_a_clean_containment() {
    let mut store = Store::memory(0);
    let f = endpoint(&mut store, "host-a");
    let g = endpoint(&mut store, "host-b");
    store.add_edge(f, g, "SMB").unwrap();
    let index = store.freeze();

    // Cutting an unrelated/empty set severs nothing.
    let reading = sever_residual(&index, f, &[], &SeverScope::Full, &[], Direction::Downstream);
    assert_eq!(
        reading.residual_reachable, reading.baseline_reachable,
        "a no-op sever leaves reachability unchanged"
    );
    assert!(reading.contained.is_empty());

    // And the governed artifact refuses to present it as settled containment.
    let artifact = build_containment_artifact(&reading);
    assert_eq!(
        artifact.epistemic_level,
        EpistemicLevel::Speculative,
        "a sever that contained nothing must be speculative, never a clean result"
    );
    assert_eq!(artifact.status, "INCONCLUSIVE");
}
