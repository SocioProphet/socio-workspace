# Vendor freshness plane (W12)

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
   `UNDECLARED` finding. **Declared > discovered.** The same pass VERIFIES
   `guard.invoked_by_ci` by following the invocation chain in the consumer repo, and
   compares a declared guard floor against the value the guard file actually holds
   (W12.6 below).
5. **Graph vocabulary** — every `vfp:` term used in a lift graph is declared in the
   vocabulary, and the four spine terms exist.

Layers 1–3 and 5 always run. Layer 4 needs the consumer repos on disk; where they are
absent it reports `SKIPPED`, **never** passed. Consumer repos are located via
`--repo-root NAME=PATH`, `VENDOR_FRESHNESS_REPO_ROOTS`, the materialized workspace
path, then `~/dev/<name>`.

Real output, against both consumer repos materialized (abridged):

```
$ make vendor-freshness-validate
NOTE: WORKSPACE-UNBOUND source 'kbpedia-kko': SocioProphet/kbpedia is not declared in the workspace manifest (declared, with reason)
NOTE: CONTRACT-REVIEW-PENDING source 'hellgraph-engine': 44 release(s) 0.1.0..0.4.39 were appended by the detector and nobody has said what they moved
NOTE: STALE sourceos-spec-schemas@market-replay: vendored commit 487e4b61… != upstream 65925aed… [disposition remediation-required]
NOTE: GUARD-NOT-INVOKED sourceos-spec-schemas@market-replay: apps/market-replay/src/market_replay/contract.py
NOTE: GUARD-INVOKED hellgraph-engine@hellgraph-service: apps/hellgraph-service/scripts/check-engine-version.mjs <- `make engine-guards` in .github/workflows/validate-target-diagnostics.yml (Makefile) runs apps/hellgraph-service/scripts/check-engine-version.mjs
validated 11 declared vendored artifact(s) in vendor-freshness.yaml
```

Negative vectors in `fixtures/vendor-freshness/`, each executed by
`tests/test_vendor_freshness.py` and asserted to fail **for its own reason** — plus a
test asserting that no fixture sits in the directory unrun, because a written-but-never-executed
fixture is the same failure class as a never-invoked guard.

## Not in increment 1

- No lift generator. `lift.engine-pins.ttl` is hand-authored from the register.
- No SHACL shapes for `vfp:` (the `nrg:` sibling has them).
- The `lifecycle-warden` bump itself — filed as `VFP-0001`, due 2026-09-30, which the
  validator will begin failing on.

---

# Increment 2 — the detector (W12.2)

Increment 1 recorded what upstream looked like **when a human last looked**. This is
the machine that looks, so that "a human last looked" stops being the mechanism.

`tools/detect_vendor_freshness.py`, `make vendor-freshness-detect`,
`.github/workflows/vendor-freshness-detect.yml` (daily, plus `repository_dispatch:
upstream-release`, plus manual).

## Observe → recompute → emit

**Observe.** `git ls-remote` against a public HTTPS URL. That is the entire network
surface: no API token, no registry credential, no new secret.

> **Argument order is load-bearing.** Flags precede the URL; ref patterns follow it.
> `git ls-remote main <url>` treats `main` as the repository and fails with
> *"'main' does not appear to be a git repository"* — a message that reads like a
> permissions problem and is not one. It silently made three sources look unreachable
> on the first run.

> **Do not pass `--refs`.** An annotated tag's own sha is the sha of the tag OBJECT,
> and `--refs` suppresses exactly the `^{}` peeled lines that reveal the commit.
> hellgraph mixes annotated and lightweight tags, so both forms must be handled.

**Recompute.** By importing `compute_state` from the validator — not by computing the
same answer, but by calling the same function object, which
`test_detector_uses_the_gates_definition_of_stale` asserts. A detector with its own
opinion of staleness is a second register, and two registers disagreeing is how the
first stops being believed.

**Emit.** One `EffectRequest` per stale artifact, in the shape § *Emitting an
EffectRequest* specifies, whose `parameters` carry the evidence rather than a diff
summary: gap size and the releases in it, blast radius over consumer APPS, contract
crossings with the Contract node each one moved, the discriminating version marker,
the golden receipt fixtures that must survive, the guard floor that moves with the
tarball, and every file that names the pin.

## What the first real run found

Three things nobody knew, produced by the detector on its first execution:

