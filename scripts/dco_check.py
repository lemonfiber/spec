#!/usr/bin/env python3
"""Verify every commit in base..head carries a Signed-off-by matching its author.
Implements GOV-R29/GOV-R30. Usage: dco_check.py <base_sha> <head_sha>
"""
import subprocess, sys, re

base, head = sys.argv[1], sys.argv[2]
_REF = re.compile(r"\A[0-9A-Za-z._/-]{1,255}\Z")
if not (_REF.match(base) and _REF.match(head)):
    sys.exit("dco_check: base and head must be valid git refs")
fmt = "%H%x00%an%x00%ae%x00%P%x00%b%x01"
out = subprocess.run(["git", "log", f"--format={fmt}", f"{base}..{head}"],
                     capture_output=True, text=True, check=True).stdout


def is_bot(name: str, email: str) -> bool:
    return name.endswith("[bot]") or "[bot]@" in email or email == "noreply@github.com"


problems = []
for rec in filter(None, out.split("\x01\n")):
    parts = rec.strip("\x01\n").split("\x00")
    if len(parts) < 5:
        continue
    sha, an, ae, parents, body = parts[0], parts[1], parts[2], parts[3], parts[4]
    # Merge commits (more than one parent) and bot-authored commits carry no
    # sign-off by design — GitHub authors them (branch updates, auto-merges), so
    # there is no human to attest. Exempt both rather than block on the
    # unattestable.
    if " " in parents.strip() or is_bot(an, ae):
        continue
    signoffs = re.findall(r"^Signed-off-by:[^<]*<([^>]+)>\s*$", body, re.M)
    if not any(email.lower() == ae.lower() for email in signoffs):
        problems.append(f"{sha[:8]} by {an} <{ae}> lacks a matching Signed-off-by")

if problems:
    print("::error::DCO sign-off missing:")
    for p in problems:
        print(f"  {p}")
    print("\nAdd it with: git commit -s   (see spec 50-governance/dco.md)")
    sys.exit(1)
print("DCO: all commits signed off")
