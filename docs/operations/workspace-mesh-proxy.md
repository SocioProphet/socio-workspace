# Workspace Mesh Proxy Targets

Sociosphere is the topology entrypoint. The Google Workspace Operations Mesh implementation currently lives in:

```text
~/dev/prophet-platform-fabric-mlops-ts-suite
```

The root `GNUmakefile` includes the existing `Makefile` and adds proxy targets that delegate to the fabric repo.

## Default path

```bash
cd ~/dev/sociosphere
git pull --ff-only
make terraform-workspace-mesh-plan-safe
```

## Override fabric repo location

```bash
make FABRIC_REPO=/path/to/prophet-platform-fabric-mlops-ts-suite terraform-workspace-mesh-plan-safe
```

## Available proxy targets

```text
doctor-workspace-ops
validate-workspace-prototype
validate-workspace-mesh
validate-workspace-all
terraform-workspace-mesh-init
terraform-workspace-mesh-fmt
terraform-workspace-mesh-validate
terraform-workspace-mesh-plan
terraform-workspace-mesh-plan-out
terraform-workspace-mesh-plan-json
validate-workspace-mesh-plan-json
terraform-workspace-mesh-plan-safe
tofu-workspace-mesh-init
tofu-workspace-mesh-fmt
tofu-workspace-mesh-validate
tofu-workspace-mesh-plan
tofu-workspace-mesh-plan-safe
```

## Boundary

These targets do not duplicate the mesh in Sociosphere. They preserve the fabric repo as the implementation authority while making Sociosphere a convenient operational launcher.
