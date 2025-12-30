SHELL := /bin/bash

# --- Paths
SOCK ?= /tmp/socioprophet.sock

# --- Go API (UDS)
api-build:
	cd apps/api/cmd/socioprophet-api && go build -o ../../../bin/socioprophet-api
api-run: api-build
	rm -f $(SOCK); TRITRPC_SOCK=$(SOCK) ./bin/socioprophet-api

# --- Go Gateway (HTTP→UDS bridge)
gateway-build:
	cd apps/gateway/cmd/tritrpc-gateway && go build -o ../../../bin/tritrpc-gateway
gateway-run: gateway-build
	TRITRPC_SOCK=$(SOCK) GATEWAY_PORT=8080 ./bin/tritrpc-gateway

# --- Vue
web-dev:
	cd apps/socioprophet-web && pnpm install && pnpm dev

# --- Kustomize dry-run (requires kubectl + kustomize)
kustomize-dev:
	kustomize build apps/api/kustomize/overlays/dev | kubectl apply -f -
	kustomize build apps/gateway/kustomize/overlays/dev | kubectl apply -f -
	kustomize build apps/socioprophet-web/kustomize/overlays/dev | kubectl apply -f -

# --- Bootstrap repo (init git, first commit)
bootstrap:
	./scripts/bootstrap_repo.sh
