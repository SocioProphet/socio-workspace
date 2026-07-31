/**
 * zero_trust_test.ts — PROVE THE CONTROL FIRES BOTH WAYS.
 *
 * A control that only ever serves is suspect. This test drives the REAL MCP SDK
 * Server (over an in-memory client/server transport, so no network) with REAL
 * collaborators — the real Rust `gbrg-analyze` binary and the real Python
 * `mcp_gate.py` (which subprocesses the real agent-registry authorize.py and
 * writes the real durable ledger). It asserts:
 *
 *   (a) SERVED  — under ACTIVE authority, impact_query returns a ProofArtifact
 *                 OBJECT (nested claim.epistemicLevel + derivation), NEVER a
 *                 bare float, and an allow MCP_CALL + an MCP_RESULT ledger event
 *                 are written.
 *   (b) REFUSED — under SUSPENDED authority, the SAME call is refused fail-closed
 *                 (isError, NO ProofArtifact), and a deny MCP_CALL ledger event
 *                 is written. Same input, opposite outcome => it is AUTHORITY,
 *                 not content, doing the blocking.
 *
 * Also exercises minimal_context_query (gate inclusion) and graph_status, and
 * verifies the ledger hash-chain is intact.
 */
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { readFileSync, existsSync, rmSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { createHash } from "node:crypto";

import { makeServer, runTool, RuntimeConfig, ServerDeps } from "../src/server.js";
import { makeAnalyze } from "../src/analyze.js";
import {
  makeAuthorize,
  makeEmitResult,
  makeFilterIncluded,
  GateConfig,
} from "../src/gate.js";
import { isProofArtifact, ToolRefusedError } from "../src/types.js";

const here = dirname(fileURLToPath(import.meta.url)); // dist/test
const mcpRoot = resolve(here, "..", ".."); // .../gbrg/mcp
const gbrgRoot = resolve(mcpRoot, ".."); // .../gbrg

const BIN = resolve(gbrgRoot, "target", "release", "gbrg-analyze");
const ACTIVE = resolve(mcpRoot, "fixtures", "agent-authority-current-state.gbrg-mcp.active.json");
const SUSPENDED = resolve(mcpRoot, "fixtures", "agent-authority-current-state.gbrg-mcp.suspended.json");
const REGISTRY = resolve(mcpRoot, "registry", "capability_registry.json");
const TARGET_FILE = resolve(gbrgRoot, "crates", "gbrg-core", "src", "lib.rs");
const TARGET_DIR = resolve(gbrgRoot, "crates", "gbrg-analyze", "tests", "fixtures");

let passed = 0;
let failed = 0;
function ok(name: string, cond: boolean, detail = ""): void {
  if (cond) {
    passed++;
    console.log(`PASS: ${name}`);
  } else {
    failed++;
    console.log(`FAIL: ${name} ${detail}`);
  }
}

function readLedger(path: string): any[] {
  if (!existsSync(path)) return [];
  return readFileSync(path, "utf-8")
    .split("\n")
    .filter((l) => l.trim())
    .map((l) => JSON.parse(l));
}

function sha256Canonical(obj: unknown): string {
  return "sha256:" + createHash("sha256").update(canonical(obj)).digest("hex");
}
// Match Python's json.dumps(sort_keys=True, separators=(",",":")).
function canonical(v: unknown): string {
  if (v === null) return "null";
  if (Array.isArray(v)) return "[" + v.map(canonical).join(",") + "]";
  if (typeof v === "object") {
    const o = v as Record<string, unknown>;
    const keys = Object.keys(o).sort();
    return "{" + keys.map((k) => JSON.stringify(k) + ":" + canonical(o[k])).join(",") + "}";
  }
  return JSON.stringify(v);
}

async function main(): Promise<void> {
  const tmp = mkdtempSync(resolve(tmpdir(), "gbrg-mcp-test-"));
  const LEDGER = resolve(tmp, "mcp-events.jsonl");

  const gateCfg: GateConfig = {
    pythonBin: "python3",
    gateScript: resolve(mcpRoot, "mcp_gate.py"),
    ledgerPath: LEDGER,
    registryPath: REGISTRY,
  };
  const deps: ServerDeps = {
    analyze: makeAnalyze(BIN),
    authorize: makeAuthorize(gateCfg),
    emitResult: makeEmitResult(gateCfg),
    filterIncluded: makeFilterIncluded(gateCfg),
  };
  // Mutable config: we flip the agent's authority between calls.
  const config: RuntimeConfig = { stateFile: ACTIVE, graphRoot: TARGET_DIR };

  // ---- Real MCP SDK server + client over in-memory transport ----
  const server = makeServer(deps, config);
  const client = new Client({ name: "gbrg-mcp-test-client", version: "0.0.0" }, { capabilities: {} });
  const [clientT, serverT] = InMemoryTransport.createLinkedPair();
  await Promise.all([server.connect(serverT), client.connect(clientT)]);

  // ---- SDK wiring: 3 tools listed ----
  const list = await client.listTools();
  ok("SDK server lists 3 tools", list.tools.length === 3, `got ${list.tools.length}`);
  ok(
    "tools are the 3 GBRG tools",
    ["impact_query", "minimal_context_query", "graph_status"].every((n) =>
      list.tools.some((t) => t.name === n),
    ),
  );

  // ===================================================================== //
  // (a) SERVED — ACTIVE authority.
  // ===================================================================== //
  config.stateFile = ACTIVE;
  const served: any = await client.callTool({
    name: "impact_query",
    arguments: { path: TARGET_FILE, cellId: "as_label" },
  });
  ok("(a) served call is NOT an error", served.isError !== true, JSON.stringify(served.content));
  const servedResult = served.structuredContent;
  ok("(a) served returns structuredContent", !!servedResult);
  const artifact = servedResult?.artifact;
  ok("(a) result carries a ProofArtifact OBJECT (not a float)", isProofArtifact(artifact),
    `typeof=${typeof artifact}`);
  ok("(a) artifact has nested claim.epistemicLevel", typeof artifact?.claim?.epistemicLevel === "string",
    `got ${artifact?.claim?.epistemicLevel}`);
  ok("(a) artifact has derivation", typeof artifact?.derivation === "string" && artifact.derivation.length > 0);
  ok("(a) blast_radius is a NESTED number in [0,1] (never returned bare)",
    typeof artifact?.blast_radius === "number" && artifact.blast_radius >= 0 && artifact.blast_radius <= 1,
    `got ${artifact?.blast_radius}`);
  ok("(a) declared_by is the MCP agent", artifact?.declared_by?.startsWith("agent-registry://"));
  ok("(a) the response itself is an OBJECT, not a number", typeof servedResult === "object" && typeof servedResult !== "number");

  // ===================================================================== //
  // (b) REFUSED — SUSPENDED authority, SAME call.
  // ===================================================================== //
  config.stateFile = SUSPENDED;
  const refused: any = await client.callTool({
    name: "impact_query",
    arguments: { path: TARGET_FILE, cellId: "as_label" },
  });
  ok("(b) suspended call IS a fail-closed error", refused.isError === true);
  ok("(b) refusal produced NO ProofArtifact (no structuredContent)", refused.structuredContent === undefined,
    `got ${JSON.stringify(refused.structuredContent)}`);
  ok("(b) refusal message names fail-closed", String(refused.content?.[0]?.text ?? "").includes("REFUSED (fail-closed)"));

  // Same input, opposite outcome -> it is AUTHORITY, not content, blocking.
  ok("(b) SAME input as (a) but refused => authority is the gate",
    served.isError !== true && refused.isError === true);

  // Direct runTool assertion: suspended -> throws ToolRefusedError (typed refusal).
  let threw: unknown = null;
  try {
    await runTool("impact_query", { path: TARGET_FILE, cellId: "as_label" }, deps,
      { stateFile: SUSPENDED, graphRoot: TARGET_DIR });
  } catch (e) {
    threw = e;
  }
  ok("(b) runTool throws ToolRefusedError under suspended authority", threw instanceof ToolRefusedError,
    `got ${threw}`);

  // ===================================================================== //
  // minimal_context_query (gate inclusion) + graph_status, under ACTIVE.
  // ===================================================================== //
  config.stateFile = ACTIVE;
  const minimal: any = await client.callTool({ name: "minimal_context_query", arguments: { path: TARGET_DIR } });
  const mc = minimal.structuredContent;
  ok("minimal_context_query served", minimal.isError !== true);
  ok("minimal_context_query returns only INCLUDED cells, each a ProofArtifact",
    Array.isArray(mc?.included) && mc.included.length > 0 && mc.included.every((a: unknown) => isProofArtifact(a)),
    `included=${mc?.included_count}/${mc?.total}`);

  const status: any = await client.callTool({ name: "graph_status", arguments: { path: TARGET_DIR } });
  const gs = status.structuredContent;
  ok("graph_status served as a ProofArtifact (not a bare count)", isProofArtifact(gs?.artifact));
  ok("graph_status reports epistemicLevel spread", typeof gs?.epistemicLevelSpread === "object" && gs.counts.cells > 0,
    `cells=${gs?.counts?.cells}`);

  // ===================================================================== //
  // LEDGER — every call left a durable, hash-chained event.
  // ===================================================================== //
  const events = readLedger(LEDGER);
  const calls = events.filter((e) => e.type === "MCP_CALL");
  const results = events.filter((e) => e.type === "MCP_RESULT");
  const allowCalls = calls.filter((e) => e.decision?.allow === true);
  const denyCalls = calls.filter((e) => e.decision?.allow === false);

  ok("ledger has >=1 ALLOW MCP_CALL event (served path)", allowCalls.length >= 1, `got ${allowCalls.length}`);
  ok("ledger has >=1 DENY MCP_CALL event (refused path)", denyCalls.length >= 1, `got ${denyCalls.length}`);
  ok("ledger has >=1 MCP_RESULT event (served result)", results.length >= 1, `got ${results.length}`);
  ok("every event actor is the MCP SPIFFE id",
    events.every((e) => e.actor?.spiffe_id === "spiffe://socioprophet/mcp/gbrg"));
  ok("every event targets an mcp_tool with a capability_digest",
    events.every((e) => e.target?.kind === "mcp_tool" && /^sha256:[a-f0-9]{64}$/.test(e.target?.capability_digest)));

  // Hash-chain integrity: prev_hash links, and each hash recomputes.
  let chainOk = true;
  let recomputeOk = true;
  const genesis = "sha256:" + createHash("sha256").update("gbrg-mcp-ledger-genesis").digest("hex");
  for (let i = 0; i < events.length; i++) {
    const e = events[i];
    const expectedPrev = i === 0 ? genesis : events[i - 1].hash;
    if (e.prev_hash !== expectedPrev) chainOk = false;
    const core = {
      event_id: e.event_id, ts: e.ts, type: e.type, actor: e.actor, target: e.target,
      payload_hash: e.payload_hash, policy_hash: e.policy_hash, prev_hash: e.prev_hash, decision: e.decision,
    };
    if (sha256Canonical(core) !== e.hash) recomputeOk = false;
  }
  ok("ledger prev_hash chain is intact (genesis-linked)", chainOk);
  ok("every ledger hash recomputes (independent sha256)", recomputeOk);
  ok("every event policy_hash == sha256(capability_registry.json)",
    events.every((e) => e.policy_hash === sha256Canonical(JSON.parse(readFileSync(REGISTRY, "utf-8")))));

  // ---- summary ----
  console.log("\n--- ONE SERVED ProofArtifact (impact_query as_label) ---");
  console.log(JSON.stringify(artifact, null, 2));
  console.log("\n--- ONE DENY LEDGER EVENT (refused, fail-closed) ---");
  console.log(JSON.stringify(denyCalls[0], null, 2));

  await client.close();
  await server.close();
  rmSync(tmp, { recursive: true, force: true });

  console.log(`\n==== ${passed} PASSED, ${failed} FAILED ====`);
  if (failed > 0) process.exit(1);
}

main().catch((e) => {
  console.error("test harness error:", e);
  process.exit(1);
});
