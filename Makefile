SHELL := /bin/bash

UI_DIR := apps/ui-workbench

# --- ui-workbench targets ---

.PHONY: ui-preflight ui-install ui-build ui-check ui-dev

ui-preflight:
	./tools/ui-preflight.sh

ui-install:
	cd $(UI_DIR) && npm ci

ui-build:
	cd $(UI_DIR) && npm run build

ui-check: ui-preflight ui-build
	@echo "OK: ui-check passed"

ui-dev: ui-preflight
	cd $(UI_DIR) && npm run dev
# --- end ui-workbench targets ---

# --- standards validation targets ---
.PHONY: validate validate-standards spine-v0-validate active-spine-overlay-validate active-spine-sources-validate spine-canonical-sources-drift-validate topology-doc-active-spine-validate active-spine-boundaries-validate active-spine-validation-stack-doc-validate neurosymbolic-repo-graph-reasoner-doc-validate neurosymbolic-repo-graph-fixtures-validate neurosymbolic-repo-graph-ttl-fixtures-validate first-party-rdf-parse-validate neurosymbolic-repo-graph-vocabulary-validate neurosymbolic-repo-graph-shacl-contract-validate neurosymbolic-vendored-artifact-graph-validate runner-overlay-discovery-validate runner-overlay-merge-order-validate agent-reliability-governance-queue-validate authority-dependencies-validate governed-intelligence-rollout-validate multidomain-geospatial-standards-compliance-validate program-dashboard-validate model-fabric-work-register-validate lattice-data-governai-topology-validate lattice-runtime-profile-consumer-parity-validate lattice-demo-readiness-validate lattice-replay-evidence-membrane-validate lattice-runtime-release-readiness-validate lattice-product-readiness-program-validate lattice-operating-model-validate lattice-deployment-topology-validate lattice-security-isolation-model-validate lattice-observability-sre-validate lattice-release-rollback-controls-validate lattice-environment-fingerprints-validate superconscious-reasoning-validate sociosphere-authority-dependency-graph-tier2-binding-ci lawful-learning-phase8-registration-validate evidence-fabric-repos-validate evidence-fabric-surface-integrations-validate context-fabric-registration-validate corpus-loop-v0-validate neurosymbolic-chronos-validate corpus-loop-v1-validate corpus-loop-v1-resolution-validate corpus-loop-v1-resolution-live corpus-loop-demo-packet-validate corpus-loop-demo-assemble-check corpus-loop-demo-assemble-write corpus-loop-check svf-registry-validate svf-runner-list svf-runner-select-smoke svf-runner-verify-receipt-smoke svf-runner-run-smoke svf-runner-tampered-receipt-smoke svf-runner-unregistered-action-smoke svf-export-latest svf-export-manifest-validate svf-workspace-validate registry-admissions-validate effective-canonical-registry-validate vendor-freshness-validate vendor-freshness-detect vendor-freshness-detect-check omnirisk-allocation-validate portfolio-position-binding-validate

validate: validate-standards spine-v0-validate active-spine-overlay-validate active-spine-sources-validate spine-canonical-sources-drift-validate topology-doc-active-spine-validate active-spine-boundaries-validate active-spine-validation-stack-doc-validate neurosymbolic-repo-graph-reasoner-doc-validate neurosymbolic-repo-graph-fixtures-validate neurosymbolic-repo-graph-ttl-fixtures-validate first-party-rdf-parse-validate neurosymbolic-repo-graph-vocabulary-validate neurosymbolic-repo-graph-shacl-contract-validate neurosymbolic-vendored-artifact-graph-validate runner-overlay-discovery-validate runner-overlay-merge-order-validate agent-reliability-governance-queue-validate authority-dependencies-validate governed-intelligence-rollout-validate program-dashboard-validate model-fabric-work-register-validate lattice-data-governai-topology-validate lattice-runtime-profile-consumer-parity-validate lattice-demo-readiness-validate lattice-replay-evidence-membrane-validate lattice-runtime-release-readiness-validate lattice-product-readiness-program-validate lattice-operating-model-validate lattice-deployment-topology-validate lattice-security-isolation-model-validate lattice-observability-sre-validate lattice-release-rollback-controls-validate lattice-environment-fingerprints-validate superconscious-reasoning-validate sociosphere-authority-dependency-graph-tier2-binding-ci lawful-learning-phase8-registration-validate evidence-fabric-repos-validate evidence-fabric-surface-integrations-validate context-fabric-registration-validate corpus-loop-v0-validate neurosymbolic-chronos-validate corpus-loop-v1-validate corpus-loop-v1-resolution-validate svf-workspace-validate vendor-freshness-validate board-spec-validate agent-prompt-catalog-validate omnirisk-allocation-validate portfolio-position-binding-validate
	@echo "OK: validate"

