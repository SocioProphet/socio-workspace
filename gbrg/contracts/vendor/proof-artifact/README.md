# Vendored: canonical ProofArtifact schema v1

`proof-artifact.schema.v1.json` is a **verbatim, sovereign-vendored copy** of the
estate-canonical ProofArtifact schema. Authoritative home:

- repo: `SocioProphet/socioprophet-standards-storage`
- path: `schemas/proof-artifact/proof-artifact.schema.v1.json`
- `$id`: `https://schemas.socioprophet.ai/proof-artifact/v1.json`

The GBRG contracts `blast-radius-proof-artifact.schema.json` and
`containment-proof-artifact.schema.json` bind to it via `allOf` and `$ref` its
`epistemicLevel` enum instead of copy-pasting it (standards-storage#97, R2).
Vendored (not CDN-fetched) so the `$ref` resolves offline.

Do NOT edit locally. Update upstream in standards-storage and re-vendor the exact bytes.
