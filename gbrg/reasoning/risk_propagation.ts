/**
 * risk_propagation.ts — GBRG causal TRACK 1: PLN probabilistic-logic risk
 * propagation.
 *
 * HONEST LABEL: this is **probabilistic-logic (PLN) transitive risk
 * propagation** — it computes how the risk of a downstream cell flows *up*
 * through the call graph to its (transitive) callers, attenuating a (strength,
 * confidence) truth value at every hop. It is **NOT** Pearl-style causal
 * inference: there is no do-calculus, no intervention/counterfactual, no
 * structural-causal-model identification. "Causal TRACK 1" is a program name,
 * not a claim of Pearl causality.
 *
 * WHAT IS REAL HERE:
 *   - The RISK SEEDS come from REAL `gbrg-analyze` ProofArtifacts, obtained via
 *     the same subprocess pattern as gbrg/mcp/src/analyze.ts (we do NOT
 *     re-score anything in TypeScript — that is the GBRG lane rule).
 *   - The transitive inference is run by the REAL `forwardChain()` from
 *     `@socioprophet/hellgraph` (its in-process PLN deduction rule
 *     A→B ⊗ B→C ⇒ A→C, with s = s1·s2 and c = c1·c2·0.9). We NEVER reimplement
 *     forwardChain — we project onto the store and read back what it derived.
 *
 * CALL TOPOLOGY IS NOW REAL TOO:
 *   - `gbrg-analyze --emit-edges` surfaces the analyzer's internal `CALLS`
 *     topology (with stable cell-IRI endpoints) alongside the artifacts, so the
 *     end-to-end path (`analyzeAndPropagate`) consumes the REAL call graph from
 *     analyze output — the caller no longer has to supply it. `CallEdge[]` may
 *     still be passed explicitly to `projectAndPropagate`/`propagateFromArtifacts`
 *     for unit tests or synthetic topologies, but it is no longer required to run
 *     PLN over real analyze output.
 *
 * Edge orientation: a `calls` edge `from → to` (caller → callee) becomes a
 * graph edge `from → to` meaning "from is exposed to the risk of to". PLN
 * deduction over these edges yields A→C = "A is transitively exposed to C's
 * risk", with confidence decayed by the 0.9-per-hop factor baked into
 * hellgraph's deduction rule.
 */

import { spawn } from 'node:child_process'
import {
  getHellGraph,
  forwardChain,
  type GraphEdge,
  type PLNResult,
} from '@socioprophet/hellgraph'

// ─────────────────────────────────────────────────────────────────────────────
// ProofArtifact — the SUBSET of the real gbrg-analyze / gbrg-mcp ProofArtifact
// we consume. Full schema: gbrg/mcp/src/types.ts and
// gbrg/contracts/blast-radius-proof-artifact.schema.json. We consume it; we do
// NOT redefine or re-score it.
// ─────────────────────────────────────────────────────────────────────────────

export type EpistemicLevel =
  | 'proved'
  | 'bounded'
  | 'empirical'
  | 'synthetic'
  | 'speculative'
  | 'rejected'

export interface ProofArtifact {
  cell_id?: string
  claim: { epistemicLevel: EpistemicLevel; statement?: string }
  status: string
  dependents_count: number
  test_coverage_reach: boolean
  churn_frequency: number
  blast_radius: number
  derivation: string
  declared_by: string
  generated: boolean
}

// ─────────────────────────────────────────────────────────────────────────────
// Public types
// ─────────────────────────────────────────────────────────────────────────────

/** A cell to place on the risk graph, distilled from a ProofArtifact. */
export interface RiskCell {
  cellId: string
  epistemicLevel: EpistemicLevel
  testCoverageReach: boolean
  blastRadius: number
}

/** A directed call: `from` calls `to`. Risk of `to` propagates up to `from`. */
export interface CallEdge {
  from: string
  to: string
}

/**
 * A raw edge as emitted by `gbrg-analyze --emit-edges`: stable cell-IRI endpoints
 * plus the edge kind label (`CALLS` | `INHERITS` | `IMPORTS` | `TESTED_BY` | ...).
 * We consume these; we do NOT synthesize topology.
 */
export interface AnalyzeEdge {
  from: string
  to: string
  kind: string
}

/** The `--emit-edges` bundle: real artifacts AND the real internal topology. */
export interface AnalyzeBundle {
  artifacts: ProofArtifact[]
  edges: AnalyzeEdge[]
}

