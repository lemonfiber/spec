#!/usr/bin/env python3
"""Validate feature-doc frontmatter against feature.schema.json.

Checks the required keys, enum membership, the id/area/filename agreement, and the
label registry, and rejects unknown keys. Exit 0 when every feature is valid, 1
with the violations named. Run from the repo root.
"""
import json
import re
import sys
import glob
import pathlib

import metafm

SCHEMA = json.loads(
    pathlib.Path("10-functional/features/_meta/feature.schema.json").read_text(encoding="utf-8")
)
PROPS = SCHEMA["properties"]
REQUIRED = SCHEMA["required"]
LABELS = set(PROPS["labels"]["items"]["enum"])
ID_RE = re.compile(r"^[A-K][0-9]+$")


def enum(name):
    return set(PROPS[name]["enum"])


def problems_for(path):
    fm = metafm.load(path)
    if fm is None:
        return [f"{path}: no frontmatter block"]
    out = []
    for key in REQUIRED:
        if key not in fm:
            out.append(f"{path}: missing required key '{key}'")
    for key in fm:
        if key not in PROPS:
            out.append(f"{path}: unknown key '{key}'")
    for key in ("kind", "area", "audience", "status", "tracks", "priority"):
        if key in fm and fm[key] not in enum(key):
            out.append(f"{path}: {key} = '{fm[key]}' is not an allowed value")
    fid = fm.get("id", "")
    if fid and not ID_RE.match(fid):
        out.append(f"{path}: id '{fid}' is malformed")
    if fid and "area" in fm and fid[:1] != fm["area"]:
        out.append(f"{path}: id '{fid}' does not match area '{fm['area']}'")
    stem = pathlib.Path(path).stem
    if fid and not stem.lower().startswith(fid.lower() + "-"):
        out.append(f"{path}: id '{fid}' does not match filename '{stem}'")
    for label in fm.get("labels", []):
        if label not in LABELS:
            out.append(f"{path}: label '{label}' is not in the registry")
    for dep in fm.get("depends", []):
        if not ID_RE.match(dep):
            out.append(f"{path}: depends entry '{dep}' is malformed")
    return out


def main():
    files = sorted(glob.glob("10-functional/features/[a-k]-*/*.md"))
    problems = []
    for path in files:
        problems.extend(problems_for(path))
    if problems:
        print("frontmatter: problems found:")
        for line in problems:
            print("  " + line)
        return 1
    print(f"frontmatter: {len(files)} feature docs valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
