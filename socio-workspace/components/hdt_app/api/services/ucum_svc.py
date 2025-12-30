import yaml, os, json
from ucum.validator import normalize as _norm
def normalize_observation(obs: dict):
    path = os.path.join(os.path.dirname(__file__), "..","..","ucum","allowed_units_top100.yaml")
    allowed = yaml.safe_load(open(path))
    o = dict(obs)
    issues = []
    # valueQuantity or components
    if "component" in o:
        for c in o["component"]:
            for cd in c.get("code",{}).get("coding",[]):
                if cd.get("system")=="http://loinc.org":
                    nq, iss = _norm(cd.get("code"), c.get("valueQuantity",{}), allowed)
                    c["valueQuantity"] = nq; issues += iss
    elif "code" in o and "valueQuantity" in o:
        for cd in o["code"].get("coding",[]):
            if cd.get("system")=="http://loinc.org":
                nq, iss = _norm(cd.get("code"), o.get("valueQuantity",{}), allowed)
                o["valueQuantity"] = nq; issues += iss
    return o, issues
