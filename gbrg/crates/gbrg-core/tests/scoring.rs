//! Scoring differentiator proof.
//!
//! Builds small graphs (cells + edges, like `tests/smoke.rs`), freezes them, and
//! asserts that `emit_proof_artifact` derives the right `epistemicLevel` AND emits
//! a non-empty explanatory `derivation`. Also proves `churn_frequency` is real by
//! running git against a throwaway repo.

use std::fs;
use std::process::Command;

use gbrg_core::{
    ast_hash_of, blast_radius_score, churn_frequency, emit_proof_artifact, BlastRadiusInputs,
    CellKind, EdgeKind, GraphEdge, ScoringConfig, SemanticCell,
};
use hg_analytics::Store;

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

/// (a) tested cell with few dependents → `empirical`.
/// (b) untested cell with dependents above threshold → `speculative`.
/// Both assert the emitted ProofArtifact's epistemicLevel AND a non-empty derivation.
#[test]
fn epistemic_levels_empirical_and_speculative() {
    let config = ScoringConfig::default(); // dependents_threshold = 15
    let mut store = Store::memory(0);

    // --- Case (a): TARGET_A, tested, 2 dependents (few) ---
    let a = write(&mut store, &cell("target_a", b"fn target_a() {}"));
    let a_caller1 = write(&mut store, &cell("a_caller1", b"fn c1() { target_a(); }"));
    let a_caller2 = write(&mut store, &cell("a_caller2", b"fn c2() { target_a(); }"));
    let a_test = write(&mut store, &cell("a_test", b"#[test] fn t() { target_a(); }"));
    edge(&mut store, a_caller1, a, EdgeKind::Calls);
    edge(&mut store, a_caller2, a, EdgeKind::Calls);
    edge(&mut store, a_test, a, EdgeKind::TestedBy); // A is reached by a test

    // --- Case (b): TARGET_B, NOT tested, 20 dependents (> threshold 15) ---
    let b = write(&mut store, &cell("target_b", b"fn target_b() {}"));
    for i in 0..20 {
        let caller = write(&mut store, &cell(&format!("b_caller{i}"), b"fn bc() { target_b(); }"));
        edge(&mut store, caller, b, EdgeKind::Calls);
    }
    // (no TESTED_BY edge into B)

    let index = store.freeze();

    let cell_a = cell("target_a", b"fn target_a() {}");
    let cell_b = cell("target_b", b"fn target_b() {}");

    // churn supplied directly here (churn_frequency() itself is proved real below).
    let art_a = emit_proof_artifact(&cell_a, &index, 0.0, false, &config);
    let art_b = emit_proof_artifact(&cell_b, &index, 0.0, false, &config);

    // --- (a) empirical ---
    assert_eq!(
        art_a.dependents_count, 2,
        "TARGET_A should have exactly 2 CALLS dependents"
    );
    assert!(
        art_a.test_coverage_reach,
        "TARGET_A should be reached by a test"
    );
    assert_eq!(
        art_a.claim.epistemic_level.as_str(),
        "empirical",
        "tested + few dependents must derive `empirical`; derivation was: {}",
        art_a.derivation
    );
    assert!(
        !art_a.derivation.trim().is_empty(),
        "derivation must be a non-empty explanatory string"
    );
    assert!(
        art_a.derivation.contains("empirical"),
        "derivation should explain the empirical verdict: {}",
        art_a.derivation
    );

    // --- (b) speculative ---
    assert_eq!(
        art_b.dependents_count, 20,
        "TARGET_B should have 20 CALLS dependents"
    );
    assert!(
        !art_b.test_coverage_reach,
        "TARGET_B should have NO test reach"
    );
    assert_eq!(
        art_b.claim.epistemic_level.as_str(),
        "speculative",
        "untested + dependents above threshold must derive `speculative`; derivation was: {}",
        art_b.derivation
    );
    assert!(
        !art_b.derivation.trim().is_empty(),
        "derivation must be a non-empty explanatory string"
    );

    // ProofArtifact must serialise to schema-shaped JSON with the epistemicLevel nested in claim.
    let json_b = art_b.to_json().expect("serialise artifact");
    assert!(json_b.contains("\"epistemicLevel\":\"speculative\""));
    assert!(json_b.contains("\"declared_by\":\"agent-registry://gbrg-scorer\""));
    assert!(json_b.contains("\"blast_radius\":"));

    // blast_radius must stay in [0,1] (feeds SCOPE-D computeRiskScore).
    assert!(
        (0.0..=1.0).contains(&art_a.blast_radius) && (0.0..=1.0).contains(&art_b.blast_radius),
        "blast_radius out of [0,1]: a={}, b={}",
        art_a.blast_radius,
        art_b.blast_radius
    );
    // Untested, high-dependents B must be a *larger* blast radius than tested, low-dep A.
    assert!(
        art_b.blast_radius > art_a.blast_radius,
        "expected B (untested, 20 deps) blast_radius {} > A (tested, 2 deps) {}",
        art_b.blast_radius,
        art_a.blast_radius
    );
}

