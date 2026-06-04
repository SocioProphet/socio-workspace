# Workspace control plane context integration

Source branch: `workspace-disposition-summary-baseline-v0`

Related PR: #460

Related umbrella issue: #439

Related disposition issues: #451, #452, #453

Status: integration note only. This file does not change `manifest/workspace.toml`, does not move pins, does not rename repositories, and does not regenerate the resolved lock.

## Purpose

This note integrates two upstream design inputs into the current Sociosphere workspace inventory and disposition lane:

1. `context-management-patterns.md`
2. `workspace_control_plane_formalized_update_and_inventory.md`

The purpose is to keep the current GitOps work aligned with the broader Workspace Control Plane / Prophet Workspace thesis rather than treating the workspace lock and disposition work as isolated repository hygiene.

## Control-plane interpretation

The Workspace Control Plane document establishes that canonical state should live in a user-owned, local-first control plane, while vendor assistants and clouds are replaceable interfaces. It also frames each chat/session as an append-only event log, episodic memory object, microbatch of assets and claims, governed provenance bundle, and replay unit.

For the current Sociosphere work, that means the workspace manifest, lock, resolved lock, coverage reports, disposition metadata, and disposition summaries should be treated as control-plane artifacts rather than ad hoc CI files.

Current mapping:

| Workspace-control-plane invariant | Current Sociosphere artifact | Current maturity |
|---|---|---|
| Canonical local-first state | `manifest/workspace.toml`, `manifest/workspace.lock.json` | Present |
| Resolved replayable state | `manifest/workspace.resolved.lock.json` | Partial, WCF acceptance slice only |
| Durable event/provenance bundle | `reports/workspace-resolved-lock-*.json`, `reports/workspace-manifest-reconciliation.*` | Present as reports, not yet event-sourced |
| Attention/hold state | `manifest/workspace.dispositions.json` | Present |
| Capability / trust boundary | trust profile refs and disposition guardrails | Partial |
| Mirror/live/action rail separation | documented as required architecture | Not yet encoded as repo metadata |
| Pattern registry | readiness / disposition / batch reports | Initial, not yet formal pattern schema |

## Context-management interpretation

The Context Management Patterns document establishes that critical state must be written to durable artifacts before summarization or session restart. Conversation history is transient; artifacts, Git commits, `.aiwg/` state, and project files are the durable substrate.

For the current Sociosphere work, that means:

- Chat readouts are not sufficient.
- GitHub issue comments are not sufficient.
- The correct durable state is the combination of manifest files, report files, validation scripts, workflows, and PR history.
- Every restart should begin by reading the durable state, not by relying on conversation memory.

Current mapping:

| Context-management principle | Current Sociosphere implementation | Gap |
|---|---|---|
| Persist important decisions before summarizing | reports and manifest metadata committed to Git | Good |
| Conversation context is ephemeral | restart brief now points to files and PRs | Good |
| Cross-platform persistence must be file-backed | reports and manifests are platform-neutral | Good |
| Session resume needs checklist | no Sociosphere-specific resume checklist yet | Gap |
| Multi-directory skill/config discovery | not yet mapped to Sociosphere capability discovery | Gap |

## Impact on the disposition lane

The disposition lane is not just repository cleanup. It is the first concrete instance of a broader control-plane pattern:

1. Detect divergence between declared state and observed state.
2. Record evidence without mutating canonical state.
3. Classify uncertainty into explicit disposition states.
4. Add machine-readable governance metadata.
5. Add summary/reporting views.
6. Only then mutate canonical state through controlled PRs.
7. Regenerate resolved state after canonical state changes.

This is exactly the same lifecycle expected for future roots, claims, assets, capabilities, attention marks, and external side-effect workflows.

## Required integration into future work

### 1. Add a Sociosphere session-resume checklist

The repo should include a durable checklist for resuming this work across ChatGPT, Claude Code, Copilot, Cursor, or any other coding agent. It should mirror the context-management pattern but use Sociosphere-specific artifacts.

