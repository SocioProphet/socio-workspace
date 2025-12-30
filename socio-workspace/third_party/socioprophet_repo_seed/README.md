# SocioProphet — Monorepo (Vue + TritRPC + Kustomize + Argo CD)

SocioProphet is a modular, **TritRPC‑first** platform with a Vue 3 portal and Unix‑domain‑socket (UDS) services.
This repo is production‑oriented but starts intentionally small so you can move fast and evolve safely.

## Quick Start (local dev)

### Prereqs
- Go >= 1.22
- Node >= 20 and **pnpm** (`corepack enable` then `corepack prepare pnpm@latest --activate`)
- Docker / Podman
- `kubectl`, `kustomize`, and (optional) Argo CD CLI

### Bring up API (UDS) + Gateway (HTTP bridge for browsers)
```bash
# 1) build & run the UDS API
make api-run
# 2) (optional) run the gateway bridge so browsers can call health over HTTP in dev
make gateway-run
```

### Bring up the web portal
```bash
cd apps/socioprophet-web
pnpm install
pnpm dev
```

Visit the Vite dev URL. The Status badge queries the gateway’s `/health` which relays a `PING` over UDS to the API and returns `PONG`.

> TritRPC is the **first‑class** wire; the gateway is a dev/productization bridge. In production, keep HTTP only at the edge, inside a zero‑trust boundary.

## Deploy (Kubernetes, Kustomize, Argo CD)
- Kustomize bases for each app live under `apps/*/kustomize` with `overlays/{dev,prod}`.
- Example Argo CD ApplicationSet is at `k8s/argo-cd/appsets/socioprophet-appset.yaml`. Update repo URL/paths and apply in your Argo CD cluster.

## Repo Map
```
apps/
  api/                 # Go UDS service (TritRPC-first; simple health exemplar)
  gateway/             # Optional HTTP bridge → UDS for browsers (dev/edge)
  socioprophet-web/    # Vue 3 + Vite portal (no React/Carbon)
docs/                  # Architecture, security, and TritRPC framing doc
k8s/                   # Argo CD ApplicationSet + namespaces
scripts/               # Bootstrap and local dev helpers
tools/                 # TritRPC examples (client/server)
.github/workflows/     # Minimal CI (build checks); deployment is Argo CD
```

## Security Posture
- UDS default socket: `/tmp/socioprophet.sock` (override `TRITRPC_SOCK`).
- Optional AEAD key (env `TRITRPC_AEAD_KEY`, 32 bytes hex) reserved for framing; current example runs clear for readability.
- Nonces, CRC, and replay‑guard are outlined in `docs/TRITRPC_SPEC.md` and are intended to be enforced at the library layer.

## License
MIT — see `LICENSE`.
