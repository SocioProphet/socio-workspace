"""The shared reasoning runtime is domain-agnostic and genuinely liftable (convergence step 3).

The core claim of step 3 is that the reasoning runtime does NOT depend on any sociosphere-
specific detector/executor/engine — so it can be lifted into another repo (a future Debater 2.0
build) the way the kernel already is. This asserts that boundary with teeth, in a fresh
interpreter (so imports from other tests can't mask a leak).
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_DOMAIN_PREFIXES = ("automation.detectors", "automation.executors", "engines")


def test_importing_the_runtime_pulls_no_domain_modules():
    code = (
        "import automation.reasoning, sys;"
        "leaked=[m for m in sys.modules if m.startswith("
        f"{_DOMAIN_PREFIXES!r})];"
        "assert not leaked, 'reasoning runtime leaked domain modules: '+repr(leaked);"
        "print('DECOUPLED')"
    )
    r = subprocess.run([sys.executable, "-c", code], cwd=str(ROOT), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "DECOUPLED" in r.stdout


def test_public_api_is_complete():
    from automation import reasoning
    for name in ("decide_composed", "compose_evidence", "effective_law", "run_once",
                 "Suppressor", "fingerprint", "stamp", "epistemic_level_for",
                 "ResponsePolicy", "DEFAULT_POLICY", "load_policy",
                 "collect_metrics", "render_prometheus", "alerts", "analyze_outcomes"):
        assert hasattr(reasoning, name), f"reasoning runtime missing {name}"


def test_runtime_actually_reasons_through_the_public_api():
    from automation import reasoning
    # a domain supplies evidence-bearing beacons; the runtime composes + grades them
    beacons = [{"kind_class": "mirror_drift", "system": "x", "evidence": {"signal": True}}] * 3
    r = reasoning.decide_composed(beacons)
    assert r["action"] == "auto_fix"                 # three weak signals composed
    assert r["epistemic_level"] in reasoning.EPISTEMIC_LEVELS
    assert r["content_sha256"].startswith("sha256:")  # stamped with the canonical envelope
