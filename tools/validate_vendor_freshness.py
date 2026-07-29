#!/usr/bin/env python3
"""Validate the vendor freshness register.

Enforces registry/vendor-freshness.yaml against
registry/vendor-freshness.schema.yaml, in four layers:

1. Well-formedness — required fields, enum membership, unique ids, source_id
   referential integrity, and the sub-fields each disposition obliges.

2. Workspace binding — every repo named here must resolve to a repo already
   declared in manifest/workspace.toml, manifest/workspace.lock.json, or a
   committed manifest/*.repos.toml overlay. This is what makes the register an
   extension of the workspace manifest rather than a second, parallel one. A
   repo that is genuinely absent must say so via `workspace_binding: unbound`
   with a reason; silence is an error.

3. Disposition agreement — the freshness state is RECOMPUTED from the recorded
   versions and policy, and a declared disposition that contradicts the computed
   state fails. You may not declare `current` while five releases behind. An
   expired waiver or an overdue remediation fails, so a filed finding cannot
   quietly become the new silence. An upstream observation older than
   policy.observation_max_age_days fails, so the register cannot rot the way the
   artifacts it governs did.

4. On-disk reality — when a consumer repo is materialized locally, every
   declared path must exist and every recorded version and digest must match the
   bytes actually vendored. The same sweep looks for vendored artifacts that are
   NOT declared here; an undeclared artifact is itself a finding.

Layers 1-3 are pure register checks and always run. Layer 4 needs the consumer
repos on disk; where they are absent it is reported as SKIPPED, never as passed.

Consumer repos are located, in order: --repo-root NAME=PATH, the
VENDOR_FRESHNESS_REPO_ROOTS environment variable (NAME=PATH, comma separated),
the materialized workspace path from the manifest, then ~/dev/<name>.

Exit codes: 0 clean, 1 findings.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "registry" / "vendor-freshness.yaml"
MANIFEST_DIR = ROOT / "manifest"
GRAPH_DIR = ROOT / "registry" / "vendor-freshness"
VOCAB = GRAPH_DIR / "vendor-freshness.ttl"

REQUIRED_TOP = {"manifest_id", "status", "schema", "purpose", "policy", "coverage", "sources", "artifacts"}
REQUIRED_SOURCE = {"source_id", "repo", "url", "artifact_kind", "version_scheme", "upstream_ref", "observed_at", "observation_method"}
REQUIRED_ARTIFACT = {"artifact_id", "source_id", "consumer_repo", "consumer_url", "consumer_app", "freshness_policy", "owner", "disposition", "tier"}

STATUS = {"seed", "active", "superseded"}
# Tier grades the severity of UNVERIFIABILITY. It never grades the severity of
# CONTRADICTION: a declared disposition that contradicts the recomputed state is an
# error at every tier, always. Softening that would make the tier field a way to
# opt out of the gate, which is the one thing it must not be.
TIERS = {"foundation", "reference"}
STRICTEST_FIRST = ["foundation", "reference"]
ARTIFACT_KINDS = {"npm-tarball", "json-schema", "rdf-ontology", "source-port", "derived-output"}
VERSION_SCHEMES = {"semver", "digest", "commit"}
POLICIES = {"pin-exact", "track-minor", "track-latest"}
DISPOSITIONS = {"current", "remediation-open", "remediation-required", "waived", "observation-required"}

# computed freshness state -> dispositions that may be declared against it
AGREEMENT = {
    "current": {"current"},
    "stale": {"remediation-open", "remediation-required", "waived"},
    "unknown": {"observation-required", "waived"},
}

SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
TGZ_VERSION_RE = re.compile(r"-(\d+\.\d+\.\d+)\.tgz$")


# ── helpers ──────────────────────────────────────────────────────────────────

def semver(value: str) -> tuple[int, int, int] | None:
    match = SEMVER_RE.match(str(value or ""))
    return (int(match.group(1)), int(match.group(2)), int(match.group(3))) if match else None


def normalize_url(url: str) -> str:
    return str(url or "").strip().rstrip("/").removesuffix(".git").lower()


def parse_date(value: Any) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def workspace_urls() -> set[str]:
    """Every repo URL the workspace manifest, lock, or overlays already declare."""
    urls: set[str] = set()
    for path in sorted(MANIFEST_DIR.glob("*.toml")):
        urls |= {normalize_url(u) for u in re.findall(r'url\s*=\s*"([^"]+)"', path.read_text(encoding="utf-8"))}
    lock = MANIFEST_DIR / "workspace.lock.json"
    if lock.exists():
        data = json.loads(lock.read_text(encoding="utf-8"))
        urls |= {normalize_url(r.get("url", "")) for r in data.get("repos", []) if r.get("url")}
    return {u for u in urls if u}


def resolve_repo_root(repo: str, overrides: dict[str, Path]) -> Path | None:
    """Locate a consumer repo on disk, or None when it is not materialized."""
    short = repo.split("/")[-1]
    if short in overrides:
        return overrides[short] if overrides[short].is_dir() else None
    candidates = [ROOT / "components" / short.replace("-", "_"), ROOT / "components" / short, Path.home() / "dev" / short]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None


# ── layer 1: well-formedness ─────────────────────────────────────────────────

def check_shape(data: Any, errors: list[str]) -> tuple[dict[str, dict], list[dict]]:
    if not isinstance(data, dict):
        errors.append("register root must be a mapping")
        return {}, []

    missing = sorted(REQUIRED_TOP - set(data))
    if missing:
        errors.append(f"missing top-level fields: {missing}")
    if data.get("status") not in STATUS:
        errors.append(f"status must be one of {sorted(STATUS)}, got {data.get('status')!r}")

    policy = data.get("policy")
    if not isinstance(policy, dict):
        errors.append("policy must be a mapping")
        policy = {}
    if not isinstance(policy.get("observation_max_age_days"), int):
        errors.append("policy.observation_max_age_days must be an integer")
    if policy.get("default_freshness_policy") not in POLICIES:
        errors.append(f"policy.default_freshness_policy must be one of {sorted(POLICIES)}")

    coverage = data.get("coverage")
    if not isinstance(coverage, dict) or not isinstance(coverage.get("mechanically_scanned"), list) or not isinstance(coverage.get("declared_only"), list):
        errors.append("coverage must declare mechanically_scanned and declared_only lists")

    sources: dict[str, dict] = {}
    raw_sources = data.get("sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        errors.append("sources must be a non-empty list")
        raw_sources = []
    for index, source in enumerate(raw_sources):
        label = f"sources[{index}]"
        if not isinstance(source, dict):
            errors.append(f"{label} must be a mapping")
            continue
        source_id = source.get("source_id")
        label = f"source {source_id!r}" if source_id else label
        gaps = sorted(REQUIRED_SOURCE - set(source))
        if gaps:
            errors.append(f"{label} missing required fields: {gaps}")
        if source.get("artifact_kind") not in ARTIFACT_KINDS:
            errors.append(f"{label} artifact_kind must be one of {sorted(ARTIFACT_KINDS)}")
        scheme = source.get("version_scheme")
        if scheme not in VERSION_SCHEMES:
            errors.append(f"{label} version_scheme must be one of {sorted(VERSION_SCHEMES)}")
        if scheme == "semver" and not semver(source.get("upstream_latest_version", "")):
            errors.append(f"{label} version_scheme semver requires a valid upstream_latest_version")
        upstream_digest = source.get("upstream_latest_digest")
        if scheme == "digest" and upstream_digest != "unknown" and not DIGEST_RE.match(str(upstream_digest or "")):
            errors.append(f"{label} version_scheme digest requires upstream_latest_digest as sha256:<64 hex> or 'unknown'")
        if parse_date(source.get("observed_at")) is None:
            errors.append(f"{label} observed_at must be an ISO date (YYYY-MM-DD)")
        if isinstance(source_id, str) and source_id:
            if source_id in sources:
                errors.append(f"duplicate source_id: {source_id}")
            sources[source_id] = source
        else:
            errors.append(f"{label} source_id must be a non-empty string")

    artifacts: list[dict] = []
    raw_artifacts = data.get("artifacts")
    if not isinstance(raw_artifacts, list) or not raw_artifacts:
        errors.append("artifacts must be a non-empty list")
        raw_artifacts = []
    seen: set[str] = set()
    for index, artifact in enumerate(raw_artifacts):
        label = f"artifacts[{index}]"
        if not isinstance(artifact, dict):
            errors.append(f"{label} must be a mapping")
            continue
        artifact_id = artifact.get("artifact_id")
        label = f"artifact {artifact_id!r}" if artifact_id else label
        gaps = sorted(REQUIRED_ARTIFACT - set(artifact))
        if gaps:
            errors.append(f"{label} missing required fields: {gaps}")
        if not isinstance(artifact_id, str) or not artifact_id:
            errors.append(f"{label} artifact_id must be a non-empty string")
        elif artifact_id in seen:
            errors.append(f"duplicate artifact_id: {artifact_id}")
        else:
            seen.add(artifact_id)

        source_id = artifact.get("source_id")
        if source_id not in sources:
            errors.append(f"{label} references unknown source_id {source_id!r}")

        policy_value = artifact.get("freshness_policy")
        if policy_value not in POLICIES:
            errors.append(f"{label} freshness_policy must be one of {sorted(POLICIES)}")
        if policy_value == "pin-exact" and not str(artifact.get("pin_reason") or "").strip():
            errors.append(f"{label} freshness_policy pin-exact requires pin_reason")

        if not str(artifact.get("owner") or "").strip():
            errors.append(f"{label} owner must be a non-empty string")

        if artifact.get("disposition") not in DISPOSITIONS:
            errors.append(f"{label} disposition must be one of {sorted(DISPOSITIONS)}")

        tier = artifact.get("tier")
        if tier not in TIERS:
            errors.append(f"{label} tier must be one of {sorted(TIERS)}, got {tier!r}")
        elif tier == "foundation" and not str(artifact.get("tier_reason") or "").strip():
            # Foundation is the strict tier; claiming it without saying why is how a
            # tier becomes a label rather than a decision.
            errors.append(f"{label} tier foundation requires tier_reason")

        if not artifact.get("artifact_path") and not artifact.get("artifact_paths"):
            errors.append(f"{label} must declare artifact_path or artifact_paths")
        for entry in artifact.get("artifact_paths") or []:
            if not isinstance(entry, dict) or not entry.get("path"):
                errors.append(f"{label} artifact_paths entries need a path")
            elif entry.get("digest") and not DIGEST_RE.match(str(entry["digest"])):
                errors.append(f"{label} artifact_paths[{entry['path']}].digest must be sha256:<64 hex>")

        digest = artifact.get("vendored_digest")
        if digest is not None and not DIGEST_RE.match(str(digest)):
            errors.append(f"{label} vendored_digest must be sha256:<64 hex>")

        for entry in artifact.get("declared_in") or []:
            if not isinstance(entry, dict) or not entry.get("path") or not entry.get("note"):
                errors.append(f"{label} declared_in entries need both path and note")
        for entry in artifact.get("receipt_fixtures") or []:
            if not isinstance(entry, dict) or not DIGEST_RE.match(str(entry.get("digest", ""))):
                errors.append(f"{label} receipt_fixtures entries need a sha256:<64 hex> digest")

        # sub-fields each disposition obliges
        disposition = artifact.get("disposition")
        remediation = artifact.get("remediation") or {}
        waiver = artifact.get("waiver") or {}
        if disposition == "remediation-open" and not remediation.get("pull_request"):
            errors.append(f"{label} disposition remediation-open requires remediation.pull_request")
        if disposition == "remediation-required":
            if not remediation.get("finding_id"):
                errors.append(f"{label} disposition remediation-required requires remediation.finding_id")
            if parse_date(remediation.get("due")) is None:
                errors.append(f"{label} disposition remediation-required requires remediation.due as an ISO date")
        if disposition == "waived":
            if not str(waiver.get("reason") or "").strip():
                errors.append(f"{label} disposition waived requires waiver.reason")
            if parse_date(waiver.get("expires")) is None:
                errors.append(f"{label} disposition waived requires waiver.expires as an ISO date")

        artifacts.append(artifact)

    return sources, artifacts


# ── layer 2: workspace binding ───────────────────────────────────────────────

def check_workspace_binding(sources: dict[str, dict], artifacts: list[dict], errors: list[str], notes: list[str]) -> None:
    declared = workspace_urls()
    for source_id, source in sources.items():
        url = normalize_url(source.get("url", ""))
        if url in declared:
            continue
        if source.get("workspace_binding") == "unbound":
            if not str(source.get("workspace_binding_reason") or "").strip():
                errors.append(f"source {source_id!r} declares workspace_binding unbound without workspace_binding_reason")
            else:
                notes.append(f"WORKSPACE-UNBOUND source {source_id!r}: {source.get('repo')} is not declared in the workspace manifest (declared, with reason)")
        else:
            errors.append(
                f"source {source_id!r} url {source.get('url')} is not declared in manifest/workspace.toml, "
                "manifest/workspace.lock.json, or a committed manifest/*.repos.toml overlay; "
                "declare workspace_binding: unbound with a reason if that is intended"
            )
    for artifact in artifacts:
        url = normalize_url(artifact.get("consumer_url", ""))
        if url and url not in declared:
            errors.append(f"artifact {artifact.get('artifact_id')!r} consumer_url {artifact.get('consumer_url')} is not a workspace-declared repo")


# ── layer 3: freshness computation and disposition agreement ─────────────────

def upstream_is_observed(source: dict) -> bool:
    """Whether the source records an upstream reference we could name."""
    scheme = source.get("version_scheme")
    if scheme == "semver":
        return semver(source.get("upstream_latest_version", "")) is not None
    if scheme == "digest":
        value = source.get("upstream_latest_digest")
        return bool(value) and value != "unknown"
    if scheme == "commit":
        value = source.get("upstream_latest_commit")
        return bool(value) and value != "unknown"
    return False


def compute_state(artifact: dict, source: dict) -> tuple[str, str]:
    """Recompute freshness from recorded state. Returns (state, reason)."""
    policy = artifact.get("freshness_policy")
    if policy == "pin-exact":
        # A deliberate pin is only 'current' if we can name what it is pinned to.
        # Claiming to be intentionally frozen at an upstream nobody has observed is
        # not a pin — it is an unknown wearing a pin's clothes.
        if not upstream_is_observed(source):
            return "unknown", "pin-exact but the source records no observed upstream reference to be pinned to"
        return "current", "pin-exact: intentionally frozen against an observed upstream"

    scheme = source.get("version_scheme")

    if scheme == "semver":
        vendored = semver(artifact.get("vendored_version", ""))
        upstream = semver(source.get("upstream_latest_version", ""))
        if vendored is None or upstream is None:
            return "unknown", "vendored_version or upstream_latest_version is not a valid semver"
        if policy == "track-minor":
            if vendored[0] != upstream[0]:
                return "stale", f"major differs: vendored {artifact['vendored_version']} vs upstream {source['upstream_latest_version']}"
            if vendored < upstream:
                return "stale", f"vendored {artifact['vendored_version']} is behind upstream {source['upstream_latest_version']}"
            return "current", f"vendored {artifact['vendored_version']} is at or ahead of upstream"
        if vendored != upstream:
            return "stale", f"track-latest: vendored {artifact['vendored_version']} != upstream {source['upstream_latest_version']}"
        return "current", "track-latest: vendored equals upstream"

    if scheme == "digest":
        upstream = source.get("upstream_latest_digest")
        if not upstream or upstream == "unknown":
            return "unknown", "upstream_latest_digest not observed"
        vendored = artifact.get("vendored_digest")
        if not vendored:
            return "unknown", "vendored_digest not recorded"
        return ("current", "digest matches upstream") if vendored == upstream else ("stale", "digest differs from upstream")

    if scheme == "commit":
        upstream = source.get("upstream_latest_commit")
        if not upstream or upstream == "unknown":
            return "unknown", "upstream_latest_commit not observed"
        vendored = str(artifact.get("vendored_commit") or "")
        if not vendored:
            return "unknown", "vendored_commit not recorded"
        matches = upstream.startswith(vendored) or vendored.startswith(upstream)
        return ("current", "commit matches upstream") if matches else ("stale", f"vendored commit {vendored} != upstream {upstream}")

    return "unknown", f"unsupported version_scheme {scheme!r}"


def source_tier(source_id: str, artifacts: list[dict]) -> str:
    """A source inherits the STRICTEST tier of anything vendored from it.

    An upstream feeding one foundation consumer and four reference ones is a
    foundation upstream. Taking the loosest tier would let a reference copy set the
    observation budget for the engine that answers production queries.
    """
    tiers = {a.get("tier") for a in artifacts if a.get("source_id") == source_id}
    for candidate in STRICTEST_FIRST:
        if candidate in tiers:
            return candidate
    return "reference"


def check_release_chain(sources: dict[str, dict], artifacts: list[dict], errors: list[str], notes: list[str]) -> None:
    """The supersession chain must actually be walkable from the register.

    `gapSize` is the length of a vfp:supersededBy path, and blast-radius reasoning is
    worth little without it. A source that names a latest version it does not list as
    a release has a chain with a hole in it, and the derived questions silently answer
    from a shorter chain than reality — which is a smaller number, in the reassuring
    direction. So a hole is an error, not a note.
    """
    for source_id, source in sources.items():
        if source.get("version_scheme") != "semver":
            continue
        releases = source.get("releases") or []
        if not releases:
            errors.append(
                f"source {source_id!r} is semver and declares no releases:; the supersession chain "
                "cannot be built, so staleness distance and contract-crossing risk cannot be derived "
                "from this register. `make vendor-freshness-detect` populates it."
            )
            continue

        known = {str(r.get("version")) for r in releases if isinstance(r, dict)}
        latest = source.get("upstream_latest_version")
        if latest and str(latest) not in known:
            errors.append(
                f"source {source_id!r} declares upstream_latest_version {latest} with no matching "
                f"releases: entry — the chain does not reach its own head"
            )
        for artifact in artifacts:
            if artifact.get("source_id") != source_id:
                continue
            vendored = artifact.get("vendored_version")
            if vendored and str(vendored) not in known:
                errors.append(
                    f"artifact {artifact.get('artifact_id')!r} pins {vendored}, which source "
                    f"{source_id!r} does not list as a release — the chain has no anchor to walk from"
                )

        catalog = {c.get("contract_id") for c in source.get("contracts") or [] if isinstance(c, dict)}
        contract_silent = []
        for release in releases:
            if not isinstance(release, dict):
                errors.append(f"source {source_id!r} releases entries must be mappings")
                continue
            changes = release.get("changes_contract")
            if not changes:
                contract_silent.append(str(release.get("version")))
                continue
            for change in changes:
                if not isinstance(change, dict):
                    errors.append(f"source {source_id!r} release {release.get('version')} changes_contract entries must be mappings")
                    continue
                contract_id = change.get("contract_id")
                if contract_id is None:
                    if not change.get("kind"):
                        errors.append(
                            f"source {source_id!r} release {release.get('version')} declares a contract change "
                            "with neither contract_id nor kind"
                        )
                    continue
                if contract_id not in catalog:
                    errors.append(
                        f"source {source_id!r} release {release.get('version')} references unknown "
                        f"contract_id {contract_id!r}; declare it under the source's contracts:"
                    )
        # Contract-silence is a legitimate, common state — most releases move nothing
        # load-bearing — so it is reported, never failed. Failing it would push people
        # to declare a contract change they had not actually checked for.
        pending = [str(r.get("version")) for r in releases
                   if isinstance(r, dict) and r.get("contract_review") == "pending"]
        if pending:
            notes.append(
                f"CONTRACT-REVIEW-PENDING source {source_id!r}: {sorted(pending)} were appended by the "
                "detector and nobody has said what they moved"
            )
        elif contract_silent:
            notes.append(f"CONTRACT-SILENT source {source_id!r}: {sorted(contract_silent)}")


def check_freshness(data: dict, sources: dict[str, dict], artifacts: list[dict], today: date, errors: list[str], notes: list[str]) -> None:
    policy = data.get("policy", {}) if isinstance(data.get("policy"), dict) else {}
    default_max_age = policy.get("observation_max_age_days")
    by_tier = policy.get("tier_observation_max_age_days") or {}

    for source_id, source in sources.items():
        tier = source_tier(source_id, artifacts)
        max_age = by_tier.get(tier, default_max_age)
        observable = upstream_is_observed(source)
        gap = source.get("observation_gap") or {}

        if not observable:
            # Nobody can be late looking at something there is no way to look at. But
            # you CAN be late building the way to look at it — so a foundation source
            # the detector cannot observe must name the gap and a date to close it.
            # Without this, `unknown` is a permanent, silent parking space, which is
            # the exact state the estate was already in.
            if tier == "foundation":
                revisit = parse_date(gap.get("revisit_by"))
                if not str(gap.get("reason") or "").strip() or revisit is None:
                    errors.append(
                        f"source {source_id!r} is tier foundation and its upstream is not observable "
                        "(tools/detect_vendor_freshness.py cannot read it); declare observation_gap "
                        "with a reason and a revisit_by date"
                    )
                elif revisit < today:
                    errors.append(
                        f"source {source_id!r} observation_gap revisit_by has passed ({revisit}, today {today}); "
                        "either make the upstream observable or re-date the gap deliberately"
                    )
            else:
                notes.append(f"UNOBSERVABLE source {source_id!r} [tier {tier}]: upstream state cannot be computed")
            continue

        observed = parse_date(source.get("observed_at"))
        if observed is None or not isinstance(max_age, int):
            continue
        age = (today - observed).days
        if age > max_age:
            errors.append(
                f"source {source_id!r} observation is {age} days old (tier {tier} limit {max_age}); "
                "re-observe upstream — a stale observation makes every artifact from this source "
                "unverifiable. `make vendor-freshness-detect` refreshes it."
            )

    for artifact in artifacts:
        artifact_id = artifact.get("artifact_id")
        source = sources.get(artifact.get("source_id"))
        if source is None:
            continue
        state, reason = compute_state(artifact, source)
        disposition = artifact.get("disposition")
        allowed = AGREEMENT.get(state, set())
        if disposition not in allowed:
            errors.append(
                f"artifact {artifact_id!r} declares disposition {disposition!r} but computed freshness is {state!r} "
                f"({reason}); allowed here: {sorted(allowed)}"
            )
        if state == "stale":
            notes.append(f"STALE {artifact_id}: {reason} [disposition {disposition}]")

        remediation = artifact.get("remediation") or {}
        due = parse_date(remediation.get("due"))
        if disposition == "remediation-required" and due is not None and due < today:
            errors.append(f"artifact {artifact_id!r} remediation {remediation.get('finding_id')} is overdue (due {due}, today {today})")
        waiver = artifact.get("waiver") or {}
        expires = parse_date(waiver.get("expires"))
        if disposition == "waived" and expires is not None and expires < today:
            errors.append(f"artifact {artifact_id!r} waiver expired on {expires} (today {today})")

        guard = artifact.get("guard") or {}
        if guard and guard.get("invoked_by_ci") is False:
            notes.append(f"GUARD-NOT-INVOKED {artifact_id}: {guard.get('path') or 'no guard declared'}")


# ── layer 4: on-disk reality and undeclared-artifact sweep ───────────────────

def check_on_disk(artifacts: list[dict], sources: dict[str, dict], overrides: dict[str, Path],
                  errors: list[str], notes: list[str], required: set[str] | None = None) -> None:
    repos = sorted({a.get("consumer_repo") for a in artifacts if a.get("consumer_repo")})
    roots: dict[str, Path] = {}
    required = required or set()
    for repo in repos:
        root = resolve_repo_root(repo, overrides)
        if root is None:
            # SKIPPED is honest when nobody claimed the repo would be there. In CI it
            # is not honest — the workflow materializes the consumers on purpose, and
            # a checkout that silently failed would turn the whole on-disk layer into
            # a no-op that still prints green. --require-disk closes that.
            if repo in required or repo.split("/")[-1] in required:
                errors.append(
                    f"--require-disk names {repo} but it is not materialized; on-disk verification "
                    "would have been skipped. Refusing to report a pass for bytes nobody read."
                )
            else:
                notes.append(f"SKIPPED on-disk verification for {repo}: not materialized locally")
        else:
            roots[repo] = root
    for name in sorted(required):
        if not any(name in (repo, repo.split("/")[-1]) for repo in repos):
            errors.append(f"--require-disk names {name!r}, which no artifact declares as a consumer_repo")

    declared_paths: dict[str, set[str]] = {repo: set() for repo in roots}

    for artifact in artifacts:
        repo = artifact.get("consumer_repo")
        root = roots.get(repo)
        if root is None:
            continue
        artifact_id = artifact.get("artifact_id")

        app = artifact.get("consumer_app")
        if app and not (root / app).exists():
            errors.append(f"artifact {artifact_id!r} consumer_app {app} does not exist in {repo} at {root}")

        entries: list[tuple[str, str | None]] = []
        if artifact.get("artifact_path"):
            entries.append((artifact["artifact_path"], artifact.get("vendored_digest")))
        for item in artifact.get("artifact_paths") or []:
            if isinstance(item, dict) and item.get("path"):
                entries.append((item["path"], item.get("digest")))

        for rel, expected_digest in entries:
            path = root / rel
            declared_paths[repo].add(rel)
            if not path.exists():
                errors.append(f"artifact {artifact_id!r} declared path does not exist: {repo}/{rel}")
                continue
            if path.is_dir():
                continue
            actual = sha256_file(path)
            if expected_digest and actual != expected_digest:
                errors.append(
                    f"DRIFT artifact {artifact_id!r} {repo}/{rel}: recorded {expected_digest} but on disk {actual}"
                )
            # a version embedded in the filename must agree with the recorded version
            filename_version = TGZ_VERSION_RE.search(rel)
            recorded = artifact.get("vendored_version")
            if filename_version and recorded and filename_version.group(1) != str(recorded):
                errors.append(
                    f"DRIFT artifact {artifact_id!r}: path says {filename_version.group(1)} but vendored_version records {recorded}"
                )

        for entry in artifact.get("declared_in") or []:
            rel = entry.get("path") if isinstance(entry, dict) else None
            if rel and not (root / rel).exists():
                errors.append(f"artifact {artifact_id!r} declared_in path does not exist: {repo}/{rel}")

        guard = artifact.get("guard") or {}
        guard_path = guard.get("path")
        if guard_path and not (root / guard_path).exists():
            errors.append(f"artifact {artifact_id!r} guard path does not exist: {repo}/{guard_path}")

    # undeclared-artifact sweep over the mechanically scannable classes
    for repo, root in roots.items():
        for path in sorted(root.rglob("vendor/*.tgz")):
            if "node_modules" in path.parts:
                continue
            rel = path.relative_to(root).as_posix()
            if rel not in declared_paths[repo]:
                errors.append(
                    f"UNDECLARED vendored artifact {repo}/{rel} has no entry in registry/vendor-freshness.yaml"
                )
        for package_json in sorted(root.rglob("package.json")):
            if "node_modules" in package_json.parts:
                continue
            try:
                manifest = json.loads(package_json.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                continue
            app_dir = package_json.parent
            for section in ("dependencies", "devDependencies", "optionalDependencies"):
                for name, spec in (manifest.get(section) or {}).items():
                    if not isinstance(spec, str) or not spec.startswith("file:"):
                        continue
                    target = (app_dir / spec[len("file:"):]).resolve()
                    try:
                        rel = target.relative_to(root.resolve()).as_posix()
                    except ValueError:
                        continue
                    if rel not in declared_paths[repo]:
                        errors.append(
                            f"UNDECLARED file: dependency {name} -> {repo}/{rel} "
                            f"(declared in {package_json.relative_to(root).as_posix()}) has no entry in registry/vendor-freshness.yaml"
                        )


# ── layer 5: graph vocabulary coverage ───────────────────────────────────────

def check_vocabulary(errors: list[str], notes: list[str]) -> None:
    """Every vfp: term used in a lift graph must be declared in the vocabulary.

    Mirrors tools/check_neurosymbolic_repo_graph_vocabulary.py: an undeclared term
    in a fixture is how a vocabulary silently becomes decorative.
    """
    if not VOCAB.exists():
        errors.append(f"missing graph vocabulary: {VOCAB.relative_to(ROOT)}")
        return
    vocab_text = VOCAB.read_text(encoding="utf-8")
    declared = set(re.findall(r"^vfp:([A-Za-z][A-Za-z0-9]*)\s+a\s+(?:rdfs:Class|rdfs:Property)", vocab_text, re.MULTILINE))
    if not declared:
        errors.append(f"{VOCAB.relative_to(ROOT)} declares no vfp: classes or properties")
        return

    lifts = sorted(p for p in GRAPH_DIR.glob("*.ttl") if p != VOCAB)
    if not lifts:
        notes.append("no vendor-freshness lift graphs found to check against the vocabulary")
        return
    for lift in lifts:
        used = set(re.findall(r"\bvfp:([A-Za-z][A-Za-z0-9]*)\b", lift.read_text(encoding="utf-8")))
        undeclared = sorted(used - declared)
        if undeclared:
            errors.append(f"{lift.relative_to(ROOT)} uses vfp: terms not declared in the vocabulary: {undeclared}")

    # the four spine terms the design doc is written against must exist
    spine = {"Repository", "Artifact", "ConsumerApp", "VendorPin", "vendors", "producedBy", "supersededBy", "pinnedAt"}
    missing = sorted(spine - declared)
    if missing:
        errors.append(f"{VOCAB.relative_to(ROOT)} is missing required spine terms: {missing}")


# ── entrypoint ───────────────────────────────────────────────────────────────

def run(register_path: Path, overrides: dict[str, Path], today: date, skip_disk: bool,
        required: set[str] | None = None) -> tuple[list[str], list[str], int]:
    errors: list[str] = []
    notes: list[str] = []
    try:
        data = yaml.safe_load(register_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        return [f"failed to parse {register_path}: {exc}"], [], 0

    sources, artifacts = check_shape(data, errors)
    if not errors:
        check_workspace_binding(sources, artifacts, errors, notes)
        check_release_chain(sources, artifacts, errors, notes)
        check_freshness(data if isinstance(data, dict) else {}, sources, artifacts, today, errors, notes)
        if register_path == REGISTER:
            # The graph vocabulary governs the committed register, not fixtures.
            check_vocabulary(errors, notes)
        if skip_disk:
            if required:
                errors.append("--skip-disk and --require-disk are contradictory; --require-disk exists to stop exactly this")
            notes.append("SKIPPED on-disk verification entirely (--skip-disk)")
        else:
            check_on_disk(artifacts, sources, overrides, errors, notes, required)
    return errors, notes, len(artifacts)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the vendor freshness register.")
    parser.add_argument("--register", type=Path, default=REGISTER)
    parser.add_argument("--repo-root", action="append", default=[], metavar="NAME=PATH",
                        help="Locate a consumer repo explicitly, e.g. prophet-platform=/path/to/repo")
    parser.add_argument("--skip-disk", action="store_true", help="Register checks only; skip on-disk verification.")
    parser.add_argument("--require-disk", action="append", default=[], metavar="REPO",
                        help="Fail if this consumer repo is not materialized, instead of reporting SKIPPED. "
                             "Repeatable. This is what makes the CI gate fail-closed: a checkout that "
                             "silently did not happen must not read as a pass.")
    parser.add_argument("--today", type=str, default=None, help="Override today's date (YYYY-MM-DD) for date-based checks.")
    args = parser.parse_args()

    overrides: dict[str, Path] = {}
    for item in list(args.repo_root) + [p for p in os.environ.get("VENDOR_FRESHNESS_REPO_ROOTS", "").split(",") if p.strip()]:
        if "=" not in item:
            print(f"ERROR: --repo-root expects NAME=PATH, got {item!r}", file=sys.stderr)
            return 1
        name, _, path = item.partition("=")
        overrides.setdefault(name.strip(), Path(path.strip()).expanduser())

    today = parse_date(args.today) or date.today()
    if args.today and parse_date(args.today) is None:
        print(f"ERROR: --today expects YYYY-MM-DD, got {args.today!r}", file=sys.stderr)
        return 1

    errors, notes, count = run(args.register, overrides, today, args.skip_disk, set(args.require_disk))

    for note in notes:
        print(f"NOTE: {note}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"FAILED: {len(errors)} finding(s) across {count} declared vendored artifact(s)", file=sys.stderr)
        return 1
    print(f"validated {count} declared vendored artifact(s) in {args.register.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
