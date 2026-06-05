.PHONY: workspace-mesh-gate2-candidate-template-validate workspace-mesh-gate2-local-candidate-create workspace-mesh-gate2-local-candidate-create-force workspace-mesh-gate2-local-candidate-verify

workspace-mesh-gate2-candidate-template-validate:
	python3 tools/validate_workspace_mesh_gate2_candidate_template.py

workspace-mesh-gate2-local-candidate-create: workspace-mesh-gate2-candidate-template-validate
	python3 tools/create_workspace_mesh_gate2_local_candidate_mapping.py

workspace-mesh-gate2-local-candidate-create-force: workspace-mesh-gate2-candidate-template-validate
	python3 tools/create_workspace_mesh_gate2_local_candidate_mapping.py --force

workspace-mesh-gate2-local-candidate-verify:
	python3 tools/verify_workspace_mesh_gate2_local_candidate_mapping.py
