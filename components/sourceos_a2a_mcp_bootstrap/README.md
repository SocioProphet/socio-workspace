
# sourceos-a2a-mcp bootstrap v2.2 (final)
- `.mcp/servers.json` → UDS TritRPC sockets
- `Makefile` targets:
  - `a2a-dry`  → local carriers/status via Prophet (dry)
  - `a2a-live` → opens PR live (requires GITHUB_TOKEN + Vault secrets set)
  - `ci-local` → carrier verify locally
