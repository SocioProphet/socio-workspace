//! # gbrg-analyze SPECTRUM proof — the full epistemicLevel range, end to end.
//!
//! `analyze_file` on a lone file floors every cell to `speculative`: no other file
//! calls in, and no test file reaches it, so `test_coverage_reach` is always false
//! and there are no cross-file dependents. This test builds a **real multi-file
//! tree on disk** and drives it through [`analyze_path`], proving the pipeline
//! now spans the spectrum:
//!
//! * a **tested, low-fan-in** function derives `empirical` (tests observe it, blast
//!   radius bounded);
//! * a **tested, high-fan-in** function derives `bounded` (tests observe it, but
//!   more callers than the threshold — not exhaustively verified);
//! * an **untested, high-fan-in** function derives `speculative` (the canonical
//!   "many callers, no tests" case).
//!
//! It also proves the cross-file resolver is CONSERVATIVE: a symbol name defined in
//! two files (`dup`) is AMBIGUOUS and is never fabricated into an edge.

use std::fs;
use std::path::{Path, PathBuf};

use gbrg_analyze::{analyze_path, analyze_path_report, DEFAULT_CHURN_WINDOW_DAYS};
use gbrg_core::{BlastRadiusProofArtifact, ScoringConfig};

/// Lay down a small crate-shaped tree under a unique temp dir and return its root.
///
/// ```text
/// root/
///   src/lib.rs        tested_low, tested_hub, untested_hub, dup
///   src/callers.rs    th0..th19 (call tested_hub), uh0..uh19 (call untested_hub), dup
///   src/uses_dup.rs   ud (calls the AMBIGUOUS dup)
///   tests/it.rs       #[test] t_runs { tested_low(); tested_hub(); }  (NOT in a macro)
/// ```
fn write_tree() -> PathBuf {
    // Unique per call: tests run concurrently in one process, so a pid-only path
    // would race (one test's remove_dir_all vs another's read).
    use std::sync::atomic::{AtomicU64, Ordering};
    static SEQ: AtomicU64 = AtomicU64::new(0);
    let n = SEQ.fetch_add(1, Ordering::Relaxed);
    let root = std::env::temp_dir().join(format!("gbrg-spectrum-{}-{}", std::process::id(), n));
    let _ = fs::remove_dir_all(&root);
    fs::create_dir_all(root.join("src")).unwrap();
    fs::create_dir_all(root.join("tests")).unwrap();

    // Three defined functions + an ambiguously-named `dup`.
    let lib = "\
pub fn tested_low() -> i32 { 1 }
pub fn tested_hub() -> i32 { 2 }
pub fn untested_hub() -> i32 { 3 }
pub fn dup() -> i32 { 0 }
";
    fs::write(root.join("src/lib.rs"), lib).unwrap();

    // Fan-in: 20 callers of tested_hub, 20 of untested_hub (each a distinct fn).
    // A SECOND `dup` definition makes the name ambiguous across files.
    let mut callers = String::new();
    for i in 0..20 {
        callers.push_str(&format!("pub fn th{i}() {{ tested_hub(); }}\n"));
    }
    for i in 0..20 {
        callers.push_str(&format!("pub fn uh{i}() {{ untested_hub(); }}\n"));
    }
    callers.push_str("pub fn dup() -> i32 { 1 }\n");
    fs::write(root.join("src/callers.rs"), callers).unwrap();

    // A non-macro cross-file call of the ambiguous `dup` — must stay unresolved.
    fs::write(
        root.join("src/uses_dup.rs"),
        "pub fn ud() { let _ = dup(); }\n",
    )
    .unwrap();

    // A REAL test file (parent dir == `tests`). The calls are plain statements, NOT
    // inside a macro, so tree-sitter sees them and they become TESTED_BY edges.
    fs::write(
        root.join("tests/it.rs"),
        "#[test]\nfn t_runs() {\n    let _ = tested_low();\n    let _ = tested_hub();\n}\n",
    )
    .unwrap();

    root
}

