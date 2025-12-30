import os, json, uuid
from fastapi import FastAPI, Depends, HTTPException, Header, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator
import httpx, yaml

from .services.deid_engine import apply_profile as deid_apply
from .services.ucum_svc import normalize_observation

API_KEY = os.getenv("API_KEY","changeme")
OPA_URL = os.getenv("OPA_URL","")
LINKAGE_URL = os.getenv("LINKAGE_URL","http://localhost:8081")

app = FastAPI(title="HDT App v1.0")

Instrumentator().instrument(app).expose(app)

def auth(x_api_key: str = Header(None)):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")

@app.get("/healthz")
def healthz(): return {"ok": True}

# --- FHIR ingest (demo: echo with id) ---
@app.post("/api/v1/ingest/fhir", dependencies=[Depends(auth)])
def ingest_fhir(bundle: dict = Body(...)):
    bid = str(uuid.uuid4())
    # demo: just return an id; add DB persistence in your deployment
    return {"bundle_id": bid, "entries": len(bundle.get("entry",[]))}

# --- De-ID export ---
@app.post("/api/v1/export/deid", dependencies=[Depends(auth)])
def export_deid(profile: str = "safe_harbor", bundle: dict = Body(...)):
    prof_path = os.path.join(os.path.dirname(__file__), "profiles", f"{profile}.yaml")
    if not os.path.exists(prof_path):
        raise HTTPException(400, f"Unknown profile {profile}")
    out_path = "/tmp/out.json"
    deid_apply(prof_path, bundle, out_path, salt=os.getenv("DEID_SALT","HDT_STABLE"))
    return json.load(open(out_path))

# --- UCUM normalize ---
@app.post("/api/v1/ucum/normalize", dependencies=[Depends(auth)])
def ucum_normalize(observation: dict = Body(...)):
    out, issues = normalize_observation(observation)
    return {"normalized": out, "issues": issues}

# --- Consent (demo) ---
class Consent(BaseModel):
    subject: str
    scope: str
    start: str
    end: str

@app.post("/api/v1/consent", dependencies=[Depends(auth)])
def create_consent(consent: Consent):
    # demo only; persist in your DB
    return {"ok": True, "consent": consent}
