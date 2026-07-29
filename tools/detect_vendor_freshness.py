#!/usr/bin/env python3
"""Observe upstream, recompute freshness, emit re-vendor plans.

W12.2. The register that W12.1 seeded records `upstream_latest_version` with an
`observed_at` date and an `observation_method` — read by a human, once. This is the
machine that does the reading, on a schedule, so the observation cannot go stale and
a release cannot be invisible for five versions again.

Three things, in order:

1. OBSERVE. For every source, ask the upstream what its latest release actually is.
   `git ls-remote` against a public HTTPS URL — no token, no API key, no new secret.
   Anonymous ls-remote is the whole network surface of this tool.

2. RECOMPUTE. The freshness state is computed by importing `compute_state` from
   tools/validate_vendor_freshness.py. There is exactly ONE definition of "stale" in
   this repo and it is the gate's. A detector with its own opinion of staleness would
   be a second register.

3. EMIT. For every artifact the recomputation finds behind its `freshness_policy`,
   write a re-vendor PLAN: an EffectRequest, in the shape
   docs/governance/vendor-freshness-plane.md § Emitting an EffectRequest specifies,
   whose `parameters` carry the whole evidence bundle — gap, blast radius, contract
   crossings, the discriminating version marker, the receipt fixtures that must
   survive, the guard floor that moves with the tarball, and every file that names
   the pin.

The plan is the interface. This tool does not open pull requests and does not know
how to re-vendor anything; the consumer repo's executor consumes the plan and does
that work in its own CI, with its own credentials, against its own test suite. That
split is not fastidiousness: sociosphere's GITHUB_TOKEN cannot write to
prophet-platform, and the alternative is a cross-repo PAT this estate has decided
not to have.

Writing the register back (--write-register) rewrites ONLY the observed fields, in
place, line by line. It never re-serializes the YAML: the register's comments carry
the findings, and a round-trip through a YAML dumper would delete them.

Exit codes: 0 = ran (findings are data, not failure), 1 = the detector itself failed.
Staleness is reported, never fatal — the gate is the thing that fails, and it fails
on DISAGREEMENT, not on drift. See --fail-on-stale for the deliberate exception.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_vendor_freshness import (  # noqa: E402  (path set above)
    ROOT,
    REGISTER,
    compute_state,
    parse_date,
    semver,
)

PLAN_SPEC_VERSION = "0.1.0"
TAG_RE = re.compile(r"^refs/tags/v?(\d+\.\d+\.\d+)$")


# ── observation ──────────────────────────────────────────────────────────────

class ObservationError(RuntimeError):
    """Upstream could not be observed. Recorded as unobserved, never as current."""


def git_ls_remote(url: str, *flags: str, refs: tuple[str, ...] = (), timeout: int = 60) -> str:
    """Anonymous ls-remote. No credentials, no API, no secret.

    Argument order matters and is easy to get wrong: flags precede the URL, ref
    patterns FOLLOW it. `git ls-remote main <url>` treats "main" as the repository
    and fails with "'main' does not appear to be a git repository" — a message that
    reads like an access problem and is not one.
    """
    env = dict(os.environ)
    # A prompt in CI is an indefinite hang, and a hang in a scheduled job is a
    # detector that silently stopped detecting.
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_ASKPASS"] = "true"
    try:
        result = subprocess.run(
            ["git", "ls-remote", *flags, url, *refs],
            capture_output=True, text=True, timeout=timeout, env=env, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ObservationError(f"git ls-remote timed out after {timeout}s") from exc
    if result.returncode != 0:
        raise ObservationError(f"git ls-remote exited {result.returncode}: {result.stderr.strip()[:300]}")
    return result.stdout


def observe_tags(url: str) -> list[tuple[tuple[int, int, int], str, str]]:
    """Every semver tag upstream, newest last. Returns (parsed, version, COMMIT).

    Deliberately NOT `--refs`. An annotated tag's own sha is the sha of the tag
    OBJECT, not of the commit it names, and `--refs` suppresses exactly the `^{}`
    peeled lines that reveal the commit. Two annotated tags on one commit therefore
    look like two distinct releases — which is how hellgraph's v0.4.41 and v0.4.42
    (both annotated, both naming commit 5f72cf3) read as two releases when there is
    only one artifact between them. hellgraph mixes annotated and lightweight tags,
    so both forms have to be handled: peel where a peel exists, fall back otherwise.
    """
    raw: dict[str, str] = {}
    peeled: dict[str, str] = {}
    for line in git_ls_remote(url, "--tags").splitlines():
        sha, _, ref = line.partition("\t")
        ref = ref.strip()
        target = peeled if ref.endswith("^{}") else raw
        match = TAG_RE.match(ref.removesuffix("^{}"))
        if match:
            target[match.group(1)] = sha.strip()
    found = {version: peeled.get(version, sha) for version, sha in raw.items()}
    parsed = [(semver(v), v, sha) for v, sha in found.items()]
    return sorted((p for p in parsed if p[0] is not None), key=lambda item: item[0])


def tag_aliases(tags: list[tuple[tuple[int, int, int], str, str]]) -> dict[str, list[str]]:
    """Semver tags that point at the SAME commit — i.e. one of them is not a release.

    Free to compute from the ls-remote output, and it catches a silent-wrong the gap
    count would otherwise inherit: hellgraph's v0.4.42 points at the v0.4.41 commit,
    whose package.json says 0.4.41. Anyone pinning v0.4.42 gets 0.4.41 bytes, and any
    gap counted by tags over-counts by one. A version that is not a distinct artifact
    is not a release, however real its tag looks.
    """
    by_commit: dict[str, list[str]] = {}
    for _, version, commit in tags:
        by_commit.setdefault(commit, []).append(version)
    return {commit: sorted(versions) for commit, versions in by_commit.items() if len(versions) > 1}


def observe_head(url: str, ref: str) -> str:
    """The commit a branch currently points at."""
    for line in git_ls_remote(url, refs=(str(ref),)).splitlines():
        sha, _, name = line.partition("\t")
        if name.strip() in (f"refs/heads/{ref}", f"refs/tags/{ref}", str(ref)):
            return sha.strip()
    raise ObservationError(f"ref {ref!r} not found upstream")


def observe_source(source: dict, today: date) -> dict:
    """Look at one upstream. Returns an observation record, successful or not."""
    source_id = source.get("source_id")
    url = source.get("url", "")
    scheme = source.get("version_scheme")
    record: dict[str, Any] = {
        "source_id": source_id, "url": url, "version_scheme": scheme,
        "observed_at": today.isoformat(), "ok": False,
    }

    if source.get("external"):
        # Someone else's release cadence. Declared, not polled.
        record["skipped"] = "source declares external: true — upstream cadence is not ours to poll"
        return record

    try:
        if scheme == "semver":
            tags = observe_tags(url)
            if not tags:
                raise ObservationError("no semver tags found upstream")
            _, latest, sha = tags[-1]
            record.update({
                "ok": True,
                "upstream_latest_version": latest,
                "upstream_latest_ref": f"v{latest}",
                "upstream_latest_commit": sha,
                "tags": [version for _, version, _ in tags],
                "tag_commits": {version: commit for _, version, commit in tags},
                "tag_aliases": tag_aliases(tags),
                # Deliberately NOT `--refs`: this observation is only reproducible without
                # it. `--refs` suppresses the peeled `^{}` lines, and without those an
                # annotated tag reports the sha of the TAG OBJECT rather than of the commit
                # — which is how v0.4.41 and v0.4.42 (both annotated, both naming 5f72cf3)
                # read as two releases when there is one artifact. Printing a flag the tool
                # does not use would make the method line un-repeatable, and "precisely
                # enough to repeat" is the whole job of this field.
                "observation_method": (
                    f"git ls-remote --tags {url} -> newest semver tag v{latest} ({sha[:12]})"
                ),
            })
        elif scheme == "commit":
            ref = source.get("upstream_ref") or "main"
            sha = observe_head(url, ref)
            record.update({
                "ok": True,
                "upstream_latest_commit": sha,
                "observation_method": f"git ls-remote {url} {ref} -> {sha[:12]}",
            })
        elif scheme == "digest":
            # A digest source is only observable if it says WHICH upstream bytes to
            # hash. Most do not, and that gap is the finding — not something to
            # paper over by hashing something plausible.
            record["error"] = (
                "version_scheme digest is not observable by ls-remote; it needs an "
                "upstream artifact path to fetch and hash. Declared unobserved."
            )
        else:
            record["error"] = f"unsupported version_scheme {scheme!r}"
    except ObservationError as exc:
        record["error"] = str(exc)
    return record


# ── recomputation ────────────────────────────────────────────────────────────

def apply_observation(source: dict, observation: dict) -> dict:
    """A copy of the source as the observation says it is. Never mutates input."""
    updated = dict(source)
    for key in ("upstream_latest_version", "upstream_latest_ref", "upstream_latest_commit"):
        if observation.get(key):
            updated[key] = observation[key]
    if observation.get("ok"):
        updated["observed_at"] = observation["observed_at"]
        updated["observation_method"] = observation["observation_method"]
    return updated


def distinct_versions(observation: dict) -> list[str]:
    """Observed tags with alias duplicates dropped, oldest first.

    When two semver tags share a commit only one of them is an artifact. The LOWER
    version wins, because that is the one whose package.json matches its tag — the
    higher one is the mistake (hellgraph v0.4.42 -> the v0.4.41 commit, package.json
    0.4.41). Keeping both would inflate every gap through that range by one.
    """
    aliases = observation.get("tag_aliases") or {}
    dropped = {v for versions in aliases.values() for v in versions[1:]}
    ordered = sorted((semver(t), t) for t in observation.get("tags") or [] if semver(t))
    return [tag for _, tag in ordered if tag not in dropped]


def gap_releases(artifact: dict, observation: dict) -> list[str]:
    """The versions between what is vendored and what upstream has, exclusive-inclusive."""
    vendored = semver(artifact.get("vendored_version", ""))
    if vendored is None:
        return []
    return [tag for tag in distinct_versions(observation) if semver(tag) > vendored]


def contract_crossings(source: dict, gap: list[str]) -> list[dict]:
    """Releases inside the gap that DECLARE they moved a load-bearing contract.

    A gap of five patch releases is not inherently dangerous. A gap that spans a
    release which changed a receipt shape or a schema is what turns a routine bump
    into "re-verify the golden receipts before you ship this".

    Declared, never inferred. Semver is a promise about intent, not a record of what
    moved: 0.4.45 was a PATCH bump and it changed what a Cypher query answers. Reading
    danger off a version number is the same guess-instead-of-check this plane exists
    to stop, so a release with no `changes_contract` is contract-SILENT — meaning
    nobody has said, not that nothing moved.
    """
    catalog = {c.get("contract_id"): c for c in source.get("contracts") or [] if isinstance(c, dict)}
    crossings = []
    for release in source.get("releases") or []:
        if str(release.get("version")) not in gap:
            continue
        for change in release.get("changes_contract") or []:
            # `contract_id` is this register's spelling, `id` the engine ingest's. The
            # validator errors if both are present and disagree, so either is safe to read.
            contract_id = change.get("contract_id") or change.get("id")
            contract = catalog.get(contract_id, {})
            crossings.append({
                "version": str(release["version"]),
                "contract_id": contract_id,
                # A Contract node carries the kind; the change references the node.
                # `kind` inline is the pre-contracts form, still read so an upstream
                # that has not been given a contract catalog yet is not silently
                # downgraded to "crosses nothing".
                "contract_kind": contract.get("contract_kind") or change.get("kind"),
                "note": change.get("note") or contract.get("note"),
            })
    return crossings


def blast_radius(artifacts: list[dict], source_id: str) -> list[dict]:
    """Every ConsumerApp holding this upstream — the question nobody could answer.

    Counted over consumer APPS, not consumer repos. Both stale engine copies live in
    prophet-platform; counting repos would have said 1 and hidden lifecycle-warden,
    which is precisely how it stayed hidden.
    """
    return [
        {
            "artifact_id": a.get("artifact_id"),
            "consumer_repo": a.get("consumer_repo"),
            "consumer_app": a.get("consumer_app"),
            "vendored_version": a.get("vendored_version"),
            "artifact_path": a.get("artifact_path"),
            "tier": a.get("tier"),
        }
        for a in artifacts if a.get("source_id") == source_id
    ]


def build_plan(artifact: dict, source: dict, observation: dict, artifacts: list[dict],
               state: str, reason: str, today: date) -> dict:
    """The EffectRequest. Its `parameters` are the evidence, not a diff summary."""
    artifact_id = artifact["artifact_id"]
    from_version = artifact.get("vendored_version")
    to_version = observation.get("upstream_latest_version") or source.get("upstream_latest_version")
    gap = gap_releases(artifact, observation)
    crossings = contract_crossings(source, gap)
    radius = blast_radius(artifacts, artifact.get("source_id"))
    marker = artifact.get("version_marker") or {}

    return {
        "type": "EffectRequest",
        "specVersion": PLAN_SPEC_VERSION,
        "effectKind": "update",
        "capability": "vendor.revendor",
        "target": {
            "kind": "vendor-pin",
            "identifier": artifact_id,
            "location": f"{artifact.get('consumer_repo')}/{artifact.get('artifact_path')}",
        },
        # A re-emitted finding must not open a second pull request. The executor
        # keys its branch off this, so the same finding converges on one branch.
        "idempotencyKey": f"{artifact_id}@{from_version}->{to_version}",
        "requestedByEventRef": f"vendor-freshness-observation/{observation['observed_at']}/{artifact.get('source_id')}",
        "requiresHumanApproval": bool(crossings),
        "riskLabels": sorted({"contract-crossing"} | {c["contract_kind"] for c in crossings if c.get("contract_kind")}) if crossings else [],
        # The consuming app's trust zone plus its tier. Both are declared on the
        # artifact; a policy label the register cannot source is a label the membrane
        # gate would have to invent, so an undeclared zone says so rather than
        # defaulting to something reassuring.
        "policyLabels": [
            f"tier:{artifact.get('tier', 'unclassified')}",
            f"trust-zone:{artifact.get('trust_zone', 'undeclared')}",
        ],
        "parameters": {
            "artifactId": artifact_id,
            "sourceId": artifact.get("source_id"),
            "sourceRepo": source.get("repo"),
            "sourceUrl": source.get("url"),
            "packageName": source.get("package_name"),
            "consumerRepo": artifact.get("consumer_repo"),
            "consumerApp": artifact.get("consumer_app"),
            "artifactPath": artifact.get("artifact_path"),
            "tier": artifact.get("tier"),
            "freshnessPolicy": artifact.get("freshness_policy"),
            "owner": artifact.get("owner"),
            "computedState": state,
            "computedReason": reason,
            "declaredDisposition": artifact.get("disposition"),

            "fromVersion": from_version,
            "toVersion": to_version,
            "toRef": observation.get("upstream_latest_ref"),
            "toCommit": observation.get("upstream_latest_commit"),
            "gapSize": len(gap),
            "gapReleases": gap,

            "blastRadius": len(radius),
            "blastRadiusApps": radius,

            "crossesContract": bool(crossings),
            "contractKinds": sorted({c["contract_kind"] for c in crossings if c.get("contract_kind")}),
            "contractCrossings": crossings,

            # ── the discipline the executor MUST carry out, carried WITH the plan ──
            # Every one of these is here because it has already gone wrong once.
            "versionMarker": {
                "marker": marker.get("marker"),
                "presentIn": marker.get("present_in"),
                "absentIn": marker.get("absent_in"),
                "assertInside": marker.get("assert_inside", "package/ts/dist/index.js"),
                "note": marker.get("note"),
            },
            "guard": artifact.get("guard") or {},
            "receiptFixtures": artifact.get("receipt_fixtures") or [],
            "declaredIn": artifact.get("declared_in") or [],
            "observedAt": observation["observed_at"],
            "observationMethod": observation.get("observation_method"),
            "detectedOn": today.isoformat(),
        },
    }


# ── register rewrite (surgical: the comments ARE the findings) ───────────────

def block_bounds(lines: list[str], value: str, key: str = "source_id") -> tuple[int, int] | None:
    """Line range of one list item, ending at its last line of real CONTENT.

    `end` is an insertion point as well as a scan limit, so it must not include the
    blank line or the section banner that separates this item from the next. YAML
    would still parse a key inserted after a comment — comments are not structure —
    but the file would read as though the key belonged to the following section, and
    this register is meant to be read.
    """
    start = None
    for index, line in enumerate(lines):
        if re.match(rf"^\s*-\s+{re.escape(key)}:\s*{re.escape(value)}\s*$", line):
            start = index
            break
    if start is None:
        return None
    indent = len(lines[start]) - len(lines[start].lstrip())
    last_content = start
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if not line.strip():
            continue
        current = len(line) - len(line.lstrip())
        if current <= indent:
            break
        last_content = index
    return start, last_content + 1


def set_scalar(lines: list[str], start: int, end: int, key: str, value: str, quote: bool = False) -> tuple[list[str], int]:
    """Set (or insert) one scalar inside a block, returning the new end index."""
    rendered = f"'{value}'" if quote else value
    field_indent = " " * (len(lines[start]) - len(lines[start].lstrip()) + 2)
    for index in range(start + 1, end):
        if re.match(rf"^\s*{re.escape(key)}:", lines[index]):
            lines[index] = f"{field_indent}{key}: {rendered}"
            return lines, end
    lines.insert(end, f"{field_indent}{key}: {rendered}")
    return lines, end + 1


def set_folded(lines: list[str], start: int, end: int, key: str, value: str) -> tuple[list[str], int]:
    """Replace a folded (`>-`) block scalar, consuming its continuation lines."""
    field_indent = " " * (len(lines[start]) - len(lines[start].lstrip()) + 2)
    body_indent = field_indent + "  "
    replacement = [f"{field_indent}{key}: >-"] + [f"{body_indent}{value}"]
    for index in range(start + 1, end):
        if re.match(rf"^\s*{re.escape(key)}:", lines[index]):
            stop = index + 1
            while stop < end and lines[stop].strip() and (len(lines[stop]) - len(lines[stop].lstrip())) > len(field_indent):
                stop += 1
            lines[index:stop] = replacement
            return lines, end - (stop - index) + len(replacement)
    lines[end:end] = replacement
    return lines, end + len(replacement)


def next_finding_id(text: str) -> str:
    """VFP-0001, VFP-0002, … Never reuses a number already spent."""
    used = [int(n) for n in re.findall(r"finding_id:\s*VFP-(\d+)", text)]
    return f"VFP-{max(used, default=0) + 1:04d}"


def propose_dispositions(lines: list[str], proposals: list[dict]) -> list[str]:
    """File the finding the recomputation implies, with a deadline on it.

    When an observation moves an artifact from `current` to `stale`, the register
    is now self-contradictory and the gate will (correctly) fail. Leaving that for
    a human to fix by hand is the labour this plane exists to delete, so the
    detector files the weakest defensible disposition for the computed state and
    puts a date on it. It never files anything WEAKER than the state demands, and
    it never touches an artifact whose declared disposition already agrees — a
    human's `waived` or `remediation-open` stands.
    """
    for proposal in proposals:
        bounds = block_bounds(lines, proposal["artifact_id"], key="artifact_id")
        if bounds is None:
            continue
        start, end = bounds
        indent = " " * (len(lines[start]) - len(lines[start].lstrip()) + 2)
        for index in range(start + 1, end):
            if re.match(r"^\s*disposition:", lines[index]):
                lines[index] = f"{indent}disposition: {proposal['disposition']}"
                break
        if proposal["disposition"] == "remediation-required":
            block = [
                f"{indent}remediation:",
                f"{indent}  finding_id: {proposal['finding_id']}",
                f"{indent}  target_version: {proposal['target_version']}",
                f"{indent}  due: '{proposal['due']}'",
                f"{indent}  note: >-",
                f"{indent}    Filed by tools/detect_vendor_freshness.py on {proposal['detected_on']}: "
                f"{proposal['reason']}. Due date is the {proposal['tier']} tier SLA. Re-triage freely "
                f"— this is a machine-filed placeholder so the register stays internally consistent, "
                f"not a judgement about priority.",
            ]
            for index in range(start + 1, end):
                if re.match(r"^\s*remediation:", lines[index]):
                    stop = index + 1
                    while stop < end and lines[stop].strip() and (len(lines[stop]) - len(lines[stop].lstrip())) > len(indent):
                        stop += 1
                    lines[index:stop] = block
                    break
            else:
                lines[end:end] = block
    return lines


def append_releases(lines: list[str], start: int, end: int, source: dict, observation: dict) -> tuple[list[str], int]:
    """Append newly observed tags to the source's `releases:` list.

    The register stays current as a SIDE EFFECT of the thing that already polls
    upstream, rather than as a chore nobody does — which is the same argument that
    produced this plane in the first place.

    What is appended is the version, its ref, its commit, and nothing else. In
    particular NO `changes_contract`: what a release moved is a human judgement about
    behaviour, and a detector that guessed it from the version number would be
    manufacturing the exact false assurance this plane exists to remove. A newly
    appended release is contract-SILENT until someone reviews it.
    """
    known = {str(r.get("version")) for r in source.get("releases") or []}
    aliases = {v for versions in (observation.get("tag_aliases") or {}).values() for v in versions[1:]}
    fresh = [v for v in distinct_versions(observation) if v not in known and v not in aliases]
    if not fresh:
        return lines, end

    item_indent = " " * (len(lines[start]) - len(lines[start].lstrip()) + 2)
    entry_indent = item_indent + "  "
    commits = observation.get("tag_commits") or {}
    # A dropped alias must be RECORDED, not merely dropped. Otherwise 0.4.42's absence
    # from the chain looks like an oversight, and the next reader "fixes" it by adding a
    # release that is not an artifact — re-inflating every gap through that range by one.
    alias_of = {kept: rest for versions in (observation.get("tag_aliases") or {}).values()
                for kept, *rest in [sorted(versions, key=lambda v: semver(v) or (0, 0, 0))]}

    anchor = None
    for index in range(start + 1, end):
        if re.match(rf"^{re.escape(item_indent)}releases:\s*$", lines[index]):
            anchor = index
            break
    block: list[str] = []
    if anchor is None:
        block.append(f"{item_indent}releases:")
    for version in fresh:
        block.extend([
            f"{entry_indent}- version: '{version}'",
            f"{entry_indent}  ref: v{version}",
            f"{entry_indent}  commit: {commits.get(version, 'unknown')[:7]}",
        ])
        if alias_of.get(version):
            block.append(
                f"{entry_indent}  also_tagged: [{', '.join('v' + v for v in alias_of[version])}]"
            )
        block.extend([
            f"{entry_indent}  observed_by: detect_vendor_freshness.py on {observation['observed_at']}",
            f"{entry_indent}  contract_review: pending",
        ])
    if anchor is None:
        lines[end:end] = block
        return lines, end + len(block)
    stop = anchor + 1
    while stop < end and lines[stop].strip() and (len(lines[stop]) - len(lines[stop].lstrip())) > len(item_indent):
        stop += 1
    lines[stop:stop] = block
    return lines, end + len(block)


def rewrite_register(path: Path, observations: dict[str, dict], proposals: list[dict] | None = None) -> bool:
    """Rewrite only the observed fields. Returns True when the file changed."""
    original = path.read_text(encoding="utf-8")
    data = yaml.safe_load(original) or {}
    by_id = {s.get("source_id"): s for s in data.get("sources") or [] if isinstance(s, dict)}
    lines = original.splitlines()
    if proposals:
        lines = propose_dispositions(lines, proposals)
    for source_id, observation in observations.items():
        if not observation.get("ok"):
            continue
        bounds = block_bounds(lines, source_id)
        if bounds is None:
            continue
        start, end = bounds
        if observation.get("tags"):
            lines, end = append_releases(lines, start, end, by_id.get(source_id, {}), observation)
        for key in ("upstream_latest_version", "upstream_latest_ref", "upstream_latest_commit"):
            if observation.get(key):
                lines, end = set_scalar(lines, start, end, key, observation[key])
        lines, end = set_scalar(lines, start, end, "observed_at", observation["observed_at"], quote=True)
        lines, end = set_folded(lines, start, end, "observation_method", observation["observation_method"])
    updated = "\n".join(lines) + "\n"
    if updated != original:
        path.write_text(updated, encoding="utf-8")
        return True
    return False


# ── reporting ────────────────────────────────────────────────────────────────

def render_summary(results: list[dict], observations: dict[str, dict], plans: list[dict],
                   proposals: list[dict] | None = None) -> str:
    out = ["# Vendor freshness detection", ""]

    out.append("## Upstream observation")
    out.append("")
    out.append("| source | scheme | observed | result |")
    out.append("|---|---|---|---|")
    for source_id, observation in sorted(observations.items()):
        if observation.get("ok"):
            latest = observation.get("upstream_latest_version") or (observation.get("upstream_latest_commit") or "")[:12]
            result = f"latest `{latest}`"
        elif observation.get("skipped"):
            result = f"skipped — {observation['skipped']}"
        else:
            result = f"**UNOBSERVED** — {observation.get('error', 'unknown')}"
        out.append(f"| `{source_id}` | {observation.get('version_scheme')} | {observation.get('observed_at')} | {result} |")
    out.append("")

    out.append("## Recomputed state")
    out.append("")
    out.append("| artifact | tier | policy | computed | declared | agrees |")
    out.append("|---|---|---|---|---|---|")
    for entry in results:
        agrees = "yes" if entry["agrees"] else "**NO**"
        out.append(
            f"| `{entry['artifact_id']}` | {entry.get('tier', '-')} | {entry['policy']} | "
            f"{entry['state']} | {entry['disposition']} | {agrees} |"
        )
    out.append("")

    if proposals:
        out.append("## Disposition changes proposed")
        out.append("")
        out.append("An observation made a declared position false. Filed automatically so the")
        out.append("register stays internally consistent; re-triage freely.")
        out.append("")
        out.append("| artifact | was | now | finding | due |")
        out.append("|---|---|---|---|---|")
        for p in proposals:
            out.append(f"| `{p['artifact_id']}` | {p['was']} | {p['disposition']} | "
                       f"{p.get('finding_id', '-')} | {p.get('due', '-')} |")
        out.append("")

    if plans:
        out.append(f"## Re-vendor plans emitted: {len(plans)}")
        out.append("")
        for plan in plans:
            params = plan["parameters"]
            out.append(f"### `{params['artifactId']}` — {params['fromVersion']} → {params['toVersion']}")
            out.append("")
            out.append(f"- gap: **{params['gapSize']}** release(s) — {', '.join(params['gapReleases']) or 'n/a'}")
            out.append(f"- blast radius: **{params['blastRadius']}** consumer app(s) — "
                       + ", ".join(f"`{a['consumer_app']}`" for a in params["blastRadiusApps"]))
            out.append(f"- crosses contract: **{params['crossesContract']}**"
                       + (f" ({', '.join(params['contractKinds'])})" if params["contractKinds"] else ""))
            for crossing in params["contractCrossings"]:
                out.append(f"  - `{crossing['version']}` [{crossing['contract_kind']}] {crossing['note']}")
            marker = params["versionMarker"]
            if marker.get("marker"):
                out.append(f"- version marker to assert inside `{marker['assertInside']}`: "
                           f"`{marker['marker']}` (present in {marker['presentIn']}, absent in {marker['absentIn']})")
            out.append(f"- requires human approval: **{plan['requiresHumanApproval']}**")
            out.append("")
    else:
        out.append("## Re-vendor plans emitted: 0")
        out.append("")
        out.append("No artifact is behind its declared freshness policy.")
        out.append("")
    return "\n".join(out) + "\n"


# ── entrypoint ───────────────────────────────────────────────────────────────

REMEDIATION_SLA_DAYS = {"foundation": 30, "reference": 90}


def propose_for(artifact: dict, state: str, reason: str, observation: dict | None,
                today: date, register_text: str, taken: list[str]) -> dict | None:
    """The weakest disposition that is defensible for the computed state."""
    from validate_vendor_freshness import AGREEMENT
    if artifact.get("disposition") in AGREEMENT.get(state, set()):
        return None
    tier = artifact.get("tier", "reference")
    if state == "stale":
        finding = next_finding_id(register_text + "\n".join(taken))
        taken.append(f"finding_id: {finding}")
        return {
            "artifact_id": artifact.get("artifact_id"), "disposition": "remediation-required",
            "finding_id": finding, "tier": tier, "reason": reason,
            "target_version": ((observation or {}).get("upstream_latest_version")
                               or (observation or {}).get("upstream_latest_commit") or "unknown"),
            "due": (today + timedelta(days=REMEDIATION_SLA_DAYS.get(tier, 90))).isoformat(),
            "detected_on": today.isoformat(), "was": artifact.get("disposition"),
        }
    if state in ("unknown", "current"):
        return {
            "artifact_id": artifact.get("artifact_id"),
            "disposition": "observation-required" if state == "unknown" else "current",
            "tier": tier, "reason": reason, "detected_on": today.isoformat(),
            "was": artifact.get("disposition"),
        }
    return None


def run(register_path: Path, today: date, only: set[str], offline: Path | None) -> tuple[dict, list[dict], list[dict], list[dict]]:
    register_text = register_path.read_text(encoding="utf-8")
    data = yaml.safe_load(register_text)
    sources = {s["source_id"]: s for s in data.get("sources") or [] if isinstance(s, dict) and s.get("source_id")}
    artifacts = [a for a in data.get("artifacts") or [] if isinstance(a, dict)]

    if offline is not None:
        recorded = json.loads(offline.read_text(encoding="utf-8"))
        observations = {k: v for k, v in recorded.items() if not only or k in only}
    else:
        observations = {
            source_id: observe_source(source, today)
            for source_id, source in sources.items()
            if not only or source_id in only
        }

    results: list[dict] = []
    plans: list[dict] = []
    proposals: list[dict] = []
    taken: list[str] = []
    for artifact in artifacts:
        source_id = artifact.get("source_id")
        source = sources.get(source_id)
        if source is None:
            continue
        observation = observations.get(source_id)
        effective = apply_observation(source, observation) if observation else source
        state, reason = compute_state(artifact, effective)
        disposition = artifact.get("disposition")
        # Whether the DECLARED position still holds against what upstream actually
        # says today. This is the same question the gate asks; here it is a report.
        from validate_vendor_freshness import AGREEMENT
        agrees = disposition in AGREEMENT.get(state, set())
        results.append({
            "artifact_id": artifact.get("artifact_id"),
            "tier": artifact.get("tier"),
            "policy": artifact.get("freshness_policy"),
            "state": state, "reason": reason,
            "disposition": disposition, "agrees": agrees,
        })
        if not agrees:
            proposal = propose_for(artifact, state, reason, observation, today, register_text, taken)
            if proposal:
                proposals.append(proposal)
        if state == "stale" and observation and (observation.get("ok") or offline is not None):
            plans.append(build_plan(artifact, effective, observation, artifacts, state, reason, today))
    return observations, results, plans, proposals


def main() -> int:
    parser = argparse.ArgumentParser(description="Observe upstream and emit re-vendor plans.")
    parser.add_argument("--register", type=Path, default=REGISTER)
    parser.add_argument("--source", action="append", default=[], help="Restrict to one source_id (repeatable).")
    parser.add_argument("--offline", type=Path, default=None, metavar="OBSERVATIONS_JSON",
                        help="Replay recorded observations instead of touching the network.")
    parser.add_argument("--write-register", action="store_true",
                        help="Rewrite the observed fields in place, preserving comments.")
    parser.add_argument("--propose-disposition", action="store_true",
                        help="With --write-register: when an observation makes a declared disposition "
                             "false, file the weakest defensible disposition for the computed state, "
                             "with a tier-derived due date. Keeps the refreshed register internally "
                             "consistent instead of handing a human a red build to repair by hand.")
    parser.add_argument("--emit-plans", type=Path, default=None, metavar="DIR",
                        help="Write one EffectRequest plan JSON per stale artifact.")
    parser.add_argument("--consumer-repo", default=None,
                        help="Only emit plans whose consumer_repo matches (owner/name).")
    parser.add_argument("--observations-out", type=Path, default=None)
    parser.add_argument("--summary", type=Path, default=None, help="Write a markdown summary.")
    parser.add_argument("--today", type=str, default=None)
    parser.add_argument("--fail-on-stale", action="store_true",
                        help="Exit 1 when any artifact is stale. OFF by default: staleness is a "
                             "legitimate state, and a detector that fails the build on drift gets "
                             "switched off. The gate fails on DISAGREEMENT; see validate_vendor_freshness.py.")
    parser.add_argument("--fail-on-unobserved", action="store_true",
                        help="Exit 1 when a non-external source could not be observed.")
    args = parser.parse_args()

    today = parse_date(args.today) or date.today()
    if args.today and parse_date(args.today) is None:
        print(f"ERROR: --today expects YYYY-MM-DD, got {args.today!r}", file=sys.stderr)
        return 1

    try:
        observations, results, plans, proposals = run(args.register, today, set(args.source), args.offline)
    except (OSError, yaml.YAMLError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.consumer_repo:
        plans = [p for p in plans if p["parameters"]["consumerRepo"] == args.consumer_repo]

    for source_id, observation in sorted(observations.items()):
        if observation.get("ok"):
            latest = observation.get("upstream_latest_version") or observation.get("upstream_latest_commit", "")[:12]
            print(f"OBSERVED {source_id}: {latest}")
        elif observation.get("skipped"):
            print(f"SKIPPED  {source_id}: {observation['skipped']}")
        else:
            print(f"UNOBSERVED {source_id}: {observation.get('error')}")

    for entry in results:
        flag = "" if entry["agrees"] else "  <- DISAGREES WITH DECLARED DISPOSITION"
        print(f"{entry['state'].upper():<8} {entry['artifact_id']} [{entry['disposition']}]{flag}")

    for proposal in proposals:
        print(f"PROPOSE {proposal['artifact_id']}: {proposal['was']} -> {proposal['disposition']}"
              + (f" ({proposal['finding_id']}, due {proposal['due']})" if proposal.get("finding_id") else ""))

    if args.write_register:
        changed = rewrite_register(args.register, observations, proposals if args.propose_disposition else None)
        print(f"register {'updated' if changed else 'unchanged'}: {args.register}")

    if args.observations_out:
        args.observations_out.parent.mkdir(parents=True, exist_ok=True)
        args.observations_out.write_text(json.dumps(observations, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.emit_plans:
        args.emit_plans.mkdir(parents=True, exist_ok=True)
        for plan in plans:
            name = plan["parameters"]["artifactId"].replace("/", "_").replace("@", "_at_")
            (args.emit_plans / f"{name}.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
        print(f"emitted {len(plans)} re-vendor plan(s) to {args.emit_plans}")

    if args.summary:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(render_summary(results, observations, plans, proposals), encoding="utf-8")

    unobserved = [k for k, v in observations.items() if not v.get("ok") and not v.get("skipped")]
    if args.fail_on_unobserved and unobserved:
        print(f"FAILED: {len(unobserved)} source(s) could not be observed: {sorted(unobserved)}", file=sys.stderr)
        return 1
    if args.fail_on_stale and any(e["state"] == "stale" for e in results):
        print("FAILED: at least one artifact is stale", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
