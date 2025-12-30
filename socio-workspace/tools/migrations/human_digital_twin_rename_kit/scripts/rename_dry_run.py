#!/usr/bin/env python3
import sys, re
from pathlib import Path

PATTERNS = [
    (r'\bhdt_app_v1_0\b', 'human_digital_twin'),
    (r'\bHDT App v1\.0\b', 'human-digital-twin'),
    (r'\bHDT\b', 'Human Digital Twin'),
]

TEXT_EXTS = {'.py','.ts','.tsx','.vue','.go','.json','.yaml','.yml','.rego','.md','.txt','.sh','.ini','.toml','.Dockerfile'}

def scan(root: Path):
    changes = []
    for p in root.rglob('*'):
        if p.is_file():
            if p.suffix in TEXT_EXTS or p.name == 'Dockerfile':
                try:
                    s = p.read_text(encoding='utf-8', errors='ignore')
                except Exception:
                    continue
                replaced = s
                hits = []
                for pat, repl in PATTERNS:
                    if re.search(pat, replaced):
                        replaced = re.sub(pat, repl, replaced)
                        hits.append(pat)
                if hits and replaced != s:
                    changes.append((p, hits, replaced))
    return changes

def main():
    if len(sys.argv) < 2:
        print("usage: rename_dry_run.py <repo_root> [--apply]")
        sys.exit(1)
    root = Path(sys.argv[1]).resolve()
    apply = len(sys.argv) > 2 and sys.argv[2] == "--apply"
    changes = scan(root)
    print(f"# files to change: {len(changes)}")
    for p, hits, replaced in changes:
        print(f"- {p} :: {len(hits)} patterns")
        if apply:
            p.write_text(replaced)
    if apply:
        print("[ok] applied textual replacements")

if __name__ == "__main__":
    main()