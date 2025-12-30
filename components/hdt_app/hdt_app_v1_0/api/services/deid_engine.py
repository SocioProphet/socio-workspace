import datetime, hashlib, re, json, yaml, os
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+")
PHONE = re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b")
def _redact_text(s): 
    s = EMAIL.sub("[REDACTED]", s)
    return PHONE.sub("[REDACTED]", s)
def _stable_shift_days(salt, pid, window):
    n = int.from_bytes(hashlib.sha256(f"{salt}|{pid}".encode()).digest()[:4],"big")
    span = 2*window+1; return (n % span) - window
def apply_profile(profile_path, bundle_or_dict, out_path, salt="HDT_STABLE"):
    cfg = yaml.safe_load(open(profile_path))
    b = bundle_or_dict if isinstance(bundle_or_dict, dict) else json.load(open(bundle_or_dict))
    out = {"resourceType": b.get("resourceType","Bundle"), "type": b.get("type","collection"), "entry": []}
    win = cfg.get("shift_dates",{}).get("window_days",0)
    # Build Patient shifts
    shifts = {}
    for e in b.get("entry",[]):
        r = e.get("resource",{})
        if r.get("resourceType")=="Patient":
            pid = r.get("id") or ""
            shifts[pid] = _stable_shift_days(salt, pid, win) if cfg.get("shift_dates",{}).get("enable") else 0
    for e in b.get("entry",[]):
        r = e.get("resource",{}).copy()
        rt = r.get("resourceType")
        if rt=="Observation":
            subj = (r.get("subject") or {}).get("reference","")
            pid = subj.split("/")[-1] if subj else ""
            if cfg.get("shift_dates",{}).get("enable") and r.get("effectiveDateTime"):
                try:
                    dt = datetime.datetime.fromisoformat(r["effectiveDateTime"].replace("Z","+00:00"))
                    r["effectiveDateTime"] = (dt + datetime.timedelta(days=shifts.get(pid,0))).isoformat().replace("+00:00","Z")
                except Exception: pass
            if cfg.get("free_text_redact"):
                for k,v in list(r.items()):
                    if isinstance(v,str): r[k]=_redact_text(v)
        out["entry"].append({"resource": r})
    json.dump(out, open(out_path,"w"), indent=2)
