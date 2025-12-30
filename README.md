# socio-workspace (v0.1)

Workspace controller repo.

- Manifest: `manifest/workspace.toml`
- Lock: `manifest/workspace.lock.json`
- Runner (Python): `tools/runner/runner.py`
- Protocol + fixtures: `protocol/`

## Quickstart

```bash
python3 tools/runner/runner.py list
python3 tools/runner/runner.py fetch
python3 tools/runner/runner.py run build --all
python3 tools/runner/runner.py run test --all
```

## Local overrides

Create `manifest/overrides.toml` (gitignored) to point a component to a local path.
