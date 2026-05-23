from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import tomllib  # py>=3.11
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # py<3.11 fallback

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_DIR = ROOT / "manifest"
MANIFEST_PATH = MANIFEST_DIR / "workspace.toml"
OVERRIDES_PATH = MANIFEST_DIR / "overrides.toml"
COMMITTED_OVERLAY_GLOB = "*.repos.toml"


def load_toml(path: Path) -> dict[str, Any]:
    return tomllib.loads(path.read_text("utf-8"))


def committed_overlay_paths(root: Path = ROOT) -> list[Path]:
    manifest_dir = root / "manifest"
    return sorted(
        path
        for path in manifest_dir.glob(COMMITTED_OVERLAY_GLOB)
        if path.name not in {"workspace.toml", "overrides.toml"}
    )


def merge_manifest_layer(base: dict[str, Any], layer: dict[str, Any]) -> dict[str, Any]:
    """Merge one manifest layer onto another.

    Merge order is intended to be:
      workspace.toml -> committed *.repos.toml overlays -> local overrides.toml.

    workspace.* keys are shallow-merged, workspace.policy is shallow-merged,
    and repos are merged by repo name with later layers winning.
    """
    if not layer:
        return base

    merged: dict[str, Any] = {k: v for k, v in base.items()}

    merged_workspace = dict(base.get("workspace", {}))
    merged_workspace.update(layer.get("workspace", {}))
    if "policy" in base.get("workspace", {}) or "policy" in layer.get("workspace", {}):
        policy = dict(base.get("workspace", {}).get("policy", {}))
        policy.update(layer.get("workspace", {}).get("policy", {}))
        merged_workspace["policy"] = policy
    if merged_workspace:
        merged["workspace"] = merged_workspace

    by_name: dict[str, dict[str, Any]] = {}
    for repo in base.get("repos", []):
        by_name[repo["name"]] = dict(repo)
    for repo in layer.get("repos", []):
        name = repo["name"]
        current = dict(by_name.get(name, {"name": name}))
        current.update(repo)
        by_name[name] = current
    merged["repos"] = list(by_name.values())
    return merged


def load_layered_manifest(root: Path = ROOT, include_overrides: bool = True) -> dict[str, Any]:
    manifest_dir = root / "manifest"
    data = load_toml(manifest_dir / "workspace.toml")

    for overlay in committed_overlay_paths(root):
        data = merge_manifest_layer(data, load_toml(overlay))

    overrides = manifest_dir / "overrides.toml"
    if include_overrides and overrides.exists():
        data = merge_manifest_layer(data, load_toml(overrides))

    return data
