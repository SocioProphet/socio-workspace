#!/usr/bin/env node
/**
 * generate_dependency_graph.mjs — regenerate registry/dependency-graph.yaml from
 * MEASURED evidence, replacing the hand-authored version.
 *
 * Why: the hand-authored file (updated 2026-04-06) declared 60 edges of which
 * exactly ONE had both endpoints in a repo that exists. 38 of the 47 repo names
 * it referenced — adapter-contracts, asr-service, connector-jira, event-bus,
 * design-system — exist nowhere across the three orgs. A topology registry that
 * describes a different estate is worse than no registry, because it is trusted.
 *
 * Every edge here carries EVIDENCE (the file it was read from) and a KIND.
 * Nothing is inferred, nothing is aspirational. Edges to repos outside the three
 * orgs are recorded as `external: true` rather than dropped or pretended into
 * the estate.
 */
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';

const ORGS = (process.argv[2] ?? 'SocioProphet,SociOS-Linux,SourceOS-Linux').split(',');
const SINCE = process.argv[3] ?? '2026-05-01';
const OUT = process.argv[4] ?? new URL('../registry/dependency-graph.yaml', import.meta.url).pathname;

const sh = (args) => execFileSync('gh', args, { encoding: 'utf8', maxBuffer: 64*1024*1024, stdio: ['ignore','pipe','pipe'] });
const ghAll = (ep, jq) => sh(['api','-X','GET',ep,'--paginate','--jq',jq]).trim().split('\n').filter(Boolean).map(l=>JSON.parse(l)).flat();
const sleep = (ms) => Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);

// Org names come from argv (process.argv[2]); escape them before interpolating into a
// RegExp so a metacharacter in an org name cannot inject a pattern or cause backtracking.
const reEsc = (s) => String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

// ---- the real repo set (paginated; truncation here is what caused the drift
//      to be mis-measured in the first place) ---------------------------------
const realRepos = new Map(); // name -> org
for (const org of ORGS) {
  for (const r of ghAll(`orgs/${org}/repos?per_page=100`, '[.[]|{name:.name,pushed:.pushed_at,archived:.archived}]')) {
    if (!r.archived) realRepos.set(r.name, { org, pushed: r.pushed });
  }
  sleep(400);
}
const scanned = [...realRepos.entries()].filter(([, v]) => v.pushed > SINCE);
process.stderr.write(`[deps] ${realRepos.size} live repos, scanning ${scanned.length} pushed since ${SINCE}\n`);

const edges = [];
let scannedOk = 0, scanFailed = 0;

/** Read a file's text, or null when absent. 404 is the common case, not an error. */
function readFile(full, path) {
  try {
    const b64 = sh(['api', `repos/${full}/contents/${path}`, '--jq', '.content']).trim();
    return Buffer.from(b64, 'base64').toString('utf8');
  } catch { return null; }
}

for (const [name, meta] of scanned) {
  const full = `${meta.org}/${name}`;
  try {
    const b64 = sh(['api',`repos/${full}/contents/.gitmodules`,'--jq','.content']).trim();
    const text = Buffer.from(b64, 'base64').toString('utf8');
    for (const m of text.matchAll(/url\s*=\s*(\S+)/g)) {
      const target = m[1].replace(/\.git$/, '').split('/').pop();
      if (!target || target === name) continue;
      edges.push({
        from: name, to: target, type: 'submodule',
        evidence: `${full}/.gitmodules`,
        external: !realRepos.has(target),
      });
    }
    scannedOk += 1;
  } catch (e) {
    // 404 = no .gitmodules, which is the common case and NOT a failure.
    if (!/404|Not Found/.test(e.message)) scanFailed += 1;
    else scannedOk += 1;
  }
  sleep(200);

  // --- package manifests: this is where FIRST-PARTY coupling actually lives.
  //     .gitmodules turned out to measure vendoring (albert, openvino, asahi
  //     forks), not estate architecture, so it cannot be the only source.
  const pkg = readFile(full, 'package.json'); sleep(180);
  if (pkg) {
    try {
      const j = JSON.parse(pkg);
      const deps = { ...(j.dependencies||{}), ...(j.devDependencies||{}) };
      for (const [dep, spec] of Object.entries(deps)) {
        const src = `${dep} ${spec}`;
        for (const org of ORGS) {
          const m = src.match(new RegExp(`${reEsc(org)}/([A-Za-z0-9._-]+)`));
          if (m && m[1] !== name) {
            edges.push({ from: name, to: m[1], type: 'package',
              evidence: `${full}/package.json`, external: !realRepos.has(m[1]) });
          }
        }
      }
    } catch {}
  }

  // --- workflow `uses:` — CI often reveals coupling the code does not, because
  //     a reusable workflow or composite action IS a hard runtime dependency.
  try {
    const wfs = JSON.parse(sh(['api', `repos/${full}/contents/.github/workflows`, '--jq',
      '[.[]|select(.name|endswith(".yml") or endswith(".yaml"))|.name]']));
    for (const wf of wfs.slice(0, 12)) {
      const text = readFile(full, `.github/workflows/${wf}`);
      if (!text) continue;
      for (const org of ORGS) {
        for (const m of text.matchAll(new RegExp(`uses:\\s*${reEsc(org)}/([A-Za-z0-9._-]+)`, 'g'))) {
          if (m[1] !== name) {
            edges.push({ from: name, to: m[1], type: 'workflow',
              evidence: `${full}/.github/workflows/${wf}`, external: !realRepos.has(m[1]) });
          }
        }
      }
      sleep(120);
    }
  } catch { /* no workflows dir */ }
  sleep(150);

  const gomod = readFile(full, 'go.mod'); sleep(180);
  if (gomod) {
    for (const org of ORGS) {
      for (const m of gomod.matchAll(new RegExp(`github\\.com/${reEsc(org)}/([A-Za-z0-9._-]+)`, 'g'))) {
        if (m[1] !== name) {
          edges.push({ from: name, to: m[1], type: 'gomod',
            evidence: `${full}/go.mod`, external: !realRepos.has(m[1]) });
        }
      }
    }
  }
}

