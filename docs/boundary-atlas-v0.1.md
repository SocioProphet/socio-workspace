# SocioProphet Boundary Atlas v0.1

Status: bootstrap draft.  
Owner: `SocioProphet/sociosphere`.  
Standard source: `SocioProphet/prophet-platform-standards` typed boundary standard.

## Purpose

The Boundary Atlas maps repositories to typed jurisdictions, evidence contracts, claim modes, sufficiency labels, trust roots, and permitted boundary crossings.

This turns the typed-boundary doctrine into estate operations:

- repos are jurisdictions;
- APIs, schemas, proof artifacts, model cards, system cards, boot attestations, and agent traces are typed boundary surfaces;
- issues and PRs are proposed transitions;
- CI, checkers, and validators are local proof mechanisms;
- Policy Fabric decides admissibility;
- Sociosphere records coverage, gaps, and transition status.

## Core model

```text
latent state -> typed trace -> semantic/policy lift -> claim -> evidence artifact -> checker verdict -> admissibility gate -> atlas record
```

The atlas does not make a claim true. It records which repo is allowed to make which claim, under which evidence contract, and what downstream consumers may rely on.

## Initial boundary entries

The initial catalog is `catalog/boundaries.yaml`. It covers:

| Repo | Boundary class | Jurisdiction | Maturity |
| --- | --- | --- | --- |
| `SocioProphet/prophet-platform-standards` | standards | Typed-boundary standard, claim modes, sufficiency taxonomy, evidence schemas | L2 |
| `SocioProphet/sociosphere` | estate_registry | Boundary atlas, repo jurisdiction registry, transition reporting | L2 |
| `SocioProphet/prophet-platform` | runtime_verifier | Event-IR, proof artifacts, run bundles, checker contract | L1 |
| `SocioProphet/policy-fabric` | admissibility_policy | Claim-mode promotion and proof-artifact admissibility | L1 |
| `SocioProphet/ontogenesis` | law_compiler | Schema/ontology-to-law compilation | L0 |
| `SocioProphet/model-governance-ledger` | governance_evidence | Documentation evidence packets, sufficiency rubrics, adjudication | L1 |
| `SocioProphet/sherlock-search` | evidentiary_retrieval | Search, source attribution, claim-support traces | L0 |
| `SocioProphet/gaia-world-model` | world_model_trace | World-model traces, provenance, uncertainty evidence | L0 |
| `SocioProphet/agentplane` | agent_runtime | Agent execution boundary, sandboxing, output attestation | L0 |
| `SocioProphet/agent-registry` | agent_identity_capability | Agent identity, capability manifests, revocation | L0 |
| `SourceOS-Linux/sourceos-boot` | boot_trust | BootReleaseSet, TPM/PCR evidence, rollback, host trust | L0 |
| `SourceOS-Linux/sourceos-syncd` | local_state_integrity | Local-first sync, repair, replication, provenance | L0 |

## Claim mode registry

Claim modes are defined in `catalog/claim-modes.yaml`:

1. `formal_construction`
2. `illustrative_schema`
3. `fixture_validated`
4. `experimental_run`
5. `independently_reproduced`
6. `audited_run`

The atlas must not upgrade a claim beyond its evidence mode.

## Evidence contracts

Evidence contracts are defined in `catalog/evidence-contracts.yaml`. Initial contracts:

- `proof_artifact`
- `boundary_record`
- `governance_evidence_packet`
- `boot_trust_evidence`
- `local_state_integrity_evidence`

Each contract declares required fields, trust roots, and downgrade rules.

## Verdict semantics

The atlas records proof/checker verdicts but does not reinterpret them:

- `PROVED`: the claim holds for all traces consistent with the observation window and assumptions.
- `VIOLATION`: a forbidden state or transition has a witness/counterexample.
- `INCONCLUSIVE`: evidence, trust root, precision, or budget is insufficient.

`INCONCLUSIVE` is not failure. It is honest uncertainty and should create a backlog item or investigation path.

## Boundary maturity

- `L0`: repo exists; boundary informal.
- `L1`: human boundary declaration exists or implementation issue open.
- `L2`: machine-readable boundary record exists.
- `L3`: schema validation exists.
- `L4`: claim-mode/evidence gates exist in CI or policy.
- `L5`: Sociosphere ingests boundary metadata automatically.
- `L6`: cross-repo boundary checks run on PRs or release.
- `L7`: release artifacts carry evidence bundles and sufficiency labels.
- `L8`: independent replay or audit exists.

## Current interpretation

The estate has strong conceptual alignment but limited operational enforcement. The current atlas is an explicit bootstrap: it creates a shared map and identifies the first hardening queue.

Priority order:

1. Merge the typed-boundary standard.
2. Add native `BOUNDARY.md` / `.socioprophet/boundary.yaml` to the six canonical repos.
3. Implement schema validation and coverage report generation in Sociosphere.
4. Connect Prophet Platform proof artifacts to Policy Fabric admissibility gates.
5. Promote only fixture-validated evidence after deterministic examples exist.

## Non-goals

The atlas does not:

- implement downstream repo features;
- replace Policy Fabric admissibility decisions;
- certify runtime claims without evidence artifacts;
- treat logs, dashboards, or comments as proof by themselves;
- assert production readiness for repos that lack boundary declarations.
