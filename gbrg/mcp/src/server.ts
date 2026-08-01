/**
 * @socioprophet/gbrg-mcp — the agent-facing MCP surface for the Governed
 * Blast-Radius Graph, conformant to the a2a-mcp-zero-trust spec and built ON the
 * `gbrg/governance` gate foundation.
 *
 * Three READ-ONLY tools, each re-deriving the blast-radius graph for the
 * requested path per call (NOT served from a pre-frozen snapshot) and returning
 * a ProofArtifact OBJECT (never a bare float):
 *   - impact_query(path, cellId?)       -> the blast-radius ProofArtifact(s) for a target
 *   - minimal_context_query(path)       -> only the cells the GATE INCLUDES
 *   - graph_status(path)                -> counts + epistemicLevel spread, as a ProofArtifact
 *
 * ZERO-TRUST, PER CALL (see gate.ts / mcp_gate.py):
 *   1. AUTHORIZE (who) via the gbrg/governance authorize path (agent-registry
 *      authorize.py), FAIL-CLOSED, actor = agent-registry://gbrg/mcp,
 *      SPIFFE id spiffe://socioprophet/mcp/gbrg.
 *   2. CONFINE (which resource) via confine.ts (M4): the requested path is
 *      canonicalized (symlinks + `..` resolved) and must fall inside the
 *      configured allowed root, else the call is REFUSED fail-closed with a
 *      ledgered deny BEFORE any analysis runs. Authorization gates WHO may call;
 *      confinement gates WHICH resource — both must pass.
 *   3. EVERY call (served or refused) emits a hash-chained LedgerEvent via the
 *      gate's durable ledger. No ledger event => the call fails closed.
 *   4. On refusal: NO tool result is produced (a ProofArtifact is never returned).
 *
 * The tools declare NO write/exec/egress — see registry/capability_registry.json.
 */
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

import { ProofArtifact, ToolRefusedError } from "./types.js";
import { AnalyzeFn, makeAnalyze } from "./analyze.js";
import { confinePath } from "./confine.js";
import {
  AuthorizeFn,
  EmitRefusalFn,
  EmitResultFn,
  FilterIncludedFn,
  GateConfig,
  MCP_AGENT_REF,
  SPIFFE_ID,
  makeAuthorize,
  makeEmitRefusal,
  makeEmitResult,
  makeFilterIncluded,
} from "./gate.js";

export const TOOL_NAMES = ["impact_query", "minimal_context_query", "graph_status"] as const;
export type ToolName = (typeof TOOL_NAMES)[number];

/** Injected collaborators — real implementations by default, fakeable in tests. */
export interface ServerDeps {
  analyze: AnalyzeFn;
  authorize: AuthorizeFn;
  emitResult: EmitResultFn;
  emitRefusal: EmitRefusalFn;
  filterIncluded: FilterIncludedFn;
}

/** The MCP agent's CURRENT authority + the resource boundary it may analyze. */
export interface RuntimeConfig {
  /** Path to the agent's AgentAuthorityCurrentState file (active/suspended). */
  stateFile?: string;
  status?: string;
  /** Default graph root used by graph_status when no path is supplied. */
  graphRoot: string;
  /**
   * M4 resource confinement: the ONLY directory subtree whose source the tools
   * may analyze. Any requested path resolving (symlinks + `..`) outside this
   * root is refused fail-closed. Defaults to `graphRoot` when unset.
   */
  allowedRoot?: string;
}

// --------------------------------------------------------------------------- //
// Tool result shapes. Each carries ProofArtifact OBJECT(s), never a bare float.
// --------------------------------------------------------------------------- //
export interface ImpactResult {
  tool: "impact_query";
  target: { path: string; cellId?: string };
  matched: number;
  /** The primary ProofArtifact (present iff exactly-one / cellId resolved). */
  artifact?: ProofArtifact;
  artifacts: ProofArtifact[];
}
export interface MinimalContextResult {
  tool: "minimal_context_query";
  target: { path: string };
  total: number;
  included_count: number;
  included: ProofArtifact[];
}
export interface GraphStatusResult {
  tool: "graph_status";
  /** graph_status is itself expressed AS a ProofArtifact (never a bare count). */
  artifact: ProofArtifact;
  counts: { cells: number };
  epistemicLevelSpread: Record<string, number>;
}

