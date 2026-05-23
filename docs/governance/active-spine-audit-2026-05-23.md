# Active Spine Governance Audit — 2026-05-23

## Purpose

This audit records the current SocioProphet estate-control gap in `SocioProphet/sociosphere` and defines the minimum corrective registration set for the current active spine.

## Corrected active spine

| Layer | Repository | Required status |
| --- | --- | --- |
| Estate controller | `SocioProphet/sociosphere` | Canonical |
| Runtime platform | `SocioProphet/prophet-platform` | Canonical |
| Transport standard | `SocioProphet/TriTRPC` | Canonical |
| Platform standard | `SocioProphet/prophet-platform-standards` | Canonical after runtime gate consumption |
| Storage standard | `SocioProphet/socioprophet-standards-storage` | Canonical for storage namespace |
| Knowledge standard | `SocioProphet/socioprophet-standards-knowledge` | Canonical for knowledge namespace |
| Agent profile standard | `SocioProphet/socioprophet-agent-standards` | Promotion candidate until imported by runtime consumers |
| Workspace product | `SocioProphet/prophet-workspace` | Promotion candidate until deployed over platform with smoke tests |
| Proof graph runtime | `SocioProphet/hellgraph` | Restricted promotion candidate until basis, operator, and query gates mature |
| SourceOS adjacent standard | `SourceOS-Linux/sourceos-spec` | Canonical adjacent SourceOS schema lane |

## Observed gaps

1. `manifest/workspace.toml` did not register the current product, agent-standard, proof-graph, and platform runtime repositories as active-spine entries.
2. `manifest/workspace.lock.json` contains remote-only SourceOS/SociOS entries, but the manifest/lock relationship needs explicit parity enforcement.
3. `registry/canonical-repos.yaml` contains overlapping registry shapes and should be treated as transitional until normalized.
4. `registry/repo-governance-matrix-v0.yaml` is the strongest current governance artifact, but it lacked `SocioProphet/hellgraph`.
5. `catalog/boundaries.yaml` lacked typed boundary entries for several corrected-spine repositories.
6. `governance/CANONICAL_SOURCES.yaml` lacked namespaces for workspace product ownership, agent profile standards, and proof graph runtime ownership.
7. `docs/TOPOLOGY.md` described an early two-repo topology and no longer represented the estate.

## Minimum corrective patch

This branch applies registration and jurisdiction correction only. It intentionally does not normalize `registry/canonical-repos.yaml`; that file needs a separate schema-normalization PR because it mixes legacy and current registry layouts.

## Follow-on enforcement work

After this correction lands, Sociosphere should add validators for manifest/lock parity, canonical-source coverage, boundary coverage, mixed-registry-shape rejection, and topology directionality rules across standards, runtime, product, proof, and archive layers.
