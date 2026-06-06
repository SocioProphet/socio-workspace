# GitHub Controller architecture

Status: architecture note. This document defines requirements for a governed GitHub Controller that reduces connector, GitHub, CI, branch-protection, and assistant-operation impedance. It does not authorize repository mutation, issue closure, PR merge, branch deletion, production execution, or credential expansion.

## Problem

Direct agent use of generic GitHub connector calls repeatedly encounters an impedance field:

- repository state is distributed across files, branches, PRs, issues, checks, workflows, and branch-protection rules;
- GitHub mergeability and check state are asynchronous;
- connector responses may be normalized, partial, first-page-only, or mutation-focused;
- assistant memory can drift from durable state;
- retries are unsafe without idempotence classification and receipts.

The Controller exists to make GitOps state explicit, typed, inspectable, and receipt-backed.

## Design principles

1. Memory is not state.
2. Normalized connector output is not raw evidence.
3. Green CI is not branch-protection proof.
4. Every mutation requires preflight and receipt.
5. Every repeated workaround becomes a controller feature.
6. Retry without idempotence classification is a defect.
7. Probe PRs must be intentional, labeled, and cleaned up.
8. All limitations discovered during operation become ledger entries.

## Core modules

| Module | Responsibility | Inputs | Outputs |
|---|---|---|---|
| `StateHydrator` | Load durable repo, branch, PR, issue, manifest, workflow, and check state before action. | repo, branch, PR/issue refs | typed state bundle |
| `RawEvidenceStore` | Preserve raw connector/GitHub responses with timestamps and hashes. | tool responses, REST/GraphQL payloads | evidence records |
| `CapabilityMatrix` | Track what a connector can prove, mutate, paginate, and preserve. | discovered tool surface, observed failures | capability declarations |
| `PRStateMachine` | Classify PRs beyond open/closed/merged. | PR metadata, checks, reviews, branch relation | operational PR state |
| `BranchProtectionResolver` | Resolve protected branch rules and required check contexts. | repo, branch | required-context set |
| `CheckResolver` | Resolve workflow runs, jobs, statuses, checks, and SHA attachment. | commit SHA, workflow name, branch, event type | check authority report |
| `WorkflowRunPaginator` | Avoid first-page blindness when listing workflow runs/jobs/artifacts. | list endpoints and cursors | complete or bounded listings |
| `StalenessDetector` | Identify branches behind/ahead, superseded PRs, rotten topology, duplicate paths. | branch refs, PR refs, base refs | staleness classification |
| `MergePreflight` | Decide whether a merge attempt is authorized. | PR state, check authority, protection, head/base SHA | merge permit/deny with reasons |
| `MutationPlanner` | Select smallest safe mutation and classify idempotence. | intended operation, state bundle | mutation plan |
| `MutationReceiptVerifier` | Re-read durable state after mutation and verify semantic success. | mutation result, expected postcondition | receipt or failure event |
| `RetryController` | Prevent blind retry loops and classify partial-success risk. | failed mutation/read, receipt state | retry/abort/fallback decision |
| `ProbeManager` | Create, label, observe, and close probe PRs when observability must be forced. | diagnostic intent | probe lifecycle record |
| `FailureLedger` | Append impedance events to the durable ledger. | failure observation, evidence | ledger record |

## Typed state bundle

A hydrated state bundle should include:

```text
repo:
  full_name
  default_branch
  permissions
  merge_settings
  branch_protection_summary
branch:
  name
  sha
  relation_to_default
pull_request:
  number
  state
  draft
  head_ref
  base_ref
  head_sha
  base_sha
  mergeability
  operational_state
checks:
  workflow_runs
  check_runs
  statuses
  required_contexts
  missing_contexts
  stale_contexts
issues:
  linked_issues
  latest_comments
files:
  touched_paths
  existing_path_shas
receipts:
  prior_mutation_receipts
```

## Merge authority rule

A merge is not authorized unless all are true:

1. PR is canonical, not draft, not superseded, not probe-only.
2. Current head SHA and base SHA are known.
3. Branch-protection requirements are known or the absence of protection is verified.
4. Required checks are identified.
5. Required checks are attached to the current head SHA.
6. Checks are successful, skipped by policy, or explicitly waived with evidence.
7. Mergeability has been refreshed after checks completed.
8. Expected-head merge can be used or an equivalent guard exists.
9. Post-merge receipt path is known.
10. No active governance issue marks the lane held.

## Direct-to-main exception rule

Direct-to-main writes are exceptions. If unavoidable, the Controller must require:

1. low-risk classification;
2. no production execution;
3. no destructive mutation;
4. explicit rationale;
5. immediate post-write fetch receipt;
6. ledger entry if branch-first policy was bypassed.

## Probe PR lifecycle

A probe PR must include:

- `probe_only` state;
- explicit non-goal: not implementation content;
- expected workflow/check being observed;
- commit SHA and run ID receipt;
- close-without-merge policy unless explicitly promoted;
- ledger event if created because normal observability was insufficient.

## Failure ledger integration

The Controller should write ledger records for:

- connector partial surface;
- branch-protection ambiguity;
- check-context mismatch;
- workflow-run pagination or filtering gap;
- stale branch replay;
- safety-layer preemption;
- assistant/operator misuse;
- direct-to-main exception;
- unsafe retry blocked;
- probe PR created.

## MVP implementation path

1. Implement read-only `StateHydrator` over current connector calls.
2. Implement `PRStateMachine` classifications without mutation.
3. Implement `CheckResolver` with explicit incomplete/partial states.
4. Implement `MutationReceiptVerifier` for file writes and PR mutations.
5. Implement `FailureLedger` append mode.
6. Add controller CLI dry-run mode.
7. Add branch-first change-set creation only after read-only state is trustworthy.

## Non-goals

This architecture does not require bypassing GitHub protections, expanding credentials, or granting autonomous production authority. It narrows authority by making state, evidence, and mutation receipts explicit.
