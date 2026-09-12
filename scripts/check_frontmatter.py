#!/usr/bin/env python3
"""Validate feature-doc frontmatter against feature.schema.json.

Checks the required keys, enum membership, the id/area/filename agreement, the
label registry, and the coupling between `maturity` and `shipped`, and rejects
unknown keys. Exit 0 when every feature is valid, 1 with the violations named.
Run from the repo root.
"""
import glob
import pathlib
import re
import sys

import catalogue
import metafm
from patterns import VERSION

SCHEMA = catalogue.schema()
PROPS = SCHEMA["properties"]
REQUIRED = SCHEMA["required"]
LABELS = set(PROPS["labels"]["items"]["enum"])
ENUM_KEYS = ("kind", "area", "audience", "status", "maturity", "priority")
# The shape of an id has one home, the schema, and is compiled from it rather
# than written again here. The copy this replaces was the same pattern by hand,
# and a check reading its own spelling of what the schema says is a check that
# can go on passing after the schema changes.
ID_RE = re.compile(PROPS["id"]["pattern"])


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


def _shipped(fm, path):
    """`shipped` names the version that shipped it, and only a shipped feature has one.

    The two fields answer one question between them, so a version on a feature
    nobody has built is not a smaller mistake than a missing one — it is a claim
    the board would render as fact. `status` is deliberately not consulted here:
    it describes the specification, and a feature can be `accepted` and unbuilt.
    """
    out = []
    version = fm.get("shipped")
    if version is None:
        return out
    if fm.get("maturity") != "shipped":
        out.append(f"{path}: shipped = '{version}' on a feature whose maturity is "
                   f"'{fm.get('maturity')}'")
    if not VERSION.match(version):
        out.append(f"{path}: shipped = '{version}' is not a version")
    return out


def problems_for(path):
    fm = metafm.load(path)
    if fm is None:
        return [f"{path}: no frontmatter block"]
    return (
        _keys(fm, path)
        + _enums(fm, path)
        + _identity(fm, path)
        + _lists(fm, path)
        + _shipped(fm, path)
    )


def main():
    files = sorted(glob.glob(catalogue.FEATURE_DOCS))
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
