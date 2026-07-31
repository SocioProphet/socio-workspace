//! gbrg-napi — thin N-API bridge over `gbrg-core`.
//!
//! SKELETON / BEST-EFFORT: this crate compiles only where the napi build
//! toolchain is available; it is excluded from the default gbrg workspace so it
//! never blocks `gbrg-core`'s tests. Bodies here are stubs that return
//! ProofArtifact-shaped JSON *strings* (never bare floats) so the TS/MCP layer
//! always receives a governed, provenance-carrying result.
//!
//! When wired for real, these functions will: build/reuse a frozen
//! `gbrg_core::GraphIndex`, resolve the incoming `cell_id` IRI via
//! `gbrg_core::cell_iri_to_node_id`, and call the real reads
//! (`dependents_count`, `reverse_dependents`, `transitive_dependents`).

use napi_derive::napi;

/// Blast radius for a cell, returned as a ProofArtifact JSON string.
///
/// `cell_id` is a stable code IRI (e.g. `code://rust/src/lib.rs#foo`).
#[napi]
pub fn blast_radius(cell_id: String) -> String {
    // STUB: real impl resolves the IRI to a NodeId and reads the frozen index.
    format!(
        r#"{{"schemaVersion":"0.1.0","proofId":"proof-gbrg-blast-stub","claim":{{"claimId":"claim.gbrg.blast_radius","claimType":"scope_bound","statement":"blast radius of {cell_id}","epistemicLevel":"speculative"}},"status":"INCONCLUSIVE","dependents_count":0,"test_coverage_reach":false,"churn_frequency":0.0,"blast_radius":0.0,"derivation":"stub: gbrg-napi not yet wired to a frozen index","declared_by":"agent-registry://gbrg/skeleton","generated":false}}"#
    )
}

/// Containment (sever / residual reachability) for a source node, returned as a
/// ContainmentProofArtifact JSON string.
///
/// `source_id` is a stable node IRI (code cell or `endpoint://<host>`); `scope` is
/// `"full"` or `"selective"`. When wired for real this builds/reuses a frozen
/// `gbrg_core::GraphIndex` and calls `gbrg_core::emit_containment_artifact`.
#[napi]
pub fn containment_query(source_id: String, scope: String) -> String {
    // STUB: real impl resolves the IRI and runs sever_residual over the frozen index.
    format!(
        r#"{{"schemaVersion":"0.1.0","proofId":"proof-gbrg-containment-stub","claimType":"scope_bound","statement":"containment of {source_id} ({scope} scope)","epistemicLevel":"speculative","status":"INCONCLUSIVE","source":"{source_id}","scope":"{scope}","severedScope":"{scope}","baselineReachableCount":0,"residualReachableCount":0,"containedCount":0,"residualReachable":[],"derivation":"stub: gbrg-napi not yet wired to a frozen index","declaredBy":"agent-registry://gbrg/skeleton"}}"#
    )
}

/// Graph health/status as a JSON string (node/edge counts, freeze state, ...).
#[napi]
pub fn graph_status() -> String {
    // STUB: real impl reports node/edge counts from the live store/index.
    r#"{"status":"skeleton","nodes":0,"edges":0,"frozen":false}"#.to_string()
}
