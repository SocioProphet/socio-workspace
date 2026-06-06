# GitHub tool impedance dictionary

Status: governance dictionary. This document is descriptive and diagnostic. It does not authorize repository mutation, branch deletion, issue closure, PR merge, production execution, or connector credential expansion.

Purpose: name the recurring GitHub, connector, CI, branch-protection, and assistant-operation impedance patterns observed during SocioProphet GitOps work. The goal is to convert repeated friction into durable semantics, evidence capture, and controller requirements.

## Core thesis

GitOps work happens inside a nonzero impedance field. A normal-looking operation such as fetch PR, inspect checks, create file, update file, open PR, mark ready, enable auto-merge, or merge can fail or mislead for multiple independent reasons:

- GitHub state is asynchronous and multi-surface;
- connector wrappers often expose normalized or partial state;
- branch protection is not equivalent to green CI;
- workflow visibility may be filtered, paginated, delayed, or SHA-detached;
- assistant memory is not durable repository state;
- retries can duplicate or corrupt intent unless idempotence is known.

This dictionary treats every such impedance event as telemetry.

## Absolute rules

```text
No GitHub action is valid from conversation memory alone.
No normalized connector response is sufficient evidence by itself.
No green CI result is sufficient merge authority by itself.
No mutation is complete without a receipt.
No repeated workaround remains informal.
```

## Symbol dictionary