// Dedupe: the same reusable workflow referenced by five files is ONE dependency.
const seen = new Set();
const deduped = edges.filter((e) => {
  const k = `${e.from}|${e.to}|${e.type}`;
  if (seen.has(k)) return false;
  seen.add(k); return true;
});
edges.length = 0; edges.push(...deduped);

const internal = edges.filter(e => !e.external);
const external = edges.filter(e => e.external);
const nodes = [...new Set(edges.flatMap(e => [e.from, e.to]))].sort();

// Derive the finding from the data rather than hardcoding prose that goes stale.
// Hubs are what actually explain this graph: a few repos that many others depend
// on, which is where the estate's real coupling lives.
const inDeg = {};
for (const e of internal) inDeg[e.to] = (inDeg[e.to] ?? 0) + 1;
const hubs = Object.entries(inDeg).filter(([, n]) => n >= 2).sort((a, b) => b[1] - a[1]);
const byType = (t) => internal.filter(e => e.type === t).length;
const finding = [
  `# FINDING (derived, regenerated with the data):`,
  `# ${internal.length} first-party edge(s) across ${scanned.length} scanned repos.`,
  `# By type: ` + ['submodule','package','gomod','workflow'].map(t => `${t}=${byType(t)}`).join(', ') + '.',
  hubs.length
    ? `# HUBS (>=2 dependents): ` + hubs.map(([n, c]) => `${n} (${c})`).join(', ') + '.'
    : `# No repo has 2+ first-party dependents.`,
  byType('workflow') > byType('package') + byType('gomod')
    ? `# The estate is coupled through CI GOVERNANCE, not through code: shared`
      + `\n# reusable workflows outnumber package/module dependencies`
      + ` ${byType('workflow')} to ${byType('package') + byType('gomod')}.`
      + `\n# Repos are joined by the standards they must satisfy rather than by the`
      + `\n# libraries they import. Whether that is disciplined governance or missing`
      + `\n# shared libraries is a judgement this file does not try to settle.`
    : `# Code dependencies outnumber CI ones; coupling is through libraries.`,
  `# 'submodule' largely measures VENDORING of forks, not architecture — read the`,
  `# types before reading the total, and do not sum them into one number.`,
].join('\n');

const y = `# registry/dependency-graph.yaml
# GENERATED by tools/generate_dependency_graph.mjs — do not hand-edit.
#
# Every edge below was READ FROM A FILE in a real repository and carries the
# path it came from. Nothing is inferred and nothing is aspirational.
#
# This replaces the hand-authored graph (last updated 2026-04-06), which declared
# 60 edges of which exactly one had both endpoints in a repo that exists, and
# named 38 repos — adapter-contracts, asr-service, connector-jira, event-bus,
# design-system and others — that exist nowhere across the three orgs. A topology
# registry that describes a different estate is worse than none, because it is
# trusted.
#
# SCOPE IS DECLARED, NOT IMPLIED: only repos pushed since ${SINCE} were scanned
# (${scanned.length} of ${realRepos.size} live repos across ${ORGS.length} orgs). An absent edge
# means "not observed in that scope", never "does not exist".
#
# METHOD: three evidence sources, kept as distinct types.
#   submodule  .gitmodules url declarations
#   package    package.json deps naming an estate org
#   gomod      go.mod requires naming an estate org
#   workflow   .github/workflows 'uses:' a reusable workflow / composite action
#
# READ THE TYPES BEFORE READING THE COUNTS. 'submodule' turned out to measure
# VENDORING, not architecture: the heaviest submodule users are vendored forks
# (albert, openvino, kustomize) and the only estate-internal submodule edges are
# asahi-installer -> artwork/m1n1, themselves a fork of Asahi Linux. First-party
# coupling, where it exists, shows up as 'package' or 'gomod'. Do not sum the
# types into one number and call it architecture.

version: "2.0.0"
generated_at: "${new Date().toISOString()}"
generated_by: tools/generate_dependency_graph.mjs
method: gitmodules+package+gomod+workflow-scan
basis: measured
scope:
  orgs: [${ORGS.map(o=>`"${o}"`).join(', ')}]
  pushed_since: "${SINCE}"
  repos_live: ${realRepos.size}
  repos_scanned: ${scanned.length}
  repos_scan_failed: ${scanFailed}
${finding}
summary:
  edges_total: ${edges.length}
  edges_internal: ${internal.length}
  edges_external: ${external.length}
  nodes: ${nodes.length}
by_type:
${['submodule','package','gomod','workflow'].map(t=>`  ${t}: ${edges.filter(e=>e.type===t).length}`).join('\n')}
first_party_by_type:
${['submodule','package','gomod','workflow'].map(t=>`  ${t}: ${internal.filter(e=>e.type===t).length}`).join('\n')}

edges:
${edges.length ? edges.map(e => `  - from: ${e.from}
    to: ${e.to}
    type: ${e.type}
    evidence: ${e.evidence}
    external: ${e.external}`).join('\n') : '  []  # none observed in scope'}
`;
fs.writeFileSync(OUT, y);
process.stdout.write(`[deps] ${edges.length} edges (${internal.length} internal, ${external.length} external) over ${nodes.length} nodes → ${OUT}\n`);
