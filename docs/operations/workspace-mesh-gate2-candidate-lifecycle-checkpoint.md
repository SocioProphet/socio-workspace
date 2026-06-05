# Workspace Mesh Gate 2 Candidate Lifecycle Checkpoint

Mesh state: `prepared-but-not-deployed`
Gate 2 state: `planning_only`

## Purpose

This checkpoint runs the template validator, verifies the existing local candidate mapping file, and prints a compact lifecycle summary without printing candidate values.

## Command

```bash
cd ~/dev/sociosphere
git pull --ff-only
make -f workspace-mesh-gate2-candidate.mk workspace-mesh-gate2-candidate-lifecycle-checkpoint
```

## Expected current output

```text
PASS: Workspace mesh Gate 2 candidate mapping template is placeholder-only
PASS: Workspace mesh Gate 2 local candidate mapping verifies clean
Workspace Mesh Gate 2 Candidate Lifecycle Checkpoint
====================================================
mesh_state=prepared-but-not-deployed
gate_2=planning_only
local_candidate_file=.workspace-mesh/gate2-candidate-mapping.local.json
mode=placeholder_copy
fields=4
placeholder_values=4
local_candidate_values=0
source_evidence_records=0
git_ignored=true
candidate_values_printed=false
live_execution=false
next_allowed_action=local_candidate_review_only
```

## Boundary

The checkpoint does not substitute identifiers, print candidate values, run Workspace automation, or advance the mesh beyond Gate 2 planning.