validate-standards:
	@ok=1; if [ -f tools/validate_adaptation_program.py ]; then python3 tools/validate_adaptation_program.py standards/examples/adaptation/program.example.v1.json || ok=0; else echo "ERR: tools/validate_adaptation_program.py missing"; ok=0; fi; if [ -f standards/qes/tools/validate_qes_contracts.py ]; then python3 standards/qes/tools/validate_qes_contracts.py || ok=0; else echo "WARN: standards/qes/tools/validate_qes_contracts.py missing (skipping)"; fi; if [ -f tools/check_multidomain_geospatial_standards_compliance.py ]; then python3 tools/check_multidomain_geospatial_standards_compliance.py || ok=0; else echo "ERR: tools/check_multidomain_geospatial_standards_compliance.py missing"; ok=0; fi; test $$ok -eq 1

spine-v0-validate:
	python3 tools/check_spine_v0.py

active-spine-overlay-validate:
	python3 tools/check_active_spine_overlay.py

active-spine-sources-validate:
	python3 tools/check_active_spine_sources.py

spine-canonical-sources-drift-validate:
	python3 tools/check_spine_canonical_sources_drift.py

topology-doc-active-spine-validate:
	python3 tools/check_topology_doc_active_spine.py

active-spine-boundaries-validate:
	python3 tools/check_active_spine_boundaries.py

active-spine-validation-stack-doc-validate:
	python3 tools/check_active_spine_validation_stack_doc.py

neurosymbolic-repo-graph-reasoner-doc-validate:
	python3 tools/check_neurosymbolic_repo_graph_reasoner_doc.py

neurosymbolic-repo-graph-fixtures-validate:
	python3 tools/check_neurosymbolic_repo_graph_fixtures.py

neurosymbolic-repo-graph-ttl-fixtures-validate:
	python3 tools/check_neurosymbolic_repo_graph_ttl_fixtures.py

first-party-rdf-parse-validate:
	python3 tools/check_first_party_rdf_parses.py

neurosymbolic-repo-graph-vocabulary-validate:
	python3 tools/check_neurosymbolic_repo_graph_vocabulary.py

neurosymbolic-repo-graph-shacl-contract-validate:
	python3 tools/check_neurosymbolic_repo_graph_shacl_contract.py

# Lift the vendor-freshness register into the nrg: graph so THE GRAPH reasons about
# vendored-dependency staleness + blast radius. -write regenerates the committed graph;
# -validate gates that it is faithful, single-source, and vocabulary-covered.
neurosymbolic-vendored-artifact-graph-write:
	python3 tools/lift_vendor_freshness_to_graph.py --write

neurosymbolic-vendored-artifact-graph-validate:
	python3 tools/check_vendored_artifact_graph.py

# Register-only. --skip-disk is DELIBERATE and load-bearing: this target is a
# prerequisite of the aggregate `validate`, which `make -k validate` runs in
# validate.yml on a runner where the consumer repos do not exist. Without the flag the
# on-disk layer resolved nothing, emitted SKIPPED, and still printed "validated 11
# declared vendored artifact(s)" with exit 0 — a second copy of this gate, inert, next
# to the fail-closed one. Declaring the skip makes the difference between "I chose not
# to read the bytes" and "I tried and silently read none" visible in the log.
#
# The FAIL-CLOSED on-disk gate is .github/workflows/vendor-freshness.yml, which
# materializes the consumer repos and passes --require-disk. It is the enforcing copy;
# this one checks register self-consistency only.
vendor-freshness-validate:
	python3 tools/validate_vendor_freshness.py --skip-disk

# Observe upstream and report. Read-only: no register edit, no plan emission.
vendor-freshness-detect-check:
	python3 tools/detect_vendor_freshness.py

