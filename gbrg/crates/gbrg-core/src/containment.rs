//! # GBRG containment — governed sever / residual-reachability
//!
//! This module answers the containment question that network isolation (and
//! code-boundary severing) actually asks:
//!
//! > Given a foothold node, what can it reach? If we **isolate** a set of nodes
//! > (cut their edges), what is *still* reachable (the **residual**), and what
//! > becomes unreachable (the **contained** set)?
//!
//! It is deliberately **topology-agnostic**. The engine is pure graph reachability
//! over the frozen [`GraphIndex`] and does not care whether the nodes are
//! [`SemanticCell`](crate::SemanticCell)s (code-impact blast radius) or network
//! endpoints (host isolation). The *same* [`reachable_set`] / [`sever_residual`]
//! serve both; only the graph you load differs. `tests/containment.rs` proves this
//! by running both a code graph and a network-endpoint graph through these
//! functions.
//!
//! ## Why a cut-set BFS rather than mutating the graph
//! The [`GraphIndex`] is frozen and consume-only (we never edit hellgraph). So a
//! "sever" is not a graph mutation — it is a **traversal that refuses to cross the
//! severed edges**. That is correct-by-construction: the underlying graph is never
//! altered, so a reading is reproducible and a receipt over it is replayable.
//!
//! ## Semantics
//! * [`SeverScope::Full`] — a cut node keeps *no* traversable edge. Neighbours in
//!   the `allow` set (the EDR/EPP + configured exclusions) are still recorded as
//!   reachable but are **terminal**: reaching an allow-listed endpoint does not let
//!   the walk pivot onward (EDR comms are not a lateral-movement pivot). This is
//!   the "cut everything but EDR/EPP" isolation.
//! * [`SeverScope::Selective`] — a cut node keeps only the `keep_labels` edges
//!   traversable (the honoured exclusion rules); every other edge from it is cut.
//!
//! A node NOT in the cut set always expands all of its edges normally.

use std::collections::VecDeque;

use hg_analytics::{bfs_on_csr, GraphCore, GraphIndex, NodeId};
use serde::Serialize;

use crate::scoring::{EpistemicLevel, DECLARED_BY};

// ---------------------------------------------------------------------------
// Direction & scope
// ---------------------------------------------------------------------------

/// Which way reachability flows.
///
/// * [`Direction::Downstream`] follows **out-edges** (`from -> to`). For a network
///   graph where an edge `A -> B` means "A can connect to B", this is
///   "what can this foothold reach" — the lateral-movement frontier.
/// * [`Direction::Upstream`] follows **in-edges** (dependents). For a GBRG code
///   graph (`from` DEPENDS ON `to`) this is "what is impacted if this changes" —
///   the same set [`crate::transitive_dependents`] computes.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum Direction {
    Downstream,
    Upstream,
}

/// How much of a cut node's connectivity is severed.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum SeverScope {
    /// Cut every edge from a cut node. Allow-listed neighbours remain reachable
    /// but terminal. This is full network isolation.
    Full,
    /// Keep only edges with these labels traversable from a cut node; cut the rest.
    /// Models an EDR that honours a set of isolation-exclusion rules.
    Selective { keep_labels: Vec<String> },
}

impl SeverScope {
    /// Stable lowercase tag used in the [`ContainmentProofArtifact`].
    pub fn as_str(&self) -> &'static str {
        match self {
            SeverScope::Full => "full",
            SeverScope::Selective { .. } => "selective",
        }
    }
}

// ---------------------------------------------------------------------------
// Neighbour helper (direction-parameterised, label-aware)
// ---------------------------------------------------------------------------

/// Dense neighbours of dense index `d` in `dir`, optionally filtered by `label`.
/// Wraps the substrate's label-aware `in_neighbors` / `out_neighbors`.
fn neighbors<'a>(index: &'a GraphIndex, d: u32, label: Option<&str>, dir: Direction) -> &'a [u32] {
    match dir {
        Direction::Downstream => index.out_neighbors(d, label),
        Direction::Upstream => index.in_neighbors(d, label),
    }
}

