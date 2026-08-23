#!/usr/bin/env python3
"""Validate feature-doc frontmatter against feature.schema.json.

Checks the required keys, enum membership, the id/area/filename agreement, and the
label registry, and rejects unknown keys. Exit 0 when every feature is valid, 1
with the violations named. Run from the repo root.
"""
import glob
import json
import pathlib
import re
import sys

import metafm

SCHEMA = json.loads(
    pathlib.Path("10-functional/features/_meta/feature.schema.json").read_text(encoding="utf-8")
)
PROPS = SCHEMA["properties"]
REQUIRED = SCHEMA["required"]
LABELS = set(PROPS["labels"]["items"]["enum"])
ENUM_KEYS = ("kind", "area", "audience", "status", "tracks", "priority")
ID_RE = re.compile(r"^[A-L]\d+$")


def _enum(name):
    return set(PROPS[name]["enum"])


def _keys(fm, path):
    out = [f"{path}: missing required key '{k}'" for k in REQUIRED if k not in fm]
    out += [f"{path}: unknown key '{k}'" for k in fm if k not in PROPS]
    return out


def _enums(fm, path):
    return [
        f"{path}: {k} = '{fm[k]}' is not an allowed value"
        for k in ENUM_KEYS
        if k in fm and fm[k] not in _enum(k)
    ]


def _identity(fm, path):
    fid = fm.get("id", "")
    stem = pathlib.Path(path).stem
    out = []
    if fid and not ID_RE.match(fid):
        out.append(f"{path}: id '{fid}' is malformed")
    if fid and "area" in fm and fid[:1] != fm["area"]:
        out.append(f"{path}: id '{fid}' does not match area '{fm['area']}'")
    if fid and not stem.lower().startswith(fid.lower() + "-"):
        out.append(f"{path}: id '{fid}' does not match filename '{stem}'")
    return out


def _lists(fm, path):
    out = [f"{path}: label '{v}' is not in the registry" for v in fm.get("labels", []) if v not in LABELS]
    for key in ("requires", "relates"):
        out += [
            f"{path}: {key} entry '{v}' is malformed"
            for v in fm.get(key, [])
            if not ID_RE.match(v)
        ]
    # `depends` conflated "cannot be built without" with "worth reading", which is
    # how features came to be scheduled before the things they need. Split, so the
    # first can be enforced and the second left alone.
    if "depends" in fm:
        out.append(f"{path}: `depends` is retired — use `requires` and `relates`")
    return out


def problems_for(path):
    fm = metafm.load(path)
    if fm is None:
        return [f"{path}: no frontmatter block"]
    return _keys(fm, path) + _enums(fm, path) + _identity(fm, path) + _lists(fm, path)


def main():
    files = sorted(glob.glob("10-functional/features/[a-l]-*/*.md"))
    problems = [p for path in files for p in problems_for(path)]
    if problems:
        print("frontmatter: problems found:")
        for line in problems:
            print("  " + line)
        return 1
    print(f"frontmatter: {len(files)} feature docs valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
