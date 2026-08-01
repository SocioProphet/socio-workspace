/**
 * gate.ts — the zero-trust gate for the MCP surface, in TypeScript.
 *
 * This is a FAIL-CLOSED subprocess bridge to `mcp_gate.py`, which REUSES the
 * shared `gbrg/governance` gate foundation:
 *   - authorize  -> gate.authorize_inclusion -> agent-registry authorize.py
 *   - ledger     -> gbrg.governance.ledger.append (durable, hash-chained)
 *   - inclusion  -> gate.decide_inclusion (for minimal_context_query)
 *
 * Every authorize() call MUST report a written ledger event. If the subprocess
 * fails, returns non-JSON, denies, or reports `ledger_written !== true`, the
 * bridge collapses to a DENY with `ledger_written: false` — no ledger event is
 * treated as failure, exactly as the spec requires.
 */
import { spawn } from "node:child_process";
import type { ProofArtifact } from "./types.js";

export const SPIFFE_ID = "spiffe://socioprophet/mcp/gbrg";
export const MCP_AGENT_REF = "agent-registry://gbrg/mcp";

export interface AuthorizeResult {
  verdict: "allow" | "require-review" | "deny";
  reasonCode: string;
  ledgerWritten: boolean;
  event?: { event_id: string; hash: string; prev_hash: string; type: string };
}

export interface GateConfig {
  pythonBin: string; // e.g. "python3"
  gateScript: string; // absolute path to mcp_gate.py
  ledgerPath: string;
  registryPath: string;
}

function runPy(
  cfg: GateConfig,
  argv: string[],
  stdinData?: string,
): Promise<{ code: number | null; stdout: string; stderr: string }> {
  return new Promise((resolve) => {
    const child = spawn(cfg.pythonBin, [cfg.gateScript, ...argv], {
      stdio: [stdinData !== undefined ? "pipe" : "ignore", "pipe", "pipe"],
    });
    let out = "";
    let err = "";
    child.stdout?.on("data", (d) => (out += d.toString()));
    child.stderr?.on("data", (d) => (err += d.toString()));
    child.on("error", (e) => resolve({ code: -1, stdout: "", stderr: e.message }));
    child.on("close", (code) => resolve({ code, stdout: out, stderr: err }));
    if (stdinData !== undefined && child.stdin) {
      child.stdin.write(stdinData);
      child.stdin.end();
    }
  });
}

/** PER-CALL authorize + MANDATORY ledger emission. Fail-closed on any anomaly. */
export interface AuthorizeArgs {
  tool: string;
  args: Record<string, unknown>;
  stateFile?: string; // the MCP agent's current authority state
  status?: string;
}

export type AuthorizeFn = (a: AuthorizeArgs) => Promise<AuthorizeResult>;

export function makeAuthorize(cfg: GateConfig): AuthorizeFn {
  return async ({ tool, args, stateFile, status }: AuthorizeArgs): Promise<AuthorizeResult> => {
    const argv = [
      "authorize",
      "--tool",
      tool,
      "--args-json",
      JSON.stringify(args ?? {}),
      "--ledger",
      cfg.ledgerPath,
      "--registry",
      cfg.registryPath,
    ];
    if (stateFile) argv.push("--state-file", stateFile);
    if (status) argv.push("--status", status);

    const { stdout, stderr } = await runPy(cfg, argv);
    let parsed: {
      verdict?: string;
      reason_code?: string;
      ledger_written?: boolean;
      event?: AuthorizeResult["event"];
    };
    try {
      parsed = JSON.parse(stdout.trim());
    } catch {
      // Unparseable gate output -> cannot confirm authority OR ledger -> DENY.
      return { verdict: "deny", reasonCode: `gate_unparseable:${stderr.trim().slice(0, 80)}`, ledgerWritten: false };
    }
    const verdict = (parsed.verdict as AuthorizeResult["verdict"]) ?? "deny";
    const ledgerWritten = parsed.ledger_written === true;
    // No ledger event => treat as failure regardless of verdict.
    if (!ledgerWritten) {
      return { verdict: "deny", reasonCode: `no_ledger_event:${parsed.reason_code ?? ""}`, ledgerWritten: false, event: parsed.event };
    }
    return { verdict, reasonCode: parsed.reason_code ?? "", ledgerWritten, event: parsed.event };
  };
}

/** Emit the post-success MCP_RESULT ledger event (best-effort, still durable). */
export type EmitResultFn = (tool: string, result: unknown) => Promise<boolean>;

export function makeEmitResult(cfg: GateConfig): EmitResultFn {
  return async (tool: string, result: unknown): Promise<boolean> => {
    const argv = [
      "emit-result",
      "--tool",
      tool,
      "--result-json",
      JSON.stringify(result ?? {}),
      "--ledger",
      cfg.ledgerPath,
      "--registry",
      cfg.registryPath,
    ];
    const { stdout } = await runPy(cfg, argv);
    try {
      return JSON.parse(stdout.trim()).ledger_written === true;
    } catch {
      return false;
    }
  };
}

/**
 * Emit a fail-closed REFUSAL ledger event (a deny MCP_CALL) for a call that was
 * authorized (the caller may act) but blocked by RESOURCE confinement (the
 * requested path is outside the allowed root). This is the ledger record that
 * proves "no analysis performed": it is written BEFORE any analyze() runs.
 */
export interface RefusalResult {
  ledgerWritten: boolean;
  event?: AuthorizeResult["event"];
}
export type EmitRefusalFn = (
  tool: string,
  reasonCode: string,
  args: Record<string, unknown>,
) => Promise<RefusalResult>;

export function makeEmitRefusal(cfg: GateConfig): EmitRefusalFn {
  return async (tool, reasonCode, args): Promise<RefusalResult> => {
    const argv = [
      "refuse",
      "--tool",
      tool,
      "--reason-code",
      reasonCode,
      "--args-json",
      JSON.stringify(args ?? {}),
      "--ledger",
      cfg.ledgerPath,
      "--registry",
      cfg.registryPath,
    ];
    const { stdout } = await runPy(cfg, argv);
    try {
      const parsed = JSON.parse(stdout.trim());
      return { ledgerWritten: parsed.ledger_written === true, event: parsed.event };
    } catch {
      return { ledgerWritten: false };
    }
  };
}

/** CONSUME the gate foundation's inclusion decision to pick minimal context. */
export interface FilterIncludedResult {
  included: ProofArtifact[];
  included_count: number;
  total: number;
}
export type FilterIncludedFn = (artifacts: ProofArtifact[]) => Promise<FilterIncludedResult>;

export function makeFilterIncluded(cfg: GateConfig): FilterIncludedFn {
  return async (artifacts: ProofArtifact[]): Promise<FilterIncludedResult> => {
    const { stdout } = await runPy(cfg, ["filter-include"], JSON.stringify(artifacts));
    return JSON.parse(stdout.trim()) as FilterIncludedResult;
  };
}
