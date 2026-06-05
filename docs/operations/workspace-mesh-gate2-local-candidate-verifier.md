# Workspace Mesh Gate 2 Local Candidate Verifier

Mesh state: `prepared-but-not-deployed`
Gate 2 state: `planning_only`

## Purpose

The local candidate verifier checks an existing local candidate mapping file without recreating it.

The verifier is read-only and does not print candidate values.

## Local file checked

```text
.workspace-mesh/gate2-candidate-mapping.local.json
```

## Command

```bash
make -f workspace-mesh-gate2-candidate.mk workspace-mesh-gate2-local-candidate-verify
```

## Expected placeholder-copy output

```text
PASS: Workspace mesh Gate 2 local candidate mapping verifies clean
local_file=.workspace-mesh/gate2-candidate-mapping.local.json
mode=placeholder_copy
fields=4
placeholder_values=4
local_candidate_values=0
source_evidence_records=0
git_ignored=true
dry_run_required=true
candidate_values_printed=false
```

## Boundary

This verifier does not substitute identifiers, print local candidate values, run Workspace automation, or advance the mesh beyond planning.
