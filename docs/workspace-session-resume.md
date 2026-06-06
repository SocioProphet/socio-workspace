# Workspace session resume checklist

Status: operational runbook. This document does not change workspace inventory, pins, refs, resolved-lock generation, or disposition state.

Purpose: define the minimum durable-state review required before continuing Sociosphere workspace inventory, resolved-lock, disposition, or control-plane work in any agent or coding environment.

This checklist is grounded in the principle that conversation context is ephemeral. Durable project state lives in repository files, reports, manifests, validation scripts, workflows, issues, PRs, and commits.

## When to use this checklist

Use this checklist whenever:

- restarting a long-running ChatGPT, Claude Code, Cursor, Copilot, or other coding-agent session;
- switching machines or coding environments;
- resuming work after summarization or context compaction;
- continuing work after another agent or human advanced `main`;
- preparing to mutate `manifest/workspace.toml`, lock files, disposition metadata, or resolved-lock artifacts;
- reviewing #439, #451, #452, #453, or successor reconciliation work.

## Absolute rule

Do not rely on conversation memory as the source of truth.

Before making changes, load the durable state from the repository and current GitHub issue/PR state.

## Mandatory restart sequence

### 1. Confirm repository and branch state

Run or inspect the equivalent of:

```bash
git status --short
git branch --show-current
git log --oneline -8
```

Required checks:

- working tree is clean before starting a new change;
- current branch is intentional;
- recent commits are understood;
- no accidental direct-to-main edit is underway;
- if `main` moved since the last session, branch from latest `main` before changing files.

### 2. Read canonical declared workspace state

Read:

- `manifest/workspace.toml`
- `manifest/workspace.lock.json`

Purpose:

- identify declared repo membership;
- identify declared refs and pins;
- identify roles, local paths, trust zones, and required capabilities;
- avoid editing generated or observed state when the canonical declared state is the real target.

### 3. Read observed and resolved workspace state

Read, when present:

- `manifest/workspace.resolved.lock.json`
- `reports/workspace-resolved-lock-coverage.baseline.json`
- `reports/workspace-resolved-lock-missing-classification.baseline.json`
- `reports/workspace-resolved-lock-high-risk-live-outcomes.json`
- `reports/workspace-resolved-lock-standard-main-live-outcomes.batch-*.json`

Purpose:

- distinguish declared state from observed live resolution;
- avoid claiming full-estate materialization from a partial artifact;
- preserve the boundary between offline declared lock and live resolved lock.

### 4. Read disposition and governance state

Read:

- `manifest/workspace.dispositions.json`
- `reports/workspace-disposition-summary.baseline.json`
- `reports/workspace-manifest-cleanup.readiness-v0.md`
- `reports/workspace-manifest-cleanup.readiness-v0.json`
- `reports/workspace-control-plane-context-integration.md`

Purpose:

- identify entries that are pinned, held, stale candidates, planned stubs, candidate successors, ref anomalies, or canonical-retain candidates;
- avoid deleting, renaming, or repinning entries whose disposition is not settled;
- use disposition metadata as the active attention/hold registry for workspace inventory.

### 5. Run or inspect validators and reporters

Relevant tools:

```bash
python3 tools/validate_workspace_dispositions.py
python3 tools/report_workspace_disposition_summary.py
python3 tools/report_workspace_resolved_lock_coverage.py
```

Before modifying these tools or their inputs, confirm what each one does:

- `validate_workspace_dispositions.py` validates disposition metadata offline.
- `report_workspace_disposition_summary.py` summarizes disposition metadata offline.
- `report_workspace_resolved_lock_coverage.py` compares declared lock and resolved lock coverage offline.

None of these should mutate `manifest/workspace.toml`.

### 6. Inspect active governance issues

Inspect current state of:

- #439 — full-estate workspace resolved lock umbrella
- #451 — pins, aliases, and stale refs
- #452 — connector and service manifest entries
- #453 — documentation and support manifest entries

Minimum checks:

- issue state: open or closed;
- latest comments;
- linked PRs;
- final disposition status if closed;
- whether the next intended change belongs to that issue.

### 7. Inspect recent and open PRs

Inspect recent merged PRs and open PRs touching:

- `manifest/`
- `reports/`
- `tools/report_workspace_*`
- `tools/validate_workspace_*`
- `.github/workflows/workspace-*`
- `docs/workspace-*`

Required checks:

- determine whether another agent already created or merged the intended artifact;
- do not recreate an existing report or workflow under a colliding path;
- do not overwrite concurrent work;
- if a path exists, update it intentionally with the file SHA rather than calling create-file blindly.

### 8. Classify the intended change before writing

Every change must be one of these types:

