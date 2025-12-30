#!/usr/bin/env python3
import json, sys, hashlib, binascii, os
from nacl.signing import VerifyKey
def verify(path):
    o=json.load(open(path)); u={"type":o["type"],"time":o["time"],"payload":o["payload"],"dryRun":o["dryRun"]}
    h=hashlib.sha256(json.dumps(u,separators=(",",":"),ensure_ascii=False).encode()).digest()
    sig=binascii.unhexlify(o["sig"]); pub=binascii.unhexlify(o["pub"])
    VerifyKey(pub).verify(h,sig); return True
if __name__=="__main__":
    d="out/carriers"; ok=0; fail=0
    if os.path.isdir(d):
        for n in os.listdir(d):
            if n.endswith(".json"):
                try: 
                    if verify(os.path.join(d,n)): ok+=1
                except Exception: fail+=1
    print(json.dumps({"verified":ok,"failed":fail}))