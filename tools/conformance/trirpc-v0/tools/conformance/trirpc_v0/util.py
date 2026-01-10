from __future__ import annotations
from pathlib import Path


def find_repo_root(start: Path) -> Path:
    """
    Find the repository root that contains schemas/ and a likely root marker.
    Falls back to the nearest ancestor with schemas/.
    """
    start = start.resolve()
    for d in [start, *start.parents]:
        if (d / "schemas").is_dir() and (
            (d / ".git").exists()
            or (d / "pyproject.toml").exists()
            or (d / "WORKSPACE.yaml").exists()
        ):
            return d
    for d in [start, *start.parents]:
        if (d / "schemas").is_dir():
            return d
    return start.parents[0]
