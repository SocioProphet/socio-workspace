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


# Dockerfile only treats `#` as a comment at the START of a line. A `#` after a non-shell
# instruction (COPY/ADD/FROM/…) is parsed as an ARGUMENT, not a comment — buildx then chokes
# (`COPY … # the responder's core` → "unexpected end of statement looking for matching
# single-quote"). This shipped and the build had NEVER succeeded via buildx; the other tests
# here only regex the COPY *source*, so they passed anyway. This guard catches the class.
_NON_SHELL_INSTRUCTIONS = ("COPY", "ADD", "FROM", "WORKDIR", "ENV", "EXPOSE", "ARG",
                           "LABEL", "USER", "ENTRYPOINT", "CMD", "VOLUME", "STOPSIGNAL")


def test_no_inline_comments_on_dockerfile_instructions():
    offenders = []
    for n, line in enumerate(DOCKERFILE.read_text("utf-8").splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.split()[0].upper() in _NON_SHELL_INSTRUCTIONS and "#" in s:
            offenders.append(f"L{n}: {s}")
    assert not offenders, (
        "Dockerfile has inline `#` comments on non-shell instructions — Dockerfile does NOT "
        "strip these, so buildx parses them as arguments and the build fails. Move the comment "
        f"to its own line above the instruction:\n  " + "\n  ".join(offenders)
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
