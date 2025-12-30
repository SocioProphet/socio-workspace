# Socio Workspace (meta-repo)

This repo materializes a *composable workspace* (manifest + lock) that can orchestrate builds/tests across many independent repos.

## Quickstart

```bash
python3 -m venv .venv && . .venv/bin/activate && pip install -r tools/runner/requirements.txt && python tools/runner/runner.py --help
```

## Layout

- `manifest/` — `workspace.toml` + `workspace.lock.json`
- `tools/runner/` — python runner (task orchestration)
- `protocol/` — protocol specs + fixtures
  - `protocol/a2a_mcp_impl_pack_v1/` — A2A/MCP implementation pack (schemas + examples)
- `components/` — component repos (CLIs/services/UI). These are **normally** materialized by the fetcher; in this zip they are included as a snapshot seed.
- `adapters/` — adapters (e.g., `cc`, `configs`)
  - `adapters/configs/docker-compose.dev.yml` — dev compose for local orchestration
- `docs/env/requirements-eval.txt` — environment notes / dependency evaluation snapshot
- `tools/migrations/human_digital_twin_rename_kit/` — migration kit for HDT rename
- `third_party/` — non-default seeds / reference repos
  - `third_party/socioprophet_repo_seed/` — prior repo scaffold + docs

## Notes

- We commit `workspace.toml` and `workspace.lock.json`.
- Local overrides (not committed): `manifest/overrides.toml`.
