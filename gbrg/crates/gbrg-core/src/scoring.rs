//! # GBRG scoring — the *differentiator*
//!
//! This module is the whole point of GBRG: instead of returning an opaque float,
//! a changed [`SemanticCell`](crate::SemanticCell) is turned into a
//! **governance-native** [`BlastRadiusProofArtifact`] that carries WHY it holds:
//! its `epistemicLevel` (from SCOPE-D's inherited enum), the raw evidence
//! (`dependents_count`, `test_coverage_reach`, `churn_frequency`), a normalised
//! `blast_radius` in `0.0..=1.0`, and a human-readable `derivation` string.
//!
//! ## Inherited SCOPE-D precedents (cited, not re-invented)
//! * `CONFIDENCE_FLOOR = 0.7` — from
//!   `/Users/michaelheller/dev/SCOPE-D/scripts/export-detection-candidates.js:49`.
//!   Carried into [`ScoringConfig::confidence_floor`] as an overridable default so
//!   GBRG's confidence gate matches SCOPE-D's.
//! * `computeRiskScore` clamps its output to `[0, 1]` — from
//!   `/Users/michaelheller/dev/SCOPE-D/scripts/arsenal-risk-scoring.js:61-69`.
//!   [`blast_radius_score`] deliberately produces the SAME `[0, 1]` scale so its
//!   output can be fed straight into `computeRiskScore` (as the `confidence`
//!   input, or as a severity proxy) without any rescaling.
//!
//! ## Epistemic mapping (work order §2.3, reconciled with the estate)
//! See [`derive_epistemic_level`] for the decision table and rationale.

use crate::{
    dependents_count, reverse_dependents, test_coverage_reach, EdgeKind, GraphIndex, NodeId,
    SemanticCell,
};
use serde::Serialize;
use std::io;
use std::path::Path;
use std::process::Command;

// ---------------------------------------------------------------------------
// ScoringConfig — ALL thresholds live here (acceptance criterion: overridable,
// never buried magic numbers in the mapping functions).
// ---------------------------------------------------------------------------

/// Tunable knobs for blast-radius scoring and epistemic-level derivation.
///
/// Every threshold used by [`derive_epistemic_level`] and [`blast_radius_score`]
/// comes from a field here — none are hardcoded inside the functions. Callers
/// override any field and pass the struct in; [`ScoringConfig::default`] gives
/// documented defaults (some inherited verbatim from SCOPE-D — see module docs).
#[derive(Clone, Debug, Serialize)]
pub struct ScoringConfig {
    /// Direct-dependents count at/below which a *tested* cell is considered
    /// exhaustively enough verified to be `empirical`; above it a tested cell is
    /// only `bounded` (not every caller was exercised). This is the boundary in
    /// the canonical "40 callers, no tests" example. Default `15`.
    pub dependents_threshold: u32,

    /// Confidence gate. **Inherited verbatim** from SCOPE-D
    /// `export-detection-candidates.js` `CONFIDENCE_FLOOR = 0.7`. Not consumed by
    /// the level mapping directly (that is structural), but carried so downstream
    /// gates that fold GBRG output into SCOPE-D use the SAME floor. Default `0.7`.
    pub confidence_floor: f64,

    /// Dependents count at which the dependents term of `blast_radius` SATURATES
    /// to 1.0 (linear ramp from 0). Chosen at `40.0` so the canonical high-blast
    /// "40 callers" case maxes the dependents term. Default `40.0`.
    pub dependents_saturation: f64,

    /// Churn value (commits/day over the window) at which the churn term of
    /// `blast_radius` SATURATES to 1.0. Default `1.0` (≈ a file changed on average
    /// once per day over the window is "maximally churny").
    pub churn_saturation: f64,

    /// Weight of the (normalised) dependents term in `blast_radius`. Default `0.5`.
    pub w_dependents: f64,
    /// Weight of the (normalised) churn term in `blast_radius`. Default `0.3`.
    pub w_churn: f64,
    /// Weight of the coverage term in `blast_radius`. Default `0.2`.
    pub w_coverage: f64,
}

impl Default for ScoringConfig {
    fn default() -> Self {
        Self {
            dependents_threshold: 15,
            confidence_floor: 0.7, // SCOPE-D CONFIDENCE_FLOOR (cited above)
            dependents_saturation: 40.0,
            churn_saturation: 1.0,
            // Weights sum to 1.0 so a weighted sum of three [0,1] terms is itself
            // in [0,1] with no post-hoc rescaling needed.
            w_dependents: 0.5,
            w_churn: 0.3,
            w_coverage: 0.2,
        }
    }
}

