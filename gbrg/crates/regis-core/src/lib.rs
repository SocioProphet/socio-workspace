//! # regis-core — Regis Entity Graph core
//!
//! Explainable, policy-vetoed entity resolution on the SAME substrate GBRG uses
//! (`hg_analytics::graphdb`, consume-only) and sharing GBRG's SCOPE-D
//! [`EpistemicLevel`] — the "one proof ancestor" of the Regis↔GBRG hybrid.
//!
//! Where GBRG answers "what is the blast radius of touching this code cell", Regis
//! answers "do these observed records resolve to one canonical entity, and *why*".
//! Both are typed nodes + typed edges + a proof-carrying decision over the same
//! frozen-CSR graph engine.
//!
//! First increment: node/edge model, the [`ResolutionDecision`] proof builder, and an
//! explainable, policy-constrained [`resolve`]. The hash-chained, replayable
//! `DecisionLedger` (merge/unmerge) is the next increment.

use std::collections::BTreeMap;
use std::io;

use hg_analytics::{sha256_hex, NodeId, Prop, Store};
use serde::Serialize;

// Re-export the shared SCOPE-D proof level so callers use one enum across GBRG + Regis.
pub use gbrg_core::EpistemicLevel;

// The hash-chained, replayable decision ledger (merge/unmerge as first-class ops).
pub mod ledger;
pub use ledger::{DecisionLedger, DecisionLedgerEntry, LedgerOp};

// ── Node property keys (namespaced, mirroring gbrg's `gbrg.*` convention) ──
pub const PROP_REGIS_ID: &str = "regis.id";
pub const PROP_ENTITY_TYPE: &str = "regis.entity_type";
pub const PROP_IDENTITY_STATE: &str = "regis.identity_state";
pub const PROP_SCOPE_FLAGS: &str = "regis.scope_flags";
pub const PROP_SOURCE: &str = "regis.source";
pub const PROP_BLOCKING_KEY: &str = "regis.blocking_key";
pub const PROP_TOPICS: &str = "regis.topics";

/// Deterministic stable IRI → `graphdb` `NodeId`: first 8 bytes of sha256(iri) as a
/// big-endian u64 (same construction as gbrg's `cell_iri_to_node_id`).
pub fn entity_iri_to_node_id(iri: &str) -> NodeId {
    let hex = sha256_hex(iri.as_bytes());
    u64::from_str_radix(&hex[..16], 16).expect("sha256_hex returns valid hex")
}

/// A clustered identity (person/org/device/…) — the canonical node.
#[derive(Clone, Debug)]
pub struct CanonicalEntity {
    pub entity_id: String, // stable IRI, e.g. "regis://entity/ce_michael"
    pub entity_type: String,
    pub identity_state: String,
    pub scope_flags: Vec<String>,
}

impl CanonicalEntity {
    pub fn node_id(&self) -> NodeId {
        entity_iri_to_node_id(&self.entity_id)
    }
}

/// An immutable observed record (NER/EL leaf) projected from Event-IR.
#[derive(Clone, Debug)]
pub struct SourceRecord {
    pub record_id: String, // stable IRI, e.g. "regis://record/sr_0001"
    pub source: String,
    pub blocking_key: String, // candidate-generation key (e.g. normalized email)
    pub topics: Vec<String>,  // prime-topics carried from the source (for policy veto)
}

impl SourceRecord {
    pub fn node_id(&self) -> NodeId {
        entity_iri_to_node_id(&self.record_id)
    }
}

/// Regis edge kinds (distinct from GBRG's code-edge kinds).
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum RegisEdgeKind {
    RecordToEntity,
    EntityToEntity,
    ConcordanceLink,
}

impl RegisEdgeKind {
    pub fn as_label(&self) -> &'static str {
        match self {
            RegisEdgeKind::RecordToEntity => "RECORD_TO_ENTITY",
            RegisEdgeKind::EntityToEntity => "ENTITY_TO_ENTITY",
            RegisEdgeKind::ConcordanceLink => "CONCORDANCE_LINK",
        }
    }
}

// ── Write path (on the shared graphdb Store) ──
pub fn write_entity(store: &mut Store, e: &CanonicalEntity) -> io::Result<NodeId> {
    let id = e.node_id();
    store.add_node(id)?;
    store.set_prop(id, PROP_REGIS_ID, Prop::Text(e.entity_id.clone()))?;
    store.set_prop(id, PROP_ENTITY_TYPE, Prop::Text(e.entity_type.clone()))?;
    store.set_prop(id, PROP_IDENTITY_STATE, Prop::Text(e.identity_state.clone()))?;
    store.set_prop(id, PROP_SCOPE_FLAGS, Prop::Text(e.scope_flags.join(",")))?;
    Ok(id)
}

