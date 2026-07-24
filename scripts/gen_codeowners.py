#!/usr/bin/env python3
"""Generate a repo's CODEOWNERS from the single maintainers registry (OPS-R17).
Usage: gen_codeowners.py <repo-name>   ->  prints CODEOWNERS to stdout.
"""
import sys, tomllib, pathlib

repo = sys.argv[1]
reg = pathlib.Path(__file__).resolve().parent.parent / "70-operations" / "maintainers.toml"
data = tomllib.load(open(reg, "rb"))

lines = [
    "# GENERATED from lemonfiber/spec 70-operations/maintainers.toml — do not edit by hand.",
    "# Regenerate: python3 scripts/gen_codeowners.py <repo>",
    "",
]
# Default owners: maintainers whose scope covers this repo with domains "*".
default = []
scoped = []  # (path_glob, handle)
for m in data.get("maintainer", []):
    scope, domains, handle = m["scope"], m["domains"], "@" + m["handle"]
    covers = "*" in scope or repo in scope
    if not covers:
        continue
    if "*" in domains:
        default.append(handle)
    else:
        for d in domains:
            if d.startswith(f"{repo}/"):
                scoped.append((d[len(repo) + 1:], handle))
if default:
    lines.append("* " + " ".join(dict.fromkeys(default)))
for glob, handle in scoped:
    lines.append(f"/{glob} {handle}")
print("\n".join(lines) + "\n")