# Refresh the observation in place and emit re-vendor plans. This is what CI runs;
# run it locally when the gate complains that an observation has aged out.
vendor-freshness-detect:
	python3 tools/detect_vendor_freshness.py --write-register --propose-disposition \
		--emit-plans build/vendor-revendor-plans --summary build/vendor-freshness-detect.md

runner-overlay-discovery-validate:
	python3 tools/check_runner_overlay_discovery.py

runner-overlay-merge-order-validate:
	python3 tools/check_runner_overlay_merge_order.py

agent-reliability-governance-queue-validate:
	python3 tools/validate_agent_reliability_governance_queue.py

authority-dependencies-validate:
	python3 tools/validate_authority_dependencies.py

governed-intelligence-rollout-validate:
	python3 -m pip install --user pyyaml >/dev/null
	python3 tools/validate_governed_intelligence_rollout.py

program-dashboard-validate:
	python3 tools/validate_program_dashboard.py

board-spec-validate:
	python3 tools/check_board_spec.py

# Omnirisk cross-cut allocation contract (OMNI-1): every fixture must behave as
# named — *.valid.json VERIFIES, *.invalid.json REJECTS — and the sealed receipt
# ledger must verify. Self-contained: node risk results are given inputs consumed
# from the economic-prophet kernel by reference, so CI is independent of that PR.
omnirisk-allocation-validate:
	python3 -m gbrg.governance.omnirisk_allocation

portfolio-position-binding-validate:
	python3 -m gbrg.governance.portfolio_position_binding

agent-prompt-catalog-validate:
	python3 tools/check_agent_prompt_catalog.py

model-fabric-work-register-validate:
	python3 tools/validate_model_fabric_work_register.py

lattice-data-governai-topology-validate:
	python3 -m pip install --user pyyaml >/dev/null
	python3 tools/validate_lattice_data_governai_topology.py

lattice-runtime-profile-consumer-parity-validate:
	python3 -m pip install --user pyyaml >/dev/null
	python3 tools/validate_lattice_runtime_profile_consumer_parity.py

lattice-demo-readiness-validate:
	python3 -m pip install --user pyyaml >/dev/null
	python3 tools/validate_lattice_demo_readiness.py

lattice-replay-evidence-membrane-validate:
	python3 -m pip install --user pyyaml >/dev/null
	python3 tools/validate_lattice_replay_evidence_membrane_registration.py

lattice-runtime-release-readiness-validate:
	python3 -m pip install --user pyyaml >/dev/null
	python3 tools/validate_lattice_runtime_release_readiness.py

lattice-product-readiness-program-validate:
	python3 -m pip install --user pyyaml >/dev/null
	python3 tools/validate_lattice_product_readiness_program.py

lattice-operating-model-validate:
	python3 -m pip install --user pyyaml >/dev/null
	python3 tools/validate_lattice_operating_model.py

lattice-deployment-topology-validate:
	python3 -m pip install --user pyyaml >/dev/null
	python3 tools/validate_lattice_deployment_topology.py

lattice-security-isolation-model-validate:
	python3 -m pip install --user pyyaml >/dev/null
	python3 tools/validate_lattice_security_isolation_model.py

lattice-observability-sre-validate:
	python3 -m pip install --user pyyaml >/dev/null
	python3 tools/validate_lattice_observability_sre.py

lattice-release-rollback-controls-validate:
	python3 -m pip install --user pyyaml >/dev/null
	python3 tools/validate_lattice_release_rollback_controls.py

lattice-environment-fingerprints-validate:
	python3 -m pip install --user pyyaml >/dev/null
	python3 tools/validate_lattice_environment_fingerprints.py

superconscious-reasoning-validate:
	python3 tools/validate_superconscious_reasoning.py tests/fixtures/superconscious/deterministic >/dev/null

sociosphere-authority-dependency-graph-tier2-binding-ci:
	python3 -m json.tool schemas/composition/sociosphere-authority-dependency-graph-tier2-binding.v1.json >/dev/null
	python3 -m json.tool tests/fixtures/composition/sociosphere-authority-dependency-graph-tier2-binding.synthetic.json >/dev/null
	python3 -m json.tool tests/fixtures/composition/sociosphere-authority-dependency-graph-tier2-binding.runtime-field.invalid.synthetic.json >/dev/null
	python3 tools/check_sociosphere_authority_dependency_tier2_binding.py tests/fixtures/composition/sociosphere-authority-dependency-graph-tier2-binding.synthetic.json
	! python3 tools/check_sociosphere_authority_dependency_tier2_binding.py tests/fixtures/composition/sociosphere-authority-dependency-graph-tier2-binding.runtime-field.invalid.synthetic.json

