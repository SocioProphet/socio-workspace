"""Deploy integrity: the image must ship what the loop runs, and the daemon must fail loud.

This is the guard for a real defect: the Dockerfile shipped only automation/ + registry/, but
the loop imports third_party/ (kernel) + engines/ and shells out to tools/. In the built image
every job ImportError'd while the heartbeat stayed green — a control that cannot fail. These
tests assert the image copies every dependency, and that the scheduler preflight refuses to run
when something the loop needs is missing.
"""

from pathlib import Path

import pytest

from automation import scheduler

ROOT = Path(__file__).resolve().parent.parent
DOCKERFILE = ROOT / "deployment" / "Dockerfile"

# Every top-level directory the self-heal loop imports or shells out to.
LOOP_DEPENDENCIES = {"automation", "registry", "third_party", "engines", "tools"}


def _copied_sources() -> set:
    copied = set()
    for line in DOCKERFILE.read_text("utf-8").splitlines():
        s = line.strip()
        if not s.startswith("COPY "):
            continue
        src = s[len("COPY "):].split()[0].rstrip("/")
        copied.add(src)
    return copied


def test_image_copies_every_loop_dependency():
    copied = _copied_sources()
    missing = LOOP_DEPENDENCIES - copied
    assert not missing, (
        f"Dockerfile does not COPY {sorted(missing)} — the loop imports/uses these, so the "
        f"image would ImportError at runtime behind a green heartbeat. Copied: {sorted(copied)}"
    )


def test_required_tools_actually_exist_in_repo():
    # keeps the preflight list honest — a renamed/removed tool fails here, not silently in prod
    for tool in scheduler._REQUIRED_TOOLS:
        assert (ROOT / "tools" / tool).exists(), f"preflight references missing tools/{tool}"


def test_preflight_passes_in_a_complete_tree():
    scheduler.preflight()  # the repo has everything; must not raise


def test_preflight_fails_when_a_tool_is_missing(tmp_path):
    # a tree where imports work but the tools dir is absent -> must refuse to run
    (tmp_path / "tools").mkdir()
    with pytest.raises(RuntimeError, match="preflight FAILED.*tool"):
        scheduler.preflight(root=tmp_path)