| Symbol | Name | Definition | Typical symptom | Required response |
|---|---|---|---|---|
| `Gamma_i` | GitOps impedance field | The standing friction between intended repository operation and observed GitHub/tool behavior. | A simple PR or merge lane repeatedly requires retries, reinspection, or fallback. | Treat each friction point as ledgered telemetry. |
| `tau_s` | Stale-state lag | Delay between assumed state and state enforced by GitHub, CI, branch protection, or the connector. | PR appears green/open/mergeable, but later read contradicts that. | Rehydrate durable state before writes. |
| `chi_m` | Check-context mismatch | Required protected-branch context does not match the apparently successful workflow/check. | CI green, but branch protection still reports an expected or missing check. | Resolve required context names against the current head SHA. |
| `rho_r` | Replay requirement | Existing PR/branch topology is no longer canonical and must be replayed onto current base. | Branch is many commits behind or replacement PR becomes canonical. | Create/rebase/replay from current `main`; avoid patching rotten topology. |
| `nu_n` | Normalization loss | Connector returns simplified snapshots that omit decisive raw GitHub fields. | Tool says mergeable or returns status summary without enough raw evidence. | Preserve raw responses or fetch deeper surfaces. |
| `pi_1` | First-page truncation | Tool returns only a first page or filtered subset, creating false completeness. | `workflow_runs: []` or missing historical PR/file data that later exists elsewhere. | Paginate or mark observation as incomplete. |
| `sigma_p` | Safety-layer preemption | Connector/platform blocks a mutation before GitHub natively accepts or rejects it. | Merge/update/create call fails without a GitHub-side decision. | Record as connector/platform impedance, not GitHub-native failure. |
| `alpha_m` | Async mergeability | GitHub mergeability/check status is computed asynchronously and may be pending/stale. | Mergeability changes after later inspection. | Delay, refresh, or require expected-head preflight. |
| `beta_p` | Branch-protection race | GitHub branch protection has not accepted the current SHA/check state even though workflows appear successful. | Required status remains expected or absent. | Inspect protected-branch contexts and current head SHA. |
| `delta_r` | Durable-state rehydration | Mandatory reload of repo, branch, PR, issue, manifest, lock, workflow, and check state before mutation. | Work resumes after a long chat or another agent changed `main`. | Execute the resume checklist before writing. |
| `epsilon_r` | Evidence receipt | Durable proof of what ran or changed, where, on what SHA, and with what result. | Summary exists but no SHA/run/check/link verifies it. | Capture commit SHA, PR URL, run ID, check status, and raw payload where possible. |
| `kappa_r` | Connector-retry loop | Repeated failed tool assumptions followed by narrower calls, replacement PRs, comments, or fallback. | Fetch/create/update/merge fails, then similar attempt fails again differently. | Stop blind retries; classify idempotence and partial-success risk. |
| `omega_p` | Probe PR | Temporary PR or marker created only to force observable CI/workflow behavior. | PR has no implementation content and exists to observe a check. | Mark probe-only, capture result, close without merge unless explicitly authorized. |
| `lambda_v` | Validator promotion | Conversion of governance prose into executable schemas, validators, workflows, manifests, or receipts. | Repeated manual review becomes a validation script. | Promote repeated checks into CI or offline validators. |
| `mu_h` | Human-memory hazard | Conversation memory or assistant summary is treated as repository truth. | Agent continues from stale memory and misses merged PRs or changed files. | Re-read durable state from repository and GitHub. |
| `T_i` | Impedance telemetry | Every failure, retry, stale read, blocked mutation, or mismatch is data. | Friction is dismissed as one-off. | Enter it in the impedance ledger. |
| `R_0` | Raw-response preservation | Raw connector/GitHub responses are preserved before interpretation. | Normalized summary hides decisive data. | Store raw payload, timestamp, and hash when available. |
| `Pi_s` | PR state machine | Operational PR state is richer than open/closed/merged. | PR is open but stale, draft, superseded, probe-only, or green-but-blocked. | Classify state explicitly. |
| `Delta_n` | Native GitHub delta | Failure attributable mainly to GitHub semantics. | Async mergeability, branch-protection context propagation, stale checks. | Handle with GitHub-aware preflight and receipts. |
| `Delta_c` | Connector delta | Failure attributable mainly to wrapper, schema, pagination, safety layer, or normalized surface. | Missing field, partial list, blocked mutation, lossy result. | Capture connector capability gap. |
| `Delta_a` | Assistant/operator delta | Failure attributable mainly to wrong assumption, wrong tool call, incomplete preflight, or premature confidence. | Operation attempted before durable-state rehydration. | Record assistant-induced impedance and fix procedure. |
| `E_plus` | Post-action receipt | Independent read after every mutation. | Merge/update claimed but not verified. | Re-fetch PR/file/branch/check state after mutation. |
| `G_not_B` | Green is not branch-protected pass | Workflow success is not sufficient evidence that protected branch requirements are satisfied. | Check is green but merge still blocked. | Compare workflow/check success against required contexts on current SHA. |
| `H_star` | Canonical head check | Verify head SHA, base SHA, branch protection, and check contexts before merge. | Merge attempted on stale or wrong SHA. | Use expected-head merge where available. |
| `I_r` | Idempotent retry discipline | Retry safety must be classified before repeating a mutation. | Repeated create/update/merge calls create duplicates or ambiguous state. | Determine whether the operation is safe, unsafe, or requires receipt lookup. |
| `S_d` | Staleness decay | Branches, PRs, and plans rot as `main` advances. | Branch is tens or hundreds of commits behind. | Rebase/replay/close as superseded. |
| `N_not_E` | Narrative is not evidence | A summary, chat note, or assistant assertion is not proof. | A good explanation lacks SHA, URL, run ID, or artifact. | Attach receipts and raw evidence. |
| `C_m` | Connector capability matrix | Explicit map of what the connector can prove, mutate, paginate, and preserve. | Tool expected to support branch protection or full workflow listing but cannot. | Maintain capability inventory. |
| `A_i` | Assistant-induced impedance | Tool friction caused or amplified by assistant/operator behavior. | Wrong call shape, stale trust, insufficient preflight. | Treat as first-class quality defect. |
| `W_to_K` | Workaround-to-controller law | Repeated workaround becomes a controller requirement. | Same manual fallback appears in multiple PR lanes. | Promote to GitHub Controller feature. |

## Failure class dictionary

