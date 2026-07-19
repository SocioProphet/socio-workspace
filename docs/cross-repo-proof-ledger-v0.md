# Cross-Repo Proof Ledger v0

## Purpose

This document defines the first cross-repository proof ledger for the SocioProphet / SourceOS estate. Its purpose is to connect already-landed contracts, runtime evidence, workspace registry state, and product proof surfaces into one reviewable chain.

The ledger is not a new feature surface. It is a coordination and evidence spine for proving that the current local-first platform work is coherent across repositories.

## Canonical placement

`SocioProphet/sociosphere` is the canonical home for this ledger because this repository owns the workspace manifest, lock, repo-role metadata, cross-repo governance, topology policy, and validation lanes.

Runtime evidence remains in the implementation repositories that emit it:

- `SocioProphet/prophet-platform` emits FogStack, identity, office, parity, and runtime-readiness records.
- `SocioProphet/agentplane` emits or validates execution, run, replay, evidence, and admission artifacts.
- `SocioProphet/policy-fabric` owns policy decisions and diff-hygiene verdicts.
- `SourceOS-Linux/sourceos-spec` owns SourceOS typed contracts.
- `SociOS-Linux/source-os` owns Linux workstation and office-shell realization.
- `SocioProphet/socioprophet` owns product and public proof-rendering surfaces.

## Ledger chain

```text
SourceOS contract canon
  -> SourceOS local substrate realization
  -> AgentPlane execution and evidence admission
  -> Policy Fabric decision / diff hygiene gate
  -> Prophet Platform parity-readiness evidence
  -> Sociosphere workspace registry and proof ledger
  -> Socioprophet UI proof rendering
```

## Minimum v0 evidence families

### 1. Contract canon

Source repositories:

- `SourceOS-Linux/sourceos-spec`
- `SocioProphet/socioprophet-standards-storage`
- `SocioProphet/socioprophet-standards-knowledge`

Required evidence:

- schema or contract file path
- example or fixture path
- validator or validation command when available
- explicit non-goal statement when the contract is not runtime-ready

### 2. Local substrate realization

Source repository:

- `SociOS-Linux/source-os`

Required evidence:

- workstation profile command
- doctor command
- office-shell command
- smoke/validation path
- known non-production boundaries

### 3. Execution and evidence admission

Source repository:

- `SocioProphet/agentplane`

Required evidence:

- bundle or work-order reference
- run/replay/evidence artifact reference
- policy or semantic-control reference
- validation command
- denial condition for unsafe execution

### 4. Policy gate

Source repository:

- `SocioProphet/policy-fabric`

Required evidence:

- policy decision reference
- diff-hygiene gate report reference
- blocked-path / stale-branch / file-scope checks
- merge-gate decision fields

### 5. Runtime parity and readiness

Source repository:

- `SocioProphet/prophet-platform`

Required evidence:

- parity-readiness command
- readiness record path
- AgentPlane run linkage
- PolicyPlane decision linkage
- live-preflight status
- mutation-safety flags

Canonical current proof command:

```bash
make fogstack-parity-readiness
```

The current parity claim is bounded: local, CI-backed, non-mutating, evidence-based MVP parity. It is not production parity and does not authorize live cluster mutation.

### 6. Workspace proof ledger

Source repository:

- `SocioProphet/sociosphere`

Required evidence:

- workspace manifest / lock reference
- proof-ledger JSON record
- validator result
- drift / stale-ref status
- repo ownership and dependency direction

### 7. Product proof rendering

Source repository:

- `SocioProphet/socioprophet`

Required evidence:

- proof-rendering route or panel
- API/source record consumed
- fallback behavior
- explicit non-production labels where applicable

## v0 acceptance gates

The v0 ledger is acceptable only when all of the following are true:

1. The ledger JSON validates with `tools/validate_cross_repo_proof_ledger_v0.py`.
2. Every listed evidence edge names a source repository and target repository.
3. Every edge has a status from `planned`, `seeded`, `validated`, `consumed`, or `blocked`.
4. No edge claims production readiness.
5. Every live/preflight/runtime edge carries an explicit mutation posture.
6. Every UI proof surface names the underlying platform evidence source.
7. Every deferred gap is represented as a concrete follow-up, not a vague backlog note.

## Explicit non-goals

This ledger does not:

- replace source repository contracts;
- redefine runtime schemas owned by downstream repositories;
- claim production readiness;
- grant live cluster mutation authority;
- replace Policy Fabric, AgentPlane, or Prophet Platform evidence records;
- allow UI surfaces to become canonical evidence authorities.

## Immediate follow-up

1. Wire `tools/validate_cross_repo_proof_ledger_v0.py` into `make validate` after this first tranche is reviewed.
2. Add generated proof-ledger snapshots from `prophet-platform` parity readiness output.
3. Add a Socioprophet proof panel that consumes the parity-readiness record by reference.
4. Extend Sociosphere drift checks so missing or stale evidence refs fail the workspace proof check.
5. Require agentic PR work orders to cite this ledger when touching cross-repo proof surfaces.
