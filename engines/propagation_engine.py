"""Propagation engine for dependency queries and cascade simulation."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_DIR = ROOT / "registry"
METRICS_DIR = ROOT / "metrics"
DEP_GRAPH_FILE = REGISTRY_DIR / "dependency-graph.yaml"
PROP_RULES_FILE = REGISTRY_DIR / "change-propagation-rules.yaml"
PROPAGATION_LOG = METRICS_DIR / "propagation-log.jsonl"


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists() or yaml is None:
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _normalize_repo_id(repo_id: str | None) -> str | None:
    """Normalize registry identifiers for cross-file lookups.

    Some registry files use mixed case or underscore variants for the same repo.
    Normalizing here keeps dependency and propagation lookups stable across those
    schema variants without changing the on-disk source names. Examples:
    ``TriTRPC`` becomes ``tritrpc`` and ``socioprophet_integration`` becomes
    ``socioprophet-integration``.
    """
    if repo_id is None:
        return None
    return str(repo_id).strip().replace("_", "-").lower()


def get_dependents(repo_name: str, dep_graph: dict[str, Any]) -> list[str]:
    """Return dependent repos from webhook-style dependency graph payload."""
    entry = dep_graph.get("dependencies", {}).get(repo_name, {})
    deps = entry.get("dependents", [])
    result: list[str] = []
    for d in deps:
        name = d.get("name") if isinstance(d, dict) else str(d)
        if name and name != "all-repos":
            result.append(name)
    return result


def get_propagation_rules(repo_name: str, rules: dict[str, Any]) -> dict[str, Any]:
    """Legacy `propagation_rules: {repo: {on_main_merge: ...}}` shape.

    registry/change-propagation-rules.yaml has NOT used this shape for a long time --
    it is a top-level `rules:` list keyed on `trigger.repo`. So this returned {} for
    every repository in the estate, and `propagate()` then wrote a log line saying
    "status": "success" with an empty actions list. The propagation webhook has never
    propagated anything, for any repo, and said it succeeded each time.

    Kept only so a caller still passing the old file shape keeps working; propagate()
    now reads the modern rules through PropagationEngine and falls back to this.
    """
    return rules.get("propagation_rules", {}).get(repo_name, {}).get("on_main_merge", {})


def _log_event(event: dict[str, Any]) -> None:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    with PROPAGATION_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event) + "\n")


def simulate_automation(action_type: str, targets: list[str], repo: str) -> dict[str, Any]:
    """Records an action as "triggered" without triggering it. DRY RUN ONLY.

    The name is the bug: this was the only thing propagate() ever called, so a cascade
    was "triggered" in the log and nowhere else. Real dispatch is _dispatch().
    """
    return {
        "action": action_type,
        "targets": targets,
        "triggered_by": repo,
        "status": "simulated",
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    }


ORG = os.environ.get("SOCIOSPHERE_ORG", "SocioProphet")

#: Opt-in for repository_dispatch, which needs Contents: Write on the target.
ALLOW_DISPATCH = os.environ.get("PROPAGATION_ALLOW_DISPATCH", "").lower() in ("1", "true", "yes")

#: Marks issues this engine opened, so a repeated merge updates rather than duplicates.
PROPAGATION_MARKER = "<!-- sociosphere:propagation -->"


# ── SCM backend ──────────────────────────────────────────────────────────────
#
# The dispatcher needs exactly three verbs: list open issue titles, create an issue,
# and fire a repository dispatch. Everything else about propagation is registry maths.
#
# They are behind a backend because the estate is migrating to a sovereign Gitea and the
# engine should not have to be rewritten when that lands -- the seam is the point. This
# is deliberately NOT a `gh` clone: the estate rule is a small wrapper over the verbs
# actually used, because a hundred-command compatibility layer drifts and then lies
# exactly where the two APIs diverge. Three verbs is maintainable.
#
# GitHub remains the default and is the only backend exercised today. The mirrors in
# Gitea are PULL mirrors (read-only; a push returns 403), so GitHub is still the only
# writable copy and sovereign cannot yet be canonical. The Gitea backend below is
# written against the documented REST API but is UNVERIFIED against a live instance --
# it is the seam being ready, not a claim that the cutover is done.

SCM_BACKEND = os.environ.get("SCM_BACKEND", "github").lower()
GITEA_URL = os.environ.get("GITEA_URL", "").rstrip("/")
GITEA_TOKEN = os.environ.get("GITEA_TOKEN", "")


def _gh(args: list[str], *, check: bool = True) -> tuple[int, str]:
    proc = subprocess.run(["gh", *args], capture_output=True, text=True)
    if check and proc.returncode != 0:
        return proc.returncode, proc.stderr.strip()
    return proc.returncode, proc.stdout.strip()


def _gitea(method: str, path: str, payload: dict[str, Any] | None = None) -> tuple[int, str]:
    """Minimal Gitea REST call. Fails LOUDLY when unconfigured rather than returning
    an empty result that would read as 'nothing there'."""
    import urllib.error
    import urllib.request

    if not GITEA_URL or not GITEA_TOKEN:
        return 1, ("SCM_BACKEND=gitea but GITEA_URL/GITEA_TOKEN are unset; refusing to "
                   "report an empty result that would look like 'nothing found'")
    req = urllib.request.Request(
        f"{GITEA_URL}/api/v1{path}", method=method,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Authorization": f"token {GITEA_TOKEN}",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return 0, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:400]
    except Exception as e:  # network, DNS, TLS
        return 1, str(e)[:400]


def scm_open_issue_titles(repo: str) -> list[str] | None:
    """Open issue titles in ``repo``. None means the lookup FAILED, which is not the
    same as an empty list -- treating a failed lookup as 'no duplicates' would reopen
    the same issue on every run."""
    if SCM_BACKEND == "gitea":
        rc, out = _gitea("GET", f"/repos/{ORG}/{repo}/issues?state=open&limit=50")
    else:
        rc, out = _gh(["issue", "list", "--repo", f"{ORG}/{repo}", "--state", "open",
                       "--json", "title", "--limit", "50"], check=False)
    if rc != 0 or not out:
        return None
    try:
        return [i.get("title", "") for i in json.loads(out)]
    except json.JSONDecodeError:
        return None


def scm_create_issue(repo: str, title: str, body: str) -> tuple[int, str]:
    if SCM_BACKEND == "gitea":
        return _gitea("POST", f"/repos/{ORG}/{repo}/issues",
                      {"title": title, "body": body})
    return _gh(["issue", "create", "--repo", f"{ORG}/{repo}",
                "--title", title, "--body", body], check=False)


def scm_dispatch(repo: str, payload: dict[str, str]) -> tuple[int, str]:
    if SCM_BACKEND == "gitea":
        # Gitea has no repository_dispatch equivalent; its workflow_dispatch is not the
        # same shape. Saying so beats emitting a call that 404s and reads as a transient.
        return 1, ("gitea has no repository_dispatch equivalent; convert the rule to "
                   "`notify` or run the target's workflow directly")
    args = ["api", f"repos/{ORG}/{repo}/dispatches", "-X", "POST",
            "-f", "event_type=sociosphere-propagation"]
    for k, v in sorted(payload.items()):
        args += ["-f", f"client_payload[{k}]={v}"]
    return _gh(args, check=False)


def _existing_issue(target: str, title: str) -> str | None:
    """An open issue with this exact title, if one is already there.

    Without this, every merge to a busy trigger repo opens another copy of the same
    notification. An actuator that spams is switched off within a week, and then the
    estate is back where it started.
    """
    titles = scm_open_issue_titles(target)
    if titles is None:
        # Lookup failed. Returning None here would mean "no duplicate", so the caller
        # would open another copy on every run -- the spam that gets an actuator muted.
        return "unknown"
    return "duplicate" if title in titles else None


def _dispatch(step: dict[str, Any], source: str, ref: str) -> dict[str, Any]:
    """Actually act on one cascade step. Returns what happened, honestly."""
    target = step["repo"]
    action = step.get("action", "notify")
    rule = step.get("source_rule", "?")
    result: dict[str, Any] = {"repo": target, "action": action, "rule": rule,
                              "depth": step.get("depth")}

    if action == "trigger_ci":
        # repository_dispatch requires CONTENTS: WRITE on the target -- the ability to
        # push to someone else's repo. A governance beacon's job is to tell people, not
        # to change their repos, so this is refused by default rather than merely
        # unfunded by the token.
        #
        # Relying on token scope alone would make the read-only posture a property of
        # how the App happens to be granted, and a later over-grant would silently turn
        # writes back on with nobody deciding to. Refusing here means the posture holds
        # regardless of the credential, and the credential is a second line of defence.
        if not ALLOW_DISPATCH:
            result["status"] = "blocked_no_dispatch"
            result["detail"] = (
                "trigger_ci needs Contents: Write on the target; refused because "
                "PROPAGATION_ALLOW_DISPATCH is not set. Change the rule to `notify` if "
                "an issue is enough, or set the flag deliberately.")
            return result
        rc, out = scm_dispatch(target, {"source_repo": source, "rule": rule, "ref": ref})
        result["status"] = "dispatched" if rc == 0 else "failed"
        if rc != 0:
            result["error"] = out
        return result

    title = f"[propagation] {source} changed — {rule}"
    body = (
        f"{PROPAGATION_MARKER}\n\n"
        f"{step.get('message', '')}\n\n"
        f"---\n"
        f"- source: `{source}` @ `{ref}`\n"
        f"- rule: `{rule}` (depth {step.get('depth')})\n"
    )
    if step.get("auto_pr"):
        # Honest about the limit: the rule asks for a PR, and this engine does not know
        # what change to make in the target. It says so rather than claiming a PR.
        body += (f"- the rule requests an automatic PR (`{step.get('pr_title')}`); this "
                 "notification does not open one, because the required change is "
                 "repo-specific\n")
    body += "\nOpened automatically by sociosphere change propagation."

    existing = _existing_issue(target, title)
    if existing == "unknown":
        result["status"] = "skipped_lookup_failed"
        result["detail"] = ("could not list open issues, so a duplicate cannot be ruled "
                            "out; skipping rather than risking a repeat notification")
        return result
    if existing:
        result["status"] = "already_open"
        return result

    rc, out = scm_create_issue(target, title, body)
    result["status"] = "notified" if rc == 0 else "failed"
    result["detail"] = out
    return result


#: How deep a cascade is DISPATCHED, as opposed to computed.
#:
#: Depth 1 is the repos a rule names explicitly, each with a message a human wrote for
#: that seam. Depth 2+ is derived by walking the graph, and every such step carries the
#: generic "Cascade from <hub>". Because sociosphere is a hub, dispatching depth 2 from
#: an interpretability change notifies heller-winters-theorem, yang-mills and two other
#: unrelated maths repos -- with no message explaining why. That is exactly the noise
#: that gets an actuator muted, and a muted actuator returns the estate to silence.
#: The deeper steps are still computed and logged; they are just not sent.
DEFAULT_DISPATCH_DEPTH = 1


def propagate(repo_name: str, ref: str = "refs/heads/main",
              *, execute: bool = False,
              dispatch_depth: int = DEFAULT_DISPATCH_DEPTH) -> int:
    """Fan a merge out to the repos the rules say should hear about it.

    Dry run unless ``execute`` is set: this opens issues and fires repository_dispatch
    in other repositories, which is not something to do as a side effect of importing a
    module or running a validation job.
    """
    if not ref.endswith("/main"):
        print(f"INFO: skipping propagation for non-main ref '{ref}'")
        return 0

    dep_graph = _load_yaml(DEP_GRAPH_FILE)
    dependents = get_dependents(repo_name, dep_graph)

    engine = PropagationEngine()
    engine.load()
    policy = (_load_yaml(PROP_RULES_FILE).get("cascade_policy") or {})
    max_depth = int(policy.get("max_notification_depth", 3))
    steps = engine.compute_cascade(repo_name, max_depth=max_depth)

    event: dict[str, Any] = {
        "repo": repo_name,
        "ref": ref,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "dependents": dependents,
        "references": engine.referrers_of(repo_name),
        "cascade_steps": len(steps),
        "executed": execute,
        "actions_triggered": [],
    }

    if not steps:
        # NOT success. No rule matching a repo is the condition that let a new repo sit
        # in the registry while every merge cascaded to nothing -- reporting it as a
        # successful propagation is how that stayed invisible.
        event["status"] = "no_rule"
        _log_event(event)
        print(f"WARN: no propagation rule triggers on '{repo_name}'. Changes to it "
              f"reach no one. Add a rule to {PROP_RULES_FILE.name}.", file=sys.stderr)
        return 0

    actions_triggered: list[dict[str, Any]] = []
    for step in steps:
        if int(step.get("depth", 1)) > dispatch_depth:
            actions_triggered.append({
                "repo": step["repo"], "action": step.get("action", "notify"),
                "rule": step.get("source_rule"), "depth": step.get("depth"),
                "status": "computed_not_sent",
            })
            continue
        if execute:
            actions_triggered.append(_dispatch(step, repo_name, ref))
            continue
        # A dry run must predict what execution WOULD do. Reporting "simulated" for a
        # trigger_ci that execution will refuse describes a run that cannot happen, and
        # the whole point of the dry mode is to be trusted before the switch is flipped.
        if step.get("action") == "trigger_ci" and not ALLOW_DISPATCH:
            actions_triggered.append({
                "repo": step["repo"], "action": "trigger_ci",
                "rule": step.get("source_rule"), "depth": step.get("depth"),
                "status": "blocked_no_dispatch",
            })
            continue
        actions_triggered.append(
            simulate_automation(step.get("action", "notify"), [step["repo"]], repo_name))

    event["actions_triggered"] = actions_triggered
    failed = [a for a in actions_triggered if a.get("status") == "failed"]
    event["status"] = "failed" if failed else ("executed" if execute else "dry_run")
    _log_event(event)

    verb = "dispatched" if execute else "would dispatch (dry run; pass --execute)"
    print(f"{repo_name} -> {verb} {len(steps)} step(s):")
    for a in actions_triggered:
        tgt = a.get("repo") or (a.get("targets") or ["?"])[0]
        print(f"  [{a.get('status')}] {a.get('action')} -> {tgt}"
              + (f"  ({a['error']})" if a.get("error") else ""))
    if failed:
        print(f"ERROR: {len(failed)} propagation action(s) failed", file=sys.stderr)
        return 1
    return 0


class PropagationEngine:
    """Compute and validate dependency propagation."""

    def __init__(self, registry_dir: str | Path | None = None) -> None:
        self._dir = Path(registry_dir) if registry_dir else REGISTRY_DIR
        self._edges: list[dict[str, Any]] = []
        self._rules: list[dict[str, Any]] = []
        self._dep_levels: dict[str, int] = {}
        self._adjacency: dict[str, list[str]] = defaultdict(list)
        self._reverse_adjacency: dict[str, list[str]] = defaultdict(list)
        #: Governance/provenance edges from lane packs that declare
        #: does_not_create_runtime_dependency. Recorded and traversable, but kept out of
        #: cycle detection and dependency levels -- see load().
        self._reference_edges: list[dict[str, Any]] = []
        self._ref_adjacency: dict[str, list[str]] = defaultdict(list)
        self._ref_reverse_adjacency: dict[str, list[str]] = defaultdict(list)
        self._loaded = False

    def load(self) -> None:
        dep_raw = _load_yaml(self._dir / "dependency-graph.yaml")
        self._edges = []

        def add_edge(src: str | None, dst: str | None, edge_type: str = "depends_on") -> None:
            normalized_src = _normalize_repo_id(src)
            normalized_dst = _normalize_repo_id(dst)
            if not normalized_src or not normalized_dst:
                return
            if normalized_dst not in self._adjacency[normalized_src]:
                self._adjacency[normalized_src].append(normalized_dst)
            if normalized_src not in self._reverse_adjacency[normalized_dst]:
                self._reverse_adjacency[normalized_dst].append(normalized_src)
            self._edges.append({"from": normalized_src, "to": normalized_dst, "type": edge_type})

        for edge in dep_raw.get("edges", []):
            if not isinstance(edge, dict):
                continue
            add_edge(edge.get("from"), edge.get("to"), str(edge.get("type", "depends_on")))

        # Additive edge packs. Lanes record their edges in registry/*-dependency-edges.yaml
        # specifically to avoid rewriting the large aggregate file -- but this engine only
        # ever read the aggregate, so every pack was dark: 17 governed edges across the
        # interpretability-harness and lawful-learning lanes existed on disk, were
        # validated by their own CI, and reached nothing. A registry fragment nothing
        # loads is a document, not an edge.
        #
        # They are loaded as REFERENCE edges, not dependencies, because both packs
        # declare `does_not_create_runtime_dependency` and `does_not_change_dependency_
        # _graph_aggregate` in their own non_claims. Folding them into the dependency
        # adjacency would contradict the thing the file says about itself -- and does so
        # visibly: it introduces a sociosphere -> superconscious -> systems-learning-loops
        # -> sociosphere cycle out of what is really "sociosphere RECORDS superconscious
        # as doctrine owner". Reference edges are traversable and reportable; they do not
        # drive cycle detection or dependency levels, and notification reach for these
        # lanes comes from explicit propagation rules instead.
        #
        # Deferred/pre-promotion edges are skipped entirely: they describe a path a lane
        # INTENDS to take, and traversing one would assert a relationship that does not
        # exist yet.
        for pack_path in sorted(self._dir.glob("*-dependency-edges.yaml")):
            pack = _load_yaml(pack_path)
            non_claims = set(pack.get("non_claims") or [])
            as_dependency = "does_not_create_runtime_dependency" not in non_claims
            for edge in pack.get("edges", []):
                if not isinstance(edge, dict):
                    continue
                if str(edge.get("state", "active")).lower() not in ("active", "in_use"):
                    continue
                src = _normalize_repo_id(edge.get("from"))
                dst = _normalize_repo_id(edge.get("to"))
                if not src or not dst:
                    continue
                etype = str(edge.get("type", "depends_on"))
                if as_dependency:
                    add_edge(src, dst, etype)
                    continue
                if dst not in self._ref_adjacency[src]:
                    self._ref_adjacency[src].append(dst)
                if src not in self._ref_reverse_adjacency[dst]:
                    self._ref_reverse_adjacency[dst].append(src)
                self._reference_edges.append({
                    "from": src, "to": dst, "type": etype,
                    "lane": edge.get("lane"), "pack": pack_path.name,
                })

        for repo_name, entry in dep_raw.get("dependencies", {}).items():
            normalized_repo = _normalize_repo_id(repo_name)
            if not normalized_repo or not isinstance(entry, dict):
                continue
            for dep in entry.get("depends_on", []):
                dep_name = dep.get("name") if isinstance(dep, dict) else dep
                dep_type = dep.get("type", "depends_on") if isinstance(dep, dict) else "depends_on"
                add_edge(normalized_repo, dep_name, str(dep_type))
            for dependent in entry.get("dependents", []):
                dependent_name = dependent.get("name") if isinstance(dependent, dict) else dependent
                dep_type = dependent.get("type", "dependent") if isinstance(dependent, dict) else "dependent"
                add_edge(dependent_name, normalized_repo, str(dep_type))

        for level_str, repos in dep_raw.get("dependency_levels", {}).items():
            level = -1 if level_str == "archived" else int(level_str)
            for repo_id in repos:
                normalized_repo = _normalize_repo_id(repo_id)
                if normalized_repo:
                    self._dep_levels[normalized_repo] = level

        rules_raw = _load_yaml(self._dir / "change-propagation-rules.yaml")
        normalized_rules: list[dict[str, Any]] = []
        for rule in rules_raw.get("rules", []):
            if not isinstance(rule, dict):
                continue
            trigger_repo = rule.get("trigger", {}).get("repo")
            if trigger_repo is None:
                trigger_repo = rule.get("trigger_repo")
            normalized_trigger = _normalize_repo_id(trigger_repo)
            if not normalized_trigger:
                continue

            propagate_to = rule.get("propagate_to")
            if propagate_to is None:
                propagate_to = []
                for cascade in rule.get("cascades", []):
                    if not isinstance(cascade, dict):
                        continue
                    target = _normalize_repo_id(cascade.get("target"))
                    if not target:
                        continue
                    propagate_to.append(
                        {
                            "repo": target,
                            "action": cascade.get("action", "notify"),
                            "message": cascade.get("reason", ""),
                            "auto_pr": cascade.get("auto_pr", False),
                            "pr_title": cascade.get("pr_title", ""),
                        }
                    )
            else:
                normalized_targets: list[dict[str, Any]] = []
                for target in propagate_to:
                    if not isinstance(target, dict):
                        continue
                    repo = _normalize_repo_id(target.get("repo"))
                    if not repo:
                        continue
                    normalized_target = dict(target)
                    normalized_target["repo"] = repo
                    normalized_targets.append(normalized_target)
                propagate_to = normalized_targets

            normalized_rules.append(
                {
                    **rule,
                    "trigger": {"repo": normalized_trigger},
                    "propagate_to": propagate_to,
                }
            )

        for repo_name, rule in rules_raw.get("propagation_rules", {}).items():
            if not isinstance(rule, dict):
                continue
            trigger_repo = _normalize_repo_id(repo_name)
            on_main_merge = rule.get("on_main_merge", {})
            if not trigger_repo or not isinstance(on_main_merge, dict):
                continue
            propagate_to = []
            for action in on_main_merge.get("automation", []):
                if not isinstance(action, dict):
                    continue
                for target in action.get("targets", []):
                    normalized_target = _normalize_repo_id(target)
                    if normalized_target:
                        propagate_to.append(
                            {
                                "repo": normalized_target,
                                "action": action.get("type", "notify"),
                                "message": on_main_merge.get("trigger", ""),
                                "auto_pr": False,
                                "pr_title": "",
                            }
                        )
            normalized_rules.append(
                {
                    "id": f"legacy-{trigger_repo}",
                    "trigger": {"repo": trigger_repo},
                    "propagate_to": propagate_to,
                    "max_cascade_depth": on_main_merge.get("max_cascade_depth"),
                }
            )
        self._rules = normalized_rules
        self._loaded = True

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()

    def dependencies_of(self, repo_id: str) -> list[str]:
        self._ensure_loaded()
        return list(self._adjacency.get(_normalize_repo_id(repo_id) or repo_id, []))

    def dependents_of(self, repo_id: str) -> list[str]:
        self._ensure_loaded()
        return list(self._reverse_adjacency.get(_normalize_repo_id(repo_id) or repo_id, []))

    def references_of(self, repo_id: str) -> list[str]:
        """Governance/provenance edges out of this repo, from lane packs.

        Separate from dependencies_of by design: these are relationships the estate
        RECORDS, not ones a build or runtime consumes. Blast-radius analysis wants both;
        cycle detection wants only the latter.
        """
        self._ensure_loaded()
        return list(self._ref_adjacency.get(_normalize_repo_id(repo_id) or repo_id, []))

    def referrers_of(self, repo_id: str) -> list[str]:
        self._ensure_loaded()
        return list(self._ref_reverse_adjacency.get(_normalize_repo_id(repo_id) or repo_id, []))

    def reference_edges(self) -> list[dict[str, Any]]:
        self._ensure_loaded()
        return list(self._reference_edges)

    def dependency_level(self, repo_id: str) -> int | None:
        self._ensure_loaded()
        return self._dep_levels.get(_normalize_repo_id(repo_id) or repo_id)

    def get_rule(self, repo_id: str) -> dict[str, Any] | None:
        self._ensure_loaded()
        normalized_repo = _normalize_repo_id(repo_id)
        for rule in self._rules:
            if rule.get("trigger", {}).get("repo") == normalized_repo:
                return rule
        return None

    def all_rules(self) -> list[dict[str, Any]]:
        self._ensure_loaded()
        return list(self._rules)

    def all_graph_nodes(self) -> set[str]:
        self._ensure_loaded()
        nodes: set[str] = set()
        for edge in self._edges:
            nodes.add(edge["from"])
            nodes.add(edge["to"])
        return nodes

    def compute_cascade(self, changed_repo: str, max_depth: int = 3) -> list[dict[str, Any]]:
        self._ensure_loaded()
        changed_repo = _normalize_repo_id(changed_repo) or changed_repo
        results: list[dict[str, Any]] = []
        visited: set[str] = {changed_repo}
        queue: deque[tuple[str, int, str]] = deque()

        rule = self.get_rule(changed_repo)
        seed_targets: list[dict[str, Any]] = list(rule.get("propagate_to", [])) if rule else []
        rule_max = rule.get("max_cascade_depth") if rule else None
        if isinstance(rule_max, int):
            max_depth = min(max_depth, rule_max)

        explicit = {t.get("repo") for t in seed_targets}
        for dep in self.dependents_of(changed_repo):
            if dep not in explicit:
                seed_targets.append({"repo": dep, "action": "notify", "message": f"{changed_repo} changed"})

        for target in seed_targets:
            repo = target.get("repo")
            if not repo or repo in visited:
                continue
            visited.add(repo)
            queue.append((repo, 1, rule.get("id", "dependency_graph") if rule else "dependency_graph"))
            results.append(
                {
                    "depth": 1,
                    "repo": repo,
                    "action": target.get("action", "notify"),
                    "message": target.get("message", ""),
                    "auto_pr": target.get("auto_pr", False),
                    "pr_title": target.get("pr_title", ""),
                    "source_rule": rule.get("id", "dependency_graph") if rule else "dependency_graph",
                }
            )

        while queue:
            current, depth, source_rule = queue.popleft()
            if depth >= max_depth:
                continue
            for downstream in self.dependents_of(current):
                if downstream in visited:
                    continue
                visited.add(downstream)
                nd = depth + 1
                queue.append((downstream, nd, source_rule))
                results.append(
                    {
                        "depth": nd,
                        "repo": downstream,
                        "action": "notify",
                        "message": f"Cascade from {current}",
                        "auto_pr": False,
                        "pr_title": "",
                        "source_rule": source_rule,
                    }
                )

        results.sort(key=lambda x: x["depth"])
        return results

    def detect_cycles(self) -> list[list[str]]:
        self._ensure_loaded()
        visited: set[str] = set()
        stack: set[str] = set()
        path: list[str] = []
        cycles: list[list[str]] = []

        def dfs(node: str) -> None:
            visited.add(node)
            stack.add(node)
            path.append(node)
            for neighbor in self._adjacency.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in stack:
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    if cycle not in cycles:
                        cycles.append(cycle)
            stack.remove(node)
            path.pop()

        for node in list(self.all_graph_nodes()):
            if node not in visited:
                dfs(node)
        return cycles

    def merge_order(self) -> list[str]:
        self._ensure_loaded()
        by_level = sorted(self._dep_levels.items(), key=lambda kv: kv[1])
        return [repo for repo, _level in by_level if _level >= 0]


def main() -> int:
    parser = argparse.ArgumentParser(description="PropagationEngine CLI")
    parser.add_argument("cmd", choices=["cascade", "cycles", "merge-order", "nodes", "webhook"])
    parser.add_argument("--repo", default=None)
    parser.add_argument("--ref", default="refs/heads/main")
    parser.add_argument("--max-depth", type=int, default=3)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument(
        "--execute", action="store_true",
        help="actually open issues and fire repository_dispatch in target repos. "
             "Without it `webhook` is a dry run -- this reaches into other "
             "repositories, so it is never the default.")
    parser.add_argument(
        "--dispatch-depth", type=int, default=DEFAULT_DISPATCH_DEPTH,
        help="how deep to actually SEND. Deeper steps are still computed and "
             "logged as computed_not_sent.")
    args = parser.parse_args()

    if args.cmd == "webhook":
        if not args.repo:
            print("ERROR: --repo is required", file=sys.stderr)
            return 2
        return propagate(args.repo, args.ref, execute=args.execute,
                         dispatch_depth=args.dispatch_depth)

    engine = PropagationEngine()
    engine.load()

    if args.cmd == "cycles":
        cycles = engine.detect_cycles()
        if cycles:
            for cycle in cycles:
                print(" -> ".join(cycle), file=sys.stderr)
            return 1
        print("OK: no cycles detected")
        return 0

    if args.cmd == "merge-order":
        order = engine.merge_order()
        if args.format == "json":
            print(json.dumps(order, indent=2))
        else:
            for repo in order:
                print(repo)
        return 0

    if args.cmd == "nodes":
        nodes = sorted(engine.all_graph_nodes())
        if args.format == "json":
            print(json.dumps(nodes, indent=2))
        else:
            for node in nodes:
                print(node)
        return 0

    if not args.repo:
        print("ERROR: --repo is required for cascade", file=sys.stderr)
        return 2
    cascade = engine.compute_cascade(args.repo, max_depth=args.max_depth)
    if args.format == "json":
        print(json.dumps(cascade, indent=2))
    else:
        for item in cascade:
            print(f"d{item['depth']} {item['repo']} [{item['action']}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
