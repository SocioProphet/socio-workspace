/**
 * confine.ts — FAIL-CLOSED resource confinement for the GBRG MCP surface.
 *
 * Adversarial-review finding M4: authorization gates *who* may call a tool, but
 * nothing gated *which resource* the tool reads. An authorized agent could pass
 * ANY caller-supplied path (`/etc`, a sibling repo, a `..` traversal, or a
 * symlink pointing out of the tree) and GBRG would parse that arbitrary readable
 * source tree. This module is the second, independent gate: it decides whether a
 * requested path is inside the configured allowed root, and REFUSES (fail-closed)
 * everything else BEFORE any analysis is performed.
 *
 * The rule (fail-closed): canonicalize the allowed root and the requested path —
 * resolving `..` AND following symlinks on every existing component — then admit
 * the request iff the canonical target is the allowed root or a descendant of it.
 * Anything unresolvable, or resolving outside the root, is refused. Symlinks are
 * resolved BEFORE the containment check so an in-root symlink that points out of
 * the tree cannot be used to escape.
 */
import { realpathSync } from "node:fs";
import { dirname, isAbsolute, relative, resolve } from "node:path";

export type ConfineReasonCode = "path_out_of_root" | "path_unresolvable" | "root_unresolvable";

export interface ConfineDecision {
  /** true iff the canonical target is within the canonical allowed root. */
  allowed: boolean;
  /** The fully-canonicalized (symlink- and `..`-resolved) absolute path. */
  canonical: string;
  /** The canonical allowed root the check was performed against. */
  root: string;
  /** Set iff allowed === false. */
  reasonCode?: ConfineReasonCode;
}

/**
 * Canonicalize a path: resolve `..`, then follow symlinks on the LONGEST existing
 * prefix and re-append any non-existent tail (so a not-yet-created leaf is still
 * anchored to a symlink-resolved real ancestor). Absolute inputs are honoured
 * as-is; relative inputs resolve against `baseRoot`.
 */
function canonicalize(inputPath: string, baseRoot: string): string {
  const abs = isAbsolute(inputPath) ? resolve(inputPath) : resolve(baseRoot, inputPath);
  let existing = abs;
  const tail: string[] = [];
  // Walk up until realpathSync succeeds on an existing ancestor.
  // Guaranteed to terminate: dirname() reaches a fixed point at the fs root.
  for (;;) {
    try {
      const real = realpathSync(existing);
      return tail.length ? resolve(real, ...tail) : real;
    } catch {
      const parent = dirname(existing);
      if (parent === existing) {
        // Nothing along the path exists — return the lexically-resolved absolute
        // path; the containment check below still applies (fail-closed).
        return abs;
      }
      tail.unshift(existing.slice(parent.length + 1));
      existing = parent;
    }
  }
}

/** True iff `child` is the same path as `root` or strictly beneath it. */
function isWithin(child: string, root: string): boolean {
  if (child === root) return true;
  const rel = relative(root, child);
  return rel !== "" && !rel.startsWith("..") && !isAbsolute(rel);
}

/**
 * Decide whether `requestedPath` is confined to `allowedRoot`. Never throws —
 * every failure mode (unresolvable root, unresolvable/escaping path) collapses to
 * `allowed: false` with a reason code, so callers can ledger a refusal.
 */
export function confinePath(requestedPath: string, allowedRoot: string): ConfineDecision {
  let root: string;
  try {
    root = realpathSync(resolve(allowedRoot));
  } catch {
    // The allowed root itself cannot be resolved — refuse everything, fail-closed.
    return {
      allowed: false,
      canonical: resolve(allowedRoot),
      root: resolve(allowedRoot),
      reasonCode: "root_unresolvable",
    };
  }

  const requested = String(requestedPath ?? "");
  if (!requested.trim()) {
    return { allowed: false, canonical: root, root, reasonCode: "path_unresolvable" };
  }

  const canonical = canonicalize(requested, root);
  if (!isWithin(canonical, root)) {
    return { allowed: false, canonical, root, reasonCode: "path_out_of_root" };
  }
  return { allowed: true, canonical, root };
}
