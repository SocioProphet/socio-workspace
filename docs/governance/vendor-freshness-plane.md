# Vendor freshness plane (W12, increment 1)

## The failure this exists for

`prophet-platform` vendored `socioprophet-hellgraph-0.4.40.tgz` while the engine's
`main` was at **0.4.45**. Five merged releases were invisible in production.

The headline item was a silent-wrong Cypher defect fixed in 0.4.45: against 9,825
real emitted events, `MATCH (n:MarketDataEvent) RETURN n` answered **one row of empty
strings** — HTTP 200, with a `queryHash` and an `evaluatedAtSeq` on it. Node-only
patterns compiled to zero clauses, which `findMatches` satisfies with one empty
binding. Production was confidently wrong, with a receipt.

A second instance was already present and unnoticed: `apps/lifecycle-warden` vendors
its **own separate copy** of the same tarball, byte-identical, equally stale, with no
version guard at all.

Nobody was negligent. There was no mechanism. **Merging an engine PR does not ship
it** — a vendored copy only moves when a human re-vendors it, and nothing in the
estate enumerated the copies, so nothing could notice they had stopped moving.

## Why sociosphere

`sociosphere` already owns the canonical workspace manifest and lock, runner
semantics, and deterministic multi-repo materialization. `docs/TOPOLOGY.md` rule 4
governs submodule pins; `docs/NAMING_VERSIONING.md` §5 governs pin-bump discipline.

A vendored tarball is the same object as a submodule pin — one repo holding another
repo at one version — routed around the mechanism that governs pins. It belongs to
whoever owns cross-repo composition, and that is this repo. The alternative, letting
each consumer police its own vendoring, is exactly the arrangement that produced two
stale copies in one repository.

This increment **extends** the existing surfaces rather than standing beside them:

| Existing convention | How this extends it |
|---|---|
| `manifest/workspace.toml`, `workspace.lock.json` declare repos | Every repo named in the vendor register must resolve to a repo those files already declare. A repo that genuinely is not declared must say `workspace_binding: unbound` **with a reason**; silence fails. |
| `registry/*.yaml` + `registry/*.schema.yaml` + `tools/validate_*.py` | `registry/vendor-freshness.yaml` + `.schema.yaml` + `tools/validate_vendor_freshness.py`, same shape as the impedance ledger. |
| `fixtures/<topic>/bad-*.yaml` negative vectors | `fixtures/vendor-freshness/`, ten negative vectors, each asserted to fail **for its own reason**. |
| `nrg:` repo-graph vocabulary + lift fixtures | `vfp:` vocabulary, sibling namespace, same lift-and-check pattern. |
| `make validate` aggregate + per-topic CI workflow | `make vendor-freshness-validate`, folded into `validate`, plus `.github/workflows/vendor-freshness.yml`. |

**Deliberately not done:** vendored artifacts are *not* added to `manifest/workspace.toml`
as `[[repos]]`. That list is the repo inventory, read by `check_topology.py`,
`check_spine_v0.py`, the lock generator and the canonical-source validators. Artifacts
are not repos; injecting them would corrupt every one of those consumers. The register
is a new file that *binds to* the manifest by URL, which is the extension point that
does not break anything.

## What is actually vendored (seeded 2026-07-29)

Eleven declared artifacts across six upstreams. Every version, digest and constant was
read off disk or out of git, not inferred.

| Artifact | Consumer | State |
|---|---|---|
| `@socioprophet/hellgraph` 0.4.40 | `prophet-platform/apps/hellgraph-service` | **stale, 5 behind**; PR #1030 open |
| `@socioprophet/hellgraph` 0.4.40 | `prophet-platform/apps/lifecycle-warden` | **stale, 5 behind**; no PR, no guard |
| sourceos-spec `MarketDataEvent.json` | `apps/market-replay` | digest-pinned; upstream unobserved |
| sourceos-spec ×4 (Effect/Order/Execution) | `apps/hellgraph-service/src/schemas` | digest-pinned; upstream unobserved |
| KKO 2.10 TBox | `hellgraph/ontology/kko` | current; best-formed provenance in the estate |
| KKO 2.10 TBox (3rd copy) | `apps/owl-reasoner` | current; no runtime assertion |
| KBpedia RC 2.10 ABox | `apps/hellgraph-service/ontology` | **no provenance of any kind** |
| ontogenesis index + shapes | `apps/lattice-studio` | commit `e791402` |
| TriTRPC Go bindings | `libs/go/tritrpcbridge` | second, ungoverned pin of a submodule upstream |
| regis-entity-graph schemas ×4 | `apps/regis-acr-api` | vendored in prose only |
| zero-trust kernel schemas ×6 | `apps/compute-gateway` | called vendored; **no source repo named** |

