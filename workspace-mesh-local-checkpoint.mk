.PHONY: workspace-mesh-local-checkpoint

workspace-mesh-local-checkpoint:
	$(MAKE) workspace-mesh-operator-checkpoint
	$(MAKE) -f workspace-mesh-gate2-candidate.mk workspace-mesh-gate2-candidate-lifecycle-checkpoint
	$(MAKE) -f workspace-mesh-gate2-promotion.mk workspace-mesh-gate2-promotion-blocker-validate
	$(MAKE) -f workspace-mesh-current-state.mk workspace-mesh-current-state-validate
	python3 tools/workspace_mesh_local_checkpoint.py