Minimum checklist:

- Read `manifest/workspace.toml`.
- Read `manifest/workspace.lock.json`.
- Read `manifest/workspace.resolved.lock.json` if present.
- Read `manifest/workspace.dispositions.json`.
- Run or inspect `tools/validate_workspace_dispositions.py`.
- Run or inspect `tools/report_workspace_disposition_summary.py`.
- Inspect recent PRs and issues #439, #451, #452, #453.
- Check whether current branch is touching manifest membership, pins, refs, or reporting only.

### 2. Promote disposition states into a general control-plane state pattern

The current statuses should become a reusable pattern for other control-plane domains:

- `pending_confirmation`
- `candidate_successor_pending_confirmation`
- `retain_candidate_canonical`
- `pin_drift_review_required`
- `ref_reconciliation_required`
- `stale_or_uncreated_pending_confirmation`
- `planned_or_stale_*_pending_confirmation`

Equivalent state patterns should later apply to roots, mounted accounts, capabilities, topic manifests, claim bundles, workflow runs, and external actions.

### 3. Connect disposition metadata to the attention registry

The Workspace Control Plane design calls for an attention registry with pin, watch, revisit, incubate, hold, and forget states. Current workspace dispositions are effectively attention marks for inventory entries.

Proposed mapping:

| Disposition action | Attention state |
|---|---|
| `preserve_pin` | pin |
| `hold_for_confirmation` | hold |
| `verify_ref_before_manifest_change` | revisit |
| `retain` | watch |
| candidate successor present | incubate |

### 4. Treat resolved-lock regeneration as replay, not a one-off script

The control-plane design treats sessions and workflows as replay units. The resolved-lock generator should eventually emit a durable workflow/event record:

- input manifest ref
- resolver mode
- fixture/live source
- generated artifact hash
- unresolved entry list
- disposition metadata version
- approval or operator identity

### 5. Split connector entries by mirror/live/action rails

The connector/service stubs in #452 should not be classified only as present/missing. The control-plane architecture requires roots and integrations to declare rail behavior:

- mirror rail: local copy/index allowed
- live rail: just-in-time fetch allowed
- action rail: side effects allowed

Future manifest metadata should represent this explicitly.

### 6. Add provenance and claim separation to inventory reports

The current reports mix observations and conclusions. Future reports should separate:

- asset: repository or manifest entry
- observation: lookup returned 404
- claim: repo is stale candidate
- confidence: low/medium/high
- provenance: tool run / report / issue / commit
- validity window: when the claim should be rechecked

## Recommended next PR sequence after #460

1. Add `docs/workspace-session-resume.md` using the Sociosphere-specific checklist.
2. Add a schema file for `manifest/workspace.dispositions.json` so the current validator has a formal contract.
3. Add a disposition-to-attention mapping report.
4. Add inbound-reference scanning for #453 docs/support cleanup.
5. Add connector rail metadata design for #452 before deleting or replacing connector stubs.
6. Add pin/ref review templates for #451.

## Boundary

This integration note does not change the current operational sequence:

1. Merge baseline disposition summary report.
2. Generate a stable dashboard from disposition metadata.
3. Resolve #453 first if we want the lowest-risk manifest cleanup.
4. Resolve #451 only with explicit pin/ref review.
5. Resolve #452 only after planned/stale/private/merged status is confirmed.
6. Regenerate resolved lock and coverage only after manifest cleanup PRs merge.

## Conclusion

The uploaded documents confirm that the workspace inventory work is part of the larger local-first, event-sourced, provenance-governed Workspace Control Plane. The immediate implication is procedural: every important state transition needs to land as a durable artifact before summarization, restart, or manifest mutation.

The current Sociosphere lane now has the right shape: declared state, observed state, disposition state, summary state, and then controlled mutation. The next work should formalize that shape so it becomes reusable across roots, capabilities, assets, claims, workflows, and external actions.
