# Vendor freshness — the sovereign path (W12.3)

**Status: partly REAL, partly SPEC. The split is stated per component below, and
nothing here claims to work that was not run.**

## The problem this closes

`apps/hellgraph-service/package.json` says:

```json
"@socioprophet/hellgraph": "file:vendor/socioprophet-hellgraph-0.4.40.tgz"
```

A **filename** is the pin. That has three consequences, all of which have already
cost something:

1. **A bump is a rename in N places.** `package.json`, `package-lock.json` (twice),
   the guard's `MIN_ENGINE`, plus the same set again in `apps/lifecycle-warden`. Miss
   one and the repo is internally inconsistent in a way nothing detects.
2. **A filename asserts nothing about the bytes.** `socioprophet-hellgraph-0.4.45.tgz`
   is a claim, not evidence. The W12.2 executor has to unpack the tarball and assert a
   marker *inside* `ts/dist/index.js` precisely because the name proves nothing.
3. **There is no publish step at all.** hellgraph has no workflow that runs `npm pack`
   — `docker-publish.yml` builds a container on tag push, and that is the only
   tag-triggered job in the repo. The tarball that reaches production is made **by
   hand, on a laptop**, and committed as a binary blob. That is the sovereign supply
   chain today.

A digest pin fixes all three: `registry.socioprophet.ai/socioprophet/hellgraph@sha256:…`
is the bytes, cannot be wrong, and moving it is a one-line change.

## What is REAL

### The OCI publish path — `tools/publish_vendor_artifact_oci.py`

Stdlib-only client for the OCI Distribution API. No oras, skopeo, crane, or docker: a
sovereign path that needs four vendor CLIs installed is not sovereign.

**Exercised against zot v2.1.2** (`distSpecVersion 1.1.0`) running in a local
container, publishing the actual `socioprophet-hellgraph-0.4.40.tgz` (275,186 bytes):

| Step | Observed |
|---|---|
| `GET /v2/` | 200 |
| `POST /v2/<repo>/blobs/uploads/` | 202 + relative `Location` |
| `PUT <location>?digest=sha256:…` (layer, config) | 201 + `Docker-Content-Digest` |
| `PUT /v2/<repo>/manifests/<tag>` | 201, server digest **==** locally recomputed digest |
| `GET /v2/<repo>/manifests/sha256:<d>` | 200, bytes byte-identical to what was PUT |
| `GET /v2/<repo>/blobs/sha256:<d>` | 200, 275,186 bytes byte-identical to the source tarball |
| `GET manifests/<never-pushed digest>` | 404 `MANIFEST_UNKNOWN` |
| same bytes pushed under a second tag | 201, **identical** manifest digest |

A pure-`curl` reimplementation produced the identical manifest digest — a check on the
canonical encoding, not merely on the Python.

`artifactType`, `subject`, and the referrers API all work on this version, so a
signature or an attestation can be attached to the artifact later without changing
its digest.

### The quirk that shapes the whole design

**Overwriting a tag ORPHANS the manifest digest that tag previously held.** Isolated
A/B, one variable:

- manifest held only by tag `0.4.40`; push different content to `0.4.40` →
  `GET manifests/<old-digest>` returns **404**. The pin is dead.
- with a **second tag** still referencing it → **200**, bytes identical.
- pushing by digest *after* tagging does **not** protect it — still 404.

The manifest blob is still readable through the blobs endpoint, so this is
index-level dereferencing rather than immediate deletion. zot reported
`GC:true, GCDelay 1h`; that hour was not waited out, so no claim is made about
eventual deletion.

**Mitigation, proven:** every publish also writes an immutable alias tag
`sha256-<hex>` (71 chars, inside the 128-char OCI tag limit). Without it the digest
404s; with it the digest resolves and the bytes are identical. Any promise of digest
pinning on zot must do this or an equivalent.

Other rejections worth knowing before writing a publisher:

| Case | Result |
|---|---|
| manifest with no `config` field | 400 `MANIFEST_INVALID` — `config` is mandatory even for artifacts |
| empty config descriptor referenced without uploading the 2-byte `{}` blob | 400 `MANIFEST_INVALID` |
| legacy `application/vnd.oci.artifact.manifest.v1+json` | 415 — use image manifest + `artifactType` |
| manifest `PUT` with wrong or missing `Content-Type` | 415 |
| `subject` pointing at a manifest that does not exist | **201** — zot does not validate it; dangling referrers are possible |
| `DELETE manifests/<tag>` | 202. The registry is **not** append-only by default |

### The production registry, as far as it was verified

`https://registry.socioprophet.ai/v2/` answers:

```
HTTP/2 401
www-authenticate: Basic realm="zot-sovereign"
```

That is the correct OCI auth challenge, from a live Google-fronted endpoint with a
valid certificate. **That is the only thing about production verified here.** Nothing
was pushed to it.

## What is SPEC ONLY

Everything below is designed and written down. None of it has been run.

### 1. Publishing to production zot

