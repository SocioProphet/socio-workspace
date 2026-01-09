# sociosphere (v0.1)

Workspace controller repo.

- Manifest: `manifest/workspace.toml`
- Lock: `manifest/workspace.lock.json`
- Runner (Python): `tools/runner/runner.py`
- Protocol + fixtures: `protocol/`

## Scope and backlog

See `docs/SCOPE_PURPOSE_STATUS_BACKLOG.md` for scope, current state, and the rolling backlog.

## Quickstart

```bash
python3 tools/runner/runner.py list
python3 tools/runner/runner.py fetch
python3 tools/runner/runner.py run build --all
python3 tools/runner/runner.py run test --all
```

## Local overrides

Create `manifest/overrides.toml` (gitignored) to point a component to a local path.
