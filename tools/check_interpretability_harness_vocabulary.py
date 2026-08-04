#!/usr/bin/env python3
"""Keep the harness vocabulary aligned with the registry and with the source.

A vocabulary file that is merely well-formed is decoration. This check binds it to the
two things it describes, so it cannot quietly drift away from either:

  SEMANTIC alignment    the 14 fragment kinds in the TTL must be exactly the 14 the
                        lane registration requires, and the executor's produces /
                        cannot_produce lists must PARTITION them. A fragment kind that
                        appears in neither is one nobody has decided about.

  OPERATIONAL alignment every ih:definedIn path must exist in the executor repo. This
                        is what makes the vocabulary a live index rather than an
                        archaeology of terms: delete or rename a module and the term
                        that pointed at it fails here.

Operational alignment is skipped, not faked, when the executor repo is not checked out
alongside -- CI for this repo does not have it. Set NOETICA_IMPAIR_REPO to force it.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import yaml

try:
    import rdflib
except ImportError:
    print("rdflib not installed; cannot validate the vocabulary graph", file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parents[1]
VOCAB = ROOT / "registry" / "interpretability-harness.vocab.ttl"
REGISTRATION = ROOT / "registry" / "interpretability-harness-registration.yaml"
IH = rdflib.Namespace("https://socioprophet.org/ns/interpretability-harness#")

FRAGMENT_COUNT = 14
REQUIRED_CLAIM_TAGS = {"TagM", "TagT", "TagS", "TagE", "TagG"}


def local(term: rdflib.term.Node) -> str:
    return str(term).rsplit("#", 1)[-1]


def main() -> int:
    errors: list[str] = []
    notes: list[str] = []

    g = rdflib.Graph()
    g.parse(VOCAB, format="turtle")
    reg = yaml.safe_load(REGISTRATION.read_text(encoding="utf-8"))
    surfaces = reg["surfaces"]
    execution = surfaces.get("execution")
    if not execution:
        return _fail(["lane has no execution surface; the executor is unregistered"])

    # ── semantic: fragment kinds partition correctly ─────────────────────────
    kinds = {local(s) for s in g.subjects(rdflib.RDF.type, IH.FragmentKind)}
    required = set(surfaces["tier2_binding"]["required_fragments"])

    if len(kinds) != FRAGMENT_COUNT:
        errors.append(f"vocabulary declares {len(kinds)} fragment kinds, expected {FRAGMENT_COUNT}")
    if kinds != required:
        for missing in sorted(required - kinds):
            errors.append(f"fragment kind {missing!r} is bound by the tier-2 schema but absent from the vocabulary")
        for extra in sorted(kinds - required):
            errors.append(f"vocabulary declares fragment kind {extra!r} which the tier-2 binding does not bind")

    produces = set(execution.get("produces_fragments") or [])
    cannot = set(execution.get("cannot_produce") or {})
    overlap = produces & cannot
    if overlap:
        errors.append(f"executor both produces and cannot produce {sorted(overlap)}")
    undecided = required - produces - cannot
    if undecided:
        errors.append(
            f"fragment kind(s) {sorted(undecided)} appear in neither produces_fragments "
            "nor cannot_produce -- an undecided fragment is a gap nobody has looked at"
        )

    # The TTL's own producibility flags must agree with the registration.
    flagged_false = {
        local(s) for s, o in g.subject_objects(IH.producibleByExecutor)
        if str(o).lower() == "false"
    }
    if flagged_false != cannot:
        errors.append(
            f"vocabulary marks {sorted(flagged_false)} as not producible but the lane "
            f"registration says {sorted(cannot)}"
        )

    # ── semantic: every claim tag owes evidence ──────────────────────────────
    tags = {local(s) for s in g.subjects(rdflib.RDF.type, IH.ClaimTag)}
    if missing_tags := REQUIRED_CLAIM_TAGS - tags:
        errors.append(f"claim tag(s) missing from the vocabulary: {sorted(missing_tags)}")
    for tag in sorted(tags):
        node = IH[tag]
        if not list(g.objects(node, IH.requiresEvidence)):
            errors.append(f"claim tag {tag} declares no requiresEvidence; an untagged obligation is not enforceable")

    # ── operational: every definedIn path resolves ───────────────────────────
    paths = sorted({str(o) for o in g.objects(None, IH.definedIn)})
    exec_repo = os.environ.get("NOETICA_IMPAIR_REPO") or str(Path.home() / "dev" / "noetica-impair")
    exec_root = Path(exec_repo)
    if exec_root.is_dir():
        for rel in paths:
            if not (exec_root / rel).exists():
                errors.append(f"ih:definedIn points at {rel!r} which does not exist in {exec_root}")
        notes.append(f"operational alignment checked against {exec_root} ({len(paths)} path(s))")
    else:
        notes.append(
            f"executor repo not checked out at {exec_root}; {len(paths)} ih:definedIn "
            "path(s) NOT verified (set NOETICA_IMPAIR_REPO to force)"
        )

    # ── every declared class says what it means ──────────────────────────────
    for cls in g.subjects(rdflib.RDF.type, rdflib.RDFS.Class):
        if not list(g.objects(cls, rdflib.RDFS.comment)):
            errors.append(f"class {local(cls)} carries no rdfs:comment; a term without a definition is a label")

    if errors:
        return _fail(errors, notes)
    print(f"interpretability harness vocabulary OK: {len(g)} triples, "
          f"{len(kinds)}/{FRAGMENT_COUNT} fragment kinds aligned with the tier-2 binding, "
          f"{len(produces)} produced / {len(cannot)} structurally unavailable")
    for n in notes:
        print(f"  note: {n}")
    return 0


def _fail(errors: list[str], notes: list[str] | None = None) -> int:
    print("interpretability harness vocabulary FAILED", file=sys.stderr)
    for e in errors:
        print(f"  - {e}", file=sys.stderr)
    for n in notes or []:
        print(f"  note: {n}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
