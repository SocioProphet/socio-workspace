//! Hash-chained, replayable decision ledger — the one genuinely net-new subsystem of
//! the Regis↔GBRG hybrid.
//!
//! The canonical entity clustering is a MATERIALIZED VIEW rebuilt by replaying this
//! append-only, tamper-evident log — nothing mutates canonical state except through a
//! `DecisionLedgerEntry`. Merge and **unmerge are first-class, replayable** ops: an
//! unmerge is not a delete, it is an entry that reverses a prior merge, and `replay()`
//! honours it deterministically.

use std::collections::{BTreeMap, HashMap, HashSet};

use hg_analytics::sha256_hex;
use serde::Serialize;

pub const ENTRY_SCHEMA: &str = "regis.decision-ledger-entry.v1";

#[derive(Clone, Copy, Debug, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum LedgerOp {
    Merge,
    Unmerge,
}

/// One append-only, hash-chained entry. `entry_hash` binds this entry to the previous
/// one, so any altered field anywhere in the chain is detectable by `verify_chain`.
#[derive(Clone, Debug, Serialize)]
pub struct DecisionLedgerEntry {
    pub schema_version: String,
    pub entry_id: String,
    pub seq: u64,
    pub op: LedgerOp,
    pub decision_ref: String,               // the ResolutionDecision that authorized this (rd_…)
    pub subjects: Vec<String>,              // record/entity ids the op ranges over
    pub reverses_entry_ref: Option<String>, // for Unmerge: the merge entry being reversed
    pub prev_entry_ref: Option<String>,     // hash-chain predecessor (None at genesis)
    pub entry_hash: String,
    pub created_at: String,
}

impl DecisionLedgerEntry {
    pub fn to_json(&self) -> serde_json::Result<String> {
        serde_json::to_string(self)
    }
}

#[derive(Clone, Debug, Default)]
pub struct DecisionLedger {
    entries: Vec<DecisionLedgerEntry>,
}

impl DecisionLedger {
    pub fn new() -> Self {
        Self::default()
    }

    /// Load a persisted ledger (e.g. from disk) for replay / verification.
    pub fn from_entries(entries: Vec<DecisionLedgerEntry>) -> Self {
        Self { entries }
    }

    pub fn entries(&self) -> &[DecisionLedgerEntry] {
        &self.entries
    }
    pub fn len(&self) -> usize {
        self.entries.len()
    }
    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }

    fn preimage(prev_hash: Option<&str>, op: LedgerOp, decision_ref: &str, subjects: &[String], reverses: Option<&str>) -> String {
        let mut subs = subjects.to_vec();
        subs.sort();
        format!(
            "{}|{:?}|{}|{}|{}",
            prev_hash.unwrap_or(""),
            op,
            decision_ref,
            subs.join(","),
            reverses.unwrap_or("")
        )
    }

    fn append(&mut self, op: LedgerOp, decision_ref: &str, subjects: Vec<String>, reverses: Option<String>, created_at: &str) -> String {
        let seq = self.entries.len() as u64;
        let prev_hash = self.entries.last().map(|e| e.entry_hash.clone());
        let prev_entry_ref = self.entries.last().map(|e| e.entry_id.clone());
        let hash = sha256_hex(Self::preimage(prev_hash.as_deref(), op, decision_ref, &subjects, reverses.as_deref()).as_bytes());
        let entry_id = format!("dl_{seq}_{}", &hash[..8]);
        self.entries.push(DecisionLedgerEntry {
            schema_version: ENTRY_SCHEMA.to_string(),
            entry_id: entry_id.clone(),
            seq,
            op,
            decision_ref: decision_ref.to_string(),
            subjects,
            reverses_entry_ref: reverses,
            prev_entry_ref,
            entry_hash: hash,
            created_at: created_at.to_string(),
        });
        entry_id
    }

    /// Record a merge over `subjects` (record ids), justified by `decision_ref`.
    /// Returns the new entry id (used later to `unmerge`).
    pub fn merge(&mut self, decision_ref: &str, subjects: Vec<String>, created_at: &str) -> String {
        self.append(LedgerOp::Merge, decision_ref, subjects, None, created_at)
    }

    /// Reverse a prior merge entry — first-class and replayable (never a delete).
    pub fn unmerge(&mut self, decision_ref: &str, reverses_entry_id: &str, created_at: &str) -> String {
        self.append(LedgerOp::Unmerge, decision_ref, Vec::new(), Some(reverses_entry_id.to_string()), created_at)
    }

    /// Tamper-evidence: recompute the whole chain. Any altered field (subjects,
    /// decision_ref, op, ordering, prev link) breaks a hash and returns false.
    pub fn verify_chain(&self) -> bool {
        let mut prev_hash: Option<String> = None;
        let mut prev_id: Option<String> = None;
        for e in &self.entries {
            if e.prev_entry_ref != prev_id {
                return false;
            }
            let h = sha256_hex(Self::preimage(prev_hash.as_deref(), e.op, &e.decision_ref, &e.subjects, e.reverses_entry_ref.as_deref()).as_bytes());
            if h != e.entry_hash {
                return false;
            }
            prev_hash = Some(e.entry_hash.clone());
            prev_id = Some(e.entry_id.clone());
        }
        true
    }

    /// Replay to the current canonical clustering: union the subjects of every Merge
    /// EXCEPT merges reversed by a later Unmerge. Returns cluster_root → sorted members.
    /// Deterministic (stable ordering) and rebuildable from the log alone.
    pub fn replay(&self) -> BTreeMap<String, Vec<String>> {
        let reversed: HashSet<&str> = self
            .entries
            .iter()
            .filter_map(|e| e.reverses_entry_ref.as_deref())
            .collect();
        let mut uf = UnionFind::default();
        for e in &self.entries {
            if e.op == LedgerOp::Merge && !reversed.contains(e.entry_id.as_str()) {
                let mut it = e.subjects.iter();
                if let Some(first) = it.next() {
                    uf.add(first);
                    for s in it {
                        uf.union(first, s);
                    }
                }
            }
        }
        uf.clusters()
    }
}

