
import socket, json, os
from ..services.eval.omega import EvalKFS, promote_omega
SOCK_PATH = "/tmp/human_digital_twin.sock"
def run_shim():
    if os.path.exists(SOCK_PATH): os.remove(SOCK_PATH)
    s=socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); s.bind(SOCK_PATH); os.chmod(SOCK_PATH,0o600); s.listen(1)
    while True:
        c,_=s.accept(); data=c.recv(65536)
        try:
            req=json.loads(data.decode()); 
            if req.get("rpc")=="Evaluate":
                k=EvalKFS(**req.get("kfs",{"m_cbd":0,"m_cgt":0,"m_nhy":0}))
                omega,meta=promote_omega(req.get("prev","ABSENT"),k)
                resp={"ok":True,"omega":omega,**meta}
            else:
                resp={"ok":False,"error":"unsupported rpc"}
        except Exception as e:
            resp={"ok":False,"error":str(e)}
        c.send(json.dumps(resp).encode()); c.close()
if __name__=="__main__": run_shim()
