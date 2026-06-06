# GitHub connector capability matrix

Status: governance inventory. This document records observed connector capabilities and gaps for GitHub/GitOps work. It does not authorize repository mutation, issue closure, PR merge, branch deletion, production execution, or credential expansion.

Purpose: prevent assumptions about the GitHub connector surface. Every GitOps lane should distinguish what the connector can prove, what it can mutate, what it normalizes away, and where fallback or controller support is required.

## Capability posture

| Domain | Observed capability | Observed limitation | Impedance symbols | Controller requirement |
|---|---|---|---|---|
| Repository metadata | Can fetch repository metadata, default branch, permissions, merge settings. | Does not by itself prove branch protection rules, required status contexts, or workflow health. | `nu_n`, `C_m` | `StateHydrator`, `BranchProtectionResolver` |
| File read | Can fetch UTF-8 files by path/ref and line range. | Fetch result is normalized and not a complete raw GitHub contents payload. | `nu_n`, `R_0` | `RawEvidenceStore` |
| File create/update | Can create and update UTF-8 text files through contents API. | Direct file write can target `main`; branch creation is not exposed in the discovered file surface, and create/update returns only commit SHA. | `sigma_p`, `epsilon_r`, `A_i` | `BranchManager`, `MutationReceiptVerifier` |
| PR creation | Connector has a PR creation action in the broader PR surface. | Branch creation and multi-file atomic commit support are not guaranteed in the discovered surface for a given turn. | `rho_r`, `C_m` | `AtomicChangeSetBuilder` |
| PR fetch | Can fetch PR metadata, diffs, patches, changed filenames, comments, reviews, and review threads through separate surfaces. | PR state is spread across multiple calls; normalized PR info may not be enough for merge authority. | `nu_n`, `Pi_s` | `PRStateMachine` |
| Merge | Can merge a PR and optionally pass expected head SHA in the PR surface. | Merge may be blocked by branch protection, stale checks, safety layer, or unavailable auto-merge. | `H_star`, `beta_p`, `sigma_p` | `MergePreflight` |
| Auto-merge | Auto-merge action exists in PR surface. | Repo settings may disable auto-merge; `SocioProphet/sociosphere` reported `allow_auto_merge: false`. | `G_not_B`, `C_m` | `MergeStrategyResolver` |
| Workflow runs by commit | Can call `fetch_commit_workflow_runs`. | Action description says it filters to pull-request-triggered runs and returns first page only; push-trigger verification can return `workflow_runs: []` without proving absence. | `pi_1`, `nu_n`, `epsilon_r` | `CheckResolver`, `WorkflowRunPaginator` |
| Workflow jobs | Can fetch jobs for a workflow run and job steps/logs when run/job IDs are known. | Does not solve discovery of the correct run when run listing is incomplete. | `pi_1`, `C_m` | `WorkflowRunDiscovery` |
| Artifacts | Can fetch workflow artifacts by run ID or download artifact by ID. | Requires run/artifact IDs; first-page-only behavior may hide artifacts. | `pi_1`, `R_0` | `ArtifactResolver` |
| Search | Can search installed repositories and repository files. | Search may return no results for known concepts or may depend on indexing availability. | `SEARCH_INDEX_GAP`, `N_not_E` | `SearchFallbackRouter` |
| Branch protection | No complete branch-protection resolver was observed in the discovered surface during this tranche. | Cannot prove required contexts directly from observed tools alone. | `beta_p`, `G_not_B` | `BranchProtectionResolver` |
| Raw payload preservation | Some connector responses include normalized results and metadata. | Full raw GitHub REST/GraphQL payloads are not always exposed or retained. | `R_0`, `nu_n` | `RawEvidenceStore` |
| Pagination | Some actions explicitly return first page only. | First-page results create false completeness unless pagination is surfaced. | `pi_1` | `Paginator` |
| Mutation receipts | File writes return commit SHA, and fetch-file can verify blob presence afterward. | Mutations still require independent post-action reads; returned commit SHA alone is not enough for semantic success. | `E_plus`, `epsilon_r` | `MutationReceiptVerifier` |

## Operating rule

Before using a connector capability, classify it as one of:

- `proves`: enough to establish the claimed fact;
- `suggests`: useful signal but incomplete;
- `mutates`: changes durable state and therefore requires receipt;
- `partial`: known wrapper limitation or first-page/normalized output;
- `unsafe-alone`: must be paired with another read, check, or human/controller review.

## Current high-risk gaps

1. Complete branch-protection and required-check-context discovery.
2. Complete workflow-run listing by workflow, branch, event type, commit SHA, and pagination cursor.
3. Branch creation as a governed prelude to file writes.
4. Multi-file atomic change sets with PR creation.
5. Raw response capture and hashable evidence store.
6. Explicit idempotence classification for retries.
7. Post-mutation receipt policy encoded as a reusable tool/controller layer.

## Minimum preflight for merge authority

A future GitHub Controller must not treat a PR as merge-authorized until it can prove:

1. current PR head SHA;
2. current base SHA;
3. branch protection rule for target branch;
4. required check contexts;
5. check conclusions attached to current head SHA;
6. mergeability state after refresh;
7. draft/ready status;
8. stale/superseded topology status;
9. expected-head merge guard availability;
10. post-merge receipt path.

## Relationship to impedance ledger

When a connector capability is missing, partial, normalized, paginated, or misleading, record an event in `registry/github-tool-impedance-ledger.yaml` using symbols from `docs/governance/github-tool-impedance-dictionary.md`.
