#!/usr/bin/env python3
"""Verify every commit in base..head carries a Signed-off-by matching its author.
Implements GOV-R29/GOV-R30. Usage: dco_check.py <base_sha> <head_sha>
"""
import subprocess, sys, re

base, head = sys.argv[1], sys.argv[2]
fmt = "%H%x00%an%x00%ae%x00%b%x01"
out = subprocess.run(["git", "log", f"--format={fmt}", f"{base}..{head}"],
                     capture_output=True, text=True, check=True).stdout
problems = []
for rec in filter(None, out.split("\x01\n")):
    parts = rec.strip("\x01\n").split("\x00")
    if len(parts) < 4:
        continue
    sha, an, ae, body = parts[0], parts[1], parts[2], parts[3]
    signoffs = re.findall(r"^Signed-off-by:\s*(.+?)\s*<([^>]+)>\s*$", body, re.M)
    if not any(email.lower() == ae.lower() for _, email in signoffs):
        problems.append(f"{sha[:8]} by {an} <{ae}> lacks a matching Signed-off-by")

if problems:
    print("::error::DCO sign-off missing:")
    for p in problems:
        print(f"  {p}")
    print("\nAdd it with: git commit -s   (see spec 50-governance/dco.md)")
    sys.exit(1)
print("DCO: all commits signed off")
