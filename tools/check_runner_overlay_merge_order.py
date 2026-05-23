#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys
import tempfile

RUNNER_DIR = Path(__file__).resolve().parent / "runner"
sys.path.insert(0, str(RUNNER_DIR))

from manifest_layers import load_layered_manifest  # noqa: E402


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        write(
            root / "manifest" / "workspace.toml",
            """
            [workspace]
            name = "base"
            version = "0.1"

            [[repos]]
            name = "base_repo"
            role = "component"
            url = "https://example.invalid/base"
            ref = "main"
            local_path = "components/base_repo"

            [[repos]]
            name = "shared_repo"
            role = "component"
            url = "https://example.invalid/base-shared"
            ref = "main"
            local_path = "components/shared_repo"
            """,
        )
        write(
            root / "manifest" / "active-spine.repos.toml",
            """
            [[repos]]
            name = "overlay_repo"
            role = "component"
            url = "https://example.invalid/overlay"
            ref = "main"
            local_path = "components/overlay_repo"

            [[repos]]
            name = "shared_repo"
            role = "component"
            url = "https://example.invalid/overlay-shared"
            ref = "main"
            local_path = "components/shared_repo"
            """,
        )
        write(
            root / "manifest" / "overrides.toml",
            """
            [workspace]
            name = "override"

            [[repos]]
            name = "shared_repo"
            role = "component"
            url = "https://example.invalid/override-shared"
            ref = "main"
            local_path = "components/shared_repo"
            """,
        )

        data = load_layered_manifest(root)
        repos = {repo["name"]: repo for repo in data.get("repos", [])}

        checks = {
            "base_repo present": "base_repo" in repos,
            "overlay_repo present": "overlay_repo" in repos,
            "override workspace wins": data.get("workspace", {}).get("name") == "override",
            "override repo wins": repos.get("shared_repo", {}).get("url") == "https://example.invalid/override-shared",
        }

    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        for name in failed:
            print(f"ERR: merge-order check failed: {name}", file=sys.stderr)
        return 1

    print("OK: manifest merge order is workspace -> committed overlays -> overrides")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
