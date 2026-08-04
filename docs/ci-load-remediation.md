# CI load remediation — stop every PR from flooding the runners

## The problem (measured by `tools/ci_load_audit.py`)

- **54 workflows fire on every `pull_request`**, spawning **~60 jobs per PR**.
- A 2-file Python change runs geospatial-standards, lattice spines, edge-host-lifecycle,
  osm-attribution, ui-check — none of which it touches.
- The `validate` check name is produced by **9 different workflows**.
- Result: the self-hosted runner pool is saturated, jobs sit queued at 0 s, and merges stall —
  the "boring reliability" gap. The runners aren't broken; the fan-out is self-inflicted.

## The key fact that makes this safe

Branch protection requires **exactly one** check: **`gate / check`**. Every other workflow is
**advisory** — it consumes runners but does not gate merges. Therefore:

> **Path-filtering an advisory workflow can never block a merge.** The dangerous case — a *required*
> check that gets filtered out and leaves the PR "expected/pending" forever — applies only to
> `gate / check`, which we leave always-on.

So the fix is safe by construction.

## The fix

1. **Add a `paths:` filter to each advisory domain workflow** so it only runs when its domain
   changes. Suggested starting filters (review each against the workflow's actual inputs):

   | workflow | `paths:` (only run when these change) |
   |---|---|
   | `ui-check.yml` | `client-vue/**`, `ui/**`, `**/*.vue`, `**/*.ts` |
   | `vendor-freshness*.yml` | `registry/vendor-freshness.yaml` |
   | `osm-attribution.yml` | `**/*osm*`, `**/*geo*` |
   | `lattice-*-spine.yml` | `registry/lattice-**`, `lattice/**` |
   | `edge-host-lifecycle.yml` | `edge/**`, `infra/**` |
   | `service-register.yml` | `registry/service*` |
   | `resource-intake-adoption.yml` | `registry/resource*` |
   | `*standards*.yml` | `registry/**standards**`, `spec/**` |

2. **De-duplicate the 9× `validate`** — consolidate the identical `validate` job into one workflow
   (or one reusable workflow called with a matrix) instead of nine copies.

3. **Keep `gate / check` always-on** (it is the only gate). If it is slow, make *it* fast; never
   path-filter it.

## Expected result

A typical Python-only PR drops from **~60 jobs to ~10** (`gate / check` + python + the handful of
generic validators), clearing the runner backlog that is currently stalling every merge.

## Why this is a plan, not an auto-edit

CI gates are control-of-controls — a bad path filter that silently skips a check you *thought* was
running is a "lying green." So this repo change ships the **audit tool + this plan** for a human to
apply the workflow edits under review (`.github/workflows/**` changes are human-merge by policy).
Run `python3 tools/ci_load_audit.py` any time to re-measure and re-prioritise.
