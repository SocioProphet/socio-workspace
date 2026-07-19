# Agent Operating Contract

This repository is the SocioProphet workspace controller. Treat it as the governance, manifest, lock, runner, policy, and validation-lane home for multi-repo development. Do not implement downstream product features here.

## Non-negotiable invariants

- Work only on a topic branch or isolated worktree. Never mutate `main` directly.
- Start non-trivial work by reading `README.md`, `docs/SCOPE_PURPOSE_STATUS_BACKLOG.md`, `docs/TOPOLOGY.md`, and `docs/INTEGRATION_STATUS.md`.
- Keep changes inside Sociosphere's scope: workspace orchestration, registry metadata, manifests, locks, protocol fixtures, standards, validation tools, governance docs, and CI checks.
- Do not vendor third-party code, secrets, generated dependency trees, model weights, binary artifacts, or local machine state.
- Prefer small, reviewable PRs with deterministic validation evidence.
- If repo context is missing, update this file or a canonical doc minimally. Do not add verbose agent memory dumps.

## Required validation before PR

Run the narrowest relevant checks first, then the full workspace check when possible:

```bash
python3 tools/runner/runner.py list && python3 tools/runner/runner.py check-manifest && python3 tools/runner/runner.py lock-verify && python3 tools/check_topology.py && bash tools/check_hygiene.sh
```

For standards or governance additions, also run:

```bash
make validate-standards && make registry-validate
```

For complete local validation, run:

```bash
make workspace-check && pytest -q
```

If a check cannot be run in the current environment, record the reason in the PR body and keep the change scoped enough for CI to verify.

## Agentic coding lane protocol

Each coding-agent task should produce, at minimum:

1. an issue or task statement with acceptance criteria,
2. an isolated branch/worktree,
3. a short implementation plan,
4. bounded permission assumptions,
5. deterministic validation evidence,
6. a PR or patch,
7. an agent task receipt when the task affects governance, automation, validation, or release behavior.

Sociosphere owns the standards and validation primitives for this protocol. AgentPlane owns runtime execution. Policy-fabric owns reusable policy evaluation. Prophet-platform owns downstream product surfaces.
