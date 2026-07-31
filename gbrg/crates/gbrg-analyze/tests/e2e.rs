//! # gbrg-analyze END-TO-END proof
//!
//! This is the test that proves the whole GBRG pipeline COMPOSES on a real file:
//! parse → ingest into a HellGraph `Store` → `freeze()` → score → ProofArtifacts.
//! It is deliberately not a unit test of any one feeder — each feeder has its own
//! (`gbrg-parser` parser_test, `gbrg-core` scoring + smoke). This asserts they
//! join up correctly and that the emitted artifact is schema-shaped.
//!
//! Fixture: `tests/fixtures/hub_calls.rs` — `helper` is UNTESTED and called by
//! five other functions, so once ingested it has an in-degree (fan-in) of 5.

use gbrg_analyze::analyze_file;
use gbrg_core::ScoringConfig;
use gbrg_parser::Language;
use serde_json::Value;

fn fixture(name: &str) -> std::path::PathBuf {
    std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("tests")
        .join("fixtures")
        .join(name)
}

/// The load-bearing e2e assertion: the pipeline recovers `helper`'s real fan-in
/// off the graph, derives a real `epistemicLevel` with a non-empty `derivation`,
/// and the artifact serialises with every schema-required field present.
#[test]
fn e2e_untested_hub_function_is_speculative_and_schema_shaped() {
    let config = ScoringConfig::default(); // dependents_threshold = 15
    let artifacts = analyze_file(fixture("hub_calls.rs"), Language::Rust, &config)
        .expect("pipeline must parse + ingest + score the fixture");

    // One artifact per distinct cell; at least the six functions must be present.
    assert!(
        artifacts.len() >= 6,
        "expected >= 6 artifacts (module + 6 fns), got {}",
        artifacts.len()
    );

    // Locate the ProofArtifact for `helper` by its stable code IRI.
    let helper = artifacts
        .iter()
        .find(|a| a.cell_id.ends_with("#helper"))
        .unwrap_or_else(|| {
            let ids: Vec<_> = artifacts.iter().map(|a| a.cell_id.as_str()).collect();
            panic!("no artifact for `helper`; cell_ids were: {ids:?}")
        });

    // (1) The fan-in was REALLY recovered off the frozen index: five callers.
    assert_eq!(
        helper.dependents_count, 5,
        "helper must have 5 CALLS dependents recovered from the graph"
    );

    // (2) No TESTED_BY edge exists (the parser emits none), so coverage is false.
    assert!(
        !helper.test_coverage_reach,
        "helper is untested — no test path should reach it"
    );

    // (3) The epistemicLevel is a REAL derived value, not a placeholder. With no
    // test reach and 5 (< threshold 15) dependents the decision table yields
    // `speculative`. This is the honest verdict for a purely-parsed function.
    assert_eq!(
        helper.claim.epistemic_level.as_str(),
        "speculative",
        "untested hub within the bounded threshold must derive `speculative`; \
         derivation was: {}",
        helper.derivation
    );
    assert_eq!(
        helper.status, "INCONCLUSIVE",
        "speculative maps to the INCONCLUSIVE coarse status"
    );

    // (4) The derivation is a non-empty EXPLANATORY string (not a stub).
    assert!(
        !helper.derivation.trim().is_empty(),
        "derivation must be a non-empty explanatory string"
    );
    assert!(
        helper.derivation.contains("speculative") && helper.derivation.contains("test"),
        "derivation should explain the speculative verdict in terms of test reach: {}",
        helper.derivation
    );

    // (5) blast_radius stays in [0,1] (it feeds SCOPE-D computeRiskScore).
    assert!(
        (0.0..=1.0).contains(&helper.blast_radius),
        "blast_radius out of [0,1]: {}",
        helper.blast_radius
    );

    // (6) The artifact serialises with EVERY schema-required field present, and
    // the nested claim carries its required fields too. (Mirrors
    // contracts/blast-radius-proof-artifact.schema.json `required`.)
    let json = helper.to_json_pretty().expect("serialise ProofArtifact");
    let v: Value = serde_json::from_str(&json).expect("re-parse ProofArtifact JSON");

    for key in [
        "schemaVersion",
        "proofId",
        "claim",
        "status",
        "dependents_count",
        "test_coverage_reach",
        "churn_frequency",
        "blast_radius",
        "derivation",
        "declared_by",
        "generated",
    ] {
        assert!(
            v.get(key).is_some(),
            "schema-required top-level field `{key}` missing from artifact JSON:\n{json}"
        );
    }
    let claim = v.get("claim").expect("claim present");
    for key in ["claimId", "claimType", "statement", "epistemicLevel"] {
        assert!(
            claim.get(key).is_some(),
            "schema-required claim field `{key}` missing:\n{json}"
        );
    }

    // Spot-check the derived values survived serialisation intact.
    assert_eq!(v["claim"]["epistemicLevel"], "speculative");
    assert_eq!(v["status"], "INCONCLUSIVE");
    assert_eq!(v["dependents_count"], 5);
    assert_eq!(v["test_coverage_reach"], false);
    // proofId must satisfy the schema pattern `^proof-[a-z0-9]...`.
    assert!(
        v["proofId"].as_str().unwrap().starts_with("proof-"),
        "proofId must start with `proof-`: {}",
        v["proofId"]
    );
    // declared_by must satisfy `^agent-registry://`.
    assert!(
        v["declared_by"]
            .as_str()
            .unwrap()
            .starts_with("agent-registry://"),
        "declared_by must be an agent-registry IRI: {}",
        v["declared_by"]
    );
}