/// `blast_radius_score` boundaries and monotonicity.
#[test]
fn blast_radius_bounds() {
    let cfg = ScoringConfig::default();
    // All-max: 40+ deps, churn >= 1/day, no tests → 1.0.
    let hot = BlastRadiusInputs {
        dependents_count: 100,
        test_coverage_reach: false,
        churn_frequency: 5.0,
        generated: false,
        dead: false,
    };
    assert!((blast_radius_score(&hot, &cfg) - 1.0).abs() < 1e-9);

    // All-min: 0 deps, 0 churn, tested → 0.0.
    let cold = BlastRadiusInputs {
        dependents_count: 0,
        test_coverage_reach: true,
        churn_frequency: 0.0,
        generated: false,
        dead: false,
    };
    assert_eq!(blast_radius_score(&cold, &cfg), 0.0);
}

/// `rejected` path: a dead cell is excluded but WHY is recorded.
#[test]
fn dead_cell_is_rejected_with_reason() {
    let cfg = ScoringConfig::default();
    let mut store = Store::memory(0);
    let z = cell("zombie", b"fn zombie() {}");
    write(&mut store, &z);
    let index = store.freeze();
    let art = emit_proof_artifact(&z, &index, 0.0, /*dead=*/ true, &cfg);
    assert_eq!(art.claim.epistemic_level.as_str(), "rejected");
    assert!(art.derivation.contains("dead"), "must record WHY: {}", art.derivation);
}

/// `churn_frequency` is REAL: it counts git commits touching a file.
#[test]
fn churn_frequency_reads_real_git_history() {
    let dir = std::env::temp_dir().join(format!("gbrg-churn-{}", std::process::id()));
    let _ = fs::remove_dir_all(&dir);
    fs::create_dir_all(&dir).unwrap();

    let git = |args: &[&str]| {
        Command::new("git")
            .arg("-C")
            .arg(&dir)
            .args(args)
            .output()
            .expect("git runs")
    };
    git(&["init", "-q"]);
    git(&["config", "user.email", "t@t.t"]);
    git(&["config", "user.name", "t"]);

    let f = dir.join("hot.rs");
    for i in 0..3 {
        fs::write(&f, format!("// rev {i}\n")).unwrap();
        git(&["add", "hot.rs"]);
        git(&["commit", "-q", "-m", &format!("c{i}")]);
    }

    // 3 commits over a 30-day window → 0.1 commits/day. Use a wide window so all land.
    let rate = churn_frequency(&dir, "hot.rs", 30).unwrap();
    assert!(rate > 0.0, "expected non-zero churn, got {rate}");
    assert!((rate - 3.0 / 30.0).abs() < 1e-9, "expected 3/30, got {rate}");

    // A path with no history → 0.0 (graceful).
    let none = churn_frequency(&dir, "does-not-exist.rs", 30).unwrap();
    assert_eq!(none, 0.0);

    let _ = fs::remove_dir_all(&dir);
}

// --- helpers ---
fn write(store: &mut Store, c: &SemanticCell) -> hg_analytics::NodeId {
    gbrg_core::write_cell(store, c).unwrap()
}
fn edge(store: &mut Store, from: hg_analytics::NodeId, to: hg_analytics::NodeId, kind: EdgeKind) {
    gbrg_core::write_edge(store, &GraphEdge { from, to, kind, weight: 1.0 }).unwrap();
}
