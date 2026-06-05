# Workspace Mesh Gate 2 Schema Lifecycle Run

Mesh state: `prepared-but-not-deployed`
Gate 2 state: `planning_only`

## Purpose

This note defines the local command for proving that the Gate 2 schema, template, local verifier, and lifecycle checkpoint are aligned.

## Command

```bash
cd ~/dev/sociosphere
git pull --ff-only
make -f workspace-mesh-gate2-candidate.mk workspace-mesh-gate2-candidate-lifecycle-checkpoint
```

## Expected final checkpoint lines

```text
schema_present=true
schema_template_compatible=true
schema_validation=passed_by_lifecycle_target
mode=placeholder_copy
local_candidate_values=0
candidate_values_printed=false
live_execution=false
```

## Boundary

This run does not substitute identifiers, print candidate values, run Workspace automation, or advance the mesh beyond Gate 2 planning.
