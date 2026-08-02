#!/usr/bin/env python3
"""Guard: every first-party RDF graph must parse with rdflib.

Surfaced by SocioProphet/sociosphere#527: 5 first-party Turtle graphs in this
repo (ontologies/sociosphere.ttl plus four neurosymbolic repo-graph fixtures)
carried a slash-in-prefixed-name syntax error and failed rdflib parse. The
existing `check_neurosymbolic_repo_graph_ttl_fixtures.py` compares fields with a
regex, so it never loaded the graphs and never caught the syntax bug. This check
closes that hole: it rdflib-parses every first-party `*.ttl`/`*.jsonld` and fails
on any parse error, so an unparseable graph cannot be reintroduced.

Scope: first-party graphs only. Vendored/external trees (`node_modules`,
`third_party`, `vendor*`, `@`-pinned worktree dirs, `*.wt`) are skipped.

Negative fixtures: a fixture that is *intentionally* invalid Turtle (a syntax
negative) must be listed in NEGATIVE_SYNTAX_FIXTURES with a reason. Such a file
is expected to FAIL to parse; if one ever starts parsing, this check fails so the
declaration stays honest. NOTE: a semantically-negative fixture (e.g. the
`invalid.*` repo-graph fixtures, which model a governance state that should be
blocked) is still syntactically valid Turtle and MUST parse -- it is NOT listed
here.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

# File extension -> rdflib parse format.
FORMATS = {".ttl": "turtle", ".jsonld": "json-ld"}

# Directory names that mark vendored / external / non-first-party trees.
EXCLUDE_DIR_NAMES = {"node_modules", ".git", "third_party", "vendor", "vendored"}

# Intentional SYNTAX-negative fixtures: expected to fail rdflib parse.
# Map "<relative/path>": "<why it is intentionally invalid>".
# Empty today -- this repo has no Turtle-syntax negatives. (The `invalid.*`
# repo-graph fixtures are semantic negatives and parse fine.)
NEGATIVE_SYNTAX_FIXTURES: dict[str, str] = {}


def _excluded(path: Path) -> bool:
    for part in path.relative_to(ROOT).parts:
        if part in EXCLUDE_DIR_NAMES:
            return True
        if part.startswith("@"):
            return True
        if part.endswith(".wt"):
            return True
    return False


def _iter_graphs():
    for ext in FORMATS:
        for path in ROOT.rglob(f"*{ext}"):
            if _excluded(path):
                continue
            yield path


def main() -> int:
    from rdflib import Graph  # imported here so a missing dep gives a clear message

    failed = False
    checked = 0
    negatives_seen: set[str] = set()

    for path in sorted(_iter_graphs()):
        rel = path.relative_to(ROOT).as_posix()
        fmt = FORMATS[path.suffix.lower()]
        expected_negative = rel in NEGATIVE_SYNTAX_FIXTURES
        try:
            Graph().parse(str(path), format=fmt)
            parsed = True
            err = ""
        except Exception as exc:  # rdflib raises many parser-specific types
            parsed = False
            err = f"{type(exc).__name__}: {exc}"

        if expected_negative:
            negatives_seen.add(rel)
            if parsed:
                print(
                    f"ERR: {rel} is declared a syntax-negative fixture but now PARSES; "
                    "remove it from NEGATIVE_SYNTAX_FIXTURES or restore its negative intent.",
                    file=sys.stderr,
                )
                failed = True
            continue

        checked += 1
        if not parsed:
            print(f"ERR: {rel} failed to parse ({fmt}): {err}", file=sys.stderr)
            failed = True

    missing = set(NEGATIVE_SYNTAX_FIXTURES) - negatives_seen
    for rel in sorted(missing):
        print(
            f"ERR: declared syntax-negative fixture not found on disk: {rel}",
            file=sys.stderr,
        )
        failed = True

    if failed:
        return 1

    print(
        f"OK: all {checked} first-party RDF graph(s) parse "
        f"({len(negatives_seen)} declared syntax-negative fixture(s) skipped)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