/**
 * Distil the analyzer's real edges into the risk-propagation `CallEdge[]`: keep
 * only `CALLS` edges (caller → callee), which is exactly the "from is exposed to
 * the risk of to" orientation PLN chains. `INHERITS`/`IMPORTS`/`TESTED_BY` are not
 * call-risk edges and are intentionally excluded.
 */
export function callEdgesFromAnalyze(edges: AnalyzeEdge[]): CallEdge[] {
  return edges
    .filter((e) => e.kind === 'CALLS')
    .map((e) => ({ from: e.from, to: e.to }))
}

/** A transitive-risk edge DERIVED by hellgraph's PLN deduction. */
export interface DerivedRiskEdge {
  from: string
  to: string
  /** PLN truth-value strength (s1·s2 along the chain). */
  strength: number
  /** PLN truth-value confidence — DECAYED by 0.9 per deduction hop. */
  confidence: number
  /** hellgraph's tag for the rule that produced it, e.g. "pln_deduction". */
  epistemicClass: string
  /** Best-effort chain length in the seed call graph (A→B→C ⇒ 2). */
  hops: number
}

/** A direct (seed) risk edge as it was written to the store. */
export interface SeedRiskEdge {
  from: string
  to: string
  strength: number
  confidence: number
}

export interface PropagationResult {
  /** Seed edges written to the store (the direct call-risk edges). */
  seeds: SeedRiskEdge[]
  /** Raw hellgraph forwardChain() stats. */
  pln: PLNResult
  /** DERIVED transitive-risk edges (pln_deduction) among our cell set. */
  derived: DerivedRiskEdge[]
}

export interface PropagateOptions {
  /** Cap PLN iterations (passed through to forwardChain). Default: hellgraph's. */
  maxIters?: number
  /**
   * Turn OFF revision/abduction so ONLY transitive-risk deduction fires. Risk
   * propagation is a pure transitive-closure question, so this defaults true.
   */
  deductionOnly?: boolean
}

// ─────────────────────────────────────────────────────────────────────────────
// Risk → (strength, confidence) seeding rule
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Base propagation STRENGTH by epistemic level. Interpretation: "how strongly
 * does risk flow along an edge that ends at a cell of this epistemic level".
 *
 * speculative / untested code is the WORST case — an unproven, unmeasured cell
 * propagates its risk almost undiminished — so it seeds the HIGHEST strength.
 * proved/bounded cells are trustworthy, so they leak little risk upward.
 */
export const RISK_STRENGTH: Record<EpistemicLevel, number> = {
  speculative: 0.9, // untested + unproven — highest transitive risk
  synthetic: 0.8, // built on synthetic/not-real data
  empirical: 0.6, // observed but not proven
  bounded: 0.45, // bounded guarantee
  proved: 0.3, // proven — leaks little risk
  rejected: 0.2, // claim rejected — treated as low propagating risk
}

/**
 * STRENGTH seed for an edge that ENDS at `cell` (i.e. risk flowing *out of*
 * `cell` toward its caller). Untested cells get a small additive bump so an
 * untested `empirical` cell still out-propagates a tested one, capped at 0.95.
 */
export function riskStrength(cell: RiskCell): number {
  const base = RISK_STRENGTH[cell.epistemicLevel]
  const untestedBump = cell.testCoverageReach ? 0 : 0.05
  return Math.min(0.95, base + untestedBump)
}

/**
 * CONFIDENCE seed for an edge — "how much EVIDENCE backs this truth value".
 * A test path reaching the cell is real evidence (high confidence); without it
 * we are less certain (moderate). The parser having *found* the call keeps a
 * floor under it. Kept high enough that the per-hop 0.9 decay is the dominant,
 * visible attenuation in the derived edge.
 */
export function evidenceConfidence(cell: RiskCell): number {
  return cell.testCoverageReach ? 0.9 : 0.8
}

// ─────────────────────────────────────────────────────────────────────────────
// ProofArtifact → RiskCell
// ─────────────────────────────────────────────────────────────────────────────

