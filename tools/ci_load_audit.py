#!/usr/bin/env python3
"""Audit CI fan-out: why a 2-file PR spawns ~30 jobs, and how to cut it SAFELY.

The estate's runners aren't broken — they're saturated. Every pull_request fires ~55 workflows
regardless of what changed (a Python change runs Rust CodeQL, geospatial-standards, ui-check…). This
tool quantifies that and proposes path filters — but it accounts for the trap that makes naive path
filters dangerous: a REQUIRED status check that gets path-filtered out never runs, so the PR is
blocked forever (worse than slow). So it splits recommendations into:

  * SAFE       — non-required workflows with no path filter: add a `paths:` filter, skipping is free.
  * NEEDS-CARE — required checks: cannot be naively filtered (would block merges). De-duplicate, or
                 add a companion skip-job that reports the same check name green when paths don't match.
  * DUPLICATE  — the same check-name produced by multiple workflows: pure waste, safe to consolidate.

Read-only. It changes nothing — it hands a human a reviewable plan (CI gates are control-of-controls;
you don't auto-edit them). Run: python3 tools/ci_load_audit.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parents[1]
_WF = _ROOT / ".github" / "workflows"

# domain -> (keywords in the workflow text, the path globs a change of that domain touches)
DOMAINS = {
    "rust":   (["cargo", "rustup", "rustc", "clippy"], ["**/*.rs", "**/Cargo.toml", "**/Cargo.lock"]),
    "python": (["pytest", "pip install", "python -m", "requirements", "ruff", "flake8"],
               ["automation/**", "tests/**", "tools/**", "engines/**", "**/*.py"]),
    "ui":     (["npm ", "pnpm", "yarn", "vite", "vue-tsc", "eslint", "node "],
               ["client-vue/**", "ui/**", "**/*.vue", "**/*.ts", "**/*.tsx"]),
    "go":     (["go test", "go build", "go vet", "golangci"], ["**/*.go", "**/go.mod"]),
    "iac":    (["terraform", "tofu", "kubectl", "helm ", "kustomize"],
               ["deploy/**", "infra/**", "**/*.tf", "**/*.yaml"]),
}


def _on(data):
    on = data.get("on", data.get(True))  # YAML parses bare `on:` as the boolean True
    return on if isinstance(on, dict) else ({k: None for k in on} if isinstance(on, list) else {})


def _pr_paths(on) -> str:
    pr = on.get("pull_request")
    if isinstance(pr, dict) and (pr.get("paths") or pr.get("paths-ignore")):
        return "yes"
    return "no"


def classify(text: str) -> str:
    for dom, (keys, _globs) in DOMAINS.items():
        if any(k in text for k in keys):
            return dom
    return "generic"


def required_checks() -> set:
    try:
        out = subprocess.run(
            ["gh", "api", "repos/SocioProphet/sociosphere/branches/main/protection/required_status_checks"],
            capture_output=True, text=True, cwd=str(_ROOT), timeout=20)
        if out.returncode == 0:
            return set(json.loads(out.stdout).get("contexts", []))
    except Exception:
        pass
    return set()


def main():
    req = required_checks()
    pr_wfs, job_total = [], 0
    by_domain = {}
    check_names = {}  # job/check name -> [workflow]
    for f in sorted(_WF.glob("*.y*ml")):
        try:
            data = yaml.safe_load(f.read_text("utf-8")) or {}
        except yaml.YAMLError:
            continue
        on = _on(data)
        if "pull_request" not in on:
            continue
        jobs = data.get("jobs", {}) or {}
        text = f.read_text("utf-8")
        dom = classify(text)
        pr_wfs.append((f.name, dom, _pr_paths(on), len(jobs)))
        job_total += len(jobs)
        by_domain[dom] = by_domain.get(dom, 0) + len(jobs)
        for jname, jspec in jobs.items():
            nm = (jspec or {}).get("name", jname) if isinstance(jspec, dict) else jname
            check_names.setdefault(str(nm), []).append(f.name)

    print("=" * 78)
    print("CI LOAD AUDIT — why every PR floods the runners")
    print("=" * 78)
    print(f"pull_request workflows: {len(pr_wfs)}   |   jobs spawned per PR: ~{job_total}   |   "
          f"required checks: {len(req) or 'unknown'}")
    nofilter = [w for w in pr_wfs if w[2] == "no"]
    print(f"workflows with NO path filter (fire on EVERY change): {len(nofilter)} / {len(pr_wfs)}\n")

    print("JOBS PER PR BY DOMAIN (a python change only needs python + generic):")
    for dom, n in sorted(by_domain.items(), key=lambda kv: -kv[1]):
        waste = "  <- wasted on a python-only PR" if dom in ("rust", "go", "ui", "iac") else ""
        print(f"   {dom:8} {n:>3} jobs{waste}")
    wasted = sum(n for d, n in by_domain.items() if d in ("rust", "go", "ui", "iac"))
    print(f"   -> a python-only PR could skip ~{wasted} of ~{job_total} jobs "
          f"({100*wasted//max(job_total,1)}% less runner load)\n")

    print("DUPLICATE check names (same gate from multiple workflows = pure waste):")
    dupes = {k: v for k, v in check_names.items() if len(v) > 1}
    for nm, wfs in sorted(dupes.items(), key=lambda kv: -len(kv[1]))[:8]:
        print(f"   '{nm}' x{len(wfs)}: {', '.join(wfs)}")
    if not dupes:
        print("   (none)")

    print("\nRECOMMENDATION (safe vs needs-care — the required-check trap):")
    safe = [w for w in nofilter if w[0].replace(".yml", "").replace(".yaml", "") not in req
            and not any(w[0] in v or w[1] in " ".join([w[0]]) for v in [req])]
    safe_domain = [w for w in nofilter if w[1] in ("rust", "go", "ui", "iac")]
    print(f"   SAFE now — add `paths:` to the {len(safe_domain)} domain-specific workflows that")
    print("     obviously don't apply to most changes (rust/go/ui/iac). Skipping a NON-required")
    print("     check is free; a required one would block forever, so check each against the list.")
    for w in safe_domain[:12]:
        globs = ", ".join(DOMAINS.get(w[1], ([], ["<pick>"]))[1][:2])
        req_flag = " (REQUIRED — needs a skip-job, not a bare filter)" if w[0].replace('.yml','') in req else ""
        print(f"       {w[0]:42} paths: [{globs}]{req_flag}")
    print("\n   The single biggest win: give each domain workflow a `paths:` filter so a change only")
    print("   pays for the CI it actually needs. Est. ~{}% fewer jobs per PR.".format(100*wasted//max(job_total,1)))
    print("=" * 78)


if __name__ == "__main__":
    sys.exit(main())
