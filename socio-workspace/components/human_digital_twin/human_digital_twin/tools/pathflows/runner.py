
import json, yaml
from pathlib import Path
try:
    from human_digital_twin.api.services.eval.omega import EvalKFS, promote_omega
except Exception:
    from hdt_app_v1_0.api.services.eval.omega import EvalKFS, promote_omega

def run_scenario(name: str, steps=5):
    prev="ABSENT"; meta={}
    for k in range(steps):
        kfs=EvalKFS(m_cbd=0.6+0.1*k, m_cgt=0.55+0.1*k, m_nhy=0.5+0.1*k)
        prev, meta = promote_omega(prev, kfs)
        if prev=="DELIVERED": return prev, k+1, meta
    return prev, steps, meta

if __name__=="__main__":
    sc = list(yaml.safe_load(Path(__file__).with_name("examples.yaml").read_text()))
    out = {}
    for s in sc:
        omega, steps, meta = run_scenario(s["name"], s["expect"]["steps_max"])
        out[s["name"]] = {"omega": omega, "steps": steps, "meta": meta}
    Path("report.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
