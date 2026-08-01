/**
 * risk_propagation_test.ts — LIVE test of GBRG causal TRACK 1.
 *
 * Runs the REAL gbrg-analyze CLI on a real A→B→C source fixture to obtain REAL
 * ProofArtifacts, then runs the REAL @socioprophet/hellgraph forwardChain()
 * over the projected risk graph. Nothing here is mocked.
 *
 * Scenario: cellA calls cellB calls cellC; cellC is the deepest, untested,
 * speculative (high-risk) cell. The CALL TOPOLOGY is NOT hand-supplied — it comes
 * from `gbrg-analyze --emit-edges` (the analyzer's REAL internal `CALLS` graph). We
 * propagate risk UP that real graph and assert:
 *   (a) the analyzer surfaced the real A→B and B→C `CALLS` edges (topology is real);
 *   (b) a DERIVED A→C transitive-risk edge exists (produced by PLN deduction);
 *   (c) its confidence < the confidence of the direct edges (per-hop decay);
 *   (d) its strength is sane (0 < s <= 1 and s <= each direct edge's strength).
 */

import { test } from 'node:test'
import assert from 'node:assert/strict'
import { mkdtempSync, writeFileSync, existsSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import {
  makeAnalyzeWithEdges,
  callEdgesFromAnalyze,
  propagateFromArtifacts,
  cellFromArtifact,
  type CallEdge,
  type ProofArtifact,
} from '../risk_propagation.ts'

const HERE = dirname(fileURLToPath(import.meta.url))

/** Locate the REAL gbrg-analyze binary (env override, else worktree/main target). */
function resolveBin(): string {
  const candidates = [
    process.env.GBRG_ANALYZE_BIN,
    join(HERE, '..', '..', 'target', 'release', 'gbrg-analyze'),
    join(HERE, '..', '..', 'target', 'debug', 'gbrg-analyze'),
  ].filter(Boolean) as string[]
  for (const c of candidates) if (existsSync(c)) return c
  throw new Error(
    `gbrg-analyze binary not found. Build it: (cd gbrg && cargo build -p gbrg-analyze --release), ` +
      `or set GBRG_ANALYZE_BIN. Looked at:\n  ${candidates.join('\n  ')}`,
  )
}

/** Write a real A→B→C TypeScript fixture and return its directory. */
function writeChainFixture(): string {
  const dir = mkdtempSync(join(tmpdir(), 'gbrg-pln2-'))
  writeFileSync(
    join(dir, 'chain.ts'),
    [
      'export function cellA(x: number): number { return cellB(x) + 1 }',
      'export function cellB(x: number): number { return cellC(x) * 2 }',
      'export function cellC(x: number): number { return x - 3 }',
      '',
    ].join('\n'),
  )
  return dir
}

test('PLN transitive-risk propagation A→B→C: derived A→C edge with confidence decay', async () => {
  const bin = resolveBin()
  const dir = writeChainFixture()

  // ── (1) REAL subprocess: get REAL ProofArtifacts + REAL edge topology ────
  const bundle = await makeAnalyzeWithEdges(bin)(dir)
  const artifacts: ProofArtifact[] = bundle.artifacts
  console.log(`\n[live] gbrg-analyze bin: ${bin}`)
  console.log(`[live] real ProofArtifacts returned: ${artifacts.length}`)
  console.log(`[live] real edges surfaced by --emit-edges: ${bundle.edges.length}`)
  for (const e of bundle.edges) {
    console.log(`[live] EDGE  ${e.kind}  ${short(e.from)} -> ${short(e.to)}`)
  }

  const cellId = (fn: string) =>
    artifacts.find((a) => (a.cell_id ?? '').endsWith(`#${fn}`))?.cell_id

  const A = cellId('cellA')
  const B = cellId('cellB')
  const C = cellId('cellC')
  assert.ok(A && B && C, `expected cellA/cellB/cellC artifacts, got: ${artifacts.map((a) => a.cell_id).join(', ')}`)

  for (const [name, id] of [['A', A], ['B', B], ['C', C]] as const) {
    const a = artifacts.find((x) => x.cell_id === id)!
    console.log(
      `[live] cell${name}: epistemicLevel=${a.claim.epistemicLevel} ` +
        `test_coverage_reach=${a.test_coverage_reach} blast_radius=${a.blast_radius}`,
    )
  }

  // The deepest cell C must be the high-risk, untested seed (analyzer's verdict).
  const cCell = cellFromArtifact(artifacts.find((x) => x.cell_id === C)!)
  assert.equal(cCell.epistemicLevel, 'speculative', 'cellC should be speculative (untested/unproven)')
  assert.equal(cCell.testCoverageReach, false, 'cellC should be untested')

  // ── (2) Call topology comes from the analyzer's REAL edges, NOT hand-built ─
  const calls: CallEdge[] = callEdgesFromAnalyze(bundle.edges)
  // Prove the real topology is present: A→B and B→C were resolved by gbrg-analyze
  // itself (intra-file CALLS resolution), not supplied by this test.
  assert.ok(
    calls.some((e) => e.from === A && e.to === B),
    `expected a REAL A→B CALLS edge from gbrg-analyze, got: ${JSON.stringify(calls)}`,
  )
  assert.ok(
    calls.some((e) => e.from === B && e.to === C),
    `expected a REAL B→C CALLS edge from gbrg-analyze, got: ${JSON.stringify(calls)}`,
  )
  // And no fabricated shortcut edge (A→C is DERIVED by PLN, never emitted by analyze).
  assert.ok(
    !calls.some((e) => e.from === A && e.to === C),
    'gbrg-analyze must NOT emit a direct A→C edge; A→C is a DERIVED transitive edge only',
  )

  // ── (3) REAL forwardChain over the projected risk graph ─────────────────
  const result = propagateFromArtifacts(artifacts, calls)

  console.log(`[live] forwardChain stats: ${JSON.stringify(result.pln)}`)
  for (const s of result.seeds) {
    console.log(`[live] SEED  ${short(s.from)} -> ${short(s.to)}  strength=${s.strength} confidence=${s.confidence}`)
  }
  for (const d of result.derived) {
    console.log(
      `[live] DERIV ${short(d.from)} -> ${short(d.to)}  strength=${round(d.strength)} ` +
        `confidence=${round(d.confidence)} hops=${d.hops} class=${d.epistemicClass}`,
    )
  }

  // ── (a) a DERIVED A→C transitive-risk edge exists ───────────────────────
  const ac = result.derived.find((d) => d.from === A && d.to === C)
  assert.ok(ac, 'expected a DERIVED A→C transitive-risk edge from PLN deduction')
  assert.equal(ac!.epistemicClass, 'pln_deduction', 'derived edge must come from PLN deduction')
  assert.equal(ac!.hops, 2, 'A→C should be a 2-hop transitive edge')

  // Direct (seed) edges for comparison.
  const ab = result.seeds.find((s) => s.from === A && s.to === B)!
  const bc = result.seeds.find((s) => s.from === B && s.to === C)!
  const minDirectConf = Math.min(ab.confidence, bc.confidence)
  const minDirectStr = Math.min(ab.strength, bc.strength)

  // ── (b) confidence DECAY: derived confidence < both direct edges ────────
  assert.ok(
    ac!.confidence < minDirectConf,
    `derived confidence ${ac!.confidence} should be < min direct confidence ${minDirectConf} (per-hop decay)`,
  )
  // hellgraph's rule is c = c1·c2·0.9 — assert that exact relationship holds.
  const expectedConf = ab.confidence * bc.confidence * 0.9
  assert.ok(
    Math.abs(ac!.confidence - expectedConf) < 1e-9,
    `derived confidence ${ac!.confidence} should equal c1·c2·0.9 = ${expectedConf}`,
  )

  // ── (c) strength is sane ────────────────────────────────────────────────
  assert.ok(ac!.strength > 0 && ac!.strength <= 1, `derived strength ${ac!.strength} out of (0,1]`)
  assert.ok(
    ac!.strength <= minDirectStr + 1e-9,
    `derived strength ${ac!.strength} should be <= min direct strength ${minDirectStr}`,
  )
  const expectedStr = ab.strength * bc.strength
  assert.ok(
    Math.abs(ac!.strength - expectedStr) < 1e-9,
    `derived strength ${ac!.strength} should equal s1·s2 = ${expectedStr}`,
  )

  console.log(
    `[live] PASS — A→C derived: strength=${round(ac!.strength)} confidence=${round(ac!.confidence)} ` +
      `(< direct confidence ${minDirectConf}); decay confirmed.\n`,
  )
})

function short(id: string): string {
  const h = id.indexOf('#')
  return h >= 0 ? id.slice(h) : id
}
function round(n: number): number {
  return Math.round(n * 1e6) / 1e6
}
