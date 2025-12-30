
from typing import Tuple, Dict, Any
UCUM_MAP={'%':{'unit':'%','factor':1.0},'mg/dL':{'unit':'mg/dL','factor':1.0},'mmol/L':{'unit':'mmol/L','factor':1.0}}
def normalize_observation(obs: Dict[str, Any]) -> Tuple[Dict[str, Any], list]:
    issues=[]; out=dict(obs); vq=(obs or {}).get('valueQuantity')
    if not vq: issues.append('no_valueQuantity'); return out, issues
    unit=vq.get('unit'); 
    if unit not in UCUM_MAP: issues.append(f'unknown_unit:{unit}'); return out, issues
    vq2=dict(vq); vq2['unit']=UCUM_MAP[unit]['unit']; out['valueQuantity']=vq2; return out, issues
