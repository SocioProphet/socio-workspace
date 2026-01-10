SHELL := /usr/bin/env bash
.ONESHELL:
.SHELLFLAGS := -euo pipefail -c

PY ?= python3
PYTHONPATH := $(CURDIR)/tools

.PHONY: help schema-fingerprint schema-verify schema-update-fingerprint conformance-smoke check

help:
	@printf "%s\n" "Targets:" \
	  "  schema-fingerprint         Print deterministic schema hash" \
	  "  schema-verify              Compare against TRIRPC_V0_SCHEMA_SHA256" \
	  "  schema-update-fingerprint  Update TRIRPC_V0_SCHEMA_SHA256 from current schemas" \
	  "  conformance-smoke          Verify required artifacts exist + print paths" \
	  "  check                      Run schema-verify + conformance-smoke"

schema-fingerprint:
	PYTHONPATH="$(PYTHONPATH)" $(PY) -m conformance.trirpc_v0.fingerprint

schema-verify:
	@expected="$$(cat TRIRPC_V0_SCHEMA_SHA256)"; \
	got="$$(PYTHONPATH="$(PYTHONPATH)" $(PY) -m conformance.trirpc_v0.fingerprint | awk '{print $$2}')"; \
	if [ "$$expected" != "$$got" ]; then echo "ERR: schema fingerprint changed"; echo " expected=$$expected"; echo " got=$$got"; exit 2; fi; \
	echo "OK: schema fingerprint matches $$got"

schema-update-fingerprint:
	@PYTHONPATH="$(PYTHONPATH)" $(PY) -m conformance.trirpc_v0.fingerprint | awk '{print $$2}' > TRIRPC_V0_SCHEMA_SHA256 && echo "OK: updated TRIRPC_V0_SCHEMA_SHA256"

conformance-smoke:
	PYTHONPATH="$(PYTHONPATH)" $(PY) -m conformance.trirpc_v0.smoke

check: schema-verify conformance-smoke
