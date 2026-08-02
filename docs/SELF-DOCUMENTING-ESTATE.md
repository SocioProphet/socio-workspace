# The Self-Documenting Estate

Status: increment-1 (mechanism + drift canary). Owner: `SocioProphet/sociosphere`.

## Thesis

**The code is the source of truth. Documentation is derived from the code, not
authored beside it.** Hand-written repo docs rot the moment the code moves; a
map that is *computed* from the code cannot silently diverge from it. SocioSphere
is the composition hub: it enumerates the estate, pulls the code-derived catalog,
composes a per-repo documentation view into the Boundary Atlas, and holds a
fail-closed canary that goes RED the instant the composed docs stop matching the
code they claim to describe.

## The mechanism

```text
enumerate  ->  extract  ->  compose  ->  canary  ->  serve-over-MCP
(gh api)      (catalog     (sociosphere  (fail-      (catalog
              extractors)  Atlas)        closed)     MCP server)
```

| Stage | Where | Artifact |
| --- | --- | --- |
| **enumerate** | `tools/enumerate_estate.py` (SocioSphere) | `registry/estate-roster.json`, `registry/estate-roster.coverage.json` |
| **extract** | `prophet-core-catalog/extractors/*` (the catalog) | `catalog-index/*`, `datasets/estate-graph/*.ttl` |
| **compose** | `tools/compose_self_documentation.py` (SocioSphere) | `artifacts/self-documentation/*` |
| **canary** | `tools/verify_self_documentation.py` (SocioSphere CI) | RED/GREEN build verdict |
| **serve** | `prophet-core-catalog/tools/catalog_mcp_server.py` | house-protocol query surface |

