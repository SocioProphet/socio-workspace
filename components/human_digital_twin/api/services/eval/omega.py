
from dataclasses import dataclass
from typing import Dict, Any, Tuple

STATES = ["ABSENT","SEEDED","NORMALIZED","LINKED","TRUSTED","ACTIONABLE","DELIVERED"]

@dataclass
class EvalKFS: m_cbd: float; m_cgt: float; m_nhy: float
def clamp01(x: float) -> float: return max(0.0, min(1.0, float(x)))
def promote_omega(prev: str, k: EvalKFS) -> Tuple[str, Dict[str, Any]]:
    s = STATES.index(prev) if prev in STATES else 0
    m_cbd = clamp01(k.m_cbd); m_cgt = clamp01(k.m_cgt); m_nhy = clamp01(k.m_nhy)
    reasons = []
    if s < 1 and (m_cbd > 0 or m_cgt > 0 or m_nhy > 0): s = 1; reasons.append("seeded")
    if s < 2 and m_cbd >= 0.60: s = 2; reasons.append("normalized[cbd>=0.60]")
    if s < 3 and m_cbd >= 0.75: s = 3; reasons.append("linked[cbd>=0.75]")
    if s < 4 and m_cgt >= 0.70: s = 4; reasons.append("trusted[cgt>=0.70]")
    if s < 5 and min(m_cbd,m_cgt,m_nhy) >= 0.75: s = 5; reasons.append("actionable[all>=0.75]")
    if s < 6 and m_nhy >= 0.80: s = 6; reasons.append("delivered[nhy>=0.80]")
    return STATES[s], {"reasons":reasons,"m_cbd":m_cbd,"m_cgt":m_cgt,"m_nhy":m_nhy,"prev":prev if prev in STATES else "ABSENT","next":STATES[s]}