lawful-learning-phase8-registration-validate:
	python3 -m pip install --user pyyaml >/dev/null
	python3 tools/validate_lawful_learning_phase8_registration.py

evidence-fabric-repos-validate:
	python3 -m pip install --user pyyaml >/dev/null
	python3 tools/validate_evidence_fabric_repos.py

evidence-fabric-surface-integrations-validate:
	python3 -m pip install --user pyyaml >/dev/null
	python3 tools/validate_evidence_fabric_surface_integrations.py

context-fabric-registration-validate:
	python3 tools/validate_context_fabric_registration.py

corpus-loop-v0-validate:
	python3 -m pip install --user jsonschema >/dev/null
	python3 tools/check_clv0.py

neurosymbolic-chronos-validate:
	python3 tools/check_neurosymbolic_chronos.py

corpus-loop-v1-validate:
	python3 -m pip install --user jsonschema >/dev/null
	python3 tools/check_clv1.py

corpus-loop-v1-resolution-validate:
	python3 tools/resolve_clv1.py --require-found

corpus-loop-v1-resolution-live:
	python3 tools/resolve_clv1.py --live --write --require-found

corpus-loop-demo-packet-validate:
	python3 tools/check_corpus_loop_demo_packet.py

corpus-loop-customer-readout-validate:
	python3 tools/check_corpus_loop_customer_readout.py

corpus-loop-demo-assemble-check:
	python3 tools/assemble_corpus_loop_demo.py

corpus-loop-demo-assemble-write:
	python3 tools/assemble_corpus_loop_demo.py --write

corpus-loop-check: corpus-loop-v0-validate neurosymbolic-chronos-validate corpus-loop-v1-validate corpus-loop-v1-resolution-validate corpus-loop-demo-assemble-check corpus-loop-demo-packet-validate corpus-loop-customer-readout-validate ui-check
	@echo "OK: corpus-loop-check"

multidomain-geospatial-standards-compliance-validate:
	python3 tools/check_multidomain_geospatial_standards_compliance.py

# Pinned instant for the SVF smoke fixtures (2026-06-09T11:53:46Z). svf_runner
# stamps this into run/receipt timestamps (and the ids + digests derived from
# them) when SVF_SOURCE_DATE_EPOCH is set, so `make validate` regenerates the
# committed artifacts/svf fixtures byte-for-byte instead of churning them on the
# wall clock. Real runs leave the variable unset and record actual time.
SVF_SOURCE_DATE_EPOCH := 1781006026

svf-registry-validate:
	python3 -m pip install --user pyyaml >/dev/null
	python3 tools/validate_svf_registry.py

svf-runner-list:
	python3 -m pip install --user pyyaml >/dev/null
	python3 tools/svf_runner.py list >/dev/null

svf-runner-select-smoke:
	python3 -m pip install --user pyyaml >/dev/null
	python3 tools/svf_runner.py select --repo SocioProphet/sociosphere --changed-path registry/sovereign-validation-fabric.yaml >/dev/null

svf-runner-verify-receipt-smoke:
	python3 tools/svf_runner.py verify-receipt tests/fixtures/svf/receipt.valid.synthetic.json >/dev/null

svf-runner-run-smoke:
	python3 -m pip install --user pyyaml >/dev/null
	rm -rf artifacts/svf/runs/local-smoke
	SVF_SOURCE_DATE_EPOCH=$(SVF_SOURCE_DATE_EPOCH) python3 tools/svf_runner.py run --repo SocioProphet/sociosphere --changed-path registry/sovereign-validation-fabric.yaml --out artifacts/svf/runs/local-smoke >/dev/null
	python3 tools/svf_runner.py verify-receipt artifacts/svf/runs/local-smoke/validation-receipt.json >/dev/null