fn find<'a>(arts: &'a [BlastRadiusProofArtifact], suffix: &str) -> &'a BlastRadiusProofArtifact {
    arts.iter()
        .find(|a| a.cell_id.ends_with(suffix))
        .unwrap_or_else(|| {
            let ids: Vec<_> = arts.iter().map(|a| a.cell_id.as_str()).collect();
            panic!("no artifact ending in `{suffix}`; cell_ids: {ids:?}")
        })
}

#[test]
fn analyze_path_spans_empirical_bounded_and_speculative() {
    let root = write_tree();
    let config = ScoringConfig::default(); // dependents_threshold = 15

    let arts = analyze_path(&root, &config).expect("analyze_path must walk + score the tree");

    // --- tested, low fan-in → EMPIRICAL ---
    let low = find(&arts, "#tested_low");
    assert!(
        low.test_coverage_reach,
        "tested_low is called by a test → coverage must be true; derivation: {}",
        low.derivation
    );
    assert_eq!(
        low.claim.epistemic_level.as_str(),
        "empirical",
        "tested + few dependents must be empirical; derivation: {}",
        low.derivation
    );

    // --- tested, high fan-in (20 > 15) → BOUNDED ---
    let hub = find(&arts, "#tested_hub");
    assert!(
        hub.test_coverage_reach,
        "tested_hub is called by a test → coverage must be true"
    );
    assert_eq!(
        hub.dependents_count, 20,
        "tested_hub must have 20 CODE dependents (the TESTED_BY caller is not counted)"
    );
    assert_eq!(
        hub.claim.epistemic_level.as_str(),
        "bounded",
        "tested but 20 (> 15) dependents must be bounded; derivation: {}",
        hub.derivation
    );

    // --- untested, high fan-in → SPECULATIVE ---
    let un = find(&arts, "#untested_hub");
    assert!(
        !un.test_coverage_reach,
        "untested_hub has no test path → coverage must be false"
    );
    assert_eq!(
        un.dependents_count, 20,
        "untested_hub must have 20 dependents recovered cross-file"
    );
    assert_eq!(
        un.claim.epistemic_level.as_str(),
        "speculative",
        "untested + many dependents must be speculative; derivation: {}",
        un.derivation
    );

    // The three levels really are DISTINCT — this is the contrast the work order
    // requires (not a uniform `speculative`).
    let levels: std::collections::BTreeSet<&str> = [
        low.claim.epistemic_level.as_str(),
        hub.claim.epistemic_level.as_str(),
        un.claim.epistemic_level.as_str(),
    ]
    .into_iter()
    .collect();
    assert_eq!(
        levels,
        ["bounded", "empirical", "speculative"].into_iter().collect(),
        "expected all three levels present across the tree"
    );

    let _ = fs::remove_dir_all(&root);
}

#[test]
fn cross_file_resolution_is_conservative_on_ambiguous_names() {
    let root = write_tree();
    let config = ScoringConfig::default();

    let report =
        analyze_path_report(&root, &config, DEFAULT_CHURN_WINDOW_DAYS).expect("repo walk");

    // The unambiguous cross-file spine resolved: 20 tested_hub + 20 untested_hub
    // callers, plus the 2 test calls (tested_low, tested_hub) = 42 minimum.
    assert!(
        report.xfile_calls_resolved >= 42,
        "expected >= 42 unique cross-file calls resolved, got {}",
        report.xfile_calls_resolved
    );
    // The two test calls became TESTED_BY edges.
    assert!(
        report.tested_by_edges >= 2,
        "expected >= 2 TESTED_BY edges from the test file, got {}",
        report.tested_by_edges
    );
    // `dup` is defined in two files, so the call in uses_dup.rs is AMBIGUOUS and was
    // NOT fabricated into an edge — the honest, conservative behaviour.
    assert!(
        report.xfile_calls_ambiguous >= 1,
        "expected the ambiguous `dup` call to be counted, got {}",
        report.xfile_calls_ambiguous
    );

    let _ = fs::remove_dir_all(&root);
}

/// Sanity: the whole thing is driven off a REAL directory on disk (not in-memory).
#[test]
fn tree_is_written_to_a_real_directory() {
    let root = write_tree();
    assert!(Path::new(&root).join("src/lib.rs").is_file());
    assert!(Path::new(&root).join("tests/it.rs").is_file());
    let _ = fs::remove_dir_all(&root);
}
