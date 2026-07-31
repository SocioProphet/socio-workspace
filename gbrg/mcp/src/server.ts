/**
 * @socioprophet/gbrg-mcp — MCP server skeleton for the Governed Blast-Radius Graph.
 *
 * BUILD DEFERRED: dependencies are not installed in this scaffold (network may be
 * unavailable). This file is a well-formed skeleton; run `pnpm install && pnpm build`
 * once `@modelcontextprotocol/sdk` is available.
 *
 * Design contract: every tool returns a **ProofArtifact object** — never a bare
 * float. `blast_radius` inside the artifact is a 0.0–1.0 float so it can feed
 * SCOPE-D's `computeRiskScore`. See ../contracts/blast-radius-proof-artifact.schema.json.
 */

/**
 * GBRG-extended ProofArtifact. Mirrors
 * ../contracts/blast-radius-proof-artifact.schema.json, which INHERITS the
 * epistemicLevel enum verbatim from SCOPE-D's proof-artifact schema.
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
  /** Direct dependents (in-degree). */
  dependents_count: number;
  /** Whether a test reaches this cell. */
  test_coverage_reach: boolean;
  /** Churn frequency (unnormalised count/rate). */
  churn_frequency: number;
  /** Normalised blast-radius risk in [0.0, 1.0] — feeds SCOPE-D computeRiskScore. */
  blast_radius: number;
  /** Human-readable WHY this artifact holds. */
  derivation: string;
  /** Producer, e.g. "agent-registry://gbrg/mcp". */
  declared_by: string;
  /** True if the underlying cell is machine-generated (NOT the same as synthetic). */
  generated: boolean;
}

function stubArtifact(statement: string): ProofArtifact {
  return {
    schemaVersion: "0.1.0",
    proofId: "proof-gbrg-mcp-stub",
    claim: {
      claimId: "claim.gbrg.stub",
      claimType: "scope_bound",
      statement,
      epistemicLevel: "speculative",
    },
    status: "INCONCLUSIVE",
    dependents_count: 0,
    test_coverage_reach: false,
    churn_frequency: 0,
    blast_radius: 0.0,
    derivation: "stub: gbrg-mcp not yet wired to gbrg-core (via gbrg-napi)",
    declared_by: "agent-registry://gbrg/mcp",
    generated: false,
  };
}

/**
 * Tool STUBS. When wired, these delegate to gbrg-napi (blast_radius / graph_status)
 * which delegates to gbrg-core's real reads over a frozen GraphIndex.
 */
export const tools = {
  /** Impact of changing a cell — full blast-radius ProofArtifact. */
  impact_query(cellId: string): ProofArtifact {
    return stubArtifact(`impact of ${cellId}`);
  },

  /** Minimal dependency context needed to safely reason about a cell. */
  minimal_context_query(cellId: string): ProofArtifact {
    return stubArtifact(`minimal context for ${cellId}`);
  },

  /** Graph health/status as a ProofArtifact-shaped result. */
  graph_status(): ProofArtifact {
    return stubArtifact("gbrg graph status");
  },
};

/**
 * Server bootstrap — intentionally left as a stub import so this file type-checks
 * as a skeleton without the SDK installed. Uncomment once dependencies exist:
 *
 *   import { Server } from "@modelcontextprotocol/sdk/server/index.js";
 *   import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
 *   const server = new Server({ name: "gbrg-mcp", version: "0.1.0" }, { capabilities: { tools: {} } });
 *   // register impact_query / minimal_context_query / graph_status ...
 *   await server.connect(new StdioServerTransport());
 */
export function main(): void {
  // Build deferred — see module header.
  throw new Error("gbrg-mcp: build deferred; install @modelcontextprotocol/sdk then wire main()");
}