function matchCell(a: ProofArtifact, cellId: string): boolean {
  const id = a.cell_id ?? "";
  return id === cellId || id.endsWith(`#${cellId}`) || id.split("#").pop() === cellId;
}

/** graph_status ProofArtifact — a real (empirical) claim about the graph re-derived for this call. */
function graphStatusArtifact(artifacts: ProofArtifact[], spread: Record<string, number>): ProofArtifact {
  const n = artifacts.length;
  const spreadStr = Object.entries(spread)
    .map(([k, v]) => `${k}=${v}`)
    .join(" ");
  return {
    schemaVersion: "0.1.0",
    proofId: "proof-gbrg-graph-status",
    claim: {
      claimId: "claim.gbrg.graph_status",
      claimType: "graph_summary",
      statement: `graph (re-derived this call): ${n} scored cell(s); epistemicLevel spread → ${spreadStr || "(none)"}`,
      // Directly measured over the freshly analyzed cells -> empirical DATA, not synthetic.
      epistemicLevel: "empirical",
    },
    status: n > 0 ? "BOUNDED" : "INCONCLUSIVE",
    dependents_count: 0,
    test_coverage_reach: false,
    churn_frequency: 0,
    blast_radius: 0.0,
    derivation: `counted ${n} ProofArtifact(s) emitted by gbrg-analyze over the confined path (re-derived this call); spread computed by tallying claim.epistemicLevel`,
    declared_by: MCP_AGENT_REF,
    generated: false,
  };
}

// --------------------------------------------------------------------------- //
// CORE: run one tool under the zero-trust gate. Throws ToolRefusedError on a
// fail-closed refusal (no result is produced). This is what the SDK handler and
// the test both drive.
// --------------------------------------------------------------------------- //
export async function runTool(
  name: ToolName,
  args: Record<string, unknown>,
  deps: ServerDeps,
  config: RuntimeConfig,
): Promise<ImpactResult | MinimalContextResult | GraphStatusResult> {
  // 1. AUTHORIZE + mandatory ledger event (fail-closed).
  const authz = await deps.authorize({
    tool: name,
    args,
    stateFile: config.stateFile,
    status: config.status,
  });
  if (authz.verdict !== "allow" || !authz.ledgerWritten) {
    throw new ToolRefusedError(
      `REFUSED (fail-closed): tool=${name} verdict=${authz.verdict} reason=${authz.reasonCode}; ` +
        `no ProofArtifact produced (ledger_written=${authz.ledgerWritten})`,
      authz.reasonCode,
      authz.event?.event_id,
    );
  }

  // 2. CONFINE (which resource): authorization gated WHO may call; this gates
  //    WHICH resource. The requested path is canonicalized (symlinks + `..`
  //    resolved) and must fall inside the allowed root, else REFUSE fail-closed
  //    with a ledgered deny BEFORE any analysis runs. Both gates must pass.
  const allowedRoot = config.allowedRoot ?? config.graphRoot;
  const requestedPath =
    name === "graph_status" ? String(args.path ?? config.graphRoot) : String(args.path ?? "");
  if (!requestedPath) throw new Error(`${name} requires 'path'`);
  const confinement = confinePath(requestedPath, allowedRoot);
  if (!confinement.allowed) {
    // Ledger the refusal BEFORE any analyze() runs — no source tree is parsed.
    const refusal = await deps.emitRefusal(name, confinement.reasonCode ?? "path_out_of_root", args);
    throw new ToolRefusedError(
      `REFUSED (fail-closed): tool=${name} reason=${confinement.reasonCode} ` +
        `requested="${requestedPath}" resolved="${confinement.canonical}" is outside allowed root ` +
        `"${confinement.root}"; no analysis performed, no ProofArtifact produced ` +
        `(ledger_written=${refusal.ledgerWritten})`,
      confinement.reasonCode ?? "path_out_of_root",
      refusal.event?.event_id,
    );
  }
  // Analyze the CANONICAL (symlink-resolved) path so an in-root symlink cannot be
  // swapped to reach out-of-root content between the check and the read.
  const safePath = confinement.canonical;

  // 3. Authorized + confined: run the read-only tool, re-deriving the graph.
  let result: ImpactResult | MinimalContextResult | GraphStatusResult;
  if (name === "impact_query") {
    const cellId = args.cellId ? String(args.cellId) : undefined;
    let artifacts = await deps.analyze(safePath);
    if (cellId) artifacts = artifacts.filter((a) => matchCell(a, cellId));
    result = {
      tool: "impact_query",
      target: { path: safePath, cellId },
      matched: artifacts.length,
      artifact: artifacts.length === 1 ? artifacts[0] : undefined,
      artifacts,
    };
  } else if (name === "minimal_context_query") {
    const artifacts = await deps.analyze(safePath);
    const filtered = await deps.filterIncluded(artifacts);
    result = {
      tool: "minimal_context_query",
      target: { path: safePath },
      total: filtered.total,
      included_count: filtered.included_count,
      included: filtered.included,
    };
  } else {
    const artifacts = await deps.analyze(safePath);
    const spread: Record<string, number> = {};
    for (const a of artifacts) {
      const lvl = a.claim?.epistemicLevel ?? "unknown";
      spread[lvl] = (spread[lvl] ?? 0) + 1;
    }
    result = {
      tool: "graph_status",
      artifact: graphStatusArtifact(artifacts, spread),
      counts: { cells: artifacts.length },
      epistemicLevelSpread: spread,
    };
  }

  // 4. Emit the served-result ledger event.
  await deps.emitResult(name, result);
  return result;
}

