SHELL := /bin/bash

UI_DIR := apps/ui-workbench

.PHONY: ui-dev ui-build ui-check ui-install

# (removed) @echo "OK: ui build passed"
# --- ui-workbench targets ---

.PHONY: ui-preflight ui-install ui-build ui-check ui-dev

ui-preflight:
	./tools/ui-preflight.sh

ui-install:
	cd $(UI_DIR) && npm install && npm install -D vue-tsc typescript

ui-build:
	cd $(UI_DIR) && npm run build

ui-check: ui-preflight ui-build
	@echo "OK: ui-check passed"

ui-dev: ui-preflight
	cd $(UI_DIR) && npm run dev
# --- end ui-workbench targets ---
# --- standards validation targets ---
.PHONY: validate validate-standards

validate: validate-standards
	@echo "OK: validate"

validate-standards:
	@ok=1; if [ -f tools/validate_adaptation_program.py ]; then python3 tools/validate_adaptation_program.py standards/examples/adaptation/program.example.v1.json || ok=0; else echo "ERR: tools/validate_adaptation_program.py missing"; ok=0; fi; if [ -f standards/qes/tools/validate_qes_contracts.py ]; then python3 standards/qes/tools/validate_qes_contracts.py || ok=0; else echo "WARN: standards/qes/tools/validate_qes_contracts.py missing (skipping)"; fi; test $$ok -eq 1


# standards helpers
schemas-fp:
	python3 tools/schema_fp.py schemas/avro/trirpc/*.avsc > schemas/avro/trirpc/FINGERPRINTS.v0.txt

conformance:
	@echo "TODO: wire real conformance runner entrypoint under tools/conformance/trirpc-v0"
