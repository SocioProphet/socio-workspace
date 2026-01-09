#!/usr/bin/env python3
import argparse, subprocess, sys
from pathlib import Path

def run(cmd, cwd: Path):
    p = subprocess.run(cmd, cwd=str(cwd), text=True)
    return p.returncode

def main() -> int:
    root = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser(prog="tools/validate.py")
    ap.add_argument("--standards", action="store_true", help="Run standards validators")
    ap.add_argument("--qes", action="store_true", help="Run QES contract validation")
    args = ap.parse_args()

    # Default behavior: if no flags, do standards.
    if not (args.standards or args.qes):
        args.standards = True

    rc = 0

    # Standards currently includes QES.
    if args.standards:
        args.qes = True

    if args.qes:
        tool = root / "standards" / "qes" / "tools" / "validate_qes_contracts.py"
        if not tool.exists():
            print(f"ERR: missing QES validator: {tool}", file=sys.stderr)
            return 2
        # Run with python3 to avoid exec-bit differences.
        rc = rc or run(["python3", str(tool)], cwd=root)

    return int(rc)

if __name__ == "__main__":
    raise SystemExit(main())