pub fn write_record(store: &mut Store, r: &SourceRecord) -> io::Result<NodeId> {
    let id = r.node_id();
    store.add_node(id)?;
    store.set_prop(id, PROP_REGIS_ID, Prop::Text(r.record_id.clone()))?;
    store.set_prop(id, PROP_SOURCE, Prop::Text(r.source.clone()))?;
    store.set_prop(id, PROP_BLOCKING_KEY, Prop::Text(r.blocking_key.clone()))?;
    store.set_prop(id, PROP_TOPICS, Prop::Text(r.topics.join(",")))?;
    Ok(id)
}

/// Add a labelled Regis edge. PRECONDITION: both endpoints already written.
pub fn write_edge(store: &mut Store, from: NodeId, to: NodeId, kind: RegisEdgeKind) -> io::Result<()> {
    store.add_edge(from, to, kind.as_label())?;
    Ok(())
}

// ── The decision (proof-carrying, explainable, policy-vetoed) ──
#[derive(Clone, Copy, Debug, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Decision {
    Merge,
    PossibleMatch,
    Blocked,
    Unrelated,
}

#[derive(Clone, Debug, Serialize)]
pub struct FeatureContribution {
    pub feature: String,
    pub contribution: f64,
}

#[derive(Clone, Debug, Serialize)]
pub struct PolicyVerdict {
    pub verdict: String, // "allowed" | "vetoed" | "review_required"
    #[serde(skip_serializing_if = "Option::is_none")]
    pub forbidden_mixture: Option<Vec<String>>,
}

#[derive(Clone, Debug, Serialize)]
pub struct Confidence {
    pub score: f64,
    pub uncertainty: f64,
}

/// The required externalized output of every material resolution op — decision +
/// explanation + policy verdict + confidence/uncertainty + reversibility + the
/// shared SCOPE-D `epistemic_level`. Mirrors gbrg's `BlastRadiusProofArtifact`.
#[derive(Clone, Debug, Serialize)]
pub struct ResolutionDecision {
    pub schema_version: String,
    pub decision_id: String,
    pub operation: String,
    pub decision: Decision,
    pub subjects: Vec<String>,
    pub explanation: Vec<FeatureContribution>,
    pub policy_verdict: PolicyVerdict,
    pub confidence: Confidence,
    pub reversible: bool,
    #[serde(rename = "epistemicLevel")]
    pub epistemic_level: EpistemicLevel,
    pub declared_by: String,
}

pub const DECLARED_BY: &str = "agent-registry://regis-resolver";
pub const SCHEMA_VERSION: &str = "regis.resolution-decision.v1";

impl ResolutionDecision {
    pub fn to_json(&self) -> serde_json::Result<String> {
        serde_json::to_string(self)
    }
}

fn decision_id_for(subjects: &[String]) -> String {
    let mut sorted = subjects.to_vec();
    sorted.sort();
    format!("rd_{}", &sha256_hex(sorted.join("|").as_bytes())[..12])
}

/// Policy: forbidden prime-topic mixtures (e.g. `[["patient","ad_tech"]]`). A merge
/// whose combined topics contain a forbidden set is VETOED regardless of score.
#[derive(Clone, Debug, Default)]
pub struct Policy {
    pub forbidden_mixtures: Vec<Vec<String>>,
}

impl Policy {
    fn forbidden_hit(&self, active: &[String]) -> Option<Vec<String>> {
        for m in &self.forbidden_mixtures {
            if m.iter().all(|t| active.iter().any(|a| a == t)) {
                let mut v = m.clone();
                v.sort();
                return Some(v);
            }
        }
        None
    }
}