Findings worth stating plainly, all recorded against their artifacts in the register:

- **The guard never runs.** `apps/hellgraph-service/scripts/check-engine-version.mjs`
  is declared as an npm script (`check:engine`) with **no caller anywhere in
  prophet-platform** — no workflow, no Makefile target, no Dockerfile step. Its
  upstream-staleness step is additionally warn-only by construction. The register
  carries `guard.invoked_by_ci: false` as a first-class declared finding, because a
  guard nobody calls is not a guard.
- **Two commits for one schema family.** `market-replay` pins sourceos-spec
  `487e4b61`; `hellgraph-service` pins `7d74db81`, for the same schemas from the same
  merged PR (#204), via two independent digest mechanisms (Python and TypeScript),
  with nothing reconciling them.
- **A digest pin proves integrity, never currency.** The four `contract.ts` digests
  and the `contract.py` digest all verify correctly today. They detect local
  tampering. They cannot detect that upstream moved — which is this plane's whole
  subject.
- **`SocioProphet/kbpedia` is not in the workspace manifest at all.** The estate
  vendors an ontology from a sovereign fork the workspace controller does not know
  exists. Declared `workspace_binding: unbound` with a reason; binding it properly is
  a workspace-composition change left to a follow-up.
- **Three byte-identical copies of the KKO TBox** across two repos, consistent today
  with nothing enforcing that they stay so.

### Coverage, honestly

The undeclared-artifact sweep only finds what it can mechanically recognise: `*.tgz`
under a `vendor/` directory, and `file:` specifiers in `package.json`. Everything else
— schema copies, ontology copies, source ports — is `declared_only`. A new vendored
JSON schema can still appear without this validator noticing. Closing that needs
provenance markers **at the vendoring site**, not a cleverer scanner. This is recorded
in the register's own `coverage` block rather than left as an unstated limit.

## The graph model

Vocabulary: `registry/vendor-freshness/vendor-freshness.ttl`, namespace
`vfp: <https://socioprophet.org/ns/vendor-freshness#>`.
Worked lift of the current estate: `registry/vendor-freshness/lift.engine-pins.ttl`.

`vfp:` is a deliberate sibling of the existing `nrg:` repo-graph vocabulary.
`nrg:pinnedCommitStale` answers "is this *submodule* pin behind?". `vfp:` answers the
same question for everything that crosses repos **without** a submodule — which is
where the estate actually rotted.

### Nodes

- **`vfp:Repository`** — produces artifacts, hosts consumer apps, or both.
- **`vfp:Artifact`** — one immutable released thing, carrying `vfp:version` and
  `vfp:digest`. Identified by version or digest, never by path.
- **`vfp:ConsumerApp`** — the unit of blast radius. `prophet-platform` is not the
  consumer; `apps/hellgraph-service` is. Modelling at repo granularity is precisely
  what hid the `lifecycle-warden` copy.
- **`vfp:VendorPin`** — reified, because a pin carries its own policy, owner,
  disposition and dates. It is a governed object, not an edge label.
- **`vfp:Release`** and **`vfp:Contract`** — needed for the third question below.

### Edges

`vfp:vendors` (ConsumerApp → Artifact), `vfp:producedBy` (Artifact → Repository),
`vfp:supersededBy` (Artifact → Artifact, transitive), `vfp:pinnedAt` (VendorPin →
Artifact). Supporting: `vfp:pinFor`, `vfp:hostedIn`, `vfp:releasedAs`,
`vfp:changesContract`, `vfp:guardedBy`.

### The three derived questions

Stated precisely enough to implement. All three are **derived** — recomputed from the
graph, never declared.

**1. Staleness.** For a pin `p` with `vfp:pinnedAt` → artifact `a`:

```
gapSize(p) = length of the longest vfp:supersededBy path from a
stale(p)   ⇔ gapSize(p) > 0, subject to freshnessPolicy:
             pin-exact    → never stale, but ONLY if the source records an observed
                            upstream reference. A pin to something nobody has
                            observed is `unknown`, not `current` — it is an unknown
                            wearing a pin's clothes.
             track-minor  → stale if a newer artifact shares a's major version,
                            or if the newest artifact's major differs at all
             track-latest → stale if gapSize > 0
```

Today: `gapSize = 5` for both engine pins.

The enforcement is *not* "stale fails the build" — that would have failed the build on
day one and been switched off. It is: **the declared disposition must agree with the
computed state.** You may not declare `current` while five releases behind. Stale is a
legitimate state to be in; stale-and-undeclared is not. `remediation-required`
carries a `due` date and `waived` carries an `expires` date, and both fail once
passed, so a filed finding cannot quietly become the new silence.

**2. Blast radius.** For a proposed release `r` of repository `R` — *what breaks if I
cut 0.4.46?*

```
blastRadius(r) = | { c : vfp:ConsumerApp | ∃ a . c vfp:vendors a ∧ a vfp:producedBy R } |
```

Answered against `ConsumerApp`, not `Repository`. For engine 0.4.46 today the answer
is **2** — `hellgraph-service` and `lifecycle-warden` — which is exactly the fact that
was unavailable when 0.4.45 was cut.

**3. Contract-crossing risk.** A gap of five patch releases is not inherently
dangerous; a gap that spans a release which moved a load-bearing contract is.

```
crossesContract(p) ⇔ ∃ a', r : a (vfp:supersededBy)+ a'
                              ∧ a' vfp:releasedAs r
                              ∧ r vfp:changesContract _
contractKinds(p)   = { vfp:contractKind of each such contract }   # receipt-shape | schema | fsm
```

Today both engine pins are `crossesContract: true` — 0.4.43 re-implemented
`attribute-rank` peer discovery as an inverted index (receipt-shape risk) and 0.4.45
changed Cypher property projection (schema risk). This is what escalates a bump from
"routine" to "re-verify the golden receipts", and it is why the plane models
`Release` and `Contract` rather than just version numbers.

## Emitting an EffectRequest

The plane does not open PRs. It emits into the estate's existing spine — **event → log
→ materializer → receipt** — and a membrane gate decides.

When the reasoner derives a finding whose disposition permits action, it emits an
**`EffectRequest`** against the schema already vendored at
`apps/hellgraph-service/src/schemas/EffectRequest.json` (`specVersion` `0.1.0`). Its
required fields map as:

| Field | Value |
|---|---|
| `type` | `EffectRequest` (const) |
| `effectKind` | `update` |
| `capability` | `vendor.revendor` |
| `target` | `{ kind: "vendor-pin", identifier: "<artifact_id>", location: "<consumer_repo>/<artifact_path>" }` |
| `parameters` | `{ fromVersion, toVersion, gapSize, blastRadius, crossesContract, contractKinds }` |
| `requestedByEventRef` | the freshness observation event that produced the finding |
| `idempotencyKey` | `<artifact_id>@<fromVersion>-><toVersion>` — a re-emitted finding must not open a second PR |
| `requiresHumanApproval` | `true` whenever `crossesContract` is true |
| `riskLabels` | `contract-crossing`, `receipt-shape`, `schema`, `fsm` as derived |
| `policyLabels` | the consuming app's trust zone |

The membrane gate returns an `EffectDecision` (same vendored schema set). Only on
approve does CI open the re-vendor PR. The decision and its receipt seal into the
existing evidence chain; this plane adds **no new lineage**.

Note the recursion, and that it is not decoration: `EffectRequest.json` and
`EffectDecision.json` are themselves vendored copies of sourceos-spec, declared in
this register as `sourceos-spec-schemas@hellgraph-service` with upstream unobserved.
The contract this plane speaks is subject to this plane.

## Re-vendor discipline

**A detector that ignores this ships rot with a fresh version string.** Every step
below is load-bearing and every one is here because it has already gone wrong.

**1. `npm pack` never rebuilds.** The estate sets `ignore-scripts=true`, so `prepare`
/ `tsup` does **not** run during `npm pack`. A previous release shipped a stale `dist`
in exactly this way. Run an explicit `npm run build` from the upstream ref immediately
before packing.

**2. Assert version markers INSIDE the packed dist.** A `version` field is not
evidence — `package.json` says whatever it says regardless of what the bundle
contains. Extract the tarball and assert against the bundled `ts/dist/index.js`.

For 0.4.40 → 0.4.45 the discriminating marker is **`PROP_NS = "prop:"`** (present in
0.4.45, absent in 0.4.40). Corroborating markers: `nlq` exports (0.4.44), `admissib…`
(0.4.43), `geodesic` (0.4.43).

> **`graph:labels` is NOT a valid marker.** It is present in *both* releases — it was
> always the write-side key, and the defect was that the read side never matched it.
> A marker that is true before and after proves nothing. The register carries the
> valid marker per artifact in `version_marker` for exactly this reason.

**3. Bump the consumer's floor in the same change.** `MIN_ENGINE` in
`check-engine-version.mjs` moves with the tarball or the build goes red — the floor
and the artifact move together. And make the guard *run*: today it has no caller.

**4. Re-run the consumer suite, and read what breaks.** In PR #1030 one existing test
genuinely broke and it was a real finding, not a regression: a test asserting a *loud
refusal* that existed only because engine 0.4.6 mis-answered node-property `WHERE`. It
was a wrong-answer guard, never a capability. It was rewritten to assert correctness —
not pinned back, not deleted.

**5. Verify golden sealed-receipt fixtures are byte-identical across the bump.**
`apps/compute-gateway` pins golden receipts to "the vendored 0.4.40 dist", and 0.4.43
re-implemented the ranker's peer discovery — so this must be checked, never reasoned
about. It was: the same graph through both engines yielded a byte-identical enrich
receipt, `sha256:54fdf6b78ed3797c38fd91f8d115a2ad180c9b7e833ecc07849088b17d4f5dd1`.

> Two different digests are in play and they must not be conflated. The digest above
> is the cross-engine equivalence check over PR #1030's verification graph. The
> **committed golden fixtures** in `apps/compute-gateway/tests/test_engine_seal.py`
> are `sha256:018f2feb…` (enrich) and `sha256:35a9df2d…` (explore), over the graph
> snapshot `{seq:58, nodes:10, edges:8}`. The register records the committed fixtures
> under `receipt_fixtures`, because those are the bytes CI actually compares.

**6. Re-vendor every copy, not the one you were looking at.** `lifecycle-warden` is
the standing proof. Blast radius is a graph query for precisely this reason.

**7. Update this register in the same PR.** `vendored_version`, `vendored_digest`,
`disposition`, and the source's `observed_at` all move together. The validator's
disk check fails otherwise, which is the intended coupling.

## Validator

`tools/validate_vendor_freshness.py`, wired into `make validate` and
`.github/workflows/vendor-freshness.yml`. Five layers:

1. **Well-formedness** — required fields, enums, unique ids, `source_id` referential
   integrity, and the sub-fields each disposition obliges.
2. **Workspace binding** — every repo resolves to one the workspace manifest already
   declares, or says `unbound` with a reason.
3. **Disposition agreement** — freshness recomputed and compared against the declared
   disposition; overdue remediations, expired waivers, and observations older than
   `policy.observation_max_age_days` all fail. The register cannot rot the way the
   artifacts it governs did.
4. **On-disk reality** — declared paths exist, recorded digests match the bytes, and
   any `*.tgz` under `vendor/` or `file:` dependency with no register entry is an
   `UNDECLARED` finding. **Declared > discovered.**
5. **Graph vocabulary** — every `vfp:` term used in a lift graph is declared in the
   vocabulary, and the four spine terms exist.

Layers 1–3 and 5 always run. Layer 4 needs the consumer repos on disk; where they are
absent it reports `SKIPPED`, **never** passed. Consumer repos are located via
`--repo-root NAME=PATH`, `VENDOR_FRESHNESS_REPO_ROOTS`, the materialized workspace
path, then `~/dev/<name>`.

```
$ make vendor-freshness-validate
NOTE: WORKSPACE-UNBOUND source 'kbpedia-kko': SocioProphet/kbpedia is not declared in the workspace manifest (declared, with reason)
NOTE: STALE hellgraph-engine@hellgraph-service: vendored 0.4.40 is behind upstream 0.4.45 [disposition remediation-open]
NOTE: GUARD-NOT-INVOKED hellgraph-engine@hellgraph-service: apps/hellgraph-service/scripts/check-engine-version.mjs
NOTE: STALE hellgraph-engine@lifecycle-warden: vendored 0.4.40 is behind upstream 0.4.45 [disposition remediation-required]
NOTE: GUARD-NOT-INVOKED hellgraph-engine@lifecycle-warden: no guard declared
validated 11 declared vendored artifact(s) in vendor-freshness.yaml
```

Ten negative vectors in `fixtures/vendor-freshness/`, each executed by
`tests/test_vendor_freshness.py` and asserted to fail **for its own reason** — plus a
test asserting that no fixture sits in the directory unrun, because a written-but-never-executed
fixture is the same failure class as a never-invoked guard.

## Not in this increment

- No network calls. `upstream_latest_*` is recorded with an `observed_at` and an
  `observation_method`, and ages out. Automated observation is increment 2.
- No lift generator. `lift.engine-pins.ttl` is hand-authored from the register.
- No `EffectRequest` emission. The mapping above is specified, not implemented.
- No SHACL shapes for `vfp:` (the `nrg:` sibling has them).
- The `lifecycle-warden` bump itself — filed as `VFP-0001`, due 2026-09-30, which the
  validator will begin failing on.