// ---------------------------------------------------------------------------
// EpistemicLevel — inherited VERBATIM from SCOPE-D. Not extended.
// ---------------------------------------------------------------------------

/// SCOPE-D's `epistemicLevel` enum, inherited verbatim
/// (`contracts/blast-radius-proof-artifact.schema.json` and
/// SCOPE-D `config/schemas/proof-artifact.schema.json`).
///
/// 🔴 `Synthetic` means synthetic / not-real DATA. It is NOT derived from codegen
/// — codegen is flagged by the separate `generated: bool`. `derive_epistemic_level`
/// therefore never returns `Synthetic`; the variant is kept available for callers
/// that model synthetic data explicitly.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum EpistemicLevel {
    Proved,
    Bounded,
    Empirical,
    Synthetic,
    Speculative,
    Rejected,
}

impl EpistemicLevel {
    /// Stable lowercase string form used in the JSON contract's enum.
    pub fn as_str(&self) -> &'static str {
        match self {
            EpistemicLevel::Proved => "proved",
            EpistemicLevel::Bounded => "bounded",
            EpistemicLevel::Empirical => "empirical",
            EpistemicLevel::Synthetic => "synthetic",
            EpistemicLevel::Speculative => "speculative",
            EpistemicLevel::Rejected => "rejected",
        }
    }

    /// Coarse SCOPE-D ProofArtifact `status` for this level (`status` enum:
    /// PROVED/BOUNDED/FAILED/BLOCKED/INCONCLUSIVE/SYNTHETIC_ONLY). The fine-grained
    /// signal stays in `epistemicLevel`; `status` is the coarse gate.
    pub fn status(&self) -> &'static str {
        match self {
            // Tests reach it and blast radius is bounded → strongest GBRG assertion.
            EpistemicLevel::Proved | EpistemicLevel::Empirical => "PROVED",
            EpistemicLevel::Bounded => "BOUNDED",
            EpistemicLevel::Speculative => "INCONCLUSIVE",
            EpistemicLevel::Rejected => "BLOCKED",
            EpistemicLevel::Synthetic => "SYNTHETIC_ONLY",
        }
    }
}

// ---------------------------------------------------------------------------
// Inputs — the raw evidence a level/score is derived from.
// ---------------------------------------------------------------------------

/// The evidence bundle for a single changed cell. Populated from the frozen
/// [`GraphIndex`] (dependents + test reach), git history (churn), the cell's own
/// `generated` flag, and an external dead-code signal.
#[derive(Clone, Copy, Debug)]
pub struct BlastRadiusInputs {
    /// Direct dependents = in-degree of the cell in the frozen index.
    pub dependents_count: u32,
    /// True if at least one **test function's** call path statically reaches this
    /// cell (an incoming `TESTED_BY` edge, wired only from a real `CALLS` inside a
    /// test function body). This is call-graph REACH, NOT assertion-verified
    /// coverage: it does not prove a test asserts the cell's behaviour, only that a
    /// test executes a path that can invoke it. True behavioural coverage requires
    /// running the suite. Despite the field name it is a *reach* boolean; the name is
    /// kept for schema/back-compat. See [`derive_epistemic_level`].
    pub test_coverage_reach: bool,
    /// Historical change frequency (commits/day over the window). Unnormalised.
    pub churn_frequency: f64,
    /// True if the cell is machine-generated (codegen). Deprioritises but does NOT
    /// change the epistemic level (see module docs / ADR-001 §5).
    pub generated: bool,
    /// True if the cell is flagged dead / scheduled-for-removal. Drives `rejected`.
    pub dead: bool,
}

// ---------------------------------------------------------------------------
// epistemicLevel derivation — THE CORE VALUE.
// ---------------------------------------------------------------------------