// --------------------------------------------------------------------------- //
// MCP SDK wiring (real Server + tool handlers).
// --------------------------------------------------------------------------- //
const TOOL_DEFS = [
  {
    name: "impact_query",
    description:
      "Run GBRG over a source file/dir INSIDE THE SERVER'S ALLOWED ROOT (re-derived per call; not a frozen snapshot) and return the blast-radius ProofArtifact(s) for the target (optionally filtered to a cellId). Paths outside the allowed root are refused fail-closed. Returns a ProofArtifact object, never a bare float.",
    inputSchema: {
      type: "object" as const,
      properties: { path: { type: "string" }, cellId: { type: "string" } },
      required: ["path"],
    },
  },
  {
    name: "minimal_context_query",
    description:
      "Return only the cells the governance GATE INCLUDES for a source file/dir inside the server's allowed root (each a ProofArtifact object; re-derived per call). Paths outside the allowed root are refused fail-closed.",
    inputSchema: {
      type: "object" as const,
      properties: { path: { type: "string" } },
      required: ["path"],
    },
  },
  {
    name: "graph_status",
    description:
      "Return graph counts and the epistemicLevel spread for a path inside the server's allowed root (re-derived per call), wrapped as a ProofArtifact object. Paths outside the allowed root are refused fail-closed.",
    inputSchema: {
      type: "object" as const,
      properties: { path: { type: "string" } },
      required: [],
    },
  },
];