| Type | Examples | Requires extra review? |
|---|---|---|
| Reporting-only | add/update summary report, readiness report, integration note | Low |
| Validator-only | add/update offline validator | Medium |
| Workflow-only | add/update non-mutating CI workflow | Medium |
| Disposition metadata | add/update `manifest/workspace.dispositions.json` | Medium |
| Manifest membership | remove/add/rename repo entries | High |
| Pin/ref movement | change `rev` or `ref` | High |
| Resolved-lock regeneration | update `manifest/workspace.resolved.lock.json` | Medium/high |
| Live network materialization | run `--live --write` or equivalent | High |

If the change is manifest membership, pin/ref movement, resolved-lock regeneration, or live network materialization, do not proceed without explicit issue linkage and evidence.

### 9. Maintain hard boundaries

Unless the active task explicitly authorizes them, do not:

- delete manifest entries;
- rename manifest entries;
- move pins;
- rewrite refs;
- regenerate `manifest/workspace.resolved.lock.json`;
- claim full-estate completion;
- collapse unresolved entries into generic failure buckets;
- treat candidate successors as confirmed replacements.

### 10. Use branch-first GitOps

For normal work:

1. branch from latest `main`;
2. create or update the artifact;
3. open a PR with explicit scope and non-goals;
4. inspect changed files;
5. inspect status/checks where available;
6. merge only when file boundary and risk boundary are correct.

Direct-to-main writes are reserved for already-approved low-risk administrative corrections and should be avoided by default.

## Current durable state model

The workspace inventory lane currently uses five state layers:

| Layer | Artifact examples | Meaning |
|---|---|---|
| Declared state | `manifest/workspace.toml`, `manifest/workspace.lock.json` | Canonical repo inventory and declared refs |
| Observed state | `manifest/workspace.resolved.lock.json`, live outcome reports | What resolved or failed during lookup |
| Coverage state | coverage and missing-classification reports | How complete the resolved artifact is |
| Disposition state | `manifest/workspace.dispositions.json` | Why unresolved or risky entries are held |
| Summary/control state | baseline summaries, readiness reports, integration notes | How humans and agents should proceed |

Do not confuse these layers.

## Current high-risk entries

As of the baseline disposition summary, special handling applies to:

### Pin drift review required

- `tritfabric`
- `tritrpc`

Default action: preserve pins.

### Ref reconciliation required

- `knowledge-graph`

Default action: verify branch/ref before changing manifest.

### Alias or stale pending confirmation

- `hdt_app`

Candidate canonical successor: `human_digital_twin`.

Default action: hold for confirmation.

### Retain candidate canonical

- `human_digital_twin`

Default action: retain.

### Candidate successor pending confirmation

- `data-pipeline`

Candidate adjacent repositories:

- `datakit`
- `argo-dataflow`

Default action: hold for confirmation.

## Current lower-risk cleanup lane

Documentation/support entries likely belong to the first manifest cleanup investigation after reporting and schema work:

- `socioprophet_integration`
- `runbooks`
- `onboarding-docs`
- `architecture-docs`
- `api-specs`

Required before cleanup:

- inbound-reference scan;
- canonical documentation target confirmation;
- explicit PR rationale per entry;
- regenerated coverage after any approved manifest mutation.

## Connector/service lane caution

Connector and service entries may be planned surfaces rather than stale mistakes:

- `connector-github`
- `connector-gitlab`
- `connector-jira`
- `connector-kafka`
- `connector-slack`
- `configs`
- `dev_api`
- `asr-service`
- `embeddings-service`
- `event-bus`
- `data-pipeline`

Before cleanup, classify each as one of:

- active repo;
- renamed repo;
- merged into another repo;
- planned repo;
- private repo;
- stale manifest entry;
- archival entry.

## Restart output requirement

At the start of every resumed work session, produce a short but complete readout with:

- current branch and latest main SHA;
- current task objective;
- relevant issues and PRs;
- files expected to change;
- files that must not change;
- validation to run or inspect;
- merge/defer decision boundary.

## Minimal good readout template

```text
Objective: <one sentence>
Current base: <branch/SHA>
Relevant issues: #439, #451, #452, #453, etc.
Expected files changed: <paths>
Forbidden files changed: <paths or classes>
Validation: <commands/checks>
Risk: low/medium/high
Decision boundary: merge if <conditions>; defer if <conditions>
```

## Stop conditions

Stop and ask for review if:

- a change would delete or rename manifest entries;
- a change would move `rev` or `ref` values;
- a live resolver output conflicts with a pin;
- an unresolved repo has a plausible but unconfirmed successor;
- another branch or PR already touched the intended artifact;
- the working branch includes accidental unrelated files;
- the summary/reporting layer no longer matches the manifest or disposition state.

## Next recommended work after this checklist

1. Add a formal JSON schema for `manifest/workspace.dispositions.json`.
2. Add a disposition-to-attention mapping report.
3. Add inbound-reference scanning for #453 documentation/support cleanup.
4. Add connector rail metadata design for #452.
5. Add pin/ref review templates for #451.
6. Only then begin controlled manifest cleanup PRs.