/// Derive the `epistemicLevel` for a changed cell, plus a human-readable
/// `derivation` explaining WHY.
///
/// ## What `test-reach` means (soundness of the claim)
/// The "tests reach?" column is `test_coverage_reach`: TRUE iff a **test function's**
/// call path statically reaches this cell (an incoming `TESTED_BY` edge, wired only
/// from a real `CALLS` originating in a test function body — never from an import, a
/// bare mention, or module-scope test scaffolding). It therefore asserts
/// **reachability from a test**, NOT that any test **asserts** this cell's behaviour.
/// `empirical`/`bounded` are the strongest levels this static pipeline emits, and
/// even they claim only test-reach; assertion/line/branch coverage requires RUNNING
/// the suite and is deliberately out of scope here.
///
/// ## Decision table (work order §2.3, reconciled with the estate)
///
/// | `dead` | test-reach? | dependents vs `dependents_threshold` | level         |
/// |--------|-------------|--------------------------------------|---------------|
/// | yes    | (any)       | (any)                                | `rejected`    |
/// | no     | yes         | `<= threshold`                       | `empirical`   |
/// | no     | yes         | `> threshold`                        | `bounded`     |
/// | no     | no          | `> threshold`                        | `speculative` |
/// | no     | no          | `<= threshold`                       | `speculative` |
///
/// Rationale for the two `no-tests` rows collapsing to `speculative`: the work
/// order names `speculative` for "no tests AND dependents > threshold" (the
/// "40 callers, no tests" case). The remaining cell (no tests, *few* dependents)
/// is not covered by any of §2.3's four bullets. Without ANY test evidence there
/// is nothing empirical to stand on, so it is also `speculative` — the low
/// dependents count is still surfaced (it lowers `blast_radius`), and the
/// `derivation` string spells out which of the two speculative shapes it is.
///
/// 🔴 Never returns `Synthetic` (that is synthetic *data*, not codegen) and never
/// returns `Proved` (GBRG asserts no formal proofs). Both remain in the enum for
/// callers that legitimately model them.
///
/// All thresholds come from `config` — none are hardcoded here.
pub fn derive_epistemic_level(
    inputs: &BlastRadiusInputs,
    config: &ScoringConfig,
) -> (EpistemicLevel, String) {
    let t = config.dependents_threshold;
    let d = inputs.dependents_count;

    if inputs.dead {
        return (
            EpistemicLevel::Rejected,
            format!(
                "cell is flagged dead / scheduled-for-removal → rejected (excluded \
                 from review context); recorded so the exclusion is auditable: \
                 {d} dependents, test_coverage_reach={}, generated={}",
                inputs.test_coverage_reach, inputs.generated
            ),
        );
    }

    if inputs.test_coverage_reach {
        if d <= t {
            (
                EpistemicLevel::Empirical,
                format!(
                    "a test function's call path statically reaches this cell and {d} \
                     dependents is within the bounded threshold of {t} → empirical. \
                     NOTE: `empirical` here means TEST-REACHABLE (a test calls into \
                     this cell in the static call graph), NOT assertion-verified — the \
                     signal does not prove any test asserts this cell's behaviour. \
                     True behavioural/line coverage requires RUNNING the suite (out of \
                     scope for this static pipeline)"
                ),
            )
        } else {
            (
                EpistemicLevel::Bounded,
                format!(
                    "a test function's call path reaches this cell (test-reachable, \
                     NOT assertion-verified) but {d} dependents exceeds the bounded \
                     threshold of {t}, so not every caller is exercised → bounded"
                ),
            )
        }
    } else if d > t {
        (
            EpistemicLevel::Speculative,
            format!(
                "no test function's call path reaches this cell and {d} dependents \
                 exceeds the bounded threshold of {t} → speculative (the \"many \
                 callers, no tests\" case)"
            ),
        )
    } else {
        (
            EpistemicLevel::Speculative,
            format!(
                "no test function's call path reaches this cell; {d} dependents is \
                 within the bounded threshold of {t}, but absent any test-reach the \
                 behaviour can only be speculated → speculative"
            ),
        )
    }
}

// ---------------------------------------------------------------------------
// blast_radius_score — normalised 0.0..=1.0 (documented curve, no magic numbers).
// ---------------------------------------------------------------------------

