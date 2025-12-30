# HDT App v1.0 — Human Digital Twin (first-class service)

A production-ready scaffold for a self-sovereign **Human Digital Twin** service:
- **FastAPI** core: FHIR ingest, de‑identification export, UCUM normalization, consent storage.
- **Linkage** microservice: candidate generation + adjudication (with a tiny UI).
- **OPA** (optional) policy sidecar for purpose-of-use and break‑glass enforcement.
- **Docker Compose** + **Kubernetes** manifests.
- **Examples** and a one-liner quickstart.

## Quickstart (local)

```bash
# 0) Requirements: Docker / Docker Compose
# 1) Bring the stack up
docker compose up -d
# 2) Open API docs
open http://localhost:8080/docs
# 3) Linkage UI (adjudication)
open http://localhost:8081/ui/
```

### Notable endpoints
- `POST /api/v1/ingest/fhir` — accept a FHIR **Bundle**; persisted for demo in SQLite (or Postgres via env).
- `POST /api/v1/export/deid?profile=safe_harbor` — de‑identify a Bundle (patient‑stable date shift).
- `POST /api/v1/ucum/normalize` — normalize an Observation to allowed UCUM units.
- `POST /api/v1/consent` — store a basic Consent record (demo).
- `GET /healthz` — health probe.

Auth is API‑key (simple demo): set `API_KEY` in env and send `x-api-key: <key>`.

## Run with Postgres & OPA (Compose)
- App (FastAPI) @ :8080
- Linkage (FastAPI) @ :8081
- OPA @ :8181 (optional; app consults if `OPA_URL` is set)
- Postgres @ :5432 (optional; app uses SQLite by default; set `DATABASE_URL` to Postgres)

## Production notes
- Swap SQLite for Postgres by setting `DATABASE_URL=postgresql+psycopg2://...`.
- Mount `ucum/allowed_units_top100.yaml` and OPA policies as ConfigMaps/Secrets in K8s.
- Extend dbt OMOP models outside this app; this service focuses on ingest, consent, de‑id, linkage, UCUM.

MIT licensed. Have fun.