export function makeServer(deps: ServerDeps, config: RuntimeConfig): Server {
  const server = new Server(
    { name: "gbrg-mcp", version: "0.1.0" },
    {
      capabilities: { tools: {} },
      // Declared identity for audit/diagnostics.
      instructions: `GBRG MCP surface. identity: spiffe_id=${SPIFFE_ID}, actor=${MCP_AGENT_REF}. All tools are read-only and re-derive the graph per call (not a frozen snapshot); every call is authorized (who) AND resource-confined to the allowed root (which), both fail-closed and ledgered.`,
    },
  );

  server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools: TOOL_DEFS }));

  server.setRequestHandler(CallToolRequestSchema, async (req) => {
    const name = req.params.name as ToolName;
    const args = (req.params.arguments ?? {}) as Record<string, unknown>;
    if (!TOOL_NAMES.includes(name)) {
      return {
        isError: true,
        content: [{ type: "text" as const, text: `unknown tool: ${name}` }],
      };
    }
    try {
      const result = await runTool(name, args, deps, config);
      return {
        // structuredContent carries the ProofArtifact OBJECT(s).
        structuredContent: result as unknown as Record<string, unknown>,
        content: [{ type: "text" as const, text: JSON.stringify(result, null, 2) }],
      };
    } catch (e) {
      if (e instanceof ToolRefusedError) {
        // Fail-closed refusal: isError, NO structuredContent artifact.
        return {
          isError: true,
          content: [{ type: "text" as const, text: e.message }],
        };
      }
      return {
        isError: true,
        content: [{ type: "text" as const, text: `error: ${(e as Error).message}` }],
      };
    }
  });

  return server;
}

// --------------------------------------------------------------------------- //
// Real-deps bootstrap over stdio.
// --------------------------------------------------------------------------- //
function defaultConfig(): { deps: ServerDeps; config: RuntimeConfig } {
  const here = dirname(fileURLToPath(import.meta.url)); // dist/src
  const mcpRoot = resolve(here, "..", ".."); // .../gbrg/mcp
  const gbrgRoot = resolve(mcpRoot, ".."); // .../gbrg
  const binPath =
    process.env.GBRG_ANALYZE_BIN ?? resolve(gbrgRoot, "target", "release", "gbrg-analyze");
  const gateCfg: GateConfig = {
    pythonBin: process.env.PYTHON_BIN ?? "python3",
    gateScript: resolve(mcpRoot, "mcp_gate.py"),
    ledgerPath: process.env.GBRG_MCP_LEDGER ?? resolve(mcpRoot, "ledger", "mcp-events.jsonl"),
    registryPath: resolve(mcpRoot, "registry", "capability_registry.json"),
  };
  const deps: ServerDeps = {
    analyze: makeAnalyze(binPath),
    authorize: makeAuthorize(gateCfg),
    emitResult: makeEmitResult(gateCfg),
    emitRefusal: makeEmitRefusal(gateCfg),
    filterIncluded: makeFilterIncluded(gateCfg),
  };
  const config: RuntimeConfig = {
    stateFile:
      process.env.GBRG_MCP_STATE_FILE ??
      resolve(mcpRoot, "fixtures", "agent-authority-current-state.gbrg-mcp.active.json"),
    status: process.env.GBRG_MCP_STATUS,
    graphRoot: process.env.GBRG_GRAPH_ROOT ?? resolve(gbrgRoot, "crates"),
    // M4 resource confinement: default the allowed root to the gbrg tree (the
    // repo subtree this server legitimately analyzes). Operators may widen or
    // narrow it via GBRG_ALLOWED_ROOT; anything outside is refused fail-closed.
    allowedRoot: process.env.GBRG_ALLOWED_ROOT ?? gbrgRoot,
  };
  return { deps, config };
}

export async function main(): Promise<void> {
  const { deps, config } = defaultConfig();
  const server = makeServer(deps, config);
  const transport = new StdioServerTransport();
  await server.connect(transport);
  // eslint-disable-next-line no-console
  console.error(
    `gbrg-mcp: serving 3 read-only tools over stdio as ${SPIFFE_ID} (${MCP_AGENT_REF}); ` +
      `authorized + resource-confined to ${config.allowedRoot ?? config.graphRoot}; fail-closed + ledgered.`,
  );
}

// Run only when invoked directly (not when imported by the test).
const isDirect =
  process.argv[1] && fileURLToPath(import.meta.url) === resolve(process.argv[1]);
if (isDirect) {
  main().catch((e) => {
    // eslint-disable-next-line no-console
    console.error("gbrg-mcp fatal:", e);
    process.exit(1);
  });
}
