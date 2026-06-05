# GNUmakefile wrapper for Sociosphere.
#
# GNU Make loads GNUmakefile before Makefile. We include the existing Makefile
# first, then add cross-repo convenience targets for the Google Workspace
# Operations Mesh that lives in prophet-platform-fabric-mlops-ts-suite.

include Makefile

FABRIC_REPO ?= $(HOME)/dev/prophet-platform-fabric-mlops-ts-suite
FABRIC_MAKE ?= make -C $(FABRIC_REPO)

.PHONY: \
	fabric-repo-check \
	doctor-workspace-ops \
	validate-workspace-prototype \
	validate-workspace-mesh \
	validate-workspace-all \
	terraform-workspace-mesh-init \
	terraform-workspace-mesh-fmt \
	terraform-workspace-mesh-validate \
	terraform-workspace-mesh-plan \
	terraform-workspace-mesh-plan-out \
	terraform-workspace-mesh-plan-json \
	validate-workspace-mesh-plan-json \
	terraform-workspace-mesh-plan-safe \
	tofu-workspace-mesh-init \
	tofu-workspace-mesh-fmt \
	tofu-workspace-mesh-validate \
	tofu-workspace-mesh-plan \
	tofu-workspace-mesh-plan-safe

fabric-repo-check:
	@test -d "$(FABRIC_REPO)" || (echo "ERR: FABRIC_REPO not found: $(FABRIC_REPO)"; exit 1)
	@test -f "$(FABRIC_REPO)/Makefile" || (echo "ERR: FABRIC_REPO Makefile missing: $(FABRIC_REPO)/Makefile"; exit 1)

# Workspace operations mesh proxies. These keep Sociosphere as the topology
# entrypoint while preserving prophet-platform-fabric-mlops-ts-suite as the
# implementation authority for the mesh.
doctor-workspace-ops: fabric-repo-check
	$(FABRIC_MAKE) doctor-workspace-ops

validate-workspace-prototype: fabric-repo-check
	$(FABRIC_MAKE) validate-workspace-prototype

validate-workspace-mesh: fabric-repo-check
	$(FABRIC_MAKE) validate-workspace-mesh

validate-workspace-all: fabric-repo-check
	$(FABRIC_MAKE) validate-workspace-all

terraform-workspace-mesh-init: fabric-repo-check
	$(FABRIC_MAKE) terraform-workspace-mesh-init

terraform-workspace-mesh-fmt: fabric-repo-check
	$(FABRIC_MAKE) terraform-workspace-mesh-fmt

terraform-workspace-mesh-validate: fabric-repo-check
	$(FABRIC_MAKE) terraform-workspace-mesh-validate

terraform-workspace-mesh-plan: fabric-repo-check
	$(FABRIC_MAKE) terraform-workspace-mesh-plan

terraform-workspace-mesh-plan-out: fabric-repo-check
	$(FABRIC_MAKE) terraform-workspace-mesh-plan-out

terraform-workspace-mesh-plan-json: fabric-repo-check
	$(FABRIC_MAKE) terraform-workspace-mesh-plan-json

validate-workspace-mesh-plan-json: fabric-repo-check
	$(FABRIC_MAKE) validate-workspace-mesh-plan-json

terraform-workspace-mesh-plan-safe: fabric-repo-check
	$(FABRIC_MAKE) terraform-workspace-mesh-plan-safe

tofu-workspace-mesh-init: fabric-repo-check
	$(FABRIC_MAKE) tofu-workspace-mesh-init

tofu-workspace-mesh-fmt: fabric-repo-check
	$(FABRIC_MAKE) tofu-workspace-mesh-fmt

tofu-workspace-mesh-validate: fabric-repo-check
	$(FABRIC_MAKE) tofu-workspace-mesh-validate

tofu-workspace-mesh-plan: fabric-repo-check
	$(FABRIC_MAKE) tofu-workspace-mesh-plan

tofu-workspace-mesh-plan-safe: fabric-repo-check
	$(FABRIC_MAKE) tofu-workspace-mesh-plan-safe
