import json, yaml, sys

def evaluate(inp):
    # Very simplified stand-in for OPA evaluation.
    server = inp["server"]; tool = inp["tool"]
    allowed = {"fs.introspect/list", "fs.introspect/hash", "net.observe/flows", "policy.eval/rego_eval"}
    key = f"{server}/{tool}"
    if key not in allowed: return False
    # Quorum for egress (not allowed in allowed-set above anyway)
    return True

def main():
    data = yaml.safe_load(open("Tests/golden_requests.yaml"))
    for test in data["tests"]:
        got = {"allow": evaluate(test["input"])}
        ok = got == test["expect"]
        print(f"{'PASS' if ok else 'FAIL'} - {test['name']} -> {got} expected {test['expect']}")
        if not ok: sys.exit(1)

if __name__ == "__main__":
    main()