/// Normalise raw evidence into a single `blast_radius` in `0.0..=1.0`, suitable
/// for feeding SCOPE-D's `computeRiskScore` (which also lives in `[0,1]`).
///
/// ## The curve (all knobs from `config`)
/// Three terms, each normalised into `[0,1]`, combined by a weighted sum whose
/// weights sum to 1.0 (so the result is in `[0,1]` with no rescale):
///
/// 1. **dependents term** `d_norm = min(dependents_count / dependents_saturation, 1)`
///    — a linear ramp that saturates at `dependents_saturation` (default 40). More
///    dependents ⇒ larger blast radius.
/// 2. **churn term** `c_norm = min(churn_frequency / churn_saturation, 1)`
///    — linear ramp saturating at `churn_saturation` (default 1.0 commit/day). A
///    hotter file ⇒ larger blast radius.
/// 3. **coverage term** `cov = if test_coverage_reach { 0.0 } else { 1.0 }`
///    — test-REACH shrinks blast-radius risk: a test-reachable cell contributes 0,
///    an unreached cell contributes the full weight. (Binary today because
///    `TESTED_BY` reach is binary; note this is call-graph reach, not assertion
///    coverage — a graded, suite-run coverage fraction can replace it without
///    changing the shape.)
///
/// `blast_radius = clamp(w_dependents*d_norm + w_churn*c_norm + w_coverage*cov, 0, 1)`
///
/// The final `clamp` is belt-and-suspenders: with default weights summing to 1.0
/// and each term in `[0,1]` the sum is already in `[0,1]`, but a caller may set
/// weights that sum to >1, so we clamp to honour the schema's `maximum: 1.0`.
pub fn blast_radius_score(inputs: &BlastRadiusInputs, config: &ScoringConfig) -> f64 {
    let d_norm = if config.dependents_saturation > 0.0 {
        (inputs.dependents_count as f64 / config.dependents_saturation).min(1.0)
    } else {
        0.0
    };
    let c_norm = if config.churn_saturation > 0.0 {
        (inputs.churn_frequency / config.churn_saturation).clamp(0.0, 1.0)
    } else {
        0.0
    };
    let cov = if inputs.test_coverage_reach { 0.0 } else { 1.0 };

    let raw = config.w_dependents * d_norm + config.w_churn * c_norm + config.w_coverage * cov;
    raw.clamp(0.0, 1.0)
}

// ---------------------------------------------------------------------------
// churn_frequency — REAL: shells out to git.
// ---------------------------------------------------------------------------