svf-runner-tampered-receipt-smoke: svf-runner-run-smoke
	python3 -c 'import json; from pathlib import Path; source=Path("artifacts/svf/runs/local-smoke/validation-receipt.json"); target=Path("artifacts/svf/runs/local-smoke/validation-receipt.tampered.json"); data=json.loads(source.read_text(encoding="utf-8")); data["run_digest"]["digest"]="0"*64; target.write_text(json.dumps(data, indent=2, sort_keys=True)+"\\n", encoding="utf-8")'
	! python3 tools/svf_runner.py verify-receipt artifacts/svf/runs/local-smoke/validation-receipt.tampered.json >/dev/null

svf-runner-unregistered-action-smoke:
	python3 -m pip install --user pyyaml >/dev/null
	mkdir -p artifacts/svf/runs/unregistered-action-smoke
	python3 -c 'from pathlib import Path; import yaml; data=yaml.safe_load(Path("registry/sovereign-validation-fabric.yaml").read_text(encoding="utf-8")); data["plans"][0]["actions"]=["svf:action:sociosphere.missing-action"]; Path("artifacts/svf/runs/unregistered-action-smoke/registry.yaml").write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")'
	! SVF_SOURCE_DATE_EPOCH=$(SVF_SOURCE_DATE_EPOCH) python3 tools/svf_runner.py --registry artifacts/svf/runs/unregistered-action-smoke/registry.yaml run --repo SocioProphet/sociosphere --plan svf:plan:sociosphere.registry-dogfood --out artifacts/svf/runs/unregistered-action-smoke >/dev/null

svf-export-latest:
	python3 tools/svf_export_latest.py

svf-export-manifest-validate:
	python3 tools/validate_svf_export_manifest.py

svf-workspace-validate: svf-registry-validate svf-runner-list svf-runner-select-smoke svf-runner-verify-receipt-smoke svf-runner-run-smoke svf-runner-tampered-receipt-smoke svf-runner-unregistered-action-smoke svf-export-latest svf-export-manifest-validate
	@echo "OK: svf-workspace-validate"

# --- registry targets ---
.PHONY: registry-validate registry-admissions-validate admission-governance-shape-validate interpretability-harness-vocabulary-validate propagation-detect effective-canonical-registry-validate ontology-validate dep-cycles mirror-drift-check build-intelligence-validate deployment-topology-validate contract-lock-validate

mirror-drift-check:
	python3 engines/mirror_drift_engine.py check

registry-admissions-validate:
	python3 tools/validate_registry_admissions.py

# Admission records that a repository exists; it does not govern it. This fails when an
# admitted repo never acquired a lane, dependency edges or a propagation rule -- the
# gap that let noetica-impair sit in the staging area while every merge cascaded to
# nothing.
admission-governance-shape-validate:
	python3 tools/check_admission_governance_shape.py

interpretability-harness-vocabulary-validate:
	python3 tools/check_interpretability_harness_vocabulary.py

# Which trigger repos merged to main recently. Read-only; needs an org-read token
# to see past sociosphere itself.
propagation-detect:
	python3 tools/detect_main_merges.py

effective-canonical-registry-validate:
	python3 tools/build_effective_canonical_registry.py

registry-validate: registry-admissions-validate admission-governance-shape-validate effective-canonical-registry-validate
	@echo "==> Validating registry ontology roles and layers..."
	python3 engines/ontology_engine.py validate
	@echo "==> Checking dependency graph for cycles..."
	python3 engines/propagation_engine.py cycles
	@echo "==> Validating mirror drift status..."
	python3 engines/mirror_drift_engine.py check
	@echo "OK: registry-validate passed"

build-intelligence-validate:
	python3 tools/validate_build_intelligence.py

deployment-topology-validate:
	python3 tools/validate_deployment_topology.py

contract-lock-validate:
	python3 tools/validate_contract_locks.py

ontology-validate: registry-validate

# --- self-documenting-estate targets ---------------------------------------
# Code is the source of truth; docs are DERIVED from the code-derived catalog.
# CATALOG points at a prophet-core-catalog checkout (pinned in
# artifacts/self-documentation/catalog-pin.json).
CATALOG ?= ../prophet-core-catalog
.PHONY: estate-enumerate self-doc-compose self-doc-verify

estate-enumerate:
	python3 tools/enumerate_estate.py --catalog $(CATALOG)

self-doc-compose:
	python3 tools/compose_self_documentation.py --catalog $(CATALOG)

self-doc-verify:
	python3 tools/verify_self_documentation.py --catalog $(CATALOG)
# --- end self-documenting-estate targets -----------------------------------