1. **`sourceos-spec` had moved.** Both consumers were behind
   (`487e4b61` and `7d74db81` vs head `f656559c`). The register said
   `observation-required` because nobody had ever looked.
2. **`ontogenesis` was actually current.** `e791402` IS upstream head — good news that
   was previously unverifiable.
3. **`v0.4.42` is a duplicate tag, not a release.** `v0.4.41` and `v0.4.42` point at
   the same commit, whose `package.json` says `0.4.41`. Anyone pinning `v0.4.42` gets
   `0.4.41` bytes. The 0.4.40 → 0.4.45 gap is **five tags but four distinct
   releases**, and the peer-index rewrite ships in `0.4.43`, which
   `git tag --contains 92401f6` settles and the commit subjects (which say "0.4.42")
   do not.

The detector now computes `tag_aliases` from the ls-remote output it already has, and
drops alias duplicates from every gap count.

## The detector maintains the register

- **Observation fields** are rewritten in place, line-surgically. Never through a YAML
  dumper: the register's comments carry its findings and a round-trip would delete
  every one. `observation_method` becomes machine-owned once the detector runs; the
  human prose it replaces was findings, and findings belong on artifacts — all three
  displaced notes were already duplicated there, which was checked before replacing
  them.
- **`releases:`** gains newly observed tags, so the supersession chain stays current
  as a side effect of polling rather than as a chore. Appended entries carry
  `contract_review: pending` and **no `changes_contract`**: what a release moved is a
  judgement about behaviour, and a detector that guessed it from the version number
  would manufacture exactly the false assurance this plane removes. 0.4.45 was a
  *patch* bump and it changed what a Cypher query answers.
- **`disposition`** — with `--propose-disposition`, when an observation makes a
  declared position false the detector files the weakest defensible disposition for
  the computed state, with a `finding_id` and a tier-derived `due` date. It never
  overwrites a disposition that already agrees: a human's `remediation-open` naming a
  real PR stands. Without this, every refresh would hand a human a red build to repair
  by hand — the labour this exists to delete.

## Why the detector does not open the re-vendor PR

It cannot, without a credential this estate has decided not to have. sociosphere's
`GITHUB_TOKEN` is scoped to sociosphere; opening a PR in `prophet-platform` needs a
cross-repo PAT or a GitHub App installation token, both new long-lived secrets.

So the direction is inverted. The **consumer pulls**:
`prophet-platform/.github/workflows/revendor-vendored-artifact.yml` clones this repo
(public — anonymous, no token), runs the detector filtered to its own artifacts, and
opens the PR with its own `GITHUB_TOKEN`.

That is not a workaround for a missing credential. The re-vendor work is a build, a
pack, a lockfile and a test suite, all of which are the consumer's toolchain. A
cross-repo token would have bought the ability to push a branch, not the ability to
verify it — and an unverified re-vendor is the thing being replaced.

The `detect` job there runs another repo's code, so it holds **no write permissions**
and hands the writing job nothing but JSON. The job that can push a branch never
executes foreign code.

## What the executor proves, beyond the merged discipline

`tools/revendor/revendor.mjs` in the consumer repo performs every step of
§ *Re-vendor discipline* and fails the job on any of them. Two additions:

**The marker must DISCRIMINATE.** Asserting the marker is present in the new tarball
is half a check. The executor also asserts it is **absent from the outgoing one**, and
fails if it is in both — naming `graph:labels` as the reason. Verified against the
real bytes: `PROP_NS = "prop:"` absent in 0.4.40, present in 0.4.45; `graph:labels`
present in both. Read with `fs.readFileSync`; `file(1)` reports that bundle as `data`,
which is precisely why grep must not be used on it.

**The golden receipts, stated exactly.** `test_engine_seal.py`'s fixtures are **frozen
string constants** — that test never spawns node, never reads `vendor/*.tgz`, and
never invokes the engine. Running it green across a bump therefore says *nothing* about
the new engine, and reporting it as "golden receipts verified" would be a false
assurance of the exact kind this plane deletes. What the executor checks is that the
committed digests are byte-identical before and after, so a re-vendor cannot quietly
regenerate them. What remains uncovered — whether the NEW engine still emits those
bytes — is stated in the PR body rather than left implied. The coupling is real:
`engine_receipts.py` pins the key order to "the vendored 0.4.40 dist" and refuses
unknown keys, so a release that adds a field becomes a 422 in production while that
test stays green.

---

