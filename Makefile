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
.PHONY: validate validate-standards spine-v0-validate active-spine-overlay-validate active-spine-sources-validate spine-canonical-sources-drift-validate topology-doc-active-spine-validate active-spine-boundaries-validate active-spine-validation-stack-doc-validate neurosymbolic-repo-graph-reasoner-doc-validate neurosymbolic-repo-graph-fixtures-validate neurosymbolic-repo-graph-ttl-fixtures-validate neurosymbolic-repo-graph-vocabulary-validate neurosymbolic-repo-graph-shacl-contract-validate runner-overlay-discovery-validate runner-overlay-merge-order-validate agent-reliability-governance-queue-validate authority-dependencies-validate governed-intelligence-rollout-validate multidomain-geospatial-standards-compliance-validate program-dashboard-validate model-fabric-work-register-validate lattice-data-governai-topology-validate lattice-runtime-profile-consumer-parity-validate lattice-demo-readiness-validate lattice-replay-evidence-membrane-validate lattice-runtime-release-readiness-validate lattice-product-readiness-program-validate lattice-operating-model-validate lattice-deployment-topology-validate lattice-security-isolation-model-validate lattice-observability-sre-validate lattice-release-rollback-controls-validate lattice-environment-fingerprints-validate superconscious-reasoning-validate sociosphere-authority-dependency-graph-tier2-binding-ci lawful-learning-phase8-registration-validate evidence-fabric-repos-validate evidence-fabric-surface-integrations-validate context-fabric-registration-validate corpus-loop-v0-validate neurosymbolic-chronos-validate corpus-loop-v1-validate corpus-loop-v1-resolution-validate corpus-loop-v1-resolution-live corpus-loop-demo-packet-validate corpus-loop-demo-assemble-check corpus-loop-demo-assemble-write corpus-loop-check svf-registry-validate svf-runner-list svf-runner-select-smoke svf-runner-verify-receipt-smoke svf-runner-run-smoke svf-runner-tampered-receipt-smoke svf-runner-unregistered-action-smoke svf-workspace-validate registry-admissions-validate effective-canonical-registry-validate computational-artifacts-validate

validate: validate-standards spine-v0-validate active-spine-overlay-validate active-spine-sources-validate spine-canonical-sources-drift-validate topology-doc-active-spine-validate active-spine-boundaries-validate active-spine-validation-stack-doc-validate neurosymbolic-repo-graph-reasoner-doc-validate neurosymbolic-repo-graph-fixtures-validate neurosymbolic-repo-graph-ttl-fixtures-validate neurosymbolic-repo-graph-vocabulary-validate neurosymbolic-repo-graph-shacl-contract-validate runner-overlay-discovery-validate runner-overlay-merge-order-validate agent-reliability-governance-queue-validate authority-dependencies-validate governed-intelligence-rollout-validate program-dashboard-validate model-fabric-work-register-validate lattice-data-governai-topology-validate lattice-runtime-profile-consumer-parity-validate lattice-demo-readiness-validate lattice-replay-evidence-membrane-validate lattice-runtime-release-readiness-validate lattice-product-readiness-program-validate lattice-operating-model-validate lattice-deployment-topology-validate lattice-security-isolation-model-validate lattice-observability-sre-validate lattice-release-rollback-controls-validate lattice-environment-fingerprints-validate superconscious-reasoning-validate sociosphere-authority-dependency-graph-tier2-binding-ci lawful-learning-phase8-registration-validate evidence-fabric-repos-validate evidence-fabric-surface-integrations-validate context-fabric-registration-validate corpus-loop-v0-validate neurosymbolic-chronos-validate corpus-loop-v1-validate corpus-loop-v1-resolution-validate svf-workspace-validate computational-artifacts-validate
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

neurosymbolic-repo-graph-vocabulary-validate:
	python3 tools/check_neurosymbolic_repo_graph_vocabulary.py

neurosymbolic-repo-graph-shacl-contract-validate:
	python3 tools/check_neurosymbolic_repo_graph_shacl_contract.py

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

computational-artifacts-validate:
	python3 -m pip install --user pyyaml >/dev/null
	python3 tools/validate_computational_artifacts.py