/// Explainable, policy-constrained resolution. Groups records by blocking key; each
/// group of ≥2 yields a `ResolutionDecision`. A forbidden prime-topic mixture over the
/// group's combined topics produces a structural `Blocked` (veto), not a score.
/// Singletons yield no decision. Deterministic (stable ordering + hashed id).
pub fn resolve(records: &[SourceRecord], policy: &Policy) -> Vec<ResolutionDecision> {
    let mut groups: BTreeMap<String, Vec<&SourceRecord>> = BTreeMap::new();
    for r in records {
        groups.entry(r.blocking_key.clone()).or_default().push(r);
    }

    let mut out = Vec::new();
    for (key, members) in groups {
        if members.len() < 2 {
            continue;
        }
        let mut subjects: Vec<String> = members.iter().map(|r| r.record_id.clone()).collect();
        subjects.sort();

        let mut topics: Vec<String> = Vec::new();
        for m in &members {
            for t in &m.topics {
                if !topics.contains(t) {
                    topics.push(t.clone());
                }
            }
        }

        if let Some(fset) = policy.forbidden_hit(&topics) {
            out.push(ResolutionDecision {
                schema_version: SCHEMA_VERSION.to_string(),
                decision_id: decision_id_for(&subjects),
                operation: "resolve".to_string(),
                decision: Decision::Blocked,
                subjects,
                explanation: vec![FeatureContribution {
                    feature: format!("shared_blocking_key:{key}"),
                    contribution: 1.0,
                }],
                policy_verdict: PolicyVerdict {
                    verdict: "vetoed".to_string(),
                    forbidden_mixture: Some(fset),
                },
                confidence: Confidence { score: 0.0, uncertainty: 1.0 },
                reversible: false,
                epistemic_level: EpistemicLevel::Rejected,
                declared_by: DECLARED_BY.to_string(),
            });
            continue;
        }

        let n = members.len() as f64;
        let score = 1.0 - 1.0 / n; // 2→0.5, 3→0.67, …
        let level = if n >= 3.0 { EpistemicLevel::Bounded } else { EpistemicLevel::Empirical };
        out.push(ResolutionDecision {
            schema_version: SCHEMA_VERSION.to_string(),
            decision_id: decision_id_for(&subjects),
            operation: "resolve".to_string(),
            decision: Decision::Merge,
            subjects,
            explanation: vec![FeatureContribution {
                feature: format!("shared_blocking_key:{key}"),
                contribution: score,
            }],
            policy_verdict: PolicyVerdict { verdict: "allowed".to_string(), forbidden_mixture: None },
            confidence: Confidence { score, uncertainty: 1.0 - score },
            reversible: true,
            epistemic_level: level,
            declared_by: DECLARED_BY.to_string(),
        });
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn rec(id: &str, key: &str, topics: &[&str]) -> SourceRecord {
        SourceRecord {
            record_id: format!("regis://record/{id}"),
            source: "test".to_string(),
            blocking_key: key.to_string(),
            topics: topics.iter().map(|s| s.to_string()).collect(),
        }
    }

    #[test]
    fn deterministic_node_ids() {
        assert_eq!(entity_iri_to_node_id("regis://record/a"), entity_iri_to_node_id("regis://record/a"));
        assert_ne!(entity_iri_to_node_id("a"), entity_iri_to_node_id("b"));
    }

    #[test]
    fn merge_two_records_sharing_a_key() {
        let recs = vec![rec("sr_a", "m@ex.org", &["personal"]), rec("sr_b", "m@ex.org", &["personal"])];
        let decisions = resolve(&recs, &Policy::default());
        assert_eq!(decisions.len(), 1);
        let d = &decisions[0];
        assert_eq!(d.decision, Decision::Merge);
        assert_eq!(d.policy_verdict.verdict, "allowed");
        assert!(d.confidence.score > 0.0 && d.reversible);
        assert_eq!(d.subjects.len(), 2);
        assert!(d.to_json().unwrap().contains("epistemicLevel"));
    }

    #[test]
    fn forbidden_mixture_is_vetoed_not_scored() {
        let recs = vec![rec("sr_a", "k", &["patient"]), rec("sr_b", "k", &["ad_tech"])];
        let policy = Policy { forbidden_mixtures: vec![vec!["patient".into(), "ad_tech".into()]] };
        let d = &resolve(&recs, &policy)[0];
        assert_eq!(d.decision, Decision::Blocked);
        assert_eq!(d.policy_verdict.verdict, "vetoed");
        assert_eq!(d.epistemic_level, EpistemicLevel::Rejected);
        assert!(!d.reversible);
        assert_eq!(d.policy_verdict.forbidden_mixture.as_ref().unwrap(), &vec!["ad_tech".to_string(), "patient".to_string()]);
    }

    #[test]
    fn singletons_yield_no_decision() {
        let recs = vec![rec("sr_a", "k1", &[]), rec("sr_b", "k2", &[])];
        assert!(resolve(&recs, &Policy::default()).is_empty());
    }

    #[test]
    fn writes_onto_the_shared_graphdb_substrate() {
        let mut store = Store::memory(0);
        let e = CanonicalEntity {
            entity_id: "regis://entity/ce_1".into(),
            entity_type: "PERSON".into(),
            identity_state: "resolved".into(),
            scope_flags: vec!["CITIZEN_FOG".into()],
        };
        let eid = write_entity(&mut store, &e).unwrap();
        let r1 = write_record(&mut store, &rec("sr_a", "k", &["personal"])).unwrap();
        let r2 = write_record(&mut store, &rec("sr_b", "k", &["personal"])).unwrap();
        write_edge(&mut store, r1, eid, RegisEdgeKind::RecordToEntity).unwrap();
        write_edge(&mut store, r2, eid, RegisEdgeKind::RecordToEntity).unwrap();
        let index = store.freeze();
        assert_eq!(gbrg_core::dependents_count(&index, eid), Some(2));
    }
}
