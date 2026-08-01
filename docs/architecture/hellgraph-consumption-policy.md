# HellGraph consumption policy

One canonical HellGraph, consumed the same disciplined way everywhere it's
used in this repo — not many divergent local checkouts that quietly drift
apart. Enforced by `tools/check_hellgraph_pins.py`, which fails the build if
any dependency below violates this.

## Rust (`Cargo.toml`)

The hellgraph crates (`hg_analytics`, `hg_core`, `hg_kernel`, `hg_napi`) MUST
be a git dependency pinned by an immutable commit:

```toml
hg_core = { git = "https://github.com/SocioProphet/hellgraph-rust", rev = "3fa9c21..." }
```

A `path = …` dependency (points at whatever happens to be checked out on one
machine) or a git dependency without `rev` (a branch/tag can move out from
under you) is a violation.

## JavaScript/TypeScript (`package.json`)

A `@socioprophet/hellgraph` dependency MUST be pinned one of two ways:

**Vendored tarball (preferred — this is what prophet-platform's
`hellgraph-service` and `lifecycle-warden` already do):**

```json
"@socioprophet/hellgraph": "file:vendor/socioprophet-hellgraph-0.4.47.tgz"
```

The tarball lives in a `vendor/` directory next to the consuming
`package.json`, built with `npm pack` from a real release commit on
`SocioProphet/hellgraph`'s `main`, and committed into the repo. This is the
same "vendor, don't reference a moving target" discipline as
`feedback_vendor_dont_reference_external_cdn` — the dependency is a byte-exact
artifact sitting in version control, not a path that only resolves on one
developer's disk.

**Pinned git ref (for a git-sourced dependency, not vendored):**

```json
"@socioprophet/hellgraph": "github:SocioProphet/hellgraph#v0.4.47"
```

or pinned to a commit SHA (`#<40-hex>`). A bare `file:` path outside
`vendor/` (drifts with whatever's on that one machine right now), a missing
ref, or a moving branch (`main`/`master`/`HEAD`/`develop`) is a violation
either way.

## Re-vendoring

When a newer HellGraph release needs picking up:

1. Build the tarball from the target commit on `SocioProphet/hellgraph`'s
   `main` (`npm pack --pack-destination …` from a clean checkout — verify
   `git status` is clean and `ts/dist` matches `ts/src` first, so a stale
   build never gets vendored under a fresh version string).
2. Replace the old `.tgz` in `vendor/` with the new one and repoint the
   `package.json` reference to match the new filename exactly.
3. Run `python3 tools/check_hellgraph_pins.py` — it must exit 0.
4. Run the consuming package's own test suite before committing.

prophet-platform's `tools/revendor_engine.py` implements a more elaborate,
receipt-sealed version of this same discipline (marker-proof, atomic
multi-consumer moves, floor-never-lowers) for its own two consumers — worth
consulting as a reference if this repo ever needs the same rigor across
multiple consumers at once, but not required for a single consumer like
`gbrg/reasoning`.
