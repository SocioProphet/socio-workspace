//! gbrg-napi — thin N-API bridge over `gbrg-core`.
//!
//! Compiles as a standalone crate (excluded from the default gbrg workspace) where the napi build
//! toolchain is available. It resolves incoming code IRIs to graph `NodeId`s via
//! `gbrg_core::cell_iri_to_node_id` and returns ProofArtifact-shaped JSON strings. The frozen-index
//! QUERY that turns resolution into a real blast radius (dependents_count / transitive_dependents /
//! build_proof_artifact over a process-held `GraphIndex`) is tracked by sociosphere#591.

use gbrg_core::cell_iri_to_node_id;
use napi_derive::napi;

/// Blast radius for a cell, returned as a ProofArtifact JSON string.
///
/// `cell_id` is a stable code IRI (e.g. `code://rust/src/lib.rs#foo`).
#[napi]
pub fn blast_radius(cell_id: String) -> String {
    // Real, deterministic IRI -> NodeId resolution. The frozen-index query is tracked by
    // sociosphere#591; until an index is frozen we return an HONEST INCONCLUSIVE carrying the REAL
    // node id — never a fabricated score or a constant stub id.
    let node = cell_iri_to_node_id(&cell_id);
    format!(
        r#"{{"schemaVersion":"0.1.0","proofId":"proof-gbrg-{node:016x}","claim":{{"claimId":"claim.gbrg.blast_radius.{node:016x}","claimType":"scope_bound","statement":"blast radius of {cell_id}","epistemicLevel":"speculative"}},"status":"INCONCLUSIVE","nodeId":"{node:016x}","dependents_count":0,"test_coverage_reach":false,"churn_frequency":0.0,"blast_radius":0.0,"derivation":"resolved IRI to NodeId; no frozen GraphIndex loaded — real query pending gbrg-napi frozen-index wiring (sociosphere#591)","declared_by":"agent-registry://gbrg","generated":false}}"#
    )
}

/// Containment (sever / residual reachability) for a source node.
#[napi]
pub fn containment_query(source_id: String, scope: String) -> String {
    // Real IRI -> NodeId resolution; the sever_residual/reachable_set query over a frozen index is
    // tracked by sociosphere#591. Honest INCONCLUSIVE with the real node id until then.
    let node = cell_iri_to_node_id(&source_id);
    format!(
        r#"{{"schemaVersion":"0.1.0","proofId":"proof-gbrg-{node:016x}","claimType":"scope_bound","statement":"containment of {source_id} ({scope} scope)","epistemicLevel":"speculative","status":"INCONCLUSIVE","source":"{source_id}","nodeId":"{node:016x}","scope":"{scope}","severedScope":"{scope}","baselineReachableCount":0,"residualReachableCount":0,"containedCount":0,"residualReachable":[],"derivation":"resolved IRI to NodeId; sever_residual query pending frozen-index wiring (sociosphere#591)","declaredBy":"agent-registry://gbrg"}}"#
    )
}

/// Graph health/status as a JSON string.
#[napi]
pub fn graph_status() -> String {
    // No process-held frozen index yet (sociosphere#591); report honestly, not a skeleton constant.
    r#"{"status":"no-frozen-index","nodes":0,"edges":0,"frozen":false,"note":"gbrg-napi resolves IRIs deterministically; the frozen-index query surface is pending (sociosphere#591)"}"#.to_string()
}
