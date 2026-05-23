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
.PHONY: validate validate-standards spine-v0-validate active-spine-overlay-validate active-spine-sources-validate runner-overlay-discovery-validate runner-overlay-merge-order-validate agent-reliability-governance-queue-validate authority-dependencies-validate governed-intelligence-rollout-validate multidomain-geospatial-standards-compliance-validate program-dashboard-validate model-fabric-work-register-validate lattice-data-governai-topology-validate lattice-runtime-profile-consumer-parity-validate lattice-demo-readiness-validate lattice-replay-evidence-membrane-validate lattice-runtime-release-readiness-validate lattice-product-readiness-program-validate lattice-operating-model-validate lattice-deployment-topology-validate lattice-security-isolation-model-validate lattice-observability-sre-validate lattice-release-rollback-controls-validate lattice-environment-fingerprints-validate superconscious-reasoning-validate sociosphere-authority-dependency-graph-tier2-binding-ci lawful-learning-phase8-registration-validate evidence-fabric-repos-validate evidence-fabric-surface-integrations-validate corpus-loop-v0-validate corpus-loop-v1-validate corpus-loop-v1-resolution-validate corpus-loop-v1-resolution-live corpus-loop-demo-packet-validate corpus-loop-customer-readout-validate corpus-loop-demo-assemble-check corpus-loop-demo-assemble-write corpus-loop-check

validate: validate-standards spine-v0-validate active-spine-overlay-validate active-spine-sources-validate runner-overlay-discovery-validate runner-overlay-merge-order-validate agent-reliability-governance-queue-validate authority-dependencies-validate governed-intelligence-rollout-validate program-dashboard-validate model-fabric-work-register-validate lattice-data-governai-topology-validate lattice-runtime-profile-consumer-parity-validate lattice-demo-readiness-validate lattice-replay-evidence-membrane-validate lattice-runtime-release-readiness-validate lattice-product-readiness-program-validate lattice-operating-model-validate lattice-deployment-topology-validate lattice-security-isolation-model-validate lattice-observability-sre-validate lattice-release-rollback-controls-validate lattice-environment-fingerprints-validate superconscious-reasoning-validate sociosphere-authority-dependency-graph-tier2-binding-ci lawful-learning-phase8-registration-validate evidence-fabric-repos-validate evidence-fabric-surface-integrations-validate corpus-loop-v0-validate corpus-loop-v1-validate corpus-loop-v1-resolution-validate
	@echo "OK: validate"

validate-standards:
	@ok=1; if [ -f tools/validate_adaptation_program.py ]; then python3 tools/validate_adaptation_program.py standards/examples/adaptation/program.example.v1.json || ok=0; else echo "ERR: tools/validate_adaptation_program.py missing"; ok=0; fi; if [ -f standards/qes/tools/validate_qes_contracts.py ]; then python3 standards/qes/tools/validate_qes_contracts.py || ok=0; else echo "WARN: standards/qes/tools/validate_qes_contracts.py missing (skipping)"; fi; if [ -f tools/check_multidomain_geospatial_standards_compliance.py ]; then python3 tools/check_multidomain_geospatial_standards_compliance.py || ok=0; else echo "ERR: tools/check_multidomain_geospatial_standards_compliance.py missing"; ok=0; fi; test $$ok -eq 1

spine-v0-validate:
	python3 tools/check_spine_v0.py

active-spine-overlay-validate:
	python3 tools/check_active_spine_overlay.py

active-spine-sources-validate:
	python3 tools/check_active_spine_sources.py

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

corpus-loop-v0-validate:
	python3 -m pip install --user jsonschema >/dev/null
	python3 tools/check_clv0.py

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

corpus-loop-check: corpus-loop-v0-validate corpus-loop-v1-validate corpus-loop-v1-resolution-validate corpus-loop-demo-assemble-check corpus-loop-demo-packet-validate corpus-loop-customer-readout-validate ui-check
	@echo "OK: corpus-loop-check"

multidomain-geospatial-standards-compliance-validate:
	python3 tools/check_multidomain_geospatial_standards_compliance.py

# --- registry targets ---
.PHONY: registry-validate ontology-validate dep-cycles mirror-drift-check build-intelligence-validate deployment-topology-validate contract-lock-validate

mirror-drift-check:
	python3 engines/mirror_drift_engine.py check

registry-validate:
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

dep-cycles:
	python3 engines/propagation_engine.py cycles

# --- status targets ---
.PHONY: status status-report

status:
	python3 engines/status_reporter.py dashboard

status-report:
	python3 engines/status_reporter.py report --format json

# --- compliance targets ---
.PHONY: compliance-check compliance-summary

compliance-check:
	@echo "==> Running compliance checks..."
	python3 telemetry/compliance_checker.py check
	@echo "OK: compliance-check complete"

compliance-summary:
	python3 telemetry/compliance_checker.py summary --format json

# --- GAIA World Model v1 readiness targets ---
.PHONY: gaia-world-model-v1-readiness-validate

gaia-world-model-v1-readiness-validate:
	python3 tools/check_gaia_world_model_v1_readiness.py

# --- source exposure governance targets ---
.PHONY: source-exposure-check

source-exposure-check:
	@echo "==> Running source exposure publication safety check..."
	python3 tools/check_source_exposure.py
	@echo "OK: source-exposure-check passed"

# --- merge order ---
.PHONY: merge-order

merge-order:
	python3 engines/propagation_engine.py merge-order

# --- workspace runner targets ---
.PHONY: workspace-list lock-verify lock-update inventory topology-check proof-slice-smoke

workspace-list:
	python3 tools/runner/runner.py list

lock-verify:
	python3 tools/runner/runner.py lock-verify

lock-update:
	python3 tools/runner/runner.py lock-update

inventory:
	python3 tools/runner/runner.py inventory

topology-check:
	python3 tools/check_topology.py

proof-slice-smoke:
	python3 tools/runner/proof_slice_smoke.py

# --- identity conformance targets ---
.PHONY: identity-prime-conformance

identity-prime-conformance:
	python3 tools/conformance/validate_identity_is_prime_fixtures.py

# --- hygiene targets ---
.PHONY: hygiene-check

hygiene-check:
	@echo "==> Running repository hygiene checks..."
	bash tools/check_hygiene.sh
	python3 tools/check_final_newlines.py
	@echo "OK: hygiene-check passed"


# --- full workspace check (run in CI) ---
.PHONY: workspace-check

workspace-check: validate registry-validate build-intelligence-validate deployment-topology-validate contract-lock-validate compliance-check source-exposure-check lock-verify topology-check hygiene-check identity-prime-conformance
	@echo "OK: workspace-check passed"