| Class | Meaning | Counted as impedance? |
|---|---|---|
| `CONNECTOR_SCHEMA` | Tool call schema or parameter shape does not fit the intended operation. | Yes |
| `CONNECTOR_SAFETY_LAYER` | Connector/platform blocks mutation before GitHub makes a native decision. | Yes |
| `CONNECTOR_PARTIAL_SURFACE` | Connector lacks required fields, raw payloads, pagination, or branch-protection surface. | Yes |
| `GITHUB_ASYNC_STATE` | GitHub mergeability/check/status state is delayed or recomputed. | Yes |
| `BRANCH_PROTECTION` | Protected branch requirements block mutation despite apparent readiness. | Yes |
| `STATUS_CONTEXT_MISMATCH` | Required check context differs from visible successful workflow/check. | Yes |
| `CI_ENVIRONMENT_DRIFT` | CI checkout/environment differs from local/assumed environment. | Yes, if it causes GitOps friction; also may be a repo defect. |
| `STALE_BRANCH` | Branch/PR base has drifted from current canonical base. | Yes |
| `DRAFT_READY_TRANSITION` | Draft/ready state blocks or mutates expected PR flow. | Yes |
| `AUTO_MERGE_UNAVAILABLE` | Auto-merge disabled or not exposed for the lane. | Yes |
| `PERMISSION_BOUNDARY` | Token lacks required permission. | Track separately; not connector flakiness. |
| `RATE_LIMIT` | Tool/API/model rate or retry limit blocks action. | Yes |
| `SEARCH_INDEX_GAP` | Search/indexing fails to surface known repo state. | Yes |
| `PAYLOAD_SIZE_OR_SHAPE` | Content/body/file payload fails due to size, shape, or wrapper constraint. | Yes |
| `ASSISTANT_MISUSE` | Operator/assistant used wrong tool, stale memory, or incomplete preflight. | Yes, but blame separately. |
| `REAL_REPO_DEFECT` | Tests fail because code/config is actually wrong. | Track; not connector defect. |

## PR operational states

A PR may be:

- `unknown`: not yet fetched from durable state;
- `draft`: not review-ready;
- `ready`: open and reviewable;
- `green`: at least one visible check passed;
- `green_but_unprotected`: visible checks passed but protected requirements not proven;
- `blocked_expected_context`: branch protection expects a missing/stale context;
- `mergeability_pending`: GitHub has not finalized mergeability;
- `stale`: base branch moved enough to require rebase/replay;
- `superseded`: another PR/branch is canonical;
- `probe_only`: exists only to force observable CI;
- `canonical`: current intended landing path;
- `merged`: merged and receipt verified;
- `closed_unmerged`: closed without merge;
- `abandoned`: no longer relevant and not safe to mutate blindly.

## Missed-opportunity doctrine

Repeated GitHub/tool impedance should not be handled as isolated annoyance. Each recurrence should be converted into one of:

1. a ledger entry;
2. a dictionary symbol;
3. a validator;
4. a runbook rule;
5. a controller requirement;
6. a post-action receipt requirement;
7. a capability-matrix update.

## GitHub Controller requirements

A future GitHub Controller should include:

| Module | Purpose |
|---|---|
| `StateHydrator` | Rehydrate repo, branch, PR, issue, check, workflow, protection, and lock state. |
| `RawEvidenceStore` | Store raw connector/GitHub responses with timestamps and hashes. |
| `PRStateMachine` | Classify PR state beyond open/closed/merged. |
| `CheckResolver` | Resolve workflow runs, checks, statuses, required contexts, and SHA attachment. |
| `MergePreflight` | Verify head/base SHA, mergeability, branch protection, and expected checks before mutation. |
| `MutationReceiptVerifier` | Confirm that update/merge/close/delete actually occurred. |
| `RetryController` | Prevent blind retry loops; classify idempotence and partial-success risk. |
| `StalenessDetector` | Detect branches behind/ahead, superseded PRs, duplicate branches, and noncanonical topology. |
| `ProbeManager` | Create and clean probe PRs intentionally when observability must be forced. |
| `FailureLedger` | Record every impedance event as structured telemetry. |
| `CapabilityMatrix` | Record what each connector/tool can prove, mutate, paginate, preserve, and verify. |

## Minimum operating protocol

Before a GitHub mutation:

1. rehydrate durable repository state;
2. fetch current PR/branch/file state;
3. verify head SHA and base SHA;
4. inspect checks and required contexts where available;
5. classify PR state;
6. classify mutation idempotence;
7. execute the smallest valid mutation;
8. fetch an independent post-action receipt;
9. record impedance if anything diverged from expectation.

## Non-goals

This dictionary does not claim that all impedance is connector fault. It explicitly separates native GitHub behavior, connector wrapper behavior, assistant/operator error, permission boundaries, and real repository defects.
