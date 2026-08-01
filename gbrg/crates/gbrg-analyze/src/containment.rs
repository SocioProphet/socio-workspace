//! `gbrg-containment` CLI logic — the AUTHORITATIVE containment engine, invokable
//! over an arbitrary topology.
//!
//! The Go `gbrg-containment` front-door in prophet-platform reimplements the
//! sever/residual semantics over a fixture. This module exposes the REAL
//! `gbrg_core::emit_containment_artifact` over any topology supplied as JSON, so
//! there is one authoritative algorithm rather than a Go copy that can drift.
//!
//! Input (stdin or a file arg), JSON:
//! ```json
//! {
//!   "source": "vvv-648e9d56f1a",
//!   "direction": "downstream",           // downstream (reaches) | upstream (depends-on)
//!   "scope": "full",                     // full | selective
//!   "keep_labels": ["RDP","EDR"],        // for selective: edge labels kept traversable
//!   "cut": ["vvv-648e9d56f1a"],           // nodes to isolate (default: [source])
//!   "allow": ["edr-epp"],                 // allow-listed terminal nodes (EDR/EPP)
//!   "edges": [ {"from":"vvv-648e9d56f1a","to":"wks-2970","label":"SMB"} ]
//! }
//! ```
//!
//! Output: a `ContainmentProofArtifact` JSON with `source`/`residualReachable`
//! HUMANIZED back to the input names (the engine deals in NodeIds; this CLI knows
//! the names). A no-op sever is downgraded to `speculative` by the engine, never a
//! clean containment.

use std::collections::{HashMap, HashSet};

use gbrg_core::{cell_iri_to_node_id, emit_containment_artifact, Direction, SeverScope};
use hg_analytics::{NodeId, Store};
use serde_json::Value;

fn str_list(v: &Value, key: &str) -> Vec<String> {
    v.get(key)
        .and_then(Value::as_array)
        .map(|a| {
            a.iter()
                .filter_map(Value::as_str)
                .map(String::from)
                .collect()
        })
        .unwrap_or_default()
}

/// Register a node name: derive its NodeId, add it once, and remember hex→name.
fn reg(
    store: &mut Store,
    seen: &mut HashSet<NodeId>,
    name_of: &mut HashMap<String, String>,
    name: &str,
) -> NodeId {
    let id = cell_iri_to_node_id(name);
    if seen.insert(id) {
        let _ = store.add_node(id);
    }
    name_of.insert(format!("{id:016x}"), name.to_string());
    id
}

/// Run the authoritative containment computation over the JSON topology and return
/// the `ContainmentProofArtifact` as a JSON string (compact).
pub fn run(input_json: &str) -> Result<String, String> {
    let v: Value = serde_json::from_str(input_json).map_err(|e| format!("invalid JSON: {e}"))?;

    let source = v
        .get("source")
        .and_then(Value::as_str)
        .ok_or("missing 'source'")?
        .to_string();

    let dir = match v
        .get("direction")
        .and_then(Value::as_str)
        .unwrap_or("downstream")
    {
        "downstream" => Direction::Downstream,
        "upstream" => Direction::Upstream,
        other => {
            return Err(format!(
                "unknown direction '{other}' (want downstream|upstream)"
            ))
        }
    };

    let scope = match v.get("scope").and_then(Value::as_str).unwrap_or("full") {
        "full" => SeverScope::Full,
        "selective" => SeverScope::Selective {
            keep_labels: str_list(&v, "keep_labels"),
        },
        other => return Err(format!("unknown scope '{other}' (want full|selective)")),
    };

    let cut_names = {
        let c = str_list(&v, "cut");
        if c.is_empty() {
            vec![source.clone()]
        } else {
            c
        }
    };
    let allow_names = str_list(&v, "allow");
    let edges = v
        .get("edges")
        .and_then(Value::as_array)
        .ok_or("missing 'edges' array")?;

    let mut store = Store::memory(0);
    let mut seen: HashSet<NodeId> = HashSet::new();
    let mut name_of: HashMap<String, String> = HashMap::new();

    let source_id = reg(&mut store, &mut seen, &mut name_of, &source);
    let cut_ids: Vec<NodeId> = cut_names
        .iter()
        .map(|n| reg(&mut store, &mut seen, &mut name_of, n))
        .collect();
    let allow_ids: Vec<NodeId> = allow_names
        .iter()
        .map(|n| reg(&mut store, &mut seen, &mut name_of, n))
        .collect();

    for e in edges {
        let from = e
            .get("from")
            .and_then(Value::as_str)
            .ok_or("edge missing 'from'")?;
        let to = e
            .get("to")
            .and_then(Value::as_str)
            .ok_or("edge missing 'to'")?;
        let label = e.get("label").and_then(Value::as_str).unwrap_or("");
        let f = reg(&mut store, &mut seen, &mut name_of, from);
        let t = reg(&mut store, &mut seen, &mut name_of, to);
        store
            .add_edge(f, t, label)
            .map_err(|err| format!("add_edge {from}->{to}: {err:?}"))?;
    }

    let index = store.freeze();
    let mut artifact =
        emit_containment_artifact(&index, source_id, &cut_ids, &scope, &allow_ids, dir);

    // Humanize the engine's hex NodeIds back to the caller's names.
    if let Some(name) = name_of.get(&artifact.source) {
        artifact.source = name.clone();
    }
    artifact.residual_reachable = artifact
        .residual_reachable
        .iter()
        .map(|hex| name_of.get(hex).cloned().unwrap_or_else(|| hex.clone()))
        .collect();

    artifact.to_json().map_err(|e| format!("serialize: {e}"))
}
