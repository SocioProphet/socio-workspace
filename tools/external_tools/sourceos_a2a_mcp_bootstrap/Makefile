
.PHONY: a2a-dry a2a-live ci-local
a2a-dry:
	PROPHET_KEY?=~/.config/prophet/keys/ed25519_sk.hex
	prophet a2a run --repo socioprophet/sourceos-a2a-examples --ticket DEMO

a2a-live:
	# Requires MCP servers running and these envs set: GITHUB_TOKEN, VAULT_ADDR, VAULT_TOKEN
	prophet a2a run --repo socioprophet/sourceos-a2a-examples --ticket DEMO --live

ci-local:
	pip3 install pynacl >/dev/null || true
	python3 tools/verify_carrier.py out/carriers || true