The first four stages are wired into this repo. The extract stage lives in
[`SocioProphet/prophet-core-catalog`](https://github.com/SocioProphet/prophet-core-catalog),
whose extractors read the code of each repo and emit the code-derived assets
(schemas, services, ADRs, agents, models, policies, regex, vocabularies) plus a
KKO-grounded estate graph. SocioSphere **consumes** that catalog; it never
hand-maintains the per-repo facts. Dependency direction is respected: the estate
controller references the catalog as a source; the catalog does not depend on
SocioSphere.

## 1. Enumerate — the cross-org roster

`tools/enumerate_estate.py` lists every repo across the three estate orgs via
`gh api` and annotates each with any role / jurisdiction inferable from committed
governance surfaces (the Boundary Atlas, the workspace manifest, and — when a
catalog checkout is supplied — the catalog `sources/`). It writes the
authoritative `registry/estate-roster.json` and a reconciliation report,
`registry/estate-roster.coverage.json`.

Current cross-org picture (`registry/estate-roster.coverage.json`):

| Surface | Count |
| --- | --- |
| Repos across 3 orgs (SocioProphet 1479, SociOS-Linux 708, SourceOS-Linux 24) | **2211** |
| In the Boundary Atlas | 19 |
| In the workspace manifest | 53 |
| In the catalog `sources/` (harvested) | 147 |
| Code-derived assets present (`cataloged_with_assets`) | 147 |

**Coverage gaps found (these are data, not surprises):**

- **1968** live repos are not yet harvested by the code-catalog — the long tail
  that follow-on extractor runs will pull in.
- **45** repos named in `manifest/workspace.toml` do not resolve to a live repo
  in the three enumerated orgs (renamed, planned, sub-component, or other org).
- **9** catalog `sources/` entries do not resolve to a live repo by name
  (naming-normalization gaps, e.g. `agent_descriptors`).
- **0** Boundary-Atlas repos are missing from the estate, and **0** Atlas repos
  lack code-derived catalog coverage — so every Atlas jurisdiction claim is
  currently backed by real code.

Enumeration needs the network and a `gh` token, so it is a **periodic job, not
part of the canary**. The roster it produces is committed and cross-checked by
the canary (tooth E).

## 2. Compose — code into the Boundary Atlas

`tools/compose_self_documentation.py` joins the SocioSphere Boundary Atlas
(`catalog/boundaries.yaml`) to the code-derived catalog. For every Atlas repo the
catalog actually covers (currently **19/19**), it emits under
`artifacts/self-documentation/`:

- `repos/<repo>.json` — a per-repo record whose every field is derived: the
  boundary class / jurisdiction / maturity from the Atlas, the provenance
  (owner, status, license, source id) from the estate-graph, and the code assets
  (`asset_count`, `by_kind`, `datasets`, `sample_assets`, `glossary_terms`) from
  the catalog index.
- `cross-repo-links.json` — a repo→repo reference graph derived from the
  catalog's blast-radius / lineage edges (the self-documenting estate view).
- `index.json` — the composed manifest (scope + per-repo summary).
- `catalog-pin.json` — the catalog commit the view was composed from, plus a
  sha256 of every consumed input (catalog index files, the estate-graph TTLs, and
  `catalog/boundaries.yaml`). This is what binds the composed docs to an exact
  code state.

The Atlas records the linkage under `atlas.code_derived_documentation` in
`catalog/boundaries.yaml`: Atlas entries are backed by the composed view rather
than being hand-maintained. Composition is fully deterministic (sorted keys,
sorted lists, capped samples, no timestamps), so a fresh regenerate is
byte-identical to the committed view — which is exactly what the canary checks.

## 3. Canary — the control that makes drift impossible to hide

`tools/verify_self_documentation.py` is **fail-closed**. A control that cannot
fail is suspect; this one has five independent teeth, each an audited way to go
RED:

| Tooth | Fails when |
| --- | --- |
| **A · MISSING** | a fresh regenerate produces a code-derived doc that the committed view lacks (a covered repo left undocumented). |
| **B · UNBACKED** | a committed per-repo doc is not backed by real catalog assets (an Atlas claim with no code behind it). |
| **C · STALE/DRIFT** | the committed view is not byte-identical to a fresh regenerate from the pinned catalog (docs drifted from code). |
| **D · PIN** | the catalog is absent, or its consumed inputs no longer hash to `catalog-pin.json` (docs describe a catalog that no longer exists as pinned). |
| **E · ROSTER** | a composed repo is not present in the committed cross-org roster (roster and self-doc disagree). |

The canary regenerates the whole view into a temp dir and byte-compares, so any
divergence between the committed docs and the code — a hand-edit, a catalog
change not re-composed, an Atlas edit not re-composed, a deleted record — turns
CI red. It is wired into `.github/workflows/self-documenting-estate.yml`, which
checks out `prophet-core-catalog` at the **pinned** commit and runs the canary.

### Teeth proof (make it red, then green)

```
$ make self-doc-verify
OK self-documentation: 19 atlas repos code-derived and byte-identical to a fresh
regenerate from catalog@3d724f2e198d; all catalog-backed; all in roster.

# hand-edit a composed record (tooth C)
SELF-DOC DRIFT FAIL: committed self-documentation DRIFTED from the code/catalog
(not byte-identical to fresh regenerate): ['repos/agentplane.json']. Recompose.

# remove a covered repo's doc (tooth A)
SELF-DOC DRIFT FAIL: committed view is MISSING code-derived docs a fresh
regenerate produces: ['repos/hellgraph.json']

# catalog input moved (tooth D)
SELF-DOC DRIFT FAIL: pinned input 'index' hash mismatch: docs were derived from a
different catalog/atlas state.

# recompose and it is green again
$ make self-doc-compose && make self-doc-verify
OK self-documentation: 19 atlas repos code-derived ...
```

## Running locally

```bash
# a prophet-core-catalog checkout is the code-derived input
CATALOG=../prophet-core-catalog

make estate-enumerate  CATALOG=$CATALOG   # refresh roster (needs gh token + network)
make self-doc-compose  CATALOG=$CATALOG   # regenerate the composed view
make self-doc-verify   CATALOG=$CATALOG   # fail-closed drift canary
```

## Dogfooding the catalog

This mechanism dogfoods `prophet-core-catalog`: SocioSphere consumes the same
code-derived assets the catalog publishes for query
(`tools/catalog_query.py`, `tools/catalog_mcp_server.py`) and the same
`verify_percolation.py` effect-canary discipline. The catalog proves its READ
half percolates; this repo proves the COMPOSE half stays honest. The composed
per-repo records and cross-repo link view are themselves answerable over the
catalog MCP surface, closing the enumerate → extract → compose → canary →
serve loop.

## Increment-1 scope and follow-ons

Increment-1 makes the mechanism work end-to-end for the **19** Boundary-Atlas
repos and gives the canary real teeth. Deliberate follow-ons:

- extend the catalog `sources/` + extractors to close the **1968**-repo long tail
  and lift more repos into composition;
- reconcile the **45** manifest-only and **9** source-only naming gaps;
- promote composed records into per-repo native `BOUNDARY.md` generation;
- schedule the enumerate stage so the roster refreshes automatically.

## References

- Boundary Atlas: [`docs/boundary-atlas-v0.1.md`](boundary-atlas-v0.1.md),
  `catalog/boundaries.yaml`
- Topology / dependency direction: [`docs/TOPOLOGY.md`](TOPOLOGY.md)
- Code-derived catalog: `SocioProphet/prophet-core-catalog`
  (`catalog-index/`, `datasets/estate-graph/`, `tools/catalog_mcp_server.py`)
- Roster: `registry/estate-roster.json`, `registry/estate-roster.coverage.json`
- Tools: `tools/enumerate_estate.py`, `tools/compose_self_documentation.py`,
  `tools/verify_self_documentation.py`
- CI: `.github/workflows/self-documenting-estate.yml`