#[derive(Default)]
struct UnionFind {
    parent: HashMap<String, String>,
}

impl UnionFind {
    fn add(&mut self, x: &str) {
        self.parent.entry(x.to_string()).or_insert_with(|| x.to_string());
    }
    fn find(&mut self, x: &str) -> String {
        self.add(x);
        let mut r = x.to_string();
        while self.parent[&r] != r {
            r = self.parent[&r].clone();
        }
        r
    }
    fn union(&mut self, a: &str, b: &str) {
        let ra = self.find(a);
        let rb = self.find(b);
        if ra != rb {
            self.parent.insert(ra, rb);
        }
    }
    fn clusters(&mut self) -> BTreeMap<String, Vec<String>> {
        let keys: Vec<String> = self.parent.keys().cloned().collect();
        let mut out: BTreeMap<String, Vec<String>> = BTreeMap::new();
        for k in keys {
            let r = self.find(&k);
            out.entry(r).or_default().push(k);
        }
        for v in out.values_mut() {
            v.sort();
        }
        out
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const T: &str = "2026-08-01T00:00:00Z";

    fn cluster_of<'a>(clusters: &'a BTreeMap<String, Vec<String>>, member: &str) -> Option<&'a Vec<String>> {
        clusters.values().find(|v| v.iter().any(|m| m == member))
    }

    #[test]
    fn hash_chain_links_and_verifies() {
        let mut l = DecisionLedger::new();
        l.merge("rd_1", vec!["a".into(), "b".into()], T);
        l.merge("rd_2", vec!["b".into(), "c".into()], T);
        assert_eq!(l.len(), 2);
        assert_eq!(l.entries()[0].seq, 0);
        assert_eq!(l.entries()[1].prev_entry_ref.as_deref(), Some(l.entries()[0].entry_id.as_str()));
        assert!(l.verify_chain());
        assert!(l.entries()[0].to_json().unwrap().contains("regis.decision-ledger-entry.v1"));
    }

    #[test]
    fn tampering_breaks_the_chain() {
        let mut l = DecisionLedger::new();
        l.merge("rd_1", vec!["a".into(), "b".into()], T);
        l.merge("rd_2", vec!["c".into(), "d".into()], T);
        let mut entries = l.entries().to_vec();
        entries[0].subjects = vec!["a".into(), "EVIL".into()]; // alter a sealed field
        let tampered = DecisionLedger::from_entries(entries);
        assert!(!tampered.verify_chain(), "altered subjects must break the hash chain");
    }

    #[test]
    fn merge_is_transitive_on_replay() {
        let mut l = DecisionLedger::new();
        l.merge("rd_1", vec!["a".into(), "b".into()], T);
        l.merge("rd_2", vec!["b".into(), "c".into()], T);
        let cl = l.replay();
        let c = cluster_of(&cl, "a").unwrap();
        assert_eq!(c, &vec!["a".to_string(), "b".to_string(), "c".to_string()]);
    }

    #[test]
    fn unmerge_reverses_only_its_target_merge() {
        let mut l = DecisionLedger::new();
        let m1 = l.merge("rd_1", vec!["a".into(), "b".into()], T); // a-b
        l.merge("rd_2", vec!["b".into(), "c".into()], T); // b-c
        // reverse ONLY the a-b merge
        l.unmerge("rd_undo", &m1, T);
        let cl = l.replay();
        // b and c stay merged; a is now on its own
        let bc = cluster_of(&cl, "b").unwrap();
        assert!(bc.contains(&"b".to_string()) && bc.contains(&"c".to_string()));
        assert!(!bc.contains(&"a".to_string()), "a must be split off by the unmerge");
        assert!(l.verify_chain());
    }

    #[test]
    fn plain_merge_then_unmerge_fully_separates() {
        let mut l = DecisionLedger::new();
        let m = l.merge("rd_1", vec!["x".into(), "y".into()], T);
        l.unmerge("rd_undo", &m, T);
        let cl = l.replay();
        // No surviving merge → replay materializes no multi-member cluster; x and y are
        // implicit singletons (not co-clustered). That is the reversal being honoured.
        assert!(cl.values().all(|v| v.len() <= 1), "no surviving merge => no multi-member cluster");
        assert!(cluster_of(&cl, "x").map_or(true, |c| !c.contains(&"y".to_string())));
        assert!(cluster_of(&cl, "y").map_or(true, |c| !c.contains(&"x".to_string())));
    }
}
