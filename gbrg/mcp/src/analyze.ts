/**
 * analyze.ts — thin subprocess wrapper over the REAL Rust `gbrg-analyze` CLI.
 *
 * We do NOT reimplement any scoring in TypeScript (per the GBRG lane rule).
 * The CLI prints a JSON array of BlastRadiusProofArtifacts on stdout; we parse
 * and hand them back untouched.
 */
import { spawn } from "node:child_process";
import type { ProofArtifact } from "./types.js";

export type AnalyzeFn = (targetPath: string) => Promise<ProofArtifact[]>;

/** Build an AnalyzeFn bound to a specific `gbrg-analyze` binary. */
export function makeAnalyze(binPath: string): AnalyzeFn {
  return (targetPath: string) =>
    new Promise<ProofArtifact[]>((resolve, reject) => {
      const child = spawn(binPath, [targetPath], { stdio: ["ignore", "pipe", "pipe"] });
      let out = "";
      let err = "";
      child.stdout?.on("data", (d) => (out += d.toString()));
      child.stderr?.on("data", (d) => (err += d.toString()));
      child.on("error", (e) => reject(new Error(`gbrg-analyze spawn failed: ${e.message}`)));
      child.on("close", (code) => {
        if (code !== 0) {
          reject(new Error(`gbrg-analyze exited ${code}: ${err.trim()}`));
          return;
        }
        try {
          const parsed = JSON.parse(out) as ProofArtifact[];
          resolve(parsed);
        } catch (e) {
          reject(new Error(`gbrg-analyze produced unparseable JSON: ${(e as Error).message}`));
        }
      });
    });
}