/// Change frequency of `file_path` = (commits touching it in the last
/// `window_days`) / `window_days`, i.e. commits per day. Shells out to
/// `git -C <repo_dir> log`.
///
/// Robustness:
/// * `window_days == 0` returns the raw commit count (avoids divide-by-zero).
/// * A **shallow** clone simply reports fewer commits (git does not error); we
///   count whatever history is present.
/// * If git is missing or the path is not a repo, we return `Ok(0.0)` rather than
///   erroring — a missing history means "no observed churn", not a hard failure.
pub fn churn_frequency(repo_dir: &Path, file_path: &str, window_days: u32) -> io::Result<f64> {
    let since = format!("{window_days} days ago");
    let output = Command::new("git")
        .arg("-C")
        .arg(repo_dir)
        .args(["log", "--pretty=format:%H"])
        .arg(format!("--since={since}"))
        .arg("--")
        .arg(file_path)
        .output();

    let output = match output {
        Ok(o) => o,
        // git binary not found / not spawnable → treat as no observed churn.
        Err(_) => return Ok(0.0),
    };
    if !output.status.success() {
        // Not a repo, bad path, etc. → no observed churn (graceful).
        return Ok(0.0);
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let commits = stdout.lines().filter(|l| !l.trim().is_empty()).count() as f64;

    if window_days == 0 {
        return Ok(commits);
    }
    Ok(commits / window_days as f64)
}

// ---------------------------------------------------------------------------
// BlastRadiusProofArtifact — the governance-native output.
// ---------------------------------------------------------------------------

/// The claim sub-object (mirrors SCOPE-D ProofArtifact `claim`).
#[derive(Clone, Debug, Serialize)]
pub struct ProofClaim {
    #[serde(rename = "claimId")]
    pub claim_id: String,
    #[serde(rename = "claimType")]
    pub claim_type: String,
    pub statement: String,
    #[serde(rename = "epistemicLevel")]
    pub epistemic_level: EpistemicLevel,
}

/// The GBRG governance-native output. Serialises to JSON matching
/// `contracts/blast-radius-proof-artifact.schema.json`. `cell_id` is an additive
/// GBRG field (the contract does not set `additionalProperties: false`).
#[derive(Clone, Debug, Serialize)]
pub struct BlastRadiusProofArtifact {
    #[serde(rename = "schemaVersion")]
    pub schema_version: String,
    #[serde(rename = "proofId")]
    pub proof_id: String,
    pub claim: ProofClaim,
    pub status: String,
    /// Additive GBRG field: the stable code IRI of the scored cell.
    pub cell_id: String,
    pub dependents_count: u32,
    pub test_coverage_reach: bool,
    pub churn_frequency: f64,
    pub blast_radius: f64,
    pub derivation: String,
    pub declared_by: String,
    pub generated: bool,
}

impl BlastRadiusProofArtifact {
    /// Serialise to a JSON string (schema-shaped).
    pub fn to_json(&self) -> serde_json::Result<String> {
        serde_json::to_string(self)
    }
    /// Serialise to a pretty JSON string.
    pub fn to_json_pretty(&self) -> serde_json::Result<String> {
        serde_json::to_string_pretty(self)
    }
}

/// Placeholder producing-agent identity (schema pattern `^agent-registry://`).
pub const DECLARED_BY: &str = "agent-registry://gbrg-scorer";

/// Build a [`BlastRadiusProofArtifact`] for `cell` from an already-derived
/// [`BlastRadiusInputs`] evidence bundle. This is the pure, index-free core used
/// by tests and by [`emit_proof_artifact`].
pub fn build_proof_artifact(
    cell: &SemanticCell,
    inputs: &BlastRadiusInputs,
    config: &ScoringConfig,
) -> BlastRadiusProofArtifact {
    let (level, derivation) = derive_epistemic_level(inputs, config);
    let blast = blast_radius_score(inputs, config);

    // Stable, schema-valid proofId: `proof-` + lowercased node-id hex.
    let proof_id = format!("proof-gbrg-{:016x}", cell.node_id());
    let statement = format!(
        "blast radius of {} ({}): {} direct dependents, test_coverage_reach={}, \
         churn={:.4}/day → {}",
        cell.cell_id,
        cell.symbol_name,
        inputs.dependents_count,
        inputs.test_coverage_reach,
        inputs.churn_frequency,
        level.as_str()
    );

    BlastRadiusProofArtifact {
        schema_version: "0.1.0".to_string(),
        proof_id,
        claim: ProofClaim {
            claim_id: format!("claim.gbrg.blast_radius.{:016x}", cell.node_id()),
            claim_type: "scope_bound".to_string(),
            statement,
            epistemic_level: level,
        },
        status: level.status().to_string(),
        cell_id: cell.cell_id.clone(),
        dependents_count: inputs.dependents_count,
        test_coverage_reach: inputs.test_coverage_reach,
        churn_frequency: inputs.churn_frequency,
        blast_radius: blast,
        derivation,
        declared_by: DECLARED_BY.to_string(),
        generated: inputs.generated,
    }
}

/// Blast-radius **code dependents** of `cell` = in-degree EXCLUDING `TESTED_BY`
/// edges.
///
/// Why not just `crate::dependents_count` (raw in-degree)? A `TESTED_BY` in-edge
/// means "a test reaches this cell" — that is *coverage*, already carried by the
/// separate `test_coverage_reach` boolean. Counting it as a dependent would
/// double-count the very signal that lowers blast radius, and would let adding a
/// test *raise* a cell's dependents_count. Blast-radius "dependents" are code
/// callers (`CALLS`/`INHERITS`/`IMPORTS`), so we subtract the `TESTED_BY`
/// in-neighbours. (This sharpens the schema's prose "in-degree" toward its stated
/// intent, "direct dependents"; the numeric field stays a non-negative integer.)
pub fn code_dependents_count(index: &GraphIndex, cell: NodeId) -> u32 {
    let total = dependents_count(index, cell).unwrap_or(0);
    let tested_by =
        reverse_dependents(index, cell, Some(EdgeKind::TestedBy.as_label())).len() as u32;
    total.saturating_sub(tested_by)
}

/// Emit a [`BlastRadiusProofArtifact`] for `cell` by reading its blast-radius
/// evidence from the frozen `index` (dependents + test reach are REAL reads),
/// combined with a supplied `churn_frequency` (from [`churn_frequency`]) and an
/// external `dead` flag. `cell.generated` is carried through.
///
/// `dependents_count`/`test_coverage_reach` for a cell absent from the index
/// default to `0`/`false` (an unreferenced or brand-new cell).
pub fn emit_proof_artifact(
    cell: &SemanticCell,
    index: &GraphIndex,
    churn: f64,
    dead: bool,
    config: &ScoringConfig,
) -> BlastRadiusProofArtifact {
    let node: NodeId = cell.node_id();
    let inputs = BlastRadiusInputs {
        dependents_count: code_dependents_count(index, node),
        test_coverage_reach: test_coverage_reach(index, node),
        churn_frequency: churn,
        generated: cell.generated,
        dead,
    };
    build_proof_artifact(cell, &inputs, config)
}