**Unvalidated because it needs the `ci` htpasswd credential**, and this work adds no
new secrets. The credential already exists as `ZOT_CI_USERNAME` / `ZOT_CI_PASSWORD`
repository secrets in `prophet-platform` for the image pipeline, so the runner
workflow reads those rather than minting anything.

Two traps are already recorded against this registry and both apply to a first
artifact push. They are stated here so the first attempt does not rediscover them:

- **htpasswd is authn; `accessControl` is authz, and they are separate.** A user can
  authenticate (`GET /v2/` → 200) and still get **403** on push. The 401/403
  distinction is the tell. The user must also appear in
  `infra/k8s/zot/base/configmap.yaml` under
  `accessControl.repositories["**"].policies[].users`, because `defaultPolicy: []`
  grants nothing. **`GET /v2/` is a useless test for push rights** — it only needs
  authn. Test an actual blob write.
- **zot reads `config.json` at startup and does not hot-reload.** After ArgoCD syncs
  the configmap the running process keeps its old in-memory policy and still 403s.
  `kubectl rollout restart deploy/zot` is required after any config change.

### 2. The gitea tag-push webhook contract

The sovereign SCM is gitea; the sovereign registry is zot. The path that removes
GitHub from the middle is: **tag push in gitea → webhook → sovereign runner → build,
pack, publish to zot → notify the register.**

Webhook, configured on the upstream repo in gitea (`Settings → Webhooks → Gitea`),
event **Create** filtered to tag refs:

```json
{
  "secret": "<HMAC shared secret, gitea-side>",
  "ref": "refs/tags/v0.4.46",
  "ref_type": "tag",
  "sha": "dbe854faf5b8f53a484fd164ba6f84328b5dd24b",
  "repository": { "full_name": "SocioProphet/hellgraph",
                  "clone_url": "https://git.socioprophet.ai/SocioProphet/hellgraph.git" }
}
```

Receiver requirements, none of them optional:

- **Verify `X-Gitea-Signature`** (HMAC-SHA256 of the raw body with the shared secret)
  before parsing. An unauthenticated build trigger that publishes to the registry
  every consumer pins from is a supply-chain hole, not a convenience.
- **Ignore any version in the payload.** The version is whatever
  `package.json` says at that commit. A payload-supplied version is attacker-supplied.
- **Reject a tag that already has a published artifact** unless the digest matches
  byte for byte. Republishing a tag is how a pin silently changes meaning.
- **Reject a tag whose peeled commit already carries another semver tag.** This is not
  hypothetical: hellgraph's `v0.4.42` points at the `v0.4.41` commit, whose
  `package.json` says `0.4.41`. Anyone pinning `v0.4.42` gets `0.4.41` bytes. The
  detector now catches this after the fact (`tag_aliases`); the publisher should
  refuse it at the source.

### 3. The sovereign runner workflow

`.github/workflows/vendor-artifact-publish.yml` — written, **not run**, because it
publishes to production zot. It is written for the GitHub-hosted runner because that
is the pipeline that exists today; the gitea-Actions equivalent is the same steps with
a different `runs-on`.

Its steps are deliberately the same discipline the W12.2 executor performs, for the
same reasons: `npm run build` explicitly before `npm pack`, assert the version marker
INSIDE the packed `ts/dist/index.js` read with node, then publish.

**The tension, named rather than hidden:** this pushes to the sovereign registry FROM
GitHub Actions — the platform being left — so the zot push credential lives in GitHub
secrets. That is an acceptable interim because it is the only pipeline that exists,
and the end state is gitea Actions so the sovereign registry's supply chain does not
depend on GitHub.

### 4. The consumer side of a digest pin

**Not designed to completion, and this is the honest gap.** npm has no
`oci://…@sha256:…` specifier. Consuming a digest-pinned OCI artifact from
`package.json` needs one of:

- a **prefetch step** that resolves the digest, downloads the layer, verifies the
  sha256, writes it to `vendor/`, and leaves `file:` in place — the pin becomes a
  digest recorded in the register while `package.json` keeps a stable filename. This
  is the smallest change and the only one that does not touch npm semantics;
- a **local registry shim** translating an npm scope to OCI pulls; or
- `npm pack` output published to a **private npm registry** instead of an OCI one —
  which gitea can host, and which sidesteps the impedance mismatch entirely.

The third is probably right and is deliberately not decided here. Until it is, the
digest is recorded in `registry/vendor-freshness.yaml` as `vendored_digest` and
enforced by the fail-closed gate against the bytes on disk — which is a real digest
pin, just enforced by the register rather than by the package manager.

## Sequencing

1. **Now, no infrastructure:** the register records `vendored_digest`, and W12.5's
   fail-closed gate verifies it against the bytes in the consumer repo on every CI
   run. This is live.
2. **Next, needs the zot `ci` credential and an `accessControl` entry:** publish the
   artifact on release, and record `oci_digest` alongside `vendored_digest`. Two
   independent digests over the same bytes, which must agree.
3. **Then, needs gitea:** move the trigger from a GitHub tag push to the gitea
   webhook above, and the runner off GitHub Actions.
4. **Last, needs a decision:** how consumers reference the artifact. Until then
   `file:` stays and the register carries the pin.
