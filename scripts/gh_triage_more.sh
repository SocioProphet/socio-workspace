#!/usr/bin/env bash
set -euo pipefail
repo="${1:-SocioProphet/socioprophet}"

(gh label create "type:bug" --description "Bug" -R "$repo" 2>/dev/null || true)
(gh label create "status:stale" --description "Needs refresh" -R "$repo" 2>/dev/null || true)

# 153: docs baseline
gh issue edit 153 -R "$repo"   --add-label "area:docs,type:feature,priority:p1,status:needs-spec"   --body $'Docs scaffold for workspace controller + component task contract.

AC:
- Workspace docs live in the workspace controller repo.
- Component Task Contract v0.1 documented with examples.'

# 152: CI/CD pipeline epic
gh issue edit 152 -R "$repo"   --add-label "area:infra,type:epic,priority:p0,status:needs-spec,concept:dx"   --body $'Define CI that runs: lock-verify + fetch + per-component build/test.

AC:
- Lock drift check (fail on mismatch).
- Runner smoke test in CI.
- Matrix to run build/test for selected components.'

# 67: route auth regression/bug
gh issue edit 67 -R "$repo"   --add-label "area:web,type:bug,priority:p1,status:needs-spec"   --body $'Protected route definitions conflict with public routes.

AC:
- Clear rule for route auth gating (public/private).
- Tests covering route resolution + redirects.'