# Increment 5 — the fail-closed gate (W12.5)

## Before and after

**Before.** `.github/workflows/vendor-freshness.yml` ran the validator with the
consumer repos absent, so layer 4 reported `SKIPPED` for all eleven artifacts and the
job went green **having read no vendored bytes at all**. The register was checked
against itself. A drifted digest, a deleted tarball, or an UNDECLARED second copy
appearing — the `lifecycle-warden` case exactly — were all invisible.

**After.** Both consumer repos are cloned (public, anonymous, no token) and
`--require-disk` names them, so a checkout that silently did not happen is an ERROR
rather than a `SKIPPED` that still prints green. `--skip-disk` together with
`--require-disk` is rejected as contradictory. The job additionally **proves the gate
still fails**, by running it against a known-bad fixture and against a missing repo
and failing if either is accepted — a gate nobody has watched fail is a gate nobody
knows is wired up, which is the same class of finding as `check:engine`.

## Tier

`tier: foundation | reference` on every artifact, required.

**Tier grades the severity of UNVERIFIABILITY. It never grades CONTRADICTION.** A
declared disposition that contradicts the recomputed state fails at every tier,
always; `test_tier_never_softens_a_contradiction` asserts it for both. If tier could
soften that, it would be a supported way to opt out of the gate.

| | foundation | reference |
|---|---|---|
| observation budget | 30 days | 90 days |
| upstream the detector cannot observe | ERROR unless `observation_gap {reason, revisit_by}` | NOTE |
| expired `observation_gap.revisit_by` | ERROR | — |
| contradiction | ERROR | ERROR |

A source inherits the **strictest** tier of anything vendored from it. The clock runs
only against sources that ARE observable: you cannot be late looking at something
there is no way to look at, but you can be late building the way to look at it, and
`revisit_by` is that ratchet.

The pair `bad-foundation-observation-too-old.yaml` /
`good-reference-observation-tolerated.yaml` carry the same 44-day-old observation and
differ only in tier — one must fail, one must pass. If they ever agree, the tier has
stopped meaning anything.

**The 30-day foundation budget is what makes the detector non-optional.** Stop running
it and this repo goes red on day 31 and says why. The automation cannot fail silently,
because its silence *is* the failure signal.

## The release chain must be walkable

`gapSize` is the length of a `vfp:supersededBy` path. A semver source that declares no
`releases:`, or declares a latest version it does not list, or is pinned at a version
it does not list, has a chain with a hole — and a hole makes the derived questions
answer from a *shorter* path, which is a smaller number in the reassuring direction.
So it is an error, not a note. Contract-silence is the opposite: common, legitimate,
and reported only.

## Making the gate block

The workflow fails the run. Making it a **required status check** on `main` is a
repository-ruleset change, not a workflow change, and a required context that does not
yet exist on `main` blocks every open PR in the repo the moment it is added. It must
therefore be added AFTER this workflow is on `main`:

```
gh api -X POST repos/SocioProphet/sociosphere/rulesets ... \
  required_status_checks: [{ context: "vendor-freshness" }]
```

sociosphere currently has exactly one ruleset (Copilot review) and no required status
checks at all, so this is a deliberate, separate decision — not something to smuggle
in with a feature PR.

---

# Increment 6 — the register stops taking its own word for it (W12.6)

Increment 5 made the gate fail closed on **contradiction**. This one removes the
remaining places where the register was believed rather than checked.

## `invoked_by_ci` is verified, not asserted

It was a boolean anyone could type. That is the *same shape* as the finding the plane
was built on: `check:engine` was declared in `apps/hellgraph-service/package.json`,
called by no workflow, no Makefile target and no Dockerfile, had never once run — and
was cited as the authority that stale engines get caught. Re-creating an unfalsifiable
claim inside the tool built to destroy unfalsifiable claims is the one outcome worth
refusing outright.

So the validator follows the chain, in the consumer repo, on disk:

| shape | evidence required |
|---|---|
| direct | the guard path appears in a workflow file |
| via make | the guard path is in the recipe of a target reachable, through prerequisites, from a target a workflow names |
| via npm | the guard path is in a `package.json` script that a workflow, or a CI-reachable make target, actually **runs** |

Anything else is *unverified*, and `invoked_by_ci: true` with no evidence is an ERROR.
Three deliberate properties:

