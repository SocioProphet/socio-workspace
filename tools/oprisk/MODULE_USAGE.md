# Module Usage for Software Operational Risk Tools

The tools in `tools/oprisk/` use package-relative imports.
To avoid brittle direct-script execution, run them as modules from the repository root.

## Shape validation

```bash
python -m tools.oprisk.validate_jsonl_shapes \
  registry/software_oprisk/outage_corpus.seed.jsonl
```

## Canonical schema binding checks

```bash
python -m tools.oprisk.check_schema_bindings \
  --contracts-root /path/to/sourceos-spec
```

## Canonical schema validation

```bash
python -m tools.oprisk.validate_jsonl_contracts \
  --contracts-root /path/to/sourceos-spec \
  --target outage_corpus \
  registry/software_oprisk/outage_corpus.seed.jsonl
```

## Note

The canonical schema validation path requires a local environment with the `jsonschema` Python package available and a local checkout of `SourceOS-Linux/sourceos-spec`.
