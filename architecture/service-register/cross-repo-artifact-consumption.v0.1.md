# Cross-Repo Artifact Consumption Contract v0.1

Status: draft enforcement contract for service-register inputs.

This contract defines how SocioSphere consumes machine-readable artifacts whose canonical authority lives in another repository.

## Scope

Initial artifact family:

- Source repository: `SocioProphet/workspace-inventory`
- Source artifact: `exports/canonical-repo-estate.v1.0.csv`
- Source manifest: `exports/canonical-repo-estate.v1.0.json`
- Consumer repository: `SocioProphet/sociosphere`
- Local mirror: `architecture/service-register/canonical-repo-estate.v1.0.csv`

## Authority rule

The source repository remains authoritative for repository-estate membership.

SocioSphere may keep a local mirror for deterministic service-register validation, but the mirror must declare the upstream artifact it mirrors and the pinned artifact identity it expects.

## Pinning rule

A consumed artifact must be pinned by content identity before it is treated as enforceable input.

The first pinning mechanism is Git blob SHA because it can be recomputed locally without network access:

```text
blob <byte_length>\0<file_bytes>
```

The expected Git blob SHA for the current canonical repo-estate mirror is:

```text
10c47ac5411b82ac5bf2b15f2e4360f57e34e148
```

Future versions may add SHA-256, signed release attestations, or GitHub Actions artifact attestations. Those should be additive, not replacements for deterministic local verification.

## Local validation rule

SocioSphere CI must validate:

1. The binding manifest names the upstream repository.
2. The binding manifest names the upstream artifact path.
3. The binding manifest names the upstream manifest path.
4. The binding manifest names the upstream validation tool and workflow.
5. The local mirror exists.
6. The local mirror has the expected schema and row count.
7. The local mirror recomputes to the pinned Git blob SHA.

## Network rule

Default service-register CI must not fetch mutable upstream URLs.

Networked comparison is allowed only in a separate sync/update job that writes an explicit mirror update commit or pull request. Local validation must remain deterministic and runnable offline.

## Failure policy

Hard failure:

- Missing local mirror.
- Row-count mismatch.
- Column mismatch.
- Blob SHA mismatch.
- Binding metadata mismatch.

Warning or future gate:

- Upstream repository unreachable.
- Upstream workflow status unavailable.
- Upstream artifact has changed but no mirror update PR exists yet.

## Promotion path

1. Enforce local mirror identity using Git blob SHA.
2. Add a generated sync report comparing upstream source to local mirror.
3. Add a bot-created mirror update PR path.
4. Promote upstream drift without mirror update to a hard gate only after the sync path is reliable.