- **Declaring is not invoking.** A `package.json` script naming the guard is not
  evidence; something has to run the script. That is the original hole, restated as a
  test (`test_invoked_by_ci_true_with_an_npm_script_nobody_runs_still_fails`).
- **Reachability is from CI**, not from a developer's terminal. A make target no
  workflow names has never run in CI, however correct it is.
- **Paths match repo-relative, never by basename.** `apps/hellgraph-service` and
  `apps/lifecycle-warden` both ship a file called `check-engine-version.mjs`. A
  basename match would report one app's invocation as proof for the other — the exact
  confusion that let a second copy of the same stale tarball sit unnoticed.

**What it found the first time it ran**, which is the only real test of a check like
this — two of the four guards claiming `invoked_by_ci: true` did not survive it:

- `apps/market-replay/src/market_replay/contract.py` asserts `SCHEMA_SHA256` at
  *import*. Its only importers are market-replay's own emitter and tests, and nothing
  in CI runs them: `make test-python-apps` enumerates five apps and market-replay is
  not among them; the one workflow naming it is `images.yml`, which is
  push-to-main/dispatch only and whose Dockerfile `pip install`s and copies `src`
  without importing anything.
- `apps/hellgraph-service/src/contract.ts` enforces four digests in `loadSchema()`.
  Imported only by `contract.test.ts` and `membrane.ts`; the app's `test` script would
  run it, and no workflow or CI-reachable make target runs that script.

Both are now `invoked_by_ci: false` with the finding written down. The two engine
guards passed on evidence: `validate-target-diagnostics.yml` matrix → `make
engine-guards` → `node apps/<app>/scripts/check-engine-version.mjs`.

## A declared floor must be the floor the file holds

The register recorded `MIN_ENGINE = 0.4.40` for both engine pins. The file on
`origin/main` says `0.4.45` — it moved with the tarball in #1030/#1032 and the register
did not follow. A floor nobody re-reads rots exactly the way a tarball does, so
`floor_constant` + `floor_value` are now read out of the guard file and compared.

## `vfp:guardedBy` is finally written

It was declared in the vocabulary and exported in the engine's edge constants
(`VFP_EDGE.guardedBy`) and **never once emitted**, because the register described a
guard as a `path` — a string, which cannot be the object of a `VendorPin → Contract`
edge. `guard.guards_contract` supplies the endpoint, its ids are checked against the
source's `contracts:` catalog, and `lift.engine-pins.ttl` now emits the edge.

## Contract crossings, declared

`hellgraph-engine` now carries the full 49-release chain and a `contracts:` catalog.
The split of labour is the point:

| maintained by `make vendor-freshness-detect` | stays hand-declared |
|---|---|
| `version`, `ref`, `commit` for every observed tag | `contracts:` — the catalog of what this upstream can move |
| `also_tagged` for tags sharing a commit | `changes_contract` on a release |
| `observed_at`, `observation_method` | `contract_review: done` |
| `upstream_latest_*` | `observation_gap`, `tier`, `tier_reason`, dispositions a human owns |

The detector **never** invents `changes_contract`. A newly appended release is
`contract_review: pending`, which means *nobody has said*, not *nothing moved* —
0.4.45 was a patch bump and it changed what a Cypher query answers, so reading risk off
a version number is the guess-instead-of-check this plane exists to stop.

## The scenario is a fixture, not the live register

The detector's scenario tests used to run against `registry/vendor-freshness.yaml`. So
when VFP-0001 closed and both consumers moved to 0.4.45, eight tests went red — not
because anything regressed but because the estate got **fixed**. A suite that goes red
on remediation teaches people to edit tests during a re-vendor, which is the worst
moment for that habit. The five-release gap is now frozen in
`fixtures/vendor-freshness/scenario-engine-behind.yaml`; the live register is still
exercised for what is properly about it (internal consistency, rewrite fidelity, append
idempotency, chain reaching its head).

---

# Increment 3 — the sovereign path (W12.3)

See `docs/governance/vendor-freshness-sovereign-path.md`. In short: the OCI publish
path is **REAL** (exercised end to end against zot v2.1.2 — push, pull by digest,
byte-identical round trip, 404 on an unknown digest, idempotent re-push, with a
pure-curl reimplementation producing the identical manifest digest), and publishing to
`registry.socioprophet.ai` is **SPEC ONLY** because it needs the `ci` credential and
this work adds no secrets. The gitea webhook contract and the consumer-side digest
consumption are specified and explicitly undecided, and said so.
