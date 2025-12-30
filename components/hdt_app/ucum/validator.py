from typing import Tuple, Dict, Any, List
CONV = {
  "2345-7": {"mg/dL": ("mmol/L", 0.0555)},
  "2160-0": {"mg/dL": ("umol/L", 88.4)},
  "2093-3": {"mg/dL": ("mmol/L", 0.0259)},
  "2085-9": {"mg/dL": ("mmol/L", 0.0259)},
  "13457-7": {"mg/dL": ("mmol/L", 0.0259)},
  "2571-8": {"mg/dL": ("mmol/L", 0.0113)},
}
def normalize(code:str, q:Dict[str,Any], allowed:Dict[str,List[str]]):
  unit = (q or {}).get("unit"); val=(q or {}).get("value")
  if unit in (allowed.get(code) or []): return q, []
  conv = (CONV.get(code) or {}).get(unit)
  if conv:
    target, k = conv
    v2 = round(float(val) * k, 4)
    if target in (allowed.get(code) or []):
      return {"value": v2, "unit": target, "system": "http://unitsofmeasure.org"}, [f"Converted {unit}->{target}"]
  return q, [f"Unit {unit} not allowed for {code}"] if unit else []