// ---------------------------------------------------------------------------
// reachable_set — baseline (no cuts), fast path over the substrate BFS
// ---------------------------------------------------------------------------

/// Every node reachable from `source` in `dir`, excluding `source` itself.
///
/// The no-cut case reuses the substrate's tested [`bfs_on_csr`] over the relevant
/// CSR. This is the baseline blast radius; [`sever_residual`] computes what remains
/// of it after isolation.
pub fn reachable_set(index: &GraphIndex, source: NodeId, dir: Direction) -> Vec<NodeId> {
    let n = index.node_count();
    let src = match index.dense(source) {
        Some(d) => d as usize,
        None => return Vec::new(),
    };
    let (off, nbr) = match dir {
        Direction::Downstream => (index.out_off(), index.out_nbr()),
        Direction::Upstream => (index.in_off(), index.in_nbr()),
    };
    let dist = bfs_on_csr(n, off, nbr, src);
    (0..n)
        .filter(|&i| i != src && dist[i] != u32::MAX)
        .map(|i| index.original(i as u32))
        .collect()
}

// ---------------------------------------------------------------------------
// sever_residual — reachability that refuses to cross severed edges
// ---------------------------------------------------------------------------

/// A containment reading: what a foothold could reach, what it still can after a
/// sever, and what that sever contained. All node lists are sorted for stable
/// output and exclude `source`.
#[derive(Clone, Debug, Serialize)]
pub struct ContainmentReading {
    pub source: NodeId,
    pub direction: Direction,
    pub scope: String,
    /// Nodes that were isolated (their edges severed per `scope`).
    pub cut_nodes: Vec<NodeId>,
    /// Nodes allow-listed as terminal-but-reachable (EDR/EPP + exclusions).
    pub allow: Vec<NodeId>,
    /// Reachable from `source` before the sever.
    pub baseline_reachable: Vec<NodeId>,
    /// Reachable from `source` after the sever.
    pub residual_reachable: Vec<NodeId>,
    /// `baseline_reachable \ residual_reachable` — what the sever contained.
    pub contained: Vec<NodeId>,
}

impl ContainmentReading {
    pub fn baseline_count(&self) -> usize {
        self.baseline_reachable.len()
    }
    pub fn residual_count(&self) -> usize {
        self.residual_reachable.len()
    }
    pub fn contained_count(&self) -> usize {
        self.contained.len()
    }
}

/// Compute the residual reachable set from `source` after isolating `cut_nodes`
/// under `scope`, following `dir`. `allow` nodes remain reachable-but-terminal
/// when reached from a fully-cut node.
///
/// Returns a full [`ContainmentReading`] including the un-cut baseline so callers
/// can show before/after and the contained delta.
pub fn sever_residual(
    index: &GraphIndex,
    source: NodeId,
    cut_nodes: &[NodeId],
    scope: &SeverScope,
    allow: &[NodeId],
    dir: Direction,
) -> ContainmentReading {
    let baseline = reachable_set(index, source, dir);

    let residual_dense = residual_bfs(index, source, cut_nodes, scope, allow, dir);
    let mut residual: Vec<NodeId> = residual_dense
        .into_iter()
        .map(|d| index.original(d))
        .collect();
    residual.sort_unstable();

    let residual_lookup: std::collections::HashSet<NodeId> = residual.iter().copied().collect();
    let mut contained: Vec<NodeId> = baseline
        .iter()
        .copied()
        .filter(|n| !residual_lookup.contains(n))
        .collect();
    contained.sort_unstable();

    let mut baseline_sorted = baseline;
    baseline_sorted.sort_unstable();
    let mut cut_sorted = cut_nodes.to_vec();
    cut_sorted.sort_unstable();
    let mut allow_sorted = allow.to_vec();
    allow_sorted.sort_unstable();

    ContainmentReading {
        source,
        direction: dir,
        scope: scope.as_str().to_string(),
        cut_nodes: cut_sorted,
        allow: allow_sorted,
        baseline_reachable: baseline_sorted,
        residual_reachable: residual,
        contained,
    }
}