/** Distil a real ProofArtifact into a RiskCell (identity = its cell_id). */
export function cellFromArtifact(a: ProofArtifact): RiskCell {
  const cellId = a.cell_id ?? a.claim?.statement ?? 'unknown-cell'
  return {
    cellId,
    epistemicLevel: a.claim.epistemicLevel,
    testCoverageReach: a.test_coverage_reach,
    blastRadius: a.blast_radius,
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Store labels
// ─────────────────────────────────────────────────────────────────────────────

/**
 * PLN reasons over edges whose label is in its SOURCE_EDGES set — `RELATED_TO`
 * is the canonical one — and writes DERIVED edges back as `RELATED_TO` tagged
 * `epistemicClass: 'pln_deduction'`. We therefore seed our call-risk edges as
 * `RELATED_TO` so forwardChain will chain them, and distinguish our SEED edges
 * from DERIVED ones by a bespoke epistemicClass tag.
 */
const PLN_SOURCE_LABEL = 'RELATED_TO'
const SEED_EPISTEMIC_CLASS = 'gbrg_call_risk_seed'
const DEDUCTION_EPISTEMIC_CLASS = 'pln_deduction'

// ─────────────────────────────────────────────────────────────────────────────
// Core: project → forwardChain → read derived
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Project `cells` + `calls` onto the shared HellGraphStore, run the REAL
 * `forwardChain()`, and return the DERIVED transitive-risk edges.
 *
 * NOTE (process singleton): hellgraph's store is a process-level singleton with
 * no reset. We snapshot the pre-existing edge ids so the returned `derived`
 * set contains ONLY edges this call produced — safe to run more than once per
 * process as long as cell ids are unique.
 */
export function projectAndPropagate(
  cells: RiskCell[],
  calls: CallEdge[],
  opts: PropagateOptions = {},
): PropagationResult {
  const g = getHellGraph()
  const byId = new Map(cells.map((c) => [c.cellId, c]))
  const cellIds = new Set(byId.keys())

  // Project cells → nodes (labelled Cell, carrying their risk facts).
  for (const c of cells) {
    g.addNode(c.cellId, ['Cell'], {
      epistemicLevel: c.epistemicLevel,
      testCoverageReach: c.testCoverageReach,
      blastRadius: c.blastRadius,
    })
  }

  // Seed direct call-risk edges. Strength/confidence come from the CALLEE
  // (`to`) — the cell whose risk is flowing up to the caller (`from`).
  const seeds: SeedRiskEdge[] = []
  for (const e of calls) {
    const callee = byId.get(e.to)
    if (!callee) continue // no risk facts for the callee → skip
    const strength = riskStrength(callee)
    const confidence = evidenceConfidence(callee)
    g.addEdge(PLN_SOURCE_LABEL, e.from, e.to, {
      epistemicClass: SEED_EPISTEMIC_CLASS,
      strength,
      confidence,
      promotionState: 'seed',
    })
    seeds.push({ from: e.from, to: e.to, strength, confidence })
  }

  // Snapshot existing edge ids so we can isolate NEWLY derived edges.
  const before = new Set(g.allEdges().map((x) => x.id))

  // Run the REAL PLN forward chainer.
  const deductionOnly = opts.deductionOnly ?? true
  const pln = forwardChain({
    maxIters: opts.maxIters,
    runRevision: !deductionOnly,
    runAbduction: !deductionOnly,
  })

  // Read back DERIVED transitive-risk edges (pln_deduction) among our cells.
  const hopIndex = buildHopIndex(calls)
  const derived: DerivedRiskEdge[] = []
  for (const edge of g.allEdges()) {
    if (before.has(edge.id)) continue
    if (edge.label !== PLN_SOURCE_LABEL) continue
    if (edge.properties['epistemicClass'] !== DEDUCTION_EPISTEMIC_CLASS) continue
    if (!cellIds.has(edge.from) || !cellIds.has(edge.to)) continue
    derived.push({
      from: edge.from,
      to: edge.to,
      strength: readNum(edge, 'strength'),
      confidence: readNum(edge, 'confidence'),
      epistemicClass: DEDUCTION_EPISTEMIC_CLASS,
      hops: hopIndex.get(`${edge.from} ${edge.to}`) ?? -1,
    })
  }

  return { seeds, pln, derived }
}

/** Convenience: build the risk graph straight from real ProofArtifacts. */
export function propagateFromArtifacts(
  artifacts: ProofArtifact[],
  calls: CallEdge[],
  opts: PropagateOptions = {},
): PropagationResult {
  return projectAndPropagate(artifacts.map(cellFromArtifact), calls, opts)
}

function readNum(edge: GraphEdge, key: string): number {
  const v = edge.properties[key]
  return typeof v === 'number' ? v : Number(v)
}

/** BFS shortest-path hop counts over the seed call graph, for annotation only. */
function buildHopIndex(calls: CallEdge[]): Map<string, number> {
  const adj = new Map<string, string[]>()
  const nodes = new Set<string>()
  for (const e of calls) {
    if (!adj.has(e.from)) adj.set(e.from, [])
    adj.get(e.from)!.push(e.to)
    nodes.add(e.from)
    nodes.add(e.to)
  }
  const out = new Map<string, number>()
  for (const src of nodes) {
    const dist = new Map<string, number>([[src, 0]])
    const q = [src]
    while (q.length) {
      const u = q.shift()!
      for (const v of adj.get(u) ?? []) {
        if (!dist.has(v)) {
          dist.set(v, dist.get(u)! + 1)
          q.push(v)
        }
      }
    }
    for (const [dst, d] of dist) {
      if (dst !== src) out.set(`${src} ${dst}`, d)
    }
  }
  return out
}

// ─────────────────────────────────────────────────────────────────────────────
// Real gbrg-analyze subprocess — same pattern as gbrg/mcp/src/analyze.ts.
// We do NOT reimplement scoring; we shell out to the REAL Rust CLI and parse
// its JSON array of ProofArtifacts from stdout.
// ─────────────────────────────────────────────────────────────────────────────

export type AnalyzeFn = (targetPath: string) => Promise<ProofArtifact[]>

/** Build an AnalyzeFn bound to a specific `gbrg-analyze` binary. */
export function makeAnalyze(binPath: string): AnalyzeFn {
  return (targetPath: string) =>
    new Promise<ProofArtifact[]>((resolve, reject) => {
      const child = spawn(binPath, [targetPath], {
        stdio: ['ignore', 'pipe', 'pipe'],
      })
      let out = ''
      let err = ''
      child.stdout?.on('data', (d) => (out += d.toString()))
      child.stderr?.on('data', (d) => (err += d.toString()))
      child.on('error', (e) =>
        reject(new Error(`gbrg-analyze spawn failed: ${e.message}`)),
      )
      child.on('close', (code) => {
        if (code !== 0) {
          reject(new Error(`gbrg-analyze exited ${code}: ${err.trim()}`))
          return
        }
        try {
          resolve(JSON.parse(out) as ProofArtifact[])
        } catch (e) {
          reject(
            new Error(
              `gbrg-analyze produced unparseable JSON: ${(e as Error).message}`,
            ),
          )
        }
      })
    })
}

/**
 * Build an analyze fn that returns BOTH artifacts and the real internal topology,
 * by invoking `gbrg-analyze --emit-edges` and parsing its `{artifacts, edges}`
 * object. Same subprocess discipline as [`makeAnalyze`]; we do NOT re-score or
 * synthesize edges — we read what the Rust analyzer resolved.
 */
export function makeAnalyzeWithEdges(
  binPath: string,
): (targetPath: string) => Promise<AnalyzeBundle> {
  return (targetPath: string) =>
    new Promise<AnalyzeBundle>((resolve, reject) => {
      const child = spawn(binPath, [targetPath, '--emit-edges'], {
        stdio: ['ignore', 'pipe', 'pipe'],
      })
      let out = ''
      let err = ''
      child.stdout?.on('data', (d) => (out += d.toString()))
      child.stderr?.on('data', (d) => (err += d.toString()))
      child.on('error', (e) =>
        reject(new Error(`gbrg-analyze spawn failed: ${e.message}`)),
      )
      child.on('close', (code) => {
        if (code !== 0) {
          reject(new Error(`gbrg-analyze exited ${code}: ${err.trim()}`))
          return
        }
        try {
          const parsed = JSON.parse(out) as AnalyzeBundle
          if (!Array.isArray(parsed.artifacts) || !Array.isArray(parsed.edges)) {
            throw new Error('expected an {artifacts, edges} object from --emit-edges')
          }
          resolve(parsed)
        } catch (e) {
          reject(
            new Error(
              `gbrg-analyze --emit-edges produced unparseable JSON: ${(e as Error).message}`,
            ),
          )
        }
      })
    })
}

/**
 * End-to-end: run REAL `gbrg-analyze --emit-edges` on `targetPath`, then propagate
 * risk over the REAL `CALLS` topology it surfaced. The call graph is no longer
 * caller-supplied — both the cell risk AND the edges come from real analyze output.
 * Pass `callsOverride` only to force a synthetic topology (tests); when omitted, the
 * analyzer's real `CALLS` edges are used.
 */
export async function analyzeAndPropagate(
  binPath: string,
  targetPath: string,
  opts: PropagateOptions = {},
  callsOverride?: CallEdge[],
): Promise<{
  artifacts: ProofArtifact[]
  calls: CallEdge[]
  propagation: PropagationResult
}> {
  const { artifacts, edges } = await makeAnalyzeWithEdges(binPath)(targetPath)
  const calls = callsOverride ?? callEdgesFromAnalyze(edges)
  return { artifacts, calls, propagation: propagateFromArtifacts(artifacts, calls, opts) }
}
