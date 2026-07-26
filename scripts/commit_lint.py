#!/usr/bin/env python3
"""Enforce conventional-commit subjects on PR commits (OPS-R11), so the
generated changelog stays clean. Usage: commit_lint.py <base_sha> <head_sha>
"""
import subprocess, sys, re
base, head = sys.argv[1], sys.argv[2]
_REF = re.compile(r"\A[0-9A-Za-z._/-]{1,255}\Z")
if not (_REF.match(base) and _REF.match(head)):
    sys.exit("commit_lint: base and head must be valid git refs")
TYPES = "feat|fix|docs|refactor|test|chore|ci|perf|build|style|revert"
subject_re = re.compile(rf"^(?:{TYPES})(?:\([a-z0-9.\-]+\))?!?: .+")
out = subprocess.run(["git", "log", "--format=%H%x00%s", f"{base}..{head}"],
                     capture_output=True, text=True, check=True).stdout
bad = []
for line in filter(None, out.splitlines()):
    sha, _, subj = line.partition("\x00")
    if subj.startswith(("Merge ", "Revert ")):
        continue
    if not subject_re.match(subj):
        bad.append(f"{sha[:8]} {subj}")
if bad:
    print("::error::commit subjects must be conventional (type: subject):")
    for b in bad:
        print(f"  {b}")
    print(f"\n  types: {TYPES.replace('|', ', ')}")
    print("  e.g.  feat: health-gate service startup")
    sys.exit(1)
print("commit-lint: all subjects conventional")
