SHELL := /usr/bin/env bash
.ONESHELL:
.SHELLFLAGS := -euo pipefail -c

PY ?= python3
PYTHONPATH := $(CURDIR)/tools

.PHONY: help schema-fingerprint conformance-smoke check

help:
	@printf "%s\n" "Targets:" "  schema-fingerprint  Print deterministic schema hash" "  conformance-smoke    Minimal import + file presence smoke" "  check               Run both"

schema-fingerprint:
	PYTHONPATH="$(PYTHONPATH)" $(PY) -m conformance.trirpc_v0.fingerprint

conformance-smoke:
	PYTHONPATH="$(PYTHONPATH)" $(PY) -m conformance.trirpc_v0.smoke

check: schema-fingerprint conformance-smoke
