.PHONY: workspace-mesh-gate1-artifact-review-validate workspace-mesh-gate1-generated-artifacts-review workspace-mesh-topology-gates-validate

workspace-mesh-gate1-artifact-review-validate:
	python3 tools/validate_workspace_mesh_gate1_artifact_review.py

workspace-mesh-gate1-generated-artifacts-review:
	python3 tools/review_workspace_mesh_gate1_generated_artifacts.py

workspace-mesh-topology-gates-validate: workspace-mesh-proxy-validate workspace-mesh-release-readiness-validate workspace-mesh-gate1-artifact-review-validate