/// The cut-aware BFS. Returns the set of dense indices reachable from `source`
/// (excluding `source`) honouring the sever rules. Works in dense-index space.
fn residual_bfs(
    index: &GraphIndex,
    source: NodeId,
    cut_nodes: &[NodeId],
    scope: &SeverScope,
    allow: &[NodeId],
    dir: Direction,
) -> Vec<u32> {
    let n = index.node_count();
    let src = match index.dense(source) {
        Some(d) => d,
        None => return Vec::new(),
    };

    // Translate cut / allow node ids into dense space (nodes absent from the index
    // are simply ignored).
    let cut: std::collections::HashSet<u32> =
        cut_nodes.iter().filter_map(|&id| index.dense(id)).collect();
    let allow_set: std::collections::HashSet<u32> =
        allow.iter().filter_map(|&id| index.dense(id)).collect();

    let mut visited = vec![false; n];
    let mut reached: Vec<u32> = Vec::new();
    let mut queue: VecDeque<u32> = VecDeque::new();

    visited[src as usize] = true;
    queue.push_back(src);

    while let Some(d) = queue.pop_front() {
        // Expansion neighbours (get enqueued) + terminal neighbours (recorded only).
        let (expand, terminal) = successors(index, d, &cut, scope, &allow_set, dir);

        for v in expand {
            if !visited[v as usize] {
                visited[v as usize] = true;
                reached.push(v);
                queue.push_back(v);
            }
        }
        for v in terminal {
            if !visited[v as usize] {
                visited[v as usize] = true;
                reached.push(v); // reachable, but never expanded from here
            }
        }
    }

    reached
}

/// Compute `(nodes_to_expand, terminal_nodes)` for dense node `d` under the sever
/// rules. `terminal_nodes` are reachable but not walked onward (allow-listed
/// endpoints reached from a fully-cut node).
fn successors(
    index: &GraphIndex,
    d: u32,
    cut: &std::collections::HashSet<u32>,
    scope: &SeverScope,
    allow: &std::collections::HashSet<u32>,
    dir: Direction,
) -> (Vec<u32>, Vec<u32>) {
    if !cut.contains(&d) {
        // Not isolated: expand every edge normally.
        return (neighbors(index, d, None, dir).to_vec(), Vec::new());
    }

    // Isolated node: allow-listed neighbours are terminal-reachable regardless of scope.
    let terminal: Vec<u32> = neighbors(index, d, None, dir)
        .iter()
        .copied()
        .filter(|v| allow.contains(v))
        .collect();

    let expand = match scope {
        // Full isolation: nothing expands from a cut node.
        SeverScope::Full => Vec::new(),
        // Selective: only kept-label edges remain traversable. Using the label-aware
        // accessor per kept label is parallel-edge correct (a neighbour is retained
        // iff it is reachable via a kept label), so we never need the full label set.
        SeverScope::Selective { keep_labels } => {
            let mut out: Vec<u32> = Vec::new();
            for label in keep_labels {
                out.extend_from_slice(neighbors(index, d, Some(label.as_str()), dir));
            }
            out.sort_unstable();
            out.dedup();
            // Allow-listed endpoints are terminal by policy: reachable but never a
            // pivot. If a kept label also reaches one, it must NOT be expanded from
            // (it is already recorded in `terminal`), so drop it from the expand set.
            out.retain(|v| !allow.contains(v));
            out
        }
    };

    (expand, terminal)
}

// ---------------------------------------------------------------------------
// ContainmentProofArtifact — governance-native output (mirrors BlastRadius)
// ---------------------------------------------------------------------------

