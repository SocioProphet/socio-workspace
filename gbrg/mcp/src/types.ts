/**
 * GBRG-extended ProofArtifact — mirrors
 * ../contracts/blast-radius-proof-artifact.schema.json, which INHERITS the
 * `epistemicLevel` enum verbatim from SCOPE-D's proof-artifact schema.
 *
 * Every GBRG MCP tool returns a ProofArtifact OBJECT (or a set of them),
 * NEVER a bare float. `blast_radius` is a nested 0.0–1.0 field so it can feed
 * SCOPE-D's `computeRiskScore`.
 *
 * NOTE: `epistemicLevel: "synthetic"` means synthetic/not-real DATA. It does NOT
 * mean "auto-generated code" — that is the separate `generated` boolean.
 */
export type EpistemicLevel =
  | "proved"
  | "bounded"
  | "empirical"
  | "synthetic"
  | "speculative"
  | "rejected";

export interface ProofArtifact {
  schemaVersion: string;
  proofId: string;
  claim: {
    claimId: string;
    claimType: string;
    statement: string;
    epistemicLevel: EpistemicLevel;
  };
  status: "PROVED" | "BOUNDED" | "FAILED" | "BLOCKED" | "INCONCLUSIVE" | "SYNTHETIC_ONLY";
  cell_id?: string;
  dependents_count: number;
  test_coverage_reach: boolean;
  churn_frequency: number;
  /** Normalised blast-radius risk in [0.0, 1.0] — NESTED, never returned bare. */
  blast_radius: number;
  derivation: string;
  declared_by: string;
  generated: boolean;
  /** Optional gate-inclusion annotation added by minimal_context_query. */
  _inclusion?: { priority: string; reason: string };
}

/**
 * Structural guard: a value is a ProofArtifact iff it is an object carrying a
 * nested `claim.epistemicLevel` AND a `derivation` — and is NOT a bare number.
 * Used by the test to assert "never a float".
 */
export function isProofArtifact(v: unknown): v is ProofArtifact {
  if (typeof v !== "object" || v === null || Array.isArray(v)) return false;
  const o = v as Record<string, unknown>;
  const claim = o["claim"] as Record<string, unknown> | undefined;
  return (
    typeof claim === "object" &&
    claim !== null &&
    typeof claim["epistemicLevel"] === "string" &&
    typeof o["derivation"] === "string" &&
    typeof o["blast_radius"] === "number"
  );
}

/** Thrown when a tool call is refused fail-closed — NO artifact is produced. */
export class ToolRefusedError extends Error {
  readonly reasonCode: string;
  readonly ledgerEventId?: string;
  constructor(message: string, reasonCode: string, ledgerEventId?: string) {
    super(message);
    this.name = "ToolRefusedError";
    this.reasonCode = reasonCode;
    this.ledgerEventId = ledgerEventId;
  }
}
