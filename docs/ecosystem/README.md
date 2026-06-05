# SocioProphet Ecosystem — Repository Intelligence Index

This directory contains structured per-repository analysis for every core repo in the
SocioProphet organization. The goal is to give AI tools, engineers, and governance systems
a single, current, machine-readable source of truth for reasoning about the ecosystem.

Each file follows the same five-section schema so that automated tooling can parse it
consistently.

## Document schema (per repo file)

1. **Repository Purpose & Identity** — what it does, core responsibilities, dependents, dependencies
2. **Controlled Vocabulary & Ontology** — key terms, domain language, semantic bindings
3. **Topic Modeling** — top topics extracted from code + documentation
4. **Dependency Graph** — direct dependencies and dependent systems
5. **Change Impact Rules** — downstream impact, DevOps actions, and governance gates triggered by changes

## Repository index

| File | GitHub repo | Role |
|---|---|---|
| [sociosphere.md](sociosphere.md) | [SocioProphet/sociosphere](https://github.com/SocioProphet/sociosphere) | Workspace controller / governance graph authority |
| [socioprophet.md](socioprophet.md) | [SocioProphet/socioprophet](https://github.com/SocioProphet/socioprophet) | Main collaborative platform / institutional action surface |
| [hellgraph.md](hellgraph.md) | [SocioProphet/hellgraph](https://github.com/SocioProphet/hellgraph) | Graph reasoning / semantic governance query substrate |
| [prophet-platform.md](prophet-platform.md) | [SocioProphet/prophet-platform](https://github.com/SocioProphet/prophet-platform) | Core contracts / platform infra |
| [socioprophet-standards-storage.md](socioprophet-standards-storage.md) | [SocioProphet/socioprophet-standards-storage](https://github.com/SocioProphet/socioprophet-standards-storage) | Standards authority (storage) |
| [socioprophet-standards-knowledge.md](socioprophet-standards-knowledge.md) | [SocioProphet/socioprophet-standards-knowledge](https://github.com/SocioProphet/socioprophet-standards-knowledge) | Knowledge context standards |
| [tritrpc.md](tritrpc.md) | [SocioProphet/TriTRPC](https://github.com/SocioProphet/TriTRPC) | RPC protocol |
| [agentplane.md](agentplane.md) | [SocioProphet/agentplane](https://github.com/SocioProphet/agentplane) | Execution control plane |
| [new-hope.md](new-hope.md) | [SocioProphet/new-hope](https://github.com/SocioProphet/new-hope) | Semantic runtime |

## Ecosystem dependency summary

```
sociosphere  (workspace controller / governance graph authority)
  ├─ pins ──────────────────────────────► TriTRPC  (third_party)
  ├─ manages components ────────────────► socioprophet-web, prophet_cli, hdt_app, …
  ├─ indexes topology ──────────────────► repo ownership, authority boundaries, evidence sources
  ├─ queries via ───────────────────────► hellgraph
  └─ generates bundles ────────────────► agentplane

socioprophet  (collaborative platform / institutional action surface)
  ├─ contains AgentOS (tool registry, interfaces, policy)
  ├─ records InstitutionalAction objects
  ├─ queries governance context via ────► hellgraph
  ├─ contains agentplane sub-directory
  └─ deploys via ──────────────────────► prophet-platform

hellgraph  (graph reasoning / semantic governance query substrate)
  ├─ persists/query graph state from ───► sociosphere, ontogenesis, agentplane, prophet-platform
  ├─ supports release queries for ──────► prophet-platform
  ├─ supports action queries for ───────► socioprophet
  └─ links receipts/replay from ────────► agentplane

prophet-platform  (infra hub)
  ├─ wire format ──────────────────────► TriTRPC  (rpc/, TRITRPC_SPEC.md)
  ├─ follows standards ────────────────► socioprophet-standards-storage
  └─ deploys ──────────────────────────► socioprophet-web, API, gateway

socioprophet-standards-storage  (standards authority)
  ├─ mandates ─────────────────────────► TriTRPC  (standard 030)
  └─ is upstream to ───────────────────► socioprophet-standards-knowledge

socioprophet-standards-knowledge  (knowledge context)
  ├─ inherits invariants from ─────────► socioprophet-standards-storage
  └─ binds to ─────────────────────────► TriTRPC  (standards 030, 032)

TriTRPC  (RPC protocol — most cross-cutting)
  ├─ consumed by ──────────────────────► prophet-platform
  ├─ consumed by ──────────────────────► socioprophet-standards-storage
  ├─ consumed by ──────────────────────► socioprophet-standards-knowledge
  ├─ consumed by ──────────────────────► new-hope
  ├─ pinned by ────────────────────────► sociosphere (third_party/)
  └─ transport for ────────────────────► agentplane

agentplane  (execution control plane)
  ├─ consumes bundles from ────────────► sociosphere
  ├─ uses transport ───────────────────► TriTRPC
  └─ emits receipts/replay refs ───────► hellgraph

new-hope  (semantic runtime)
  ├─ canonical wire format ────────────► TriTRPC  (Carrier → TritRPC envelope)
  └─ aligns object model with ─────────► socioprophet-standards-knowledge
```

## Cross-cutting architectural themes

1. **TriTRPC as universal transport** — 6 of 8 repos explicitly reference TriTRPC as normative
   or operational. Fixture changes in TriTRPC propagate to all consumers simultaneously.
2. **Determinism as a design principle** — sociosphere (lock files), agentplane (replay
   artifacts), TriTRPC (canonical encoding), HellGraph (append-only valuations/checkpoints),
   and new-hope (Receptor determinism classes) all share this philosophy.
3. **Standards hierarchy** — `standards-storage` ← `standards-knowledge` ← platform
   implementations. Changes must flow downward through this hierarchy.
4. **Evidence-forward execution** — sociosphere → agentplane → RunArtifact → ReplayArtifact
   forms an end-to-end audit chain.
5. **Graph-backed governance** — SocioProphet institutional actions, Sociosphere topology,
   AgentPlane receipts, Ontogenesis vocabulary, and Prophet Platform release gates must be
   queryable through HellGraph-backed governance state.
6. **Nix for reproducibility** — agentplane and socioprophet both use Nix flakes. Environment
   changes must be validated via Nix build before any execution claims are trustworthy.

## Maintenance

Update the corresponding `.md` file whenever:
- A repo's purpose or core responsibilities change
- A new cross-repo dependency is added or removed
- A standards document is promoted or deprecated
- A new first-class object/term is introduced in any repo's vocabulary