/// Governance-native containment output. Serialises to JSON matching
/// `contracts/containment-proof-artifact.schema.json`. Like the blast-radius
/// artifact it carries WHY it holds: the epistemic level of the reading, the
/// before/after counts, and a human-readable derivation.
#[derive(Clone, Debug, Serialize)]
pub struct ContainmentProofArtifact {
    #[serde(rename = "schemaVersion")]
    pub schema_version: String,
    #[serde(rename = "proofId")]
    pub proof_id: String,
    #[serde(rename = "claimType")]
    pub claim_type: String,
    pub statement: String,
    #[serde(rename = "epistemicLevel")]
    pub epistemic_level: EpistemicLevel,
    pub status: String,
    pub source: String,
    pub scope: String,
    #[serde(rename = "severedScope")]
    pub severed_scope: String,
    #[serde(rename = "baselineReachableCount")]
    pub baseline_reachable_count: usize,
    #[serde(rename = "residualReachableCount")]
    pub residual_reachable_count: usize,
    #[serde(rename = "containedCount")]
    pub contained_count: usize,
    #[serde(rename = "residualReachable")]
    pub residual_reachable: Vec<String>,
    pub derivation: String,
    #[serde(rename = "declaredBy")]
    pub declared_by: String,
}

impl ContainmentProofArtifact {
    pub fn to_json(&self) -> serde_json::Result<String> {
        serde_json::to_string(self)
    }
    pub fn to_json_pretty(&self) -> serde_json::Result<String> {
        serde_json::to_string_pretty(self)
    }
}

/// Producing-agent identity for containment artifacts (schema pattern
/// `^agent-registry://`).
pub const CONTAINMENT_DECLARED_BY: &str = "agent-registry://gbrg-containment";

/// Build a [`ContainmentProofArtifact`] from a [`ContainmentReading`].
///
/// Epistemic level: a containment reading is an **observed** traversal over the
/// frozen index, so it is `empirical` — GBRG asserts no formal proof of network
/// state. A reading that contained nothing at all (`contained_count == 0`) is
/// downgraded to `speculative`: an isolation that severs no reachability is either
/// a mis-scoped cut or a foothold that never had the reach claimed for it, and the
/// operator must not read it as a clean containment. This keeps the artifact from
/// ever presenting a no-op sever as a settled result.
pub fn build_containment_artifact(reading: &ContainmentReading) -> ContainmentProofArtifact {
    let contained = reading.contained_count();
    let (level, level_note) = if contained == 0 {
        (
            EpistemicLevel::Speculative,
            "the sever contained nothing (residual == baseline); treat as a mis-scoped \
             or no-op isolation, not a settled containment",
        )
    } else {
        (
            EpistemicLevel::Empirical,
            "observed over the frozen graph index; residual is a reproducible traversal",
        )
    };

    let source_key = format!("{:016x}", reading.source);
    let proof_id = format!("proof-gbrg-containment-{source_key}");
    let statement = format!(
        "containment of {} ({} scope): baseline reachable {} → residual {} \
         (contained {}) following {} edges",
        source_key,
        reading.scope,
        reading.baseline_count(),
        reading.residual_count(),
        contained,
        match reading.direction {
            Direction::Downstream => "downstream/out",
            Direction::Upstream => "upstream/in",
        }
    );

    let derivation = format!(
        "{statement}; epistemicLevel={} — {level_note}",
        level.as_str()
    );

    ContainmentProofArtifact {
        schema_version: "0.1.0".to_string(),
        proof_id,
        claim_type: "scope_bound".to_string(),
        statement,
        epistemic_level: level,
        status: level.status().to_string(),
        source: source_key,
        scope: reading.scope.clone(),
        severed_scope: reading.scope.clone(),
        baseline_reachable_count: reading.baseline_count(),
        residual_reachable_count: reading.residual_count(),
        contained_count: contained,
        residual_reachable: reading
            .residual_reachable
            .iter()
            .map(|n| format!("{n:016x}"))
            .collect(),
        derivation,
        declared_by: format!("{DECLARED_BY} via {CONTAINMENT_DECLARED_BY}"),
    }
}

/// One-shot: read a containment result and emit its governed artifact.
pub fn emit_containment_artifact(
    index: &GraphIndex,
    source: NodeId,
    cut_nodes: &[NodeId],
    scope: &SeverScope,
    allow: &[NodeId],
    dir: Direction,
) -> ContainmentProofArtifact {
    let reading = sever_residual(index, source, cut_nodes, scope, allow, dir);
    build_containment_artifact(&reading)
}
