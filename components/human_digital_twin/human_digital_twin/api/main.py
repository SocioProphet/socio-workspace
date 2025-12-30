
import os, json, uuid
from fastapi import FastAPI, Depends, HTTPException, Body, APIRouter, Header
from pydantic import BaseModel
from .services.deid_engine import apply_profile as deid_apply
from .services.ucum_svc import normalize_observation
from .services.eval.omega import EvalKFS, promote_omega

app = FastAPI(title="Human Digital Twin API")

def auth(x_api_key: str | None = Header(None)):
    expected = os.getenv("API_KEY", "test")
    if x_api_key != expected: raise HTTPException(401, "unauthorized")
    return True

@app.get("/healthz") 
def healthz(): return {"ok": True}

@app.post("/api/v1/ingest/fhir", dependencies=[Depends(auth)])
def ingest_fhir(bundle: dict = Body(...)):
    bid = str(uuid.uuid4()); return {"bundle_id": bid, "entries": len(bundle.get("entry",[]))}

@app.post("/api/v1/export/deid", dependencies=[Depends(auth)])
def export_deid(profile: str = "safe_harbor", bundle: dict = Body(...)):
    prof_path = os.path.join(os.path.dirname(__file__), "profiles", f"{profile}.yaml")
    if not os.path.exists(prof_path): raise HTTPException(400, f"Unknown profile {profile}")
    out_path = "/tmp/out.json"; deid_apply(prof_path, bundle, out_path, salt=os.getenv("DEID_SALT","HDT_STABLE"))
    return json.load(open(out_path))

@app.post("/api/v1/ucum/normalize", dependencies=[Depends(auth)])
def ucum_normalize(observation: dict = Body(...)):
    out, issues = normalize_observation(observation); return {"normalized": out, "issues": issues}

class Consent(BaseModel): subject: str; scope: str; start: str; end: str
_CONSENTS: dict[str, Consent] = {}

@app.post("/api/v1/consent", dependencies=[Depends(auth)])
def create_consent(consent: Consent):
    _CONSENTS[consent.subject] = consent; return {"ok": True, "consent": consent}

eval_router = APIRouter()

@eval_router.post("/api/v1/eval", dependencies=[Depends(auth)])
def eval_resource(payload: dict = Body(...), prev: str = "ABSENT", subject: str | None = None):
    m_cbd = 0.5
    try:
        if payload.get("resourceType") == "Observation":
            _, issues = normalize_observation(payload); m_cbd = max(0.0, 1.0 - min(1.0, len(issues)/5.0))
        else: m_cbd = 0.7
    except Exception: m_cbd = 0.4
    consent_allowed = bool(subject and subject in _CONSENTS); m_cgt = 0.85 if consent_allowed else 0.4
    m_nhy = 0.8 if (consent_allowed and m_cbd >= 0.6) else 0.5
    omega, meta = promote_omega(prev, EvalKFS(m_cbd=m_cbd, m_cgt=m_cgt, m_nhy=m_nhy)); return {"omega": omega, **meta}

app.include_router(eval_router)
