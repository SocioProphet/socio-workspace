
import json, yaml, copy
from typing import Dict, Any
PHI_PATHS = {"name","birthDate","address","telecom","identifier"}
def apply_profile(profile_path: str, bundle: Dict[str, Any], out_path: str, salt: str = "HDT_STABLE") -> None:
    prof = yaml.safe_load(open(profile_path)) or {}
    remove = set(prof.get("remove_fields", [])) | PHI_PATHS
    def scrub(o):
        if isinstance(o, dict): return {k: scrub(v) for k,v in o.items() if k not in remove}
        if isinstance(o, list): return [scrub(x) for x in o]
        return o
    json.dump(scrub(copy.deepcopy(bundle)), open(out_path,"w"), indent=2)
